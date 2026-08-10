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
| Warna | Merah 4H · oranye 1H · kuning 30m · cyan 15m · abu 3m |
| Garis **tebal & pekat** | Level kuat (★★★) |
| Garis **tipis & transparan** | Level lemah (★) |

Level 4H yang tertembus jauh lebih berarti daripada level 3m yang tertembus.

### Kekuatan level (★)

Tiap level dinilai dari dua hal yang memang punya arti di pasar:

1. **Berapa kali disentuh** — tiap kali harga membentuk swing di area yang sama,
   hitungannya naik. Muncul di label sebagai `(3x)`. Level yang sudah 3x menahan
   harga jelas lebih teruji daripada yang baru sekali.
2. **Confluence antar timeframe** — kalau 15m, 1H, dan 4H sama-sama punya level di
   harga yang berdekatan, itu zona terkuat di chart. Tiap timeframe tambahan
   menambah skor.

Skor = jumlah sentuhan + jumlah timeframe yang setuju. Ambang ★★ dan ★★★ bisa
diatur di setelan. Contoh label: `4H R ***  3412.50  (3x)`.

### Kenapa label R/S-nya selalu benar

Skrip ini menyimpan banyak pivot per timeframe, lalu tiap saat memilih level
**terdekat di atas harga** sebagai resistance dan **terdekat di bawah** sebagai
support. Jadi kalau harga menembus naik, level yang tadinya resistance otomatis
diperlakukan sebagai support — itu memang perilaku S/R yang benar (level flip),
bukan garis yang salah label.

## Setelan yang biasanya perlu disesuaikan

- **Bar kiri / Bar kanan** — sensitivitas pivot. Naikkan (misal 15–20) kalau garisnya
  kebanyakan; turunkan (5–8) kalau terlalu sedikit.
- **Batas jarak (x ATR 4H)** — level yang jauh dari harga sekarang disembunyikan biar
  chart nggak penuh. Naikkan kalau level timeframe besar nggak kelihatan.
- **Toleransi zona (x ATR 4H)** — dua pivot yang jaraknya di bawah nilai ini dianggap
  level yang sama. Naikkan kalau level kembar terus dihitung terpisah (jumlah `(x)`
  nggak naik-naik padahal harga jelas sudah beberapa kali mantul di situ).
- **Selisih posisi label antar timeframe** — label tiap timeframe digeser ke kanan
  supaya nggak tumpang tindih saat beberapa timeframe punya level di harga yang sama.
  Kecilkan kalau label paling kanan keluar layar; nol bikin semua sejajar.

Kedua setelan jarak di atas diukur pakai **ATR 4H**, bukan ATR chart yang sedang dibuka.
Jadi angkanya tetap berarti sama walau kamu pindah-pindah timeframe chart — nggak perlu
disetel ulang tiap ganti dari 3m ke 1H.

## Batasan yang perlu diketahui

- Level baru **dikonfirmasi setelah `Bar kanan` bar berlalu**. Ini bukan bug — pivot
  memang baru bisa disebut pivot setelah harga berbalik dan tidak dilewati lagi.
  Skrip ini sengaja pakai `lookahead_off`: tanpa itu, garis akan terlihat sangat akurat
  saat digeser ke belakang tapi menyesatkan saat dipakai live.
- Skor kekuatan dihitung dari **struktur harga**, bukan volume. Dia tahu level sudah
  3x ditahan, tapi tidak tahu volumenya menurun atau ada berita.
- Hitungan sentuhan mulai dari nol saat indikator dipasang, lalu terisi dari riwayat
  chart yang dimuat. Kalau chart-nya baru digeser jauh ke belakang, angkanya bisa
  berubah — itu normal, bukan error.
- Alert bawaan cuma untuk tembus level 4H. Di plan free, alert bisa masuk ke app
  TradingView di HP, tapi **belum bisa kirim webhook** ke server sendiri
  (butuh plan Essential ke atas).

## Kalau nanti upgrade ke plan berbayar

Webhook terbuka, dan alert dari indikator ini bisa dikirim ke server sendiri untuk
diberi konteks tambahan (struktur timeframe lain, momentum, jarak ke level berikutnya)
lalu diteruskan ke Telegram. Selama masih plan free, lapisan itu belum ada gunanya.
