"""
Crypto pump scanner — deteksi pair USDT di MEXC yang naik >= PUMP_THRESHOLD_PCT
dalam 1 jam terakhir, lalu kirim alert ke Telegram. 100% gratis (no API key).

Pakai MEXC (bukan Binance) karena Binance nge-block IP dari lokasi yang
"restricted" (termasuk banyak infra cloud kayak GitHub Actions) — lihat
crypto-alert/README.md.

Cara kerja (2 tahap biar hemat API call):
  1. Satu bulk call /ticker/24hr (semua pair) → shortlist coin yang 24h-nya
     udah lumayan naik (>= threshold/2) + likuid.
  2. Buat tiap shortlist, ambil kline 1 menit (60 candle terakhir) → hitung
     persis kenaikan trailing 1 jam, filter >= threshold beneran.
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://api.mexc.com"
HERE = Path(__file__).parent
HISTORY_PATH = HERE / "history.json"

PUMP_THRESHOLD_PCT = float(os.environ.get("PUMP_THRESHOLD_PCT", "10"))
SHORTLIST_PCT = PUMP_THRESHOLD_PCT / 2  # prefilter 24h buat batesin jumlah kline call
MIN_QUOTE_VOLUME = float(os.environ.get("MIN_QUOTE_VOLUME", "200000"))  # volume 24h min (USDT) — filter coin gak likuid
COOLDOWN_MINUTES = float(os.environ.get("COOLDOWN_MINUTES", "180"))  # jeda sebelum simbol yg sama boleh alert lagi
MAX_SHORTLIST = 60  # cap jumlah kline call per run, jaga-jaga market lagi liar

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


def get_shortlist():
    """Bulk 24hr ticker (1 call, semua pair) → shortlist USDT pair likuid & lagi naik."""
    r = requests.get(f"{BASE}/api/v3/ticker/24hr", timeout=20)
    r.raise_for_status()
    out = []
    for t in r.json():
        sym = t.get("symbol", "")
        if not sym.endswith("USDT") or _LEVERAGED_RE.search(sym):
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


def get_1h_change(symbol):
    """Kline 1 menit x60 → pct kenaikan trailing 1 jam yang sebenernya."""
    r = requests.get(
        f"{BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": "1m", "limit": 61},
        timeout=15,
    )
    r.raise_for_status()
    kl = r.json()
    if len(kl) < 55:  # data kurang (coin baru listing dll), skip
        return None
    open_p = float(kl[0][1])
    last_p = float(kl[-1][4])
    if open_p <= 0:
        return None
    pct = (last_p - open_p) / open_p * 100
    return pct, last_p


def _fmt_price(p):
    s = f"{p:.8f}" if p < 1 else f"{p:,.4f}"
    return s.rstrip("0").rstrip(".")


def format_alert(p):
    url = f"https://www.mexc.com/exchange/{p['symbol'].replace('USDT', '_USDT')}"
    return (
        f"🚀 <b>PUMP ALERT</b>\n"
        f"<b>{p['symbol']}</b>  +{p['pct']}% (1 jam terakhir)\n"
        f"Harga: {_fmt_price(p['price'])}\n"
        f"Volume 24h: ${p['quote_volume']:,.0f}\n"
        f"🔗 {url}"
    )


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


def main():
    history = load_history()
    now = datetime.now(timezone.utc)

    shortlist = get_shortlist()
    print(f"Shortlist {len(shortlist)} coin (24h >= {SHORTLIST_PCT:.1f}% & likuid) dari MEXC.")

    pumps = []
    for s in shortlist:
        try:
            result = get_1h_change(s["symbol"])
        except Exception as e:
            print(f"warn: kline {s['symbol']} gagal ({e}), skip")
            continue
        time.sleep(0.15)
        if result is None:
            continue
        pct, last_p = result
        if pct >= PUMP_THRESHOLD_PCT:
            pumps.append({"symbol": s["symbol"], "pct": round(pct, 2), "price": last_p, "quote_volume": s["quote_volume"]})

    pumps.sort(key=lambda p: -p["pct"])
    print(f"Ketemu {len(pumps)} pump >= {PUMP_THRESHOLD_PCT}% beneran dalam 1 jam (sebelum filter cooldown).")

    new_alerts = []
    for p in pumps:
        last = history["last_alert"].get(p["symbol"])
        if last:
            elapsed_min = (now - datetime.fromisoformat(last)).total_seconds() / 60
            if elapsed_min < COOLDOWN_MINUTES:
                continue
        new_alerts.append(p)
        history["last_alert"][p["symbol"]] = now.isoformat(timespec="seconds")
        history["alerts"].append({**p, "time": now.isoformat(timespec="seconds")})

    if not new_alerts:
        print("Gak ada alert baru (kena cooldown atau emang gak ada pump).")
        return

    for p in new_alerts:
        print(f"ALERT: {p['symbol']} +{p['pct']}%")
        send_telegram(format_alert(p))

    save_history(history)


if __name__ == "__main__":
    main()
