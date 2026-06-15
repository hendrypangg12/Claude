# Panduan: Pasang Bot di MT5 VPS (dari nol sampai jalan 24 jam)

Panduan buat **non-teknis**, dikerjakan **di laptop/PC** (sekali setup).
Setelah ini, bot jalan 24 jam di VPS — laptop boleh dimatiin, mantau dari iPhone.

> ⚠️ Aplikasi kamu = **MT5** (bukan MT4). EA `TimedDailyTrade.mq5` juga buat MT5.
> Symbol emas di broker kamu = **XAUUSDb** (ada huruf "b" — wajar, tiap broker beda).

---

## BAGIAN 1 — Install MT5 di laptop & login

1. Download **MetaTrader 5 versi Windows** dari brokermu (atau dari `metatrader5.com`).
2. Install, lalu **login akun REAL kamu**: butuh **Login (nomor akun)**, **Password**, dan **Server**
   — sama persis kayak yang kamu pakai login di HP. (Cek di app HP: Settings → akun, buat lihat nama server.)
3. Pastikan grafik **XAUUSDb** bisa dibuka (klik kanan Market Watch → Symbols → cari XAUUSDb kalau belum ada).

---

## BAGIAN 2 — Masukin file bot (EA)

1. Ambil file **`TimedDailyTrade.mq5`** dari repo GitHub:
   `forex-trading/TimedDailyTrade.mq5` (branch `claude/forex-trading-gb76l2`).
   Buka di GitHub → tombol **Download raw file** → simpan ke laptop.
2. Di MT5: menu **File → Open Data Folder**.
3. Masuk folder **`MQL5\Experts\`** → copy `TimedDailyTrade.mq5` ke situ.
4. Balik ke MT5 → panel **Navigator** (Ctrl+N) → klik kanan **Expert Advisors → Refresh**.
5. Klik 2x `TimedDailyTrade` → kebuka di **MetaEditor** → tekan **F7** (Compile).
   Harus muncul **"0 errors, 0 warnings"**. Tutup MetaEditor.

---

## BAGIAN 3 — Pasang bot ke chart & atur

1. Buka chart **XAUUSDb** (timeframe bebas, mis. M5).
2. **Drag** `TimedDailyTrade` dari Navigator ke chart.
3. Tab **Common**: centang **Allow Algo Trading**.
4. Tab **Inputs**: atur (lihat README utama buat detail):
   - `InpBuyHour=3`, `InpBuyMinute=57` (jam BUY, WIB)
   - `InpCloseHour=5`, `InpCloseMinute=0` (jam CLOSE, WIB)
   - `InpLotSize` → **saran 0.01 buat awal** (0.10 sangat berisiko)
   - `InpUseStopLoss=true`, `InpStopLossPrice` → jarak SL dalam dollar
5. Klik **OK**. Pastikan tombol **Algo Trading** (toolbar atas) **nyala hijau**.
6. Lihat tab **Experts** (bawah) → ada log:
   ```
   Waktu server: ... | Waktu WIB: ...
   ```
   **Cocokkan "Waktu WIB" dengan jam HP kamu.** Kalau meleset 1 jam → ubah `InpBrokerGMTOff`
   (mis. dari 3 ke 2), OK lagi, cek lagi sampai pas.

> 💡 **TES DULU sebelum lepas:** sementara set `InpBuyMinute` ke ~2 menit dari sekarang &
> `InpCloseMinute` ~4 menit dari sekarang, lot 0.01 → lihat bot beneran BUY lalu CLOSE di tab Trade.
> Kalau udah yakin, balikin ke 03:57 / 05:00.

---

## BAGIAN 4 — Sewa VPS & pindahkan bot (biar jalan 24 jam)

1. **Klik kanan di chart** (atau klik kanan nama akun di Navigator) → **"Register a Virtual Server"**.
2. Wizard muncul → pilih lokasi server dengan **ping/latency terkecil** (biasanya disorot otomatis).
3. Pilih paket sewa (ada bulanan; kadang ada masa coba). Bayar.
4. Setelah aktif → pilih opsi **"Copy charts and Expert Advisors to the server"** → klik **Migrate**.
   Ini ngirim chart XAUUSDb + EA + settingnya ke VPS.
5. Pastikan status VPS **"Synchronized"** dan tulisan trading aktif di VPS.

✅ **Selesai.** Sekarang EA jalan di VPS 24 jam.
- **Laptop boleh ditutup/dimatiin** — bot tetap jalan.
- Dari **iPhone** kamu bisa **mantau** posisi/profit via app MT5 (tapi gak bisa ubah setting EA dari HP).

---

## Kalau mau UBAH setting nanti (lot/jam/SL)
1. Buka MT5 di **laptop** lagi.
2. Ubah Inputs EA di chart.
3. **Migrate ulang** ke VPS (Bagian 4 langkah 4) biar setting baru kepakai.

## Kalau mau STOP bot
- Matiin **Algo Trading**, atau hapus EA dari chart, lalu **Migrate ulang**.
- Buat berhenti total: stop/hapus VPS dari menu Virtual Server.

---

## Cek cepat kalau bermasalah
| Masalah | Solusi |
|---|---|
| Bot gak BUY di jam yang diharapkan | Cek "Waktu WIB" di log; betulin `InpBrokerGMTOff` |
| "0.10 lot" ditolak / margin kurang | Kecilin `InpLotSize` (mis. 0.01) |
| EA gak muncul di Navigator | Refresh + Compile (F7) lagi |
| Algo Trading mati | Klik tombolnya sampai hijau (di laptop & di VPS) |
