"""
Backtest confluence filter kita ke data historis MEXC — biar validasi strategi gak perlu
nunggu jam/hari demi jam buat ngumpulin sampel real-time.

Muter ulang logic yang SAMA PERSIS kayak pump_scanner.py (_compute_stats, _is_confirmed,
calc_setup, risk_category — di-import langsung, bukan ditulis ulang, biar gak ada risiko
out-of-sync kayak bug retrace_frac 19 Juli).

Keterbatasan jujur:
- Symbol universe = top N koin paling likuid yang ada di Binance Futures (bukan scan SEMUA
  pair kayak live, biar gak kelamaan & gak kena rate limit).
- funding_rate & orderbook_ratio GAK ADA versi historisnya (MEXC gak nyimpen), jadi kosong
  di backtest — itu emang cuma sinyal bonus di live, gak nge-gate alert.
- Data 1 menit MEXC cuma disimpen ~30 hari ke belakang.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(__file__))
from pump_scanner import (  # noqa: E402
    BASE, WINDOW_MINUTES, PUMP_THRESHOLD_PCT, MAX_PUMP_PCT, COOLDOWN_MINUTES, EXPIRE_HOURS,
    MIN_QUOTE_VOLUME, _LEVERAGED_RE, _compute_stats, _is_confirmed, calc_setup,
    risk_category, get_binance_futures,
)

BACKTEST_DAYS = float(os.environ.get("BACKTEST_DAYS", "7"))
SYMBOL_COUNT = int(os.environ.get("SYMBOL_COUNT", "40"))
STEP_MINUTES = 1  # cek TIAP menit (bukan 2, kayak live) — data udah di-fetch semua, gak ada
# ongkos API call tambahan buat evaluasi tiap menit di lokal. PENTING: dites 19 Juli, kondisi
# confluence kadang cuma "valid" persis 1 menit doang (confirmed di menit X, false lagi di X+1)
# — kalau step 2 menit, ketauan sering KELEWAT gara-gara parity kebetulan gak pas nyentuh menit
# itu. Ini juga nunjukin cron live 2-menitan punya risiko sama (miss sinyal sekejap) — alasan
# lain buat akhirnya pindah ke scan kontinu (WebSocket/VPS).
_STABLECOINS = {"USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "DAIUSDT", "USDPUSDT", "USTUSDT", "EURUSDT"}


def get_symbol_universe(n, futures_symbols):
    """Top-N koin paling likuid (24h volume) yang ada di Binance Futures — buat backtest,
    bukan scan semua ratusan pair kayak live (biar gak kelamaan fetch data historisnya)."""
    r = requests.get(f"{BASE}/api/v3/ticker/24hr", timeout=20)
    r.raise_for_status()
    out = []
    for t in r.json():
        sym = t.get("symbol", "")
        if not sym.endswith("USDT") or _LEVERAGED_RE.search(sym) or sym in _STABLECOINS:
            continue
        if futures_symbols is not None and sym not in futures_symbols:
            continue
        try:
            quote_vol = float(t["quoteVolume"])
        except (KeyError, TypeError, ValueError):
            continue
        if quote_vol < MIN_QUOTE_VOLUME:
            continue
        out.append((sym, quote_vol))
    out.sort(key=lambda x: -x[1])
    return [s for s, _ in out[:n]]


def fetch_full_klines(symbol, start_ms, end_ms):
    """Paginate /klines (maks 500/request) buat nutupin rentang start_ms..end_ms."""
    all_kl = []
    cursor = start_ms
    step_ms = 500 * 60 * 1000
    while cursor < end_ms:
        chunk_end = min(cursor + step_ms, end_ms)
        try:
            r = requests.get(
                f"{BASE}/api/v3/klines",
                params={"symbol": symbol, "interval": "1m", "startTime": cursor, "endTime": chunk_end, "limit": 500},
                timeout=15,
            )
            r.raise_for_status()
            chunk = r.json()
        except Exception as e:
            print(f"  warn: fetch {symbol} gagal ({e})")
            break
        if not chunk:
            cursor = chunk_end + 1
            continue
        all_kl.extend(chunk)
        last_close = chunk[-1][6]
        if last_close <= cursor:
            break
        cursor = last_close + 1
        time.sleep(0.1)
    return all_kl


def _resolve_outcome_backtest(sl, tp1, tp2, tp3, future_klines, expire_hours=EXPIRE_HOURS):
    """Versi backtest _resolve_outcome — data udah ke-load semua di memori, gak fetch API lagi.
    Sama logic-nya: SL dicek duluan tiap candle (konservatif), TP paling dalem yang kena dicatet."""
    if not future_klines:
        return None, None
    start_ms = future_klines[0][0]
    expire_ms = start_ms + expire_hours * 3600 * 1000
    for c in future_klines:
        if c[0] > expire_ms:
            return "expired", c[0]
        high, low = float(c[2]), float(c[3])
        if high >= sl:
            return "sl_hit", c[0]
        if low <= tp3:
            return "tp3_hit", c[0]
        if low <= tp2:
            return "tp2_hit", c[0]
        if low <= tp1:
            return "tp1_hit", c[0]
    return "expired", future_klines[-1][0]


def _btc_pct_map(btc_klines):
    """Precompute pct (open->close per window WINDOW_MINUTES) BTC di TIAP titik waktu,
    di-lookup pas simulasi tiap simbol biar gak ngitung ulang tiap kali."""
    m = {}
    n = len(btc_klines)
    for i in range(WINDOW_MINUTES, n):
        window = btc_klines[i - WINDOW_MINUTES: i + 1]
        open_p = float(window[0][1])
        last_p = float(window[-1][4])
        if open_p > 0:
            m[btc_klines[i][0]] = (last_p - open_p) / open_p * 100
    return m


def simulate_symbol(symbol, klines, btc_pct_map):
    """Muter waktu di kline symbol ini, tiap STEP_MINUTES, jalanin logic confluence yang SAMA
    kayak live. Return list of dict hasil tiap alert yang kejadian."""
    results = []
    n = len(klines)
    last_alert_ms = None
    i = WINDOW_MINUTES
    while i < n:
        window = klines[i - WINDOW_MINUTES: i + 1]
        stats = _compute_stats(window)
        i += STEP_MINUTES
        if stats is None:
            continue
        if not (PUMP_THRESHOLD_PCT <= stats["peak_pct"] <= MAX_PUMP_PCT):
            continue
        btc_pct = btc_pct_map.get(window[-1][0])
        if not _is_confirmed(stats, btc_pct):
            continue
        ts = window[-1][0]
        if last_alert_ms is not None and (ts - last_alert_ms) / 60000 < COOLDOWN_MINUTES:
            continue
        setup = calc_setup(stats["swing_high"], stats["swing_low"])
        future = [c for c in klines if c[0] > ts]
        outcome, outcome_ts = _resolve_outcome_backtest(setup["sl"], setup["tp1"], setup["tp2"], setup["tp3"], future)
        last_alert_ms = ts
        results.append({
            "symbol": symbol,
            "time": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(timespec="seconds"),
            "pct": round(stats["peak_pct"], 2),
            "price": stats["price"],
            "risk": risk_category(0, stats["peak_pct"]),  # quote_volume gak relevan di sini (udah difilter di universe)
            "rsi": stats["rsi"],
            "vol_ratio": stats["vol_ratio"],
            "divergence": stats["divergence"],
            "outcome": outcome,
            "minutes_to_resolve": round((outcome_ts - ts) / 60000, 1) if outcome_ts else None,
            **setup,
        })
    return results


def main():
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - int(BACKTEST_DAYS * 86400 * 1000)

    print(f"Backtest {BACKTEST_DAYS} hari terakhir, {SYMBOL_COUNT} koin paling likuid di Binance Futures...")
    futures_symbols = get_binance_futures()
    symbols = get_symbol_universe(SYMBOL_COUNT, set(futures_symbols) if futures_symbols else None)
    print(f"Universe: {len(symbols)} coin — {symbols}")

    print("Fetch data BTC (referensi korelasi)...")
    btc_klines = fetch_full_klines("BTCUSDT", start_ms, now_ms)
    btc_pct_map = _btc_pct_map(btc_klines)
    print(f"  {len(btc_klines)} candle BTC.")

    all_results = []
    for idx, sym in enumerate(symbols):
        print(f"[{idx+1}/{len(symbols)}] {sym}...", end=" ", flush=True)
        kl = fetch_full_klines(sym, start_ms, now_ms)
        if len(kl) < WINDOW_MINUTES + 1:
            print("data kurang, skip.")
            continue
        res = simulate_symbol(sym, kl, btc_pct_map)
        print(f"{len(res)} alert.")
        all_results.extend(res)

    wins = sum(1 for r in all_results if r["outcome"] and r["outcome"].startswith("tp"))
    losses = sum(1 for r in all_results if r["outcome"] == "sl_hit")
    expired = sum(1 for r in all_results if r["outcome"] == "expired")
    resolved = wins + losses

    print()
    print("=" * 50)
    print(f"Total alert: {len(all_results)}")
    print(f"Menang (TP1/2/3): {wins}")
    print(f"Kalah (SL): {losses}")
    print(f"Expired (gak resolve dalam {EXPIRE_HOURS}h): {expired}")
    if resolved:
        print(f"Win rate: {wins/resolved*100:.1f}%")
    print("=" * 50)

    out_path = os.path.join(os.path.dirname(__file__), "backtest_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "backtest_days": BACKTEST_DAYS,
            "symbol_count": len(symbols),
            "symbols": symbols,
            "summary": {"total": len(all_results), "wins": wins, "losses": losses, "expired": expired,
                        "win_rate_pct": round(wins/resolved*100, 1) if resolved else None},
            "alerts": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"Detail tersimpan di {out_path}")


if __name__ == "__main__":
    main()
