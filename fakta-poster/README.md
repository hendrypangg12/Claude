# Fakta Unik → Instagram (faceless page)

Auto-generate konten **original** "fakta unik / tau gak sih" jadi carousel IG 3-slide.
100% di-generate (Claude + Pillow) — **zero copyright**, aman buat autopilot, beda brand
dari BERSTOCK (look kosmik indigo + cyan).

```
Claude (fakta_generator.py)  →  Pillow (fakta_image_maker.py, 3 slide)  →  out/<ts>/
```

## Output per run
```
out/<timestamp>/
├── post_1.jpg   cover  (foto topik + scrim, "TAU GAK SIH?" + hook)*
├── post_2.jpg   fakta  (fakta inti + penjelasan, bg kosmik)
├── post_3.jpg   outro  (takeaway + Follow CTA, bg kosmik)
├── reel.mp4     versi Reel 1080x1920 (video topik + teks overlay)*
├── caption.txt  caption IG siap pakai + hashtag
└── meta.json
```
\* foto cover & reel butuh `PEXELS_API_KEY`. Tanpa key → cover pakai bg kosmik, reel di-skip.

## Background topik (foto + video) — Pexels (gratis & legal)
Konten visual diambil dari **Pexels** (stock gratis, boleh komersil, no copyright).
Claude generate keyword (`query`) → fetch foto (cover) + video (reel) yang relevan.
Daftar API key gratis: https://www.pexels.com/api/ → set `PEXELS_API_KEY`.
Reel butuh **ffmpeg** (`sudo apt install ffmpeg` / `brew install ffmpeg`).

## Setup
```bash
cd fakta-poster
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cat > .env <<EOF
ANTHROPIC_API_KEY=sk-ant-...
PEXELS_API_KEY=...        # opsional: buat foto cover + reel
EOF
```

## Pakai
```bash
python daily_fakta.py                 # Claude pilih kategori
CATEGORY=luarangkasa python daily_fakta.py
```
Kategori: `sains | sejarah | tubuh | hewan | luarangkasa | teknologi`.

## Ganti nama akun
Brand default = **FAKTANYA** (placeholder). Pas akun udah jadi, ganti via env atau
ubah `BRAND_TEXT` di `fakta_image_maker.py`:
```bash
BRAND=NAMAAKUN python daily_fakta.py
```
Nama ini muncul di chip + CTA "Follow @namaakun".

## Autopilot (GitHub Actions)
`.github/workflows/daily-fakta.yml` jalan otomatis 2x/hari (07:00 & 19:00 WIB),
generate → commit `history.json` (biar fakta gak ngulang) → upload hasil sebagai
**artifact** (carousel + reel.mp4) yang bisa di-download + post manual. Secret yang dibutuhkan:
`ANTHROPIC_API_KEY` (wajib, sudah ada di repo) + `PEXELS_API_KEY` (opsional, buat foto/video).
ffmpeg di-install otomatis di workflow.

## Catatan
- Font Poppins dipakai dari `../daily-news-poster/fonts/` (di-share).
- `out/` di-gitignore; `history.json` di-commit sebagai memory anti-duplikat.
- Upload IG masih manual (paling aman). Bisa di-wire ke Instagram Graph API nanti
  (lihat `daily-news-poster/instagram_uploader.py`).
- Tetap **cek kebenaran fakta** sebelum post — Claude akurat tapi bukan 100%.
