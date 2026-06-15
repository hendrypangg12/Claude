# Panduan: Backtest strategi gap 6 bulan (MT5 Strategy Tester)

Tujuan: cek **pakai data historis broker kamu** — kalau tiap hari:
- **BUY (long)** jam 03:47 WIB (sebelum sesi emas tutup)
- **CLOSE** jam 05:02 WIB (setelah market buka)

selama **6 bulan** ke belakang → **cuan atau rugi?** (lengkap dengan spread + swap asli).

> Dikerjakan **di laptop** (Strategy Tester gak ada di HP). Pastikan EA `TimedDailyTrade.mq5`
> udah ke-copy ke `MQL5\Experts\` dan **di-compile (F7)** dulu — lihat README / PANDUAN-VPS.

---

## Langkah backtest

1. Buka MT5 → menu **View → Strategy Tester** (atau **Ctrl+R**). Panel muncul di bawah.
2. **Expert**: pilih `TimedDailyTrade`.
3. **Symbol**: pilih **XAUUSDb** (emas, sesuai broker kamu).
4. **Period (timeframe)**: pilih **M1** (1 menit). WAJIB M1 — karena strategi ini main di menit-menit tertentu.
5. **Modelling** (mode): pilih **"Every tick based on real ticks"** (paling akurat).
   - Kalau lama/berat, boleh **"1 minute OHLC"** (cukup akurat buat strategi menit-an ini).
   - JANGAN pakai "Open prices only" (gak cocok buat strategi berbasis jam).
6. **Date**: centang **Use date** → atur **From = 6 bulan lalu**, **To = hari ini**.
7. **Deposit**: isi modal simulasi (mis. 1.000.000 IDR) + leverage sesuai akunmu.
8. **Spread**: pilih **Current** (atau angka realistis) — biar kena biaya spread beneran.
9. Klik tab **Inputs** → set:
   - Jam: `InpBuyHour=3 / InpBuyMinute=47`, `InpCloseHour=5 / InpCloseMinute=2`
   - `InpBrokerGMTOff` → samakan offset GMT server broker (default 3)
   - `InpLotSize=0.01` (buat baca hasil yang bersih; nanti tinggal dikali)
   - SL/TP sesuai mau (atau matiin `InpUseStopLoss=false` buat lihat gap murni)
10. Klik **Start**. Tunggu sampai 100%.

---

## Cara baca hasil (tab "Results" & "Graph")

| Angka | Arti | Patokan |
|---|---|---|
| **Total Net Profit** | Untung/rugi bersih total | + = cuan, − = rugi |
| **Profit Factor** | Total untung ÷ total rugi | **> 1 = cuan**, < 1 = rugi |
| **Total Trades** | Jumlah transaksi | ~120-130 (6 bln hari kerja) |
| **Profit Trades %** | Persen menang | makin tinggi makin bagus |
| **Balance Drawdown Max** | Rugi nyangkut terdalam | makin kecil makin aman |

Lihat juga tab **Graph**: garis **naik stabil** = strategi sehat. **Turun / gerigi tajam** = boncos.

---

## ⚠️ Jujur soal backtest (baca biar gak ketipu hasil bagus)

- **Swap kemungkinan KENA tiap hari.** Broker potong swap di ~00:00 waktu server (≈ 04:00 WIB) —
  itu **di dalam** jam tahan posisi kamu (03:47–05:02). Jadi tiap transaksi kemungkinan bayar swap
  1 hari (Rabu biasanya **3x lipat**). Backtest udah ngitung ini → perhatiin apakah swap nyolong cuan.
- **Gap jeda harian emas biasanya KECIL & ~50/50 arah.** Wajar kalau hasilnya tipis / dimakan biaya.
- **Past performance ≠ future.** 6 bulan cuan bukan jaminan ke depan cuan. Coba juga periode lain
  (mis. 1-2 tahun) biar lebih yakin.
- **Kualitas data** ngaruh. "Every tick based on real ticks" paling mendekati kenyataan.

---

## Sesudah backtest
- **Hasil RUGI** → jangan dipaksain pakai duit real. Revisi strategi (mis. coba SELL, ganti jam,
  atau tambah filter) lalu backtest lagi.
- **Hasil CUAN konsisten** → lanjут tes **DEMO** beberapa minggu (live tapi duit virtual) →
  baru naik ke VPS dengan duit real. Lihat PANDUAN-VPS.
