"""
Live pump scanner — jalan LOKAL di laptop kamu, scan SEMUA ALTCOIN shortlist
tiap beberapa detik (jauh lebih cepet dari GitHub Actions yang tiap 2 menit).

Sekaligus jadi SUMBER DATA buat live_dashboard.html (chart + support/resistance):
tiap cycle nulis live_data.json + nge-serve folder ini di http://localhost:8899
— dashboard fetch dari situ, BUKAN dari MEXC langsung (MEXC nge-block request
langsung dari browser / gak ada header CORS, udah dicek 20 Juli).

Reuse SEMUA logic inti dari pump_scanner.py (_compute_stats, _is_confirmed,
calc_setup, dst) biar hasilnya SELALU konsisten sama sistem cloud. history.json
juga di-share (cooldown nyambung → gak dobel alert Telegram buat pump yang sama,
dan alert dari sini ikut muncul di dashboard publik/win-rate).

Jalanin:
    cd crypto-alert
    python3 live_monitor.py
    → buka http://localhost:8899/live_dashboard.html di browser

Stop: Ctrl+C

Env (opsional):
    TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID  → biar alert tetep ke Telegram juga
    LIVE_INTERVAL_SEC=10   # jeda antar scan penuh (detik)
    LIVE_PORT=8899         # port dashboard lokal
"""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(__file__))
from pump_scanner import (  # noqa: E402
    BASE, load_history, save_history, get_binance_futures, get_shortlist,
    _compute_stats, _is_confirmed, calc_setup, risk_category, confidence_label,
    get_orderbook_ratio, format_alert, send_telegram, track_outcomes,
    PUMP_THRESHOLD_PCT, MAX_PUMP_PCT, WINDOW_MINUTES, COOLDOWN_MINUTES, REQUEST_SLEEP,
)

HERE = Path(__file__).parent
LIVE_DATA_PATH = HERE / "live_data.json"
LIVE_INTERVAL_SEC = float(os.environ.get("LIVE_INTERVAL_SEC", "10"))
LIVE_PORT = int(os.environ.get("LIVE_PORT", "8899"))
CHART_CANDLES = 90  # candle 1m per koin buat chart (60-90 cukup buat liat struktur + S/R)
FUTURES_REFRESH_SEC = 600  # listing Binance Futures jarang berubah, refresh 10 menit sekali
OUTCOME_TRACK_EVERY = 15  # cek outcome alert lama tiap N cycle

C_RESET, C_GREEN, C_RED, C_YEL, C_CYAN, C_DIM = (
    "\033[0m", "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[2m",
)


def fetch_klines(symbol, limit):
    r = requests.get(
        f"{BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": "1m", "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def scan_once(history, binance_futures, cycle):
    now = datetime.now(timezone.utc)
    shortlist = get_shortlist(set(binance_futures) if binance_futures else None)

    try:
        btc_kl = fetch_klines("BTCUSDT", WINDOW_MINUTES + 1)
        btc_stats = _compute_stats(btc_kl)
        btc_pct = btc_stats["pct"] if btc_stats else None
    except Exception:
        btc_pct = None

    ts = now.strftime("%H:%M:%S")
    btc_txt = f"{btc_pct:+.2f}%" if btc_pct is not None else "?"
    print(f"{C_CYAN}[{ts}]{C_RESET} cycle #{cycle} — {len(shortlist)} koin dipantau — BTC(30m) {btc_txt}")

    coins = []       # semua shortlist (buat dashboard, termasuk yang belum masuk range pump)
    new_alerts = []
    for s in shortlist:
        try:
            kl = fetch_klines(s["symbol"], CHART_CANDLES)
        except Exception:
            continue
        time.sleep(REQUEST_SLEEP)
        stats = _compute_stats(kl[-(WINDOW_MINUTES + 1):])
        if stats is None:
            continue
        in_range = PUMP_THRESHOLD_PCT <= stats["peak_pct"] <= MAX_PUMP_PCT
        confirmed = in_range and _is_confirmed(stats, btc_pct)
        coins.append({
            "symbol": s["symbol"], "quote_volume": s["quote_volume"], "in_range": in_range,
            "confirmed": confirmed,
            "stats": {k: stats[k] for k in ("pct", "peak_pct", "price", "swing_high", "swing_low",
                                            "vol_ratio", "last_red", "retrace_frac", "rsi")},
            "candles": [[c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in kl],
        })

        if not confirmed:
            continue
        last = history["last_alert"].get(s["symbol"])
        if last:
            elapsed_min = (now - datetime.fromisoformat(last)).total_seconds() / 60
            if elapsed_min < COOLDOWN_MINUTES:
                continue
        setup = calc_setup(stats["swing_high"], stats["swing_low"])
        p = {
            "symbol": s["symbol"], "pct": round(stats["peak_pct"], 2), "price": stats["price"],
            "quote_volume": s["quote_volume"], "risk": risk_category(s["quote_volume"], stats["peak_pct"]),
            "confidence": confidence_label(stats["peak_pct"]), "vol_ratio": stats["vol_ratio"],
            "retrace_pct": stats["retrace_pct"], "wick_ratio": stats["wick_ratio"], "rsi": stats["rsi"],
            "divergence": stats["divergence"], "vol_spike": stats["vol_spike"], "btc_pct": btc_pct,
            **setup,
        }
        p["funding_rate"] = binance_futures.get(s["symbol"]) if binance_futures else None
        p["orderbook_ratio"] = get_orderbook_ratio(s["symbol"])
        time.sleep(REQUEST_SLEEP)
        new_alerts.append(p)
        history["last_alert"][s["symbol"]] = now.isoformat(timespec="seconds")
        history["alerts"].append({**p, "time": now.isoformat(timespec="seconds"), "outcome": None})

    in_range_coins = [c for c in coins if c["in_range"]]
    in_range_coins.sort(key=lambda c: -c["stats"]["peak_pct"])
    for c in in_range_coins[:10]:
        st = c["stats"]
        tag = f"{C_GREEN}✅ CONFIRMED{C_RESET}" if c["confirmed"] else f"{C_YEL}⏳ watching{C_RESET}"
        red = "🔴" if st["last_red"] else "🟢"
        rsi = f"{st['rsi']:.0f}" if st["rsi"] is not None else "-"
        vr = f"{st['vol_ratio']:.2f}x" if st["vol_ratio"] is not None else "-"
        print(f"  {c['symbol']:<14} +{st['peak_pct']:5.1f}%  RSI {rsi:<4} {red}  vol {vr:<6} {tag}")
    if not in_range_coins:
        print(f"  {C_DIM}(gak ada koin di range pump {PUMP_THRESHOLD_PCT}-{MAX_PUMP_PCT}% saat ini — dashboard tetep nampilin semua shortlist){C_RESET}")

    for p in new_alerts:
        print(f"{C_RED}{'=' * 72}{C_RESET}")
        print(f"{C_RED}🚀 ALERT BARU: {p['symbol']} +{p['pct']}% — kirim Telegram...{C_RESET}")
        print(f"{C_RED}{'=' * 72}{C_RESET}")
        send_telegram(format_alert(p))

    history["last_scan"] = {
        "time": now.isoformat(timespec="seconds"), "shortlist_count": len(shortlist),
        "confirmed_count": len(new_alerts), "symbols": [s["symbol"] for s in shortlist],
    }
    save_history(history)

    # urutan dashboard: yang in-range (paling gede duluan) dulu, baru sisanya by pct24 shortlist
    coins.sort(key=lambda c: (-c["in_range"], -c["stats"]["peak_pct"]))
    LIVE_DATA_PATH.write_text(json.dumps({
        "time": now.isoformat(timespec="seconds"),
        "btc_pct": btc_pct,
        "window_minutes": WINDOW_MINUTES,
        "threshold": PUMP_THRESHOLD_PCT, "max_pump": MAX_PUMP_PCT,
        "coins": coins,
        "new_alerts": [p["symbol"] for p in new_alerts],
    }))
    print(C_DIM + "-" * 72 + C_RESET)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # jangan spam terminal sama access log
        pass

    def end_headers(self):  # jangan cache live_data.json
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_server():
    handler = partial(_QuietHandler, directory=str(HERE))
    srv = ThreadingHTTPServer(("127.0.0.1", LIVE_PORT), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main():
    start_server()
    print(f"{C_CYAN}=== Live Altcoin Pump Scanner ==={C_RESET}")
    print(f"Scan tiap {LIVE_INTERVAL_SEC:.0f} detik. Ctrl+C buat stop.")
    print(f"📊 Dashboard chart: {C_GREEN}http://localhost:{LIVE_PORT}/live_dashboard.html{C_RESET}")
    print(C_DIM + "-" * 72 + C_RESET)
    history = load_history()
    binance_futures = get_binance_futures()
    cycle = 0
    last_futures_refresh = time.time()
    try:
        while True:
            cycle += 1
            if time.time() - last_futures_refresh > FUTURES_REFRESH_SEC:
                binance_futures = get_binance_futures()
                last_futures_refresh = time.time()
            try:
                scan_once(history, binance_futures, cycle)
                if cycle % OUTCOME_TRACK_EVERY == 0:
                    if track_outcomes(history, datetime.now(timezone.utc)):
                        save_history(history)
            except Exception as e:
                print(f"{C_RED}warn: cycle error ({e}){C_RESET}")
            time.sleep(LIVE_INTERVAL_SEC)
    except KeyboardInterrupt:
        print(f"\n{C_CYAN}Stop.{C_RESET}")


if __name__ == "__main__":
    main()
