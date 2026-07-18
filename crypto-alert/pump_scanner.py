"""
Crypto pump scanner — deteksi pair USDT di MEXC yang naik >= PUMP_THRESHOLD_PCT
dalam WINDOW_MINUTES terakhir, lalu kirim alert ke Telegram (lengkap sama entry,
SL, TP1-3, kategori risiko, korelasi BTC, tren volume). 100% gratis (no API key).

Harga/kline dari MEXC (Binance ke-block 451 dari lokasi ini, termasuk banyak
infra cloud kayak GitHub Actions) — tapi filter "bisa di-short apa enggak" &
funding rate dari BINANCE FUTURES ASLI (via CoinGecko derivatives, gak
ke-block) — soalnya user tradingnya di Binance, bukan MEXC, dan listing MEXC
jauh lebih permisif (banyak micin coin yang gak ada di Binance). Lihat
crypto-alert/README.md.

Cara kerja (2 tahap biar hemat API call):
  1. Satu bulk call /ticker/24hr MEXC (semua pair) → shortlist coin yang
     24h-nya udah lumayan naik (>= threshold/2), likuid, DAN beneran ada
     kontrak perpetual-nya di Binance Futures.
  2. Buat tiap shortlist, ambil kline 1 menit → hitung persis kenaikan
     trailing WINDOW_MINUTES, filter >= threshold beneran.

Alert baru dikirim kalau udah ada TANDA REVERSAL (candle terakhir merah +
udah retrace >= CONFIRM_RETRACE_PCT dari swing high) — bukan langsung pas
nyentuh threshold, biar entry-nya lebih deket ke titik balik beneran,
bukan di tengah pump yang masih ngegas.

Tiap run juga nge-track outcome alert LAMA (kena SL atau nyampe TP berapa)
pake kline history sejak alert dikirim → data win-rate riil, bukan tebakan.

SL/TP BUKAN Smart Money Concept (SMC) beneran — SMC (order block, liquidity
sweep, fair value gap, multi-timeframe structure) butuh baca chart visual,
susah diotomatisasi presisi. Ini pendekatan lebih sederhana & terukur:
swing high/low dari window pump + Fibonacci retracement.
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://api.mexc.com"  # sumber harga/kline (Binance ke-block 451 dari lokasi ini)
COINGECKO = "https://api.coingecko.com/api/v3"  # sumber listing + funding rate Binance Futures ASLI (gak ke-block)
HERE = Path(__file__).parent
HISTORY_PATH = HERE / "history.json"

PUMP_THRESHOLD_PCT = float(os.environ.get("PUMP_THRESHOLD_PCT", "10"))
WINDOW_MINUTES = int(os.environ.get("WINDOW_MINUTES", "30"))  # rentang waktu deteksi pump
SHORTLIST_PCT = PUMP_THRESHOLD_PCT / 2  # prefilter 24h buat batesin jumlah kline call
MIN_QUOTE_VOLUME = float(os.environ.get("MIN_QUOTE_VOLUME", "200000"))  # volume 24h min (USDT) — filter coin gak likuid
COOLDOWN_MINUTES = float(os.environ.get("COOLDOWN_MINUTES", "180"))  # jeda sebelum simbol yg sama boleh alert lagi
MAX_SHORTLIST = 30  # cap jumlah kline call per run — dijaga kecil biar durasi run stabil < 1 menit (scan tiap 2 menit)
SL_BUFFER_PCT = 1.0  # buffer SL di atas swing high (%)
EXPIRE_HOURS = float(os.environ.get("EXPIRE_HOURS", "48"))  # alert lama yang blm SL/TP dianggap expired
CONFIRM_RETRACE_PCT = float(os.environ.get("CONFIRM_RETRACE_PCT", "1.0"))  # min retrace dari swing high sebelum alert (konfirmasi reversal)
MAX_TRACK_PER_RUN = 15  # cap jumlah alert lama yang di-cek outcome-nya per run (biar durasi run stabil)
REQUEST_SLEEP = 0.08  # jeda antar API call (turun dari 0.15 biar run lebih cepet)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_LEVERAGED_RE = re.compile(r"(UP|DOWN|BULL|BEAR|[0-9]L|[0-9]S)USDT$")


def load_history():
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text())
    return {"last_alert": {}, "alerts": []}


def save_history(history):
    history["alerts"] = history["alerts"][-500:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def get_binance_futures():
    """Daftar kontrak perpetual USDT-M Binance Futures ASLI + funding rate-nya, 1 bulk call
    lewat CoinGecko (Binance API sendiri ke-block 451 dari lokasi ini). Ini yang dipake buat
    filter "coin ini bisa di-short di Binance Futures apa enggak" — bukan MEXC — soalnya user
    tradingnya di Binance, dan listing MEXC jauh lebih permisif/beda dari Binance.
    Return dict {symbol: funding_rate_pct} atau None kalau gagal total."""
    try:
        r = requests.get(
            f"{COINGECKO}/derivatives/exchanges/binance_futures",
            params={"include_tickers": "all"},
            timeout=20,
        )
        r.raise_for_status()
        tickers = r.json().get("tickers", [])
        out = {}
        for t in tickers:
            if t.get("contract_type") == "perpetual" and t.get("target") == "USDT":
                out[t["symbol"]] = t.get("funding_rate")
        return out if out else None
    except Exception as e:
        print(f"warn: ambil daftar Binance Futures gagal ({e}), skip filter futures")
        return None


def get_shortlist(futures_symbols):
    """Bulk 24hr ticker (1 call, semua pair) → shortlist USDT pair likuid, lagi naik,
    DAN ada di Binance Futures (biar cuma alert coin yang beneran bisa di-short di sana)."""
    r = requests.get(f"{BASE}/api/v3/ticker/24hr", timeout=20)
    r.raise_for_status()
    out = []
    for t in r.json():
        sym = t.get("symbol", "")
        if not sym.endswith("USDT") or _LEVERAGED_RE.search(sym):
            continue
        if futures_symbols is not None and sym not in futures_symbols:
            continue
        try:
            quote_vol = float(t["quoteVolume"])
            pct24 = float(t["priceChangePercent"]) * 100  # MEXC: fraksi (0.0238 = 2.38%)
        except (KeyError, TypeError, ValueError):
            continue
        if quote_vol < MIN_QUOTE_VOLUME or pct24 < SHORTLIST_PCT:
            continue
        out.append({"symbol": sym, "pct24": pct24, "quote_volume": quote_vol})
    out.sort(key=lambda x: -x["pct24"])
    return out[:MAX_SHORTLIST]


def _funding_hint(fr):
    if fr is None:
        return None
    if fr >= 0.05:
        return "🔥 long crowded — sinyal short lebih valid"
    if fr <= -0.02:
        return "⚠️ short crowded — hati-hati short squeeze"
    return "netral"


def get_window_stats(symbol):
    """Kline 1 menit x WINDOW_MINUTES → pct kenaikan trailing beneran, swing high/low
    (buat SL/TP), + rasio volume paruh kedua vs paruh pertama (buat deteksi exhaustion)."""
    r = requests.get(
        f"{BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": "1m", "limit": WINDOW_MINUTES + 1},
        timeout=15,
    )
    r.raise_for_status()
    kl = r.json()
    if len(kl) < max(5, int(WINDOW_MINUTES * 0.9)):  # data kurang (coin baru listing dll), skip
        return None
    open_p = float(kl[0][1])
    last_p = float(kl[-1][4])
    if open_p <= 0:
        return None
    pct = (last_p - open_p) / open_p * 100
    swing_high = max(float(c[2]) for c in kl)
    swing_low = min(float(c[3]) for c in kl)

    mid = len(kl) // 2
    vols = [float(c[5]) for c in kl]
    vol_first = sum(vols[:mid]) / max(1, mid)
    vol_second = sum(vols[mid:]) / max(1, len(vols) - mid)
    vol_ratio = (vol_second / vol_first) if vol_first > 0 else None

    last_open, last_close = float(kl[-1][1]), float(kl[-1][4])
    last_red = last_close < last_open
    retrace_pct = (swing_high - last_p) / swing_high * 100 if swing_high > 0 else 0

    return {
        "pct": pct, "price": last_p, "swing_high": swing_high, "swing_low": swing_low,
        "vol_ratio": vol_ratio, "last_red": last_red, "retrace_pct": retrace_pct,
    }


def _volume_hint(ratio):
    if ratio is None:
        return None
    if ratio < 0.6:
        return "📉 volume melemah — momentum exhaustion, sinyal short lebih valid"
    if ratio > 1.3:
        return "📈 volume masih naik — momentum masih kuat, hati-hati lanjut naik"
    return "netral"


def get_btc_pct():
    try:
        stats = get_window_stats("BTCUSDT")
        return None if stats is None else stats["pct"]
    except Exception as e:
        print(f"warn: cek BTC gagal ({e})")
        return None


def _btc_hint(btc_pct):
    if btc_pct is None:
        return None
    if btc_pct >= 1.5:
        return "🌊 market-wide (BTC ikut naik, kurang isolated)"
    return "🎯 isolated (BTC datar/turun, sinyal lebih kuat)"


def _is_confirmed(stats, btc_pct):
    """Confluence semua sinyal reversal — biar alert lebih SELEKTIF (jarang tapi kualitas
    lebih tinggi), bukan langsung nembak begitu pct nyentuh threshold. Tetep BUKAN jaminan
    pasti — cuma nurunin peluang alert di tengah pump yang masih ngegas."""
    if not (stats["last_red"] and stats["retrace_pct"] >= CONFIRM_RETRACE_PCT):
        return False  # belum ada tanda reversal
    if stats["vol_ratio"] is None or stats["vol_ratio"] >= 0.6:
        return False  # volume belum keliatan melemah
    if btc_pct is not None and btc_pct >= 1.5:
        return False  # market-wide, bukan isolated
    return True


def calc_setup(swing_high, swing_low):
    """SL + TP1-3. BUKAN SMC — cuma swing high/low + Fibonacci retracement (38.2/61.8/100%)."""
    sl = swing_high * (1 + SL_BUFFER_PCT / 100)
    rng = swing_high - swing_low
    return {
        "sl": sl,
        "tp1": swing_high - rng * 0.382,
        "tp2": swing_high - rng * 0.618,
        "tp3": swing_low,
    }


def risk_category(quote_volume, pct):
    if quote_volume < 500_000 or pct >= 20:
        return "🔴 HIGH RISK (likuiditas tipis / pump ekstrem — rawan slippage & manipulasi)"
    if quote_volume < 3_000_000:
        return "🟡 MEDIUM RISK"
    return "🟠 MODERATE (tetep leverage — gak ada yang beneran 'aman')"


def _fmt_price(p):
    s = f"{p:.8f}" if p < 1 else f"{p:,.4f}"
    return s.rstrip("0").rstrip(".")


def format_alert(p):
    url = f"https://www.binance.com/en/futures/{p['symbol']}"
    lines = [
        "🚀 <b>PUMP ALERT</b>",
        f"<b>{p['symbol']}</b>  +{p['pct']}% ({WINDOW_MINUTES} menit terakhir)",
        f"Risiko: {p['risk']}",
        f"Konfirmasi: udah retrace {p['retrace_pct']:.2f}% dari puncak + candle terakhir merah",
        "",
        f"Entry (short): {_fmt_price(p['price'])}",
        f"SL: {_fmt_price(p['sl'])}",
        f"TP1 (38.2%): {_fmt_price(p['tp1'])}",
        f"TP2 (61.8%): {_fmt_price(p['tp2'])}",
        f"TP3 (100%): {_fmt_price(p['tp3'])}",
        "",
        f"Volume 24h: ${p['quote_volume']:,.0f}",
    ]
    fr = p.get("funding_rate")
    lines.append(f"Funding rate: {fr:+.4f}% ({_funding_hint(fr)})" if fr is not None else "Funding rate: gak ada / gagal ambil")
    vr = p.get("vol_ratio")
    lines.append(f"Volume trend: {_volume_hint(vr)}" if vr is not None else "Volume trend: gak keitung")
    bp = p.get("btc_pct")
    lines.append(f"BTC {WINDOW_MINUTES}m: {bp:+.2f}% — {_btc_hint(bp)}" if bp is not None else "BTC: gagal ambil")
    lines.append(f"🔗 {url}")
    lines.append("<i>SL/TP = swing high/low + Fibonacci, bukan SMC. Bukan saran finansial.</i>")
    return "\n".join(lines)


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram belum di-set (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID kosong), skip kirim.")
        return
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15,
    )
    if not r.ok:
        print(f"warn: gagal kirim Telegram: {r.status_code} {r.text}")


def _resolve_outcome(alert, start_ms):
    """Cek kline sejak alert dikirim: kena SL duluan atau nyampe TP berapa (short trade).
    Dalam 1 candle, SL dicek duluan (asumsi konservatif, gak overstate win-rate)."""
    try:
        r = requests.get(
            f"{BASE}/api/v3/klines",
            params={"symbol": alert["symbol"], "interval": "5m", "startTime": start_ms, "limit": 600},
            timeout=15,
        )
        r.raise_for_status()
        kl = r.json()
    except Exception as e:
        print(f"warn: track {alert['symbol']} gagal ({e})")
        return None
    # MEXC kadang balikin beberapa candle SEBELUM start_ms walau udah dikasih startTime —
    # filter manual, soalnya TP3 = swing low sebelum pump, candle lama pasti "kesentuh" TP3.
    kl = [c for c in kl if c[0] >= start_ms]
    for c in kl:
        high, low = float(c[2]), float(c[3])
        if high >= alert["sl"]:
            return "sl_hit"
        if low <= alert["tp3"]:
            return "tp3_hit"
        if low <= alert["tp2"]:
            return "tp2_hit"
        if low <= alert["tp1"]:
            return "tp1_hit"
    return None


def track_outcomes(history, now):
    """Update outcome alert lama yang belum resolved. Dibatesin MAX_TRACK_PER_RUN per run
    (yang paling lama nunggu duluan) biar durasi run stabil — sisanya kekejar run berikutnya
    (2 menit lagi, bukan nunggu lama). Return True kalau ada perubahan."""
    pending = [
        a for a in history["alerts"]
        if not a.get("outcome") and "sl" in a
        and (now - datetime.fromisoformat(a["time"])).total_seconds() / 3600 >= 0.1
    ]
    pending.sort(key=lambda a: a["time"])  # paling lama nunggu duluan
    changed = False
    for a in pending[:MAX_TRACK_PER_RUN]:
        alert_time = datetime.fromisoformat(a["time"])
        age_hours = (now - alert_time).total_seconds() / 3600
        outcome = _resolve_outcome(a, int(alert_time.timestamp() * 1000))
        time.sleep(REQUEST_SLEEP)
        if outcome:
            a["outcome"] = outcome
            a["outcome_time"] = now.isoformat(timespec="seconds")
            changed = True
        elif age_hours >= EXPIRE_HOURS:
            a["outcome"] = "expired"
            a["outcome_time"] = now.isoformat(timespec="seconds")
            changed = True
    return changed


def main():
    history = load_history()
    now = datetime.now(timezone.utc)

    outcomes_changed = track_outcomes(history, now)

    binance_futures = get_binance_futures()  # {symbol: funding_rate}, None kalau CoinGecko gagal
    shortlist = get_shortlist(set(binance_futures) if binance_futures else None)
    print(f"Shortlist {len(shortlist)} coin (24h >= {SHORTLIST_PCT:.1f}% & likuid & ada di Binance Futures) dari MEXC.")

    btc_pct = get_btc_pct()

    pumps = []
    for s in shortlist:
        try:
            stats = get_window_stats(s["symbol"])
        except Exception as e:
            print(f"warn: kline {s['symbol']} gagal ({e}), skip")
            continue
        time.sleep(REQUEST_SLEEP)
        if stats is None:
            continue
        if stats["pct"] >= PUMP_THRESHOLD_PCT:
            if not _is_confirmed(stats, btc_pct):
                continue  # belum confluence semua sinyal, tunggu run berikutnya
            setup = calc_setup(stats["swing_high"], stats["swing_low"])
            pumps.append({
                "symbol": s["symbol"],
                "pct": round(stats["pct"], 2),
                "price": stats["price"],
                "quote_volume": s["quote_volume"],
                "risk": risk_category(s["quote_volume"], stats["pct"]),
                "vol_ratio": stats["vol_ratio"],
                "retrace_pct": stats["retrace_pct"],
                "btc_pct": btc_pct,
                **setup,
            })

    pumps.sort(key=lambda p: -p["pct"])
    print(f"Ketemu {len(pumps)} pump >= {PUMP_THRESHOLD_PCT}% beneran dalam {WINDOW_MINUTES} menit (sebelum filter cooldown).")

    new_alerts = []
    for p in pumps:
        last = history["last_alert"].get(p["symbol"])
        if last:
            elapsed_min = (now - datetime.fromisoformat(last)).total_seconds() / 60
            if elapsed_min < COOLDOWN_MINUTES:
                continue
        p["funding_rate"] = binance_futures.get(p["symbol"]) if binance_futures else None
        new_alerts.append(p)
        history["last_alert"][p["symbol"]] = now.isoformat(timespec="seconds")
        history["alerts"].append({**p, "time": now.isoformat(timespec="seconds"), "outcome": None})

    for p in new_alerts:
        print(f"ALERT: {p['symbol']} +{p['pct']}%")
        send_telegram(format_alert(p))

    if new_alerts or outcomes_changed:
        save_history(history)
    else:
        print("Gak ada alert baru & gak ada outcome yang ke-update.")


if __name__ == "__main__":
    main()
