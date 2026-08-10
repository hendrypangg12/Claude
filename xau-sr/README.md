# XAU Multi-Timeframe S/R (TradingView Pine)

Indikator TradingView yang otomatis menggambar level **support & resistance** dari
**4H, 1H, 30m, 15m, dan 3m** sekaligus, dalam satu indikator.

File: [`xau_multi_tf_sr.pine`](xau_multi_tf_sr.pine)

## Kenapa satu indikator, bukan lima

Plan free TradingView cuma boleh **2 indikator aktif per chart**. Kalau tiap timeframe
dibikin indikator terpisah, slotnya habis. Di sini kelima timeframe ditarik lewat
`request.security` di dalam satu skrip, jadi cuma makan 1 slot.

## Cara pasang (sekali aja, dari laptop)

1. Buka TradingView, buka chart **XAUUSD**
2. Panel bawah → tab **Pine Editor**
3. Hapus isi editor, paste seluruh isi `xau_multi_tf_sr.pine`
4. **Save** → kasih nama → **Add to chart**

Setelah di-save, indikator ini tersimpan di **akun** TradingView kamu — bukan di laptop.
Jadi buka app TradingView di HP, chart XAU, garisnya udah ada dan update sendiri realtime.

## Cara baca chartnya

| Tampilan | Arti |
|---|---|
| Garis **solid** | Resistance (level di atas, harga cenderung tertahan) |
| Garis **putus-putus** | Support (level di bawah, harga cenderung memantul) |
| Garis makin **tebal** | Timeframe makin besar → level makin penting |
| Warna | Merah 4H · oranye 1H · kuning 30m · cyan 15m · abu 3m |

Level 4H yang tertembus jauh lebih berarti daripada level 3m yang tertembus.
Kalau beberapa timeframe punya level di harga yang berdekatan, itu zona yang kuat.

## Setelan yang biasanya perlu disesuaikan

- **Bar kiri / Bar kanan** — sensitivitas pivot. Naikkan (misal 15–20) kalau garisnya
  kebanyakan; turunkan (5–8) kalau terlalu sedikit.
- **Batas jarak (x ATR)** — level yang jauh dari harga sekarang disembunyikan biar
  chart nggak penuh. Kecilkan kalau masih ramai.

## Batasan yang perlu diketahui

- Level baru **dikonfirmasi setelah `Bar kanan` bar berlalu**. Ini bukan bug — pivot
  memang baru bisa disebut pivot setelah harga berbalik dan tidak dilewati lagi.
  Skrip ini sengaja pakai `lookahead_off`: tanpa itu, garis akan terlihat sangat akurat
  saat digeser ke belakang tapi menyesatkan saat dipakai live.
- Indikator ini **menggambar**, bukan **menganalisa**. Dia bilang "ada level di 3.412",
  bukan "level ini sudah 3x ditolak dan volumenya menurun".
- Alert bawaan cuma untuk tembus level 4H. Di plan free, alert bisa masuk ke app
  TradingView di HP, tapi **belum bisa kirim webhook** ke server sendiri
  (butuh plan Essential ke atas).

## Kalau nanti upgrade ke plan berbayar

Webhook terbuka, dan alert dari indikator ini bisa dikirim ke server sendiri untuk
diberi konteks tambahan (struktur timeframe lain, momentum, jarak ke level berikutnya)
lalu diteruskan ke Telegram. Selama masih plan free, lapisan itu belum ada gunanya.
