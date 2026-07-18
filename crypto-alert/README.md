# Crypto Pump Alert

Scan semua pair USDT **yang beneran ada kontrak perpetual-nya di Binance
Futures** tiap beberapa menit (harga/kline dari MEXC, listing+funding dari
Binance Futures asli lewat CoinGecko — lihat "Sumber data" di bawah),
deteksi kenaikan harga **>= 10% dalam 30 menit terakhir** YANG UDAH ADA
TANDA REVERSAL (candle merah + retrace dari puncak — bukan langsung pas
nyentuh threshold), kirim alert ke Telegram lengkap sama entry/SL/TP1-3/
kategori risiko/funding rate/korelasi BTC/tren volume. 100% gratis (no API
key, Telegram Bot API gratis).

**SL/TP BUKAN Smart Money Concept (SMC) beneran** — SMC (order block,
liquidity sweep, fair value gap, multi-timeframe structure) butuh baca
chart visual/kontekstual, susah diotomatisasi presisi lewat script. Yang
dipakai di sini pendekatan lebih sederhana & terukur: swing high/low dari
window pump + Fibonacci retracement (38.2% / 61.8% / 100%). Bukan saran
finansial — tetep pake risk management sendiri (position size, leverage).

Whale/on-chain outflow detection **belum dibikin** (butuh API berbayar kayak
Whale Alert buat data real-time yang bagus) — nyusul kalau mau.

## Sumber data

Binance (spot & Futures) nge-block IP dari lokasi "restricted" (451) —
kejadian di sandbox dev DAN kemungkinan besar di GitHub Actions juga
(sama-sama infra cloud). Jadi:
- **Harga/kline (deteksi pump)**: MEXC — public API, no key, gak ke-block.
- **Listing Futures + funding rate**: **Binance Futures ASLI**, diambil
  lewat CoinGecko (`/derivatives/exchanges/binance_futures`) — endpoint ini
  gak ke-block dan datanya mirror langsung dari Binance. Ini yang nentuin
  coin mana yang layak di-alert (biar gak kayak kejadian TENDIESUSDT yang
  ternyata gak ada kontraknya di Binance Futures, useless buat di-short).

## Cara setup Telegram

1. Chat **@BotFather** di Telegram → `/newbot` → ikutin instruksi → dapet
   **bot token** (format `123456:ABC-DEF...`).
2. Chat bot kamu (search username-nya, klik Start / kirim pesan apa aja).
3. Buka `https://api.telegram.org/bot<TOKEN>/getUpdates` di browser (ganti
   `<TOKEN>`) → cari `"chat":{"id": ...}` → itu **chat ID** kamu.
4. Set 2 GitHub Secrets di repo ini (Settings → Secrets and variables →
   Actions): `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`.

Tanpa secret ini, workflow tetap jalan & nyimpen history, cuma gak kirim
notif (log bakal bilang "Telegram belum di-set").

## Jalan sendiri

```bash
cd crypto-alert
pip install -r requirements.txt
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python pump_scanner.py
```

## Tuning (env var, opsional)

- `PUMP_THRESHOLD_PCT` (default `10`) — ambang % kenaikan buat trigger.
- `WINDOW_MINUTES` (default `30`) — rentang waktu deteksi kenaikannya.
- `CONFIRM_RETRACE_PCT` (default `1.0`) — minimal retrace dari swing high
  (+ candle terakhir merah) sebelum alert dikirim, biar entry deket titik
  balik beneran, bukan di tengah pump.
- `MIN_QUOTE_VOLUME` (default `200000`) — filter volume 24h minimum (USDT),
  biar gak alert coin gak likuid yang % swing-nya gampang liar.
- `COOLDOWN_MINUTES` (default `180`) — jeda minimum sebelum simbol yang sama
  boleh alert lagi.
- `EXPIRE_HOURS` (default `48`) — alert lama yang belum kena SL/TP dianggap
  "expired" di win-rate tracking.

## File

- `pump_scanner.py` — logic scan + alert.
- `history.json` — state cooldown + log alert (di-commit otomatis tiap ada
  alert baru, biar gak spam & ada riwayat).
