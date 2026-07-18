"""
Crypto pump scanner — deteksi pair USDT di MEXC yang naik >= PUMP_THRESHOLD_PCT
dalam WINDOW_MINUTES terakhir, lalu kirim alert ke Telegram (lengkap sama entry,
SL, TP1-3, kategori risiko). 100% gratis (no API key).

Pakai MEXC (bukan Binance) karena Binance nge-block IP dari lokasi yang
"restricted" (termasuk banyak infra cloud kayak GitHub Actions) — lihat
crypto-alert/README.md.

Cara kerja (2 tahap biar hemat API call):
  1. Satu bulk call /ticker/24hr (semua pair) → shortlist coin yang 24h-nya
     udah lumayan naik (>= threshold/2) + likuid.
  2. Buat tiap shortlist, ambil kline 1 menit → hitung persis kenaikan
     trailing WINDOW_MINUTES, filter >= threshold beneran.

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

BASE = "https://api.mexc.com"
BASE_FUT = "https://contract.mexc.com"
HERE = Path(__file__).parent
HISTORY_PATH = HERE / "history.json"

PUMP_THRESHOLD_PCT = float(os.environ.get("PUMP_THRESHOLD_PCT", "10"))
WINDOW_MINUTES = int(os.environ.get("WINDOW_MINUTES", "30"))  # rentang waktu deteksi pump
SHORTLIST_PCT = PUMP_THRESHOLD_PCT / 2  # prefilter 24h buat batesin jumlah kline call
MIN_QUOTE_VOLUME = float(os.environ.get("MIN_QUOTE_VOLUME", "200000"))  # volume 24h min (USDT) — filter coin gak likuid
COOLDOWN_MINUTES = float(os.environ.get("COOLDOWN_MINUTES", "180"))  # jeda sebelum simbol yg sama boleh alert lagi
MAX_SHORTLIST = 60  # cap jumlah kline call per run, jaga-jaga market lagi liar
SL_BUFFER_PCT = 1.0  # buffer SL di atas swing high (%)

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


def get_funding_rate(symbol):
    """Funding rate futures (proxy MEXC — Binance Futures ikut ke-block 451 di lokasi ini,
    tapi funding rate biasanya deket-deketan antar exchange buat pair yang sama)."""
    if not symbol.endswith("USDT"):
        return None
    fut_symbol = symbol[: -len("USDT")] + "_USDT"
    try:
        r = requests.get(f"{BASE_FUT}/api/v1/contract/funding_rate/{fut_symbol}", timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            return None
        return float(data["data"]["fundingRate"]) * 100  # jadi persen
    except Exception as e:
        print(f"warn: funding rate {symbol} gagal ({e}), skip")
        return None


def _funding_hint(fr):
    if fr is None:
        return None
    if fr >= 0.05:
        return "🔥 long crowded — sinyal short lebih valid"
    if fr <= -0.02:
        return "⚠️ short crowded — hati-hati short squeeze"
    return "netral"


def get_window_stats(symbol):
    """Kline 1 menit x WINDOW_MINUTES → pct kenaikan trailing beneran + swing high/low
    (buat hitung SL/TP)."""
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
    return {"pct": pct, "price": last_p, "swing_high": swing_high, "swing_low": swing_low}


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
    url = f"https://www.mexc.com/exchange/{p['symbol'].replace('USDT', '_USDT')}"
    lines = [
        "🚀 <b>PUMP ALERT</b>",
        f"<b>{p['symbol']}</b>  +{p['pct']}% ({WINDOW_MINUTES} menit terakhir)",
        f"Risiko: {p['risk']}",
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
    if fr is not None:
        hint = _funding_hint(fr)
        lines.append(f"Funding rate: {fr:+.4f}% ({hint})")
    else:
        lines.append("Funding rate: gak ada kontrak futures / gagal ambil")
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


def main():
    history = load_history()
    now = datetime.now(timezone.utc)

    shortlist = get_shortlist()
    print(f"Shortlist {len(shortlist)} coin (24h >= {SHORTLIST_PCT:.1f}% & likuid) dari MEXC.")

    pumps = []
    for s in shortlist:
        try:
            stats = get_window_stats(s["symbol"])
        except Exception as e:
            print(f"warn: kline {s['symbol']} gagal ({e}), skip")
            continue
        time.sleep(0.15)
        if stats is None:
            continue
        if stats["pct"] >= PUMP_THRESHOLD_PCT:
            setup = calc_setup(stats["swing_high"], stats["swing_low"])
            pumps.append({
                "symbol": s["symbol"],
                "pct": round(stats["pct"], 2),
                "price": stats["price"],
                "quote_volume": s["quote_volume"],
                "risk": risk_category(s["quote_volume"], stats["pct"]),
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
        p["funding_rate"] = get_funding_rate(p["symbol"])
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
