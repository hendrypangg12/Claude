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
├── post_1.jpg   cover  ("TAU GAK SIH?" + hook + kategori)
├── post_2.jpg   fakta  (fakta inti + penjelasan)
├── post_3.jpg   outro  (takeaway + Follow CTA)
├── caption.txt  caption IG siap pakai + hashtag
└── meta.json
```

## Setup
```bash
cd fakta-poster
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
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
**artifact** yang bisa di-download + post manual. Butuh secret `ANTHROPIC_API_KEY`
(sudah ada di repo untuk news poster).

## Catatan
- Font Poppins dipakai dari `../daily-news-poster/fonts/` (di-share).
- `out/` di-gitignore; `history.json` di-commit sebagai memory anti-duplikat.
- Upload IG masih manual (paling aman). Bisa di-wire ke Instagram Graph API nanti
  (lihat `daily-news-poster/instagram_uploader.py`).
- Tetap **cek kebenaran fakta** sebelum post — Claude akurat tapi bukan 100%.
