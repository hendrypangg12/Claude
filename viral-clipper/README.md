# Viral Clipper → BERSTOCK.ID

Download a public reel/short, stamp it with the BERSTOCK.ID brand chip + a
`via @creator` credit, and output an MP4 ready to upload.

```
yt-dlp (download)  →  Pillow (overlay PNG)  →  ffmpeg (burn-in)  →  out/<ts>/branded.mp4
```

## ⚠️ Baca dulu — hak cipta & ToS

**Repost konten orang lain = risiko.** Tool ini otomatis nambahin credit
`via @creator`, **TAPI credit bukan izin.** Download + repost mentah karya orang
bisa melanggar hak cipta dan Terms of Service Instagram → post di-takedown,
kena **strike**, atau akun **dibanned permanen**.

Lebih aman:
- Repost hanya konten yang kamu punya hak/izinnya (atau konten sendiri).
- Kalau mau pakai konten viral orang: **transform** (tambah komentar/insight/angle),
  jangan mentah — lebih defensible dan lebih beda dari ribuan akun repost.
- Pilih sumber yang **nyambung sama niche** (bisnis/tech/finance), bukan asal viral.

## Setup

```bash
cd viral-clipper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ffmpeg + ffprobe wajib ada di PATH:
#   Ubuntu/Debian : sudo apt install ffmpeg
#   macOS         : brew install ffmpeg
#   atau set FFMPEG=/path/ke/ffmpeg FFPROBE=/path/ke/ffprobe
```

## Pakai

```bash
python clip_viral.py "https://www.instagram.com/reel/XXXX/"

# opsi:
python clip_viral.py "<url>" --brand "BERSTOCK.ID" --credit "@kreatorasli"
python clip_viral.py "<url>" --no-credit     # tanpa credit (NOT recommended)
```

Output:
```
out/<timestamp>/
├── source.mp4    # download asli
├── branded.mp4   # siap upload (brand + credit)
├── overlay.png   # layer overlay
└── meta.json     # metadata (url, uploader, durasi, dimensi)
```

Font Poppins dipakai dari `../daily-news-poster/fonts/` (di-share dengan news generator).

## Catatan

- `out/` di-gitignore — video pihak ketiga TIDAK ikut ke repo.
- Sumber yang butuh login (private/age-gated) gak bisa di-download tanpa cookies.
- Bisa diotomasi lewat GitHub Actions nanti (apt install ffmpeg + pip install), tapi
  hati-hati: otomasi repost massal = paling cepat kena banned.
