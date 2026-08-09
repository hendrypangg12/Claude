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
  2. Buat tiap shortlist, ambil kline 1 menit → hitung PEAK_PCT (swing low
     ke swing high di dalam window, bukan cuma harga sekarang vs harga
     awal window — biar gak keburu ketutup pas harga udah retrace duluan
     buat konfirmasi), filter >= threshold beneran.

Alert baru dikirim kalau udah ada TANDA REVERSAL: candle terakhir merah +
udah retrace CONFIRM_MIN_RETRACE_FRAC..CONFIRM_MAX_RETRACE_FRAC dari RANGE
pump (bukan cuma minimal — dibatesin maksimal juga, biar gak alert pas
harga udah kadung anjlok jauh & entry jadi gak masuk akal).

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
POSITIONS_PATH = HERE / "positions.json"
WATCHLIST_PATH = HERE / "watchlist.json"

# PUMP_ALERT=off → alert pump 🚀 gak dikirim ke Telegram (tetep dicatat di history +
# dashboard + win-rate, jadi tinggal dinyalain lagi kapan aja tanpa kehilangan data).
# Dimatiin 26 Juli: owner mau fokus notif BTC dulu.
PUMP_ALERT_ON = os.environ.get("PUMP_ALERT", "on").lower() not in ("off", "false", "0")
SPIKE_WINDOW = int(os.environ.get("SPIKE_WINDOW", "5"))  # jumlah candle 1m buat ngukur "lonjakan"
# ZONA MATI: pump 10-12% dilewatin. Dari 79 alert live (18 Jul - 8 Agu): zona ini 22 trade,
# menang cuma 8 (36%), -5.75 R — satu-satunya zona yang RUGI. Yang bikin yakin bukan p-value
# (0.14, belum signifikan kalau data digabung) tapi UJI OUT-OF-SAMPLE: pola ini muncul di Juli
# (14 trade, 36%, -3.49 R) DAN berulang di Agustus (8 trade, 38%, -2.26 R) — dua periode
# terpisah, hasil nyaris sama. Plus untung-ruginya berat sebelah: skip zona yang ternyata
# netral nyaris gak ngerugiin, skip zona yang beneran jelek ngehemat banyak.
# Tanpa zona ini: edge naik dari +0.078 jadi +0.209 R/trade.
# Setel DEAD_ZONE_MIN=0 buat matiin filter ini.
DEAD_ZONE_MIN = float(os.environ.get("DEAD_ZONE_MIN", "10"))
DEAD_ZONE_MAX = float(os.environ.get("DEAD_ZONE_MAX", "12"))


def in_pump_range(peak_pct):
    """Satu-satunya tempat yang nentuin ukuran pump layak dialert apa nggak — dipake bareng
    pump_scanner, live_monitor, dan backtest biar gak ada risiko logikanya beda-beda."""
    if not (PUMP_THRESHOLD_PCT <= peak_pct <= MAX_PUMP_PCT):
        return False
    if DEAD_ZONE_MIN and DEAD_ZONE_MIN <= peak_pct < DEAD_ZONE_MAX:
        return False
    return True
PUMP_THRESHOLD_PCT = float(os.environ.get("PUMP_THRESHOLD_PCT", "8"))
MAX_PUMP_PCT = float(os.environ.get("MAX_PUMP_PCT", "16"))  # skip pump yang KEGEDEAN — backtest 30 hari (71 alert): bucket 8-12%=54.9% wr, 12-16%=61.5% wr, 16-20%=cuma 16.7% wr. Direvisi dari 25 (backtest 7 hari) turun ke 16 pas sampel lebih banyak.
WINDOW_MINUTES = int(os.environ.get("WINDOW_MINUTES", "30"))  # rentang waktu deteksi pump
SHORTLIST_PCT = PUMP_THRESHOLD_PCT / 2  # prefilter 24h buat batesin jumlah kline call
MIN_QUOTE_VOLUME = float(os.environ.get("MIN_QUOTE_VOLUME", "200000"))  # volume 24h min (USDT) — filter coin gak likuid
COOLDOWN_MINUTES = float(os.environ.get("COOLDOWN_MINUTES", "180"))  # jeda sebelum simbol yg sama boleh alert lagi
MAX_SHORTLIST = 30  # cap jumlah kline call per run — dijaga kecil biar durasi run stabil < 1 menit (scan tiap 2 menit)
SL_BUFFER_PCT = 1.0  # buffer SL di atas swing high (%)
EXPIRE_HOURS = float(os.environ.get("EXPIRE_HOURS", "48"))  # alert lama yang blm SL/TP dianggap expired
CONFIRM_MIN_RETRACE_FRAC = float(os.environ.get("CONFIRM_MIN_RETRACE_FRAC", "0.05"))  # min retrace (% dari RANGE pump) — pastiin ada reversal beneran
CONFIRM_MAX_RETRACE_FRAC = float(os.environ.get("CONFIRM_MAX_RETRACE_FRAC", "0.30"))  # max retrace — jangan sampe entry udah kelewat deket TP1 (0.382)/udah basi
RSI_OVERBOUGHT = float(os.environ.get("RSI_OVERBOUGHT", "65"))  # syarat wajib biar alert — RSI(14) >= ini = overbought, rawan koreksi turun
MAX_TRACK_PER_RUN = 15  # cap jumlah alert lama yang di-cek outcome-nya per run (biar durasi run stabil)
REQUEST_SLEEP = 0.08  # jeda antar API call (turun dari 0.15 biar run lebih cepet)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_LEVERAGED_RE = re.compile(r"(UP|DOWN|BULL|BEAR|[0-9]L|[0-9]S)USDT$")

# Coin yang terbukti jelek buat strategi short-the-pump ini dari backtest (BUKAN prasangka —
# BANKUSDT: 0 menang dari 4 kekalahan di backtest 30 hari, 20 Juli 2026). Update kalau ada
# data lebih banyak yang mbantah/nguatin.
SYMBOL_BLOCKLIST = {"BANKUSDT"}


def load_history():
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text())
    return {"last_alert": {}, "alerts": []}


def save_history(history):
    history["alerts"] = history["alerts"][-500:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def load_positions():
    if POSITIONS_PATH.exists():
        return json.loads(POSITIONS_PATH.read_text())
    return {"positions": []}


def save_positions(data):
    POSITIONS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


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
        if not sym.endswith("USDT") or _LEVERAGED_RE.search(sym) or sym in SYMBOL_BLOCKLIST:
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


def _rsi_series(closes, period=14):
    """RSI (Wilder's smoothing) di TIAP titik yang punya cukup data — bukan cuma 1 angka
    terakhir. series[i] = RSI pake closes[0..i], None kalau candle ke-i belum cukup histori.
    Dibikin rolling (dihitung sekali) biar bisa dipake buat divergence (perlu RSI di beberapa
    titik buat dibandingin), bukan cuma snapshot titik terakhir."""
    n = len(closes)
    series = [None] * n
    if n < period + 1:
        return series
    changes = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(c, 0) for c in changes]
    losses = [max(-c, 0) for c in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    series[period] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        series[i + 1] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    return series


def _calc_rsi(closes, period=14):
    """RSI terakhir (buat gate overbought). None kalau data kurang."""
    series = _rsi_series(closes, period)
    return series[-1] if series else None


def _rsi_hint(rsi):
    if rsi is None:
        return None
    if rsi >= 70:
        return "🔴 overbought — udah kemahalan, rawan koreksi turun"
    if rsi <= 30:
        return "🟢 oversold"
    return "netral"


def _detect_bearish_divergence(closes, period=14):
    """Divergence sederhana: bandingin RSI di puncak harga paruh kedua vs paruh pertama, TAPI
    cuma di titik-titik yang RSI-nya udah valid (window kita pendek ~30 candle, RSI(14) baru
    valid mulai candle ke-15 — kalau dipaksa hitung ulang dari titik puncak yang kepagian,
    hasilnya selalu None. Makanya pake rolling series, terus dibagi 2 di ANTARA titik valid
    doang, bukan di tengah seluruh window).
    Kalau harga bikin high LEBIH TINGGI tapi RSI-nya LEBIH RENDAH = momentum udah melemah
    walau harga masih keliatan naik — salah satu sinyal reversal paling dipercaya di TA.
    Return True/False/None (None kalau titik valid kurang buat dibandingin)."""
    series = _rsi_series(closes, period)
    valid_idx = [i for i, v in enumerate(series) if v is not None]
    if len(valid_idx) < 6:
        return None
    mid = len(valid_idx) // 2
    first_half, second_half = valid_idx[:mid], valid_idx[mid:]
    idx1 = max(first_half, key=lambda i: closes[i])
    idx2 = max(second_half, key=lambda i: closes[i])
    return closes[idx2] > closes[idx1] and series[idx2] < series[idx1]


def _compute_stats(kl):
    """Logic inti murni (gak manggil API) — dipake bareng sama get_window_stats (live) dan
    backtest.py (data historis), biar dua-duanya SELALU konsisten (gak ada risiko out-of-sync
    kayak bug retrace_frac 19 Juli, yang muncul gara-gara ada 2 tempat ngitung hal yang sama)."""
    if len(kl) < max(5, int(WINDOW_MINUTES * 0.9)):  # data kurang (coin baru listing dll), skip
        return None
    open_p = float(kl[0][1])
    last_p = float(kl[-1][4])
    if open_p <= 0:
        return None
    pct = (last_p - open_p) / open_p * 100
    swing_high = max(float(c[2]) for c in kl)
    swing_low = min(float(c[3]) for c in kl)
    # ukuran pump SEBENERNYA (low->high) — dipake buat gate threshold, BUKAN "pct" (yang udah
    # keburu ketutup retrace pas konfirmasi reversal minta harga udah turun dari puncak)
    peak_pct = (swing_high - swing_low) / swing_low * 100 if swing_low > 0 else 0

    mid = len(kl) // 2
    vols = [float(c[5]) for c in kl]
    vol_first = sum(vols[:mid]) / max(1, mid)
    vol_second = sum(vols[mid:]) / max(1, len(vols) - mid)
    vol_ratio = (vol_second / vol_first) if vol_first > 0 else None

    last_open, last_close = float(kl[-1][1]), float(kl[-1][4])
    last_red = last_close < last_open
    retrace_pct = (swing_high - last_p) / swing_high * 100 if swing_high > 0 else 0
    # retrace_pct itu % dari HARGA (buat display doang) — buat gating dipake retrace_frac,
    # % dari RANGE pump (swing_high - swing_low). Ini yang nentuin entry masih di ATAS TP1
    # (fraksi 0.382) apa udah kelewatan (baru ketauan lewat bug 19 Juli: alert telat, entry
    # udah di bawah TP1/TP2 duluan pas dikirim — "menang" karena udah kadung basi, bukan sinyal).
    rng = swing_high - swing_low
    retrace_frac = (swing_high - last_p) / rng if rng > 0 else None

    # candle yang bikin swing high — cek upper wick-nya (tanda ditolak di puncak)
    peak_candle = max(kl, key=lambda c: float(c[2]))
    p_open, p_high, p_low, p_close = (float(peak_candle[i]) for i in (1, 2, 3, 4))
    p_range = p_high - p_low
    wick_ratio = (p_high - max(p_open, p_close)) / p_range if p_range > 0 else 0

    closes = [float(c[4]) for c in kl]
    rsi = _calc_rsi(closes)
    divergence = _detect_bearish_divergence(closes)

    avg_vol = sum(vols) / len(vols) if vols else 0
    vol_spike = (vols[-1] / avg_vol) if avg_vol > 0 else None  # volume candle terakhir vs rata-rata window

    # KECEPATAN gerak: % perubahan dalam SPIKE_WINDOW candle terakhir. Beda dari "pct" (yang
    # ngukur seluruh window 30m) — ini buat nangkep LONJAKAN mendadak. Sengaja dihitung dari
    # candle, bukan dari harga notif terakhir, biar patokannya gak ke-reset tiap ada notif.
    fast_ref = float(kl[-min(SPIKE_WINDOW + 1, len(kl))][4])
    pct_fast = (last_p - fast_ref) / fast_ref * 100 if fast_ref > 0 else None

    return {
        "pct": pct, "peak_pct": peak_pct, "price": last_p, "swing_high": swing_high, "swing_low": swing_low,
        "vol_ratio": vol_ratio, "last_red": last_red, "retrace_pct": retrace_pct, "retrace_frac": retrace_frac,
        "wick_ratio": wick_ratio, "rsi": rsi, "divergence": divergence, "vol_spike": vol_spike,
        "pct_fast": pct_fast,
    }


def get_window_stats(symbol):
    """Kline 1 menit x WINDOW_MINUTES (live, dari API) → lihat _compute_stats buat logic-nya."""
    r = requests.get(
        f"{BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": "1m", "limit": WINDOW_MINUTES + 1},
        timeout=15,
    )
    r.raise_for_status()
    return _compute_stats(r.json())


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


def get_orderbook_ratio(symbol):
    """Order book depth (20 level tiap sisi) → rasio ask/bid volume di harga sekarang.
    Versi sederhana dari 'bandarmology' — BUKAN data wallet/whale beneran (itu butuh API
    berbayar), cuma ngeliat tumpukan order jual vs beli yang KELIATAN di book saat ini."""
    try:
        r = requests.get(f"{BASE}/api/v3/depth", params={"symbol": symbol, "limit": 20}, timeout=10)
        r.raise_for_status()
        data = r.json()
        bid_vol = sum(float(q) for _, q in data.get("bids", []))
        ask_vol = sum(float(q) for _, q in data.get("asks", []))
        return (ask_vol / bid_vol) if bid_vol > 0 else None
    except Exception as e:
        print(f"warn: orderbook {symbol} gagal ({e})")
        return None


def _orderbook_hint(ratio):
    if ratio is None:
        return None
    if ratio >= 1.5:
        return "🧱 tumpukan jual jauh lebih tebal dari beli — tekanan jual dominan"
    if ratio <= 0.67:
        return "🛒 tumpukan beli lebih tebal — hati-hati, bisa ketahan/reversal gak lanjut"
    return "seimbang"


def _wick_hint(wick_ratio):
    if wick_ratio is None:
        return None
    if wick_ratio >= 0.5:
        return "🔻 wick rejection kuat di puncak (harga ditolak turun lagi — tanda distribusi)"
    if wick_ratio >= 0.25:
        return "wick rejection sedang"
    return None


def _is_confirmed(stats, btc_pct):
    """Confluence semua sinyal reversal — biar alert lebih SELEKTIF (jarang tapi kualitas
    lebih tinggi), bukan langsung nembak begitu pct nyentuh threshold. Tetep BUKAN jaminan
    pasti — cuma nurunin peluang alert di tengah pump yang masih ngegas.

    retrace_frac DIBATASIN dua sisi (bukan cuma minimal) — kalau cuma dicek minimal, alert
    bisa lolos pas harga UDAH kadung anjlok jauh (entry jadi di bawah TP1/TP2, "menang" cuma
    karena telat ngirim, bukan sinyal beneran). Ketauan dari bug nyata 19 Juli."""
    if not stats["last_red"]:
        return False  # belum ada tanda reversal
    frac = stats["retrace_frac"]
    if frac is None or not (CONFIRM_MIN_RETRACE_FRAC <= frac <= CONFIRM_MAX_RETRACE_FRAC):
        return False  # belum retrace / udah retrace kelewat jauh (basi)
    if stats["vol_ratio"] is None or stats["vol_ratio"] >= 0.6:
        return False  # volume belum keliatan melemah
    if btc_pct is not None and btc_pct >= 1.5:
        return False  # market-wide, bukan isolated
    if stats["rsi"] is None or stats["rsi"] < RSI_OVERBOUGHT:
        return False  # belum overbought
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


def confidence_label(peak_pct):
    """Dikalibrasi dari backtest 30 hari (71 alert, 20 Juli 2026) — BUKAN skor sembarangan.
    RSI/volume/divergence SENGAJA gak dipake buat scoring ini: kebukti gak prediktif di data
    yang ada (win rate hampir sama antara menang & kalah), soalnya semua alert emang udah
    lolos filter minimum itu duluan — variasinya abis, gak ada bedanya lagi. Yang KEBUKTI
    beda nyata cuma ukuran pump-nya (peak_pct)."""
    if peak_pct < 12:
        return "MEDIUM (historis ~55% win rate dari backtest, n=51)"
    return "MEDIUM-HIGH (historis ~62% win rate dari backtest, n=13)"


def _fmt_price(p):
    s = f"{p:.8f}" if p < 1 else f"{p:,.4f}"
    return s.rstrip("0").rstrip(".")


def _build_reasons(p):
    """List alasan kenapa sinyal ini keluar — 3 pertama emang syarat wajib (_is_confirmed),
    sisanya info tambahan/'bandarmology' sederhana dari data yang KELIATAN publik (order book,
    wick candle) — BUKAN data wallet/whale beneran."""
    reasons = [
        f"Candle terakhir merah, retrace {p['retrace_pct']:.2f}% dari puncak (awal reversal)",
        f"Volume melemah (rasio {p['vol_ratio']:.2f} — daya beli mulai berkurang)",
    ]
    rsi = p.get("rsi")
    if rsi is not None:
        reasons.append(f"RSI(14) {rsi:.0f} — {_rsi_hint(rsi)}")
    if p.get("divergence"):
        reasons.append("📉 Bearish divergence — harga bikin high baru tapi RSI melemah (momentum sebenernya udah turun)")
    vs = p.get("vol_spike")
    if vs is not None and vs >= 1.5:
        reasons.append(f"🔺 Volume candle reversal {vs:.1f}x rata-rata — ada keyakinan jual beneran, bukan cuma ngedrift")
    bp = p.get("btc_pct")
    if bp is not None:
        reasons.append(f"BTC cuma {bp:+.2f}% ({WINDOW_MINUTES}m) — pump ini spesifik ke coin ini, bukan ikut market")
    wr = p.get("wick_ratio")
    wick_txt = _wick_hint(wr)
    if wick_txt:
        reasons.append(wick_txt)
    ob = p.get("orderbook_ratio")
    ob_txt = _orderbook_hint(ob)
    if ob_txt and ob_txt != "seimbang":
        reasons.append(ob_txt)
    fr = p.get("funding_rate")
    if fr is not None and fr >= 0.05:
        reasons.append(_funding_hint(fr))
    return reasons


def format_alert(p):
    url = f"https://www.binance.com/en/futures/{p['symbol']}"
    lines = [
        "🚀 <b>PUMP ALERT</b>",
        f"<b>{p['symbol']}</b>  +{p['pct']}% ({WINDOW_MINUTES} menit terakhir)",
        f"Risiko: {p['risk']}",
        f"Confidence: {p['confidence']}",
        "",
        "📋 <b>Alasan sinyal:</b>",
    ]
    for r in _build_reasons(p):
        lines.append(f"• {r}")
    lines += [
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
    ob = p.get("orderbook_ratio")
    lines.append(f"Order book (ask/bid): {ob:.2f}x ({_orderbook_hint(ob)})" if ob is not None else "Order book: gagal ambil")
    lines.append(f"🔗 {url}")
    lines.append("<i>SL/TP = swing high/low + Fibonacci, bukan SMC. Order book bukan data whale beneran, cuma book publik saat ini. Bukan saran finansial.</i>")
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


def _rsi_zone(rsi):
    if rsi is None:
        return None
    if rsi >= 70:
        return "overbought"
    if rsi <= 30:
        return "oversold"
    return "neutral"


def monitor_positions(positions, now):
    """Mantau posisi yang UDAH DIBUKA MANUAL (bukan dari alert kita) — beda dari pump_scanner
    yang nyari sinyal BARU, ini ngikutin posisi yang lagi jalan & push notif CUMA pas ada
    PERUBAHAN kondisi (bukan spam tiap 2 menit): SL/liq kena, TP kena, RSI pindah zona,
    atau deket likuidasi. Posisi ditambah/dihapus manual di positions.json."""
    changed = False
    for pos in positions.get("positions", []):
        if pos.get("status") != "open":
            continue
        try:
            stats = get_window_stats(pos["symbol"])
        except Exception as e:
            print(f"warn: monitor {pos['symbol']} gagal ({e})")
            continue
        if stats is None:
            continue
        # KALIBRASI harga ke feed tempat owner beneran trading. Data kita dari MEXC (BTCUSDT),
        # yang konsisten ~$45-55 di ATAS harga USD global / broker CFD (premium USDT+bursa, diukur
        # 26 Juli). Offset ini cuma nyetel ANGKA yang ditampilin biar nyambung sama layar broker —
        # persentase gerak gak kepengaruh (offset-nya nyaris habis pas dibagi). Setel ulang kalau
        # premium-nya geser: bandingin harga di app vs angka di alert, selisihnya taruh di sini.
        price = stats["price"] + pos.get("price_adjust", 0)
        nama = pos.get("label") or _short_sym(pos["symbol"])
        is_short = pos.get("side", "short") == "short"
        msgs = []

        sl_ref = pos.get("sl") or pos.get("liq_price")
        if sl_ref and ((is_short and price >= sl_ref) or (not is_short and price <= sl_ref)):
            msgs.append(f"🔴 {nama} nembus SL {_fmt_price(sl_ref)} — kena stop")
            pos["status"] = "closed"
            pos["closed_reason"] = "sl_or_liq_hit"

        for i, tp in enumerate(pos.get("tp") or []):
            hit_key = f"tp{i+1}_hit"
            if pos.get(hit_key):
                continue
            if (is_short and price <= tp) or (not is_short and price >= tp):
                msgs.append(f"✅ {nama} TP{i+1} kena {_fmt_price(tp)}")
                pos[hit_key] = True
                changed = True

        # alert pergerakan harga: tiap harga geser >= move_alert_pct (%) dari titik notifikasi
        # terakhir (pertama kali: dari entry), kirim update naik/turun + PNL — diminta owner
        # 20 Juli biar tiap penurunan/penaikan ALLO ada kabarnya, gak cuma pas RSI pindah zona.
        move_thr = pos.get("move_alert_pct")
        if move_thr and pos["status"] == "open":
            ref = pos.get("last_notify_price") or pos["entry"]
            move = (price - ref) / ref * 100
            if abs(move) >= move_thr:
                raw_pnl = (pos["entry"] - price) / pos["entry"] * 100 if is_short else (price - pos["entry"]) / pos["entry"] * 100
                roi = raw_pnl * pos.get("leverage", 1)
                arah = "📈" if move > 0 else "📉"
                untung = (move < 0) == is_short
                rsi_tx = _rsi_tag(stats["rsi"])
                msgs.append(
                    f"{arah} {nama} {_fmt_price(price)} {move:+.2f}%"
                    f" · PNL {roi:+.1f}%{'' if untung else ' ⚠️'}{rsi_tx}"
                )
                pos["last_notify_price"] = price
                changed = True

        zone = _rsi_zone(stats["rsi"])
        # Notif zona RSI terpisah DIMATIIN default (26 Juli, permintaan owner: cukup alert
        # harga naik/turun, dan angka RSI+zona toh selalu nempel di ekor notif harga itu).
        # Nyalain per-posisi dengan "rsi_zone_alert": true kalau nanti perlu lagi.
        if (pos.get("rsi_zone_alert", False) and zone is not None
                and zone != pos.get("last_rsi_zone") and zone != "neutral"):
            # cue singkat: zona yang NGELAWAN arah posisi = ⚠️ rawan balik
            lawan = (zone == "oversold") if is_short else (zone == "overbought")
            # kalau alert harga udah bunyi di run ini, RSI+zona-nya udah kebawa di situ →
            # notif zona terpisah cuma dikirim kalau ada peringatan "rawan balik" (yang penting).
            if lawan or not msgs:
                hint = " ⚠️ rawan balik" if lawan else ""
                msgs.append(f"📊 {nama} RSI {stats['rsi']:.0f} {_ZONE_TAG[zone]}{hint}")
            changed = True
        if zone is not None and zone != pos.get("last_rsi_zone"):
            pos["last_rsi_zone"] = zone
            changed = True

        if pos.get("liq_price") and pos["status"] == "open":
            dist = abs(pos["liq_price"] - price) / price * 100
            if dist < 5 and not pos.get("liq_warned"):
                msgs.append(f"🚨 {nama} DEKET LIQ {dist:.1f}%! ({_fmt_price(price)})")
                pos["liq_warned"] = True
                changed = True

        for m in msgs:
            print(f"POSITION UPDATE: {pos['symbol']} — {m[:60]}...")
            send_telegram(m)
        if msgs:
            changed = True
        if pos["status"] == "closed":
            changed = True
    return changed


_ZONE_TAG = {"overbought": "🔴OB", "oversold": "🟢OS", "neutral": ""}


def _short_sym(sym):
    """BTCUSDT -> BTC (biar notif kebaca di layar jam Garmin yang sempit)."""
    return sym[:-4] if sym.endswith("USDT") else sym


def _rsi_tag(rsi):
    """Ekor singkat ' · RSI 82 🔴OB' — kosong kalau RSI gak keitung."""
    if rsi is None:
        return ""
    tag = _ZONE_TAG.get(_rsi_zone(rsi), "")
    return f" · RSI {rsi:.0f}" + (f" {tag}" if tag else "")


def monitor_watchlist(watchlist, now):
    """Pantau koin di watchlist.json (mis. BTCUSDT) — kirim Telegram tiap harga geser
    >= move_alert_pct dari notif terakhir, PLUS update rutin tiap every_minutes (kalau di-set)
    walau harga lagi anyep. Beda dari monitor_positions: ini cuma NGABARIN harga, gak ada
    entry/SL/liq (bukan posisi yang dibuka). Diminta owner 21 Juli buat mantau BTC."""
    changed = False
    for w in watchlist.get("watch", []):
        if not w.get("enabled", True):
            continue
        sym = w["symbol"]
        try:
            stats = get_window_stats(sym)
        except Exception as e:
            print(f"warn: watch {sym} gagal ({e})")
            continue
        if stats is None:
            continue
        price = stats["price"] + w.get("price_adjust", 0)   # lihat catatan kalibrasi di monitor_positions
        ref = w.get("last_notify_price")
        move = None if not ref else (price - ref) / ref * 100

        # === LONJAKAN: cek paling awal, GAK nunggu jadwal ===
        spike_thr = w.get("spike_pct")
        fast = stats.get("pct_fast")
        if spike_thr and fast is not None and abs(fast) >= spike_thr:
            cd = w.get("spike_cooldown_min", 10)
            last_sp = w.get("last_spike_time")
            fresh = True
            if last_sp:
                fresh = (now - datetime.fromisoformat(last_sp)).total_seconds() / 60 >= cd
            if fresh:
                ikon = "🚨📈" if fast > 0 else "🚨📉"
                msg = f"{ikon} {w.get('label') or _short_sym(sym)} LONJAKAN {fast:+.2f}%/{SPIKE_WINDOW}m → {_fmt_price(price)}{_rsi_tag(stats['rsi'])}"
                print(f"SPIKE: {sym} {fast:+.2f}% dalam {SPIKE_WINDOW}m → {_fmt_price(price)}")
                send_telegram(msg)
                w["last_spike_time"] = now.isoformat(timespec="seconds")
                w["last_notify_price"] = price      # reset patokan biar notif rutin gak ngulang
                w["last_notify_time"] = now.isoformat(timespec="seconds")
                changed = True
                continue                            # cukup 1 notif buat siklus ini

        reasons = []
        thr = w.get("move_alert_pct")
        if ref is None:
            reasons.append("mulai dipantau")
        elif thr and abs(move) >= thr:
            reasons.append("gerak")
        every = w.get("every_minutes")
        if every and w.get("last_notify_time"):
            elapsed = (now - datetime.fromisoformat(w["last_notify_time"])).total_seconds() / 60
            if elapsed >= every:
                reasons.append("update rutin")
        if not reasons:
            continue

        if move is None:
            arah, gerak = "👀", ""
        elif move > 0:
            arah, gerak = "📈", f" {move:+.2f}%"
        elif move < 0:
            arah, gerak = "📉", f" {move:+.2f}%"
        else:
            arah, gerak = "➖", ""
        nama = w.get("label") or _short_sym(sym)
        msg = f"{arah} {nama} {_fmt_price(price)}{gerak}{_rsi_tag(stats['rsi'])}"
        print(f"WATCH: {sym} {arah} → {_fmt_price(price)} ({'/'.join(reasons)})")
        send_telegram(msg)
        w["last_notify_price"] = price
        w["last_notify_time"] = now.isoformat(timespec="seconds")
        changed = True
    return changed


def load_watchlist():
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text())
    return {"watch": []}


def save_watchlist(data):
    WATCHLIST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    history = load_history()
    now = datetime.now(timezone.utc)

    track_outcomes(history, now)

    positions = load_positions()
    if monitor_positions(positions, now):
        save_positions(positions)

    watchlist = load_watchlist()
    if monitor_watchlist(watchlist, now):
        save_watchlist(watchlist)

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
        if in_pump_range(stats["peak_pct"]):
            if not _is_confirmed(stats, btc_pct):
                continue  # belum confluence semua sinyal, tunggu run berikutnya
            setup = calc_setup(stats["swing_high"], stats["swing_low"])
            pumps.append({
                "symbol": s["symbol"],
                "pct": round(stats["peak_pct"], 2),
                "price": stats["price"],
                "quote_volume": s["quote_volume"],
                "risk": risk_category(s["quote_volume"], stats["peak_pct"]),
                "confidence": confidence_label(stats["peak_pct"]),
                "vol_ratio": stats["vol_ratio"],
                "retrace_pct": stats["retrace_pct"],
                "wick_ratio": stats["wick_ratio"],
                "rsi": stats["rsi"],
                "divergence": stats["divergence"],
                "vol_spike": stats["vol_spike"],
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
        p["orderbook_ratio"] = get_orderbook_ratio(p["symbol"])
        time.sleep(REQUEST_SLEEP)
        new_alerts.append(p)
        history["last_alert"][p["symbol"]] = now.isoformat(timespec="seconds")
        history["alerts"].append({**p, "time": now.isoformat(timespec="seconds"), "outcome": None})

    for p in new_alerts:
        print(f"ALERT: {p['symbol']} +{p['pct']}%")
        if PUMP_ALERT_ON:
            send_telegram(format_alert(p))
        else:
            print("  (PUMP_ALERT=off — gak dikirim ke Telegram, tetep dicatat di history)")

    # heartbeat — selalu di-update tiap run (walau gak ada alert/outcome baru) biar dashboard
    # bisa nunjukin "terakhir scan: X menit lalu" = bukti sistem masih hidup.
    history["last_scan"] = {
        "time": now.isoformat(timespec="seconds"),
        "shortlist_count": len(shortlist),
        "confirmed_count": len(new_alerts),
        "symbols": [s["symbol"] for s in shortlist],
    }
    save_history(history)


if __name__ == "__main__":
    main()
