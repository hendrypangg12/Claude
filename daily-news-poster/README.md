# Daily News → Instagram

Otomatis setiap pagi: ambil berita trending → bikin caption pakai Claude → ambil gambar dari Google → overlay headline → upload ke Instagram.

## Cara kerja

```
NewsAPI  →  Claude (caption)  →  Google Image  →  Pillow overlay  →  Instagram Graph API
```

Output di-cache ke `out/YYYY-MM-DD/` (raw image, post final, caption.txt).

## ⚠️ Risiko hak cipta (baca dulu)

Gambar di Google milik orang. Default-nya script ini **memfilter ke Creative Commons** (`IMAGE_LICENSE_FILTER` di `.env`). Kalau Anda ubah ke `any`, Anda mengambil risiko sendiri: takedown DMCA bisa kena strike (3 strike = akun banned permanen).

Selalu credit sumber berita di caption (Claude sudah disuruh begitu) dan di gambar (otomatis di overlay).

---

## Setup (one-time)

### 1. Install dependency

```bash
cd daily-news-poster
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Daftarkan API keys

| API | Link | Catatan |
|---|---|---|
| NewsAPI | https://newsapi.org | Gratis 100 req/hari |
| Anthropic | https://console.anthropic.com | ~$0.001 per post |
| Google Custom Search | https://programmablesearchengine.google.com + https://developers.google.com/custom-search/v1/introduction | Gratis 100/hari. **Wajib enable "Image search" + "Search entire web"** di setting search engine |
| imgbb | https://api.imgbb.com | Gratis. Buat host gambar sementara (IG butuh URL publik) |

Isi semuanya ke `.env`.

### 3. Instagram setup (bagian paling ribet)

Instagram **tidak** terima password login lewat API. Anda harus pakai Graph API:

1. **Convert akun IG** ke Business atau Creator (Settings → Account → Switch to Professional Account).
2. **Buat Facebook Page** kosong (facebook.com/pages/create) — IG Graph API butuh linkage ke Page.
3. **Link IG ke Page**: di Page → Settings → Linked Accounts → connect IG.
4. **Buat App** di https://developers.facebook.com:
   - Type: "Business"
   - Add product: "Instagram Graph API"
5. **Dapatkan token**:
   - Buka [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
   - Pilih app Anda
   - Generate User Token dengan permission: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
   - Token awal hanya valid 1 jam → tukar ke **Long-Lived Token** (60 hari):
     ```bash
     curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={SHORT_TOKEN}"
     ```
6. **Dapatkan `IG_USER_ID`**:
   ```bash
   curl "https://graph.facebook.com/v21.0/me/accounts?access_token={TOKEN}"
   # ambil page id, lalu:
   curl "https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={TOKEN}"
   ```
7. Masukkan `IG_USER_ID` dan `IG_ACCESS_TOKEN` ke `.env`.

> Token 60 hari akan expired. Set reminder kalender untuk refresh, atau implementasikan auto-refresh.

---

## Pakai

### Test dulu (tanpa upload)

```bash
DRY_RUN=true python daily_post.py
```

Output ada di `out/YYYY-MM-DD/post.jpg`. Buka, cek apakah hasilnya bagus.

### Jalan beneran

```bash
python daily_post.py
```

### Otomatis tiap pagi

**Opsi A: GitHub Actions (gratis, recommended)**

1. Push repo ini ke GitHub (private repo OK).
2. Copy `github-actions-example/daily-post.yml` ke `.github/workflows/daily-post.yml` di **root repo** (bukan di dalam `daily-news-poster/`).
3. Settings → Secrets and variables → Actions → tambah semua secret dari `.env.example`.
4. Workflow jalan otomatis tiap hari 07:00 WIB. Bisa juga dipicu manual dari tab Actions.

**Opsi B: cron lokal (Mac/Linux)**

```bash
crontab -e
# Tambah baris:
0 7 * * * cd /path/to/daily-news-poster && /path/to/.venv/bin/python daily_post.py >> daily.log 2>&1
```

**Opsi C: Task Scheduler (Windows)** — buat task baru, trigger Daily 07:00, action `python.exe daily_post.py`.

---

## Struktur file

```
daily-news-poster/
├── daily_post.py             # orchestrator utama
├── news_fetcher.py           # NewsAPI client
├── caption_generator.py      # Claude API client
├── image_fetcher.py          # Google Custom Search
├── image_maker.py            # Pillow overlay 1080x1080
├── instagram_uploader.py     # IG Graph API + imgbb upload
├── requirements.txt
├── .env.example
├── .gitignore
├── github-actions-example/
│   └── daily-post.yml
└── out/                      # generated posts (gitignored)
```

## Troubleshooting

- **"No images found"** → Search engine di programmablesearchengine.google.com belum di-enable "Search entire web" atau "Image search".
- **IG token expired** → refresh long-lived token (lihat step 5 di atas).
- **Caption terlalu panjang** → IG limit 2200 char termasuk hashtag. Edit `caption_generator.py` system prompt.
- **Font jelek di GitHub Actions** → DejaVuSans-Bold sudah ada di ubuntu-latest, harusnya OK. Kalau di mesin lokal teks pakai PIL default, install font: `sudo apt install fonts-dejavu` (Linux) atau script otomatis cari Arial/Liberation.

## Etika

- Selalu **credit sumber berita** (sudah otomatis di overlay + caption).
- Jangan post berita yang belum diverifikasi sebagai trending hoax.
- Patuhi [Instagram Platform Policy](https://developers.facebook.com/docs/instagram-api/overview): max 50 posts/day per akun via API, tapi realistis 1/hari sudah optimal untuk engagement.
