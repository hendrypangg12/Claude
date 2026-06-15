# TimedDailyTrade — Bot MT5: BUY & CLOSE otomatis tiap hari

Expert Advisor (EA) untuk **MetaTrader 5**. Tiap hari otomatis:
- **BUY (market)** pada jam yang kamu set (default **03:57 WIB**)
- **CLOSE / jual** pada jam yang kamu set (default **05:00 WIB**)

Symbol yang di-trade = **chart tempat EA dipasang** (mis. pasang di chart **XAUUSD** → trading emas).

---

## ⚠️ BACA DULU — Risiko (akun real)
- **Bot ini cuma jalanin jam, bukan strategi.** Beli jam 3:57 & jual jam 5:00 tiap hari **tanpa lihat pasar** secara matematis cenderung **rugi** (kena spread + swap, arah harga acak).
- **0.10 lot emas di akun kecil (~$60) = hampir pasti Margin Call / akun ludes.** Pertimbangkan **0.01 lot** atau **akun DEMO** dulu. Ubah di input `InpLotSize`.
- Tes minimal **2-4 minggu di DEMO** sebelum yakin pakai duit real.

---

## ❗ Kenapa gak bisa dari iPhone langsung
EA **TIDAK bisa jalan di MT5 iPhone/Android**. EA cuma jalan di:
1. **MT5 versi Komputer (Windows)**, ATAU
2. **VPS** (komputer awan nyala 24 jam) — biar bot tetap eksekusi jam 3:57 pagi walau HP/laptop kamu mati.

> Mac bisa pakai MT5 lewat aplikasi web/PlayOnMac, tapi paling gampang & stabil: **VPS**.

---

## 🚀 Cara pasang (Windows / VPS)

1. **Buka MT5 di komputer/VPS** → login akun real kamu.
2. Menu **File → Open Data Folder**.
3. Masuk folder `MQL5\Experts\`.
4. Copy file **`TimedDailyTrade.mq5`** ke situ.
5. Balik ke MT5, buka **Navigator** (Ctrl+N) → klik kanan **Expert Advisors → Refresh**.
   (Kalau mau, klik kanan file → **Compile** dulu, atau cukup buka MetaEditor lalu tekan **F7**.)
6. Buka chart **XAUUSD** (atau pair yang kamu mau).
7. **Drag** `TimedDailyTrade` dari Navigator ke chart.
8. Di tab **Common**: centang **Allow Algo Trading**.
9. Di tab **Inputs**: atur jam, lot, dll (lihat tabel bawah). Klik **OK**.
10. Pastikan tombol **Algo Trading** (di toolbar atas) **nyala hijau**.
11. Cek tab **Experts** (di bawah) — bakal ada log "AKTIF" + waktu server & WIB.

---

## ⏰ PENTING: setel zona waktu (biar jamnya pas)

EA pakai **waktu server broker**, tapi kamu isi jam pakai **WIB**. EA otomatis konversi pakai:
- `InpWIBOffset = 7` → WIB itu GMT+7 (**jangan diubah**).
- `InpBrokerGMTOff` → offset GMT **server broker kamu**. Umumnya **GMT+2** (musim dingin) atau **GMT+3** (musim panas).

**Cara pastiin sudah benar:** setelah pasang EA, lihat log di tab **Experts**. Ada baris:
```
Waktu server: ... | Waktu WIB: ...
```
Kalau **"Waktu WIB"** sama dengan jam asli di HP kamu → **udah benar**. Kalau meleset 1 jam → ubah `InpBrokerGMTOff` (mis. dari 3 ke 2).

---

## ⚙️ Daftar Input

| Input | Default | Arti |
|---|---|---|
| `InpBuyHour` / `InpBuyMinute` | 3 / 57 | Jam BUY (WIB) |
| `InpCloseHour` / `InpCloseMinute` | 5 / 0 | Jam CLOSE/jual (WIB) |
| `InpWIBOffset` | 7 | WIB = GMT+7 (jangan diubah) |
| `InpBrokerGMTOff` | 3 | Offset GMT server broker (cek lewat log) |
| `InpLotSize` | 0.10 | Ukuran lot |
| `InpStopLossPts` | 0 | Stop Loss (points, 0 = mati) |
| `InpTakeProfitPts` | 0 | Take Profit (points, 0 = mati) |
| `InpMaxSpreadPts` | 0 | Spread maks (points, 0 = abaikan) |
| `InpTradeMonToFri` | true | Cuma Senin-Jumat |
| `InpMagic` | 39570050 | Identitas posisi EA |
| `InpSlippagePts` | 30 | Deviasi/slippage maks (points) |

---

## ✅ Cara tes aman dulu (sangat disarankan)
1. Ganti `InpLotSize` ke **0.01**.
2. **Sementara** set `InpBuyMinute` ke beberapa menit dari sekarang + `InpCloseMinute` ~2-3 menit setelahnya → lihat EA beneran BUY lalu CLOSE.
3. Cek log di tab **Experts** + tab **Trade**.
4. Setelah yakin jam & eksekusi benar, balikin jam ke 03:57 / 05:00 dan lot sesuai maumu.

## 🛡️ Catatan keamanan
- EA cuma sentuh posisi dengan **magic number** sendiri → posisi manual kamu yang lain gak diganggu.
- Anti dobel: maksimal **1x BUY per hari**.
- Kalau free margin gak cukup, BUY dibatalkan + ditulis di log (gak bikin error).
