# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This repo holds two unrelated things — don't assume one when working on the other:

1. **`index.html`** — a single-file browser game (Nokia 3310-style Snake). See "Snake game" below.
2. **Berstock.ID content systems** — Python pipelines + a PWA that auto-generate daily
   Instagram content (news carousels, quotes) and brand viral clips. This is the bulk of
   the repo and what is actively run via GitHub Actions. See "Content systems" below.

(Also `trading-demo.html` = a standalone "Crypto Short — Paper Trading" demo page.)

## Content systems (Berstock.ID) — the active project

Auto-posts daily IG content for **@berstock.id** (bisnis / saham / ekonomi / teknologi).

| Subsystem | Folder | Pipeline |
|---|---|---|
| **Daily news carousel** | `daily-news-poster/` | NewsAPI/RSS → Claude (`caption_generator.py`: pick + caption + headline + 3 points + takeaway) → article/Google image → `image_maker.py` (Pillow, 1080×1080 ×3 slides) → `out/<ts>/` → IG Graph API (`instagram_uploader.py`) |
| **Daily quote ("Lalu")** | `daily-quote-poster/` | Claude (`quote_generator.py`) → `quote_image_maker.py` → `out/<ts>/` |
| **Fakta unik (faceless page)** | `fakta-poster/` | Claude (`fakta_generator.py`) → `fakta_image_maker.py` (3-slide, cosmic indigo+cyan, brand `FAKTANYA` placeholder) → `out/<ts>/`. Original content, zero copyright. `history.json` = cross-run dedup. Separate IG account from BERSTOCK. |
| **Viral clipper** | `viral-clipper/` | `clip_viral.py`: yt-dlp download → Pillow overlay (brand chip + `via @creator` credit) → ffmpeg burn-in → `out/<ts>/branded.mp4` |
| **Frontend PWA** | `docs/` | "Daily Generator" UI (`index.html` = Berita, `lalu.html` = Quote). Reads `manifest.json` / `lalu-manifest.json`. Hosted on GitHub Pages. |
| **Automation** | `.github/workflows/` | `daily-post.yml` (4 niche slots/day) + `daily-quote.yml` (4 mood slots/day). Run `DRY_RUN=true` (semi-manual): generate → commit to repo → upload artifact; no auto-IG. |

Key facts:
- **Model:** `claude-sonnet-4-6` (in `caption_generator.py` / `quote_generator.py`).
- **News niches** (cron, WIB): `pagi` (pemerintahan, 06:30), `saham` (12:00), `market` (18:00), `startup` (21:00), `ai` (manual). Niche hints live in `NICHE_PICK_HINTS`.
- **Design system:** navy+gold editorial, **Poppins** bundled in `daily-news-poster/fonts/`
  (shared by the clipper). `image_maker.py` renders at 2× then downscales (supersampling)
  for crisp type; slides 2 & 3 use a clean branded background (no muddy photo reuse).
  Palette: navy `(20,26,38)` / deep `(11,15,23)`, gold `(255,196,0)`, ink-on-gold `(15,18,26)`.
- **Secrets (GH Actions):** `NEWSAPI_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`
  (+ `IG_USER_ID`/`IG_ACCESS_TOKEN` only for real auto-upload). See `daily-news-poster/README.md`.
- **`out/`** is committed for news/quote (drives the PWA) but **gitignored** for `viral-clipper/`
  (don't commit third-party video into the repo).
- **Rights caveat (clipper):** reposting others' content raw can infringe copyright / violate IG
  ToS (takedown/strike/ban). The clipper adds a credit by default, but credit ≠ permission —
  prefer own/permitted content or transform it, and keep sources on-niche.

## SESSION MEMORY — IG content empire (update 7 Juni 2026)

> Konteks penting yang dibangun sesi ini. BACA ini dulu kalau lanjut kerjaan IG content.

### Branch & cara kerja
- **Default branch = `claude/halo-bYUsl`** (HEAD repo). Workflow_dispatch HANYA muncul kalau file workflow ada di branch ini → semua workflow di-commit ke `claude/halo-bYUsl`. Dev branch `claude/memory-stock-content-generator-7CHXe` di-mirror juga.
- Owner **non-teknikal, pakai HP** (iPhone). Selalu kasih langkah step-by-step + link workflow yang bisa di-tap. Bahasa Indonesia santai.
- **Aku TIDAK bisa trigger workflow** (integration 403) + **TIDAK bisa akses Pexels lokal** (API key cuma di GH Secrets). Pola kerja: owner Run workflow → konten di-commit ke repo → aku `git pull` → compress → kirim via file.
- **ffmpeg/ffprobe lokal di `/tmp/ffmpeg` & `/tmp/ffprobe`** (bukan PATH). Set `fv.FFMPEG=/tmp/ffmpeg` kalau render lokal.
- **"Failure" di workflow run = NORMAL**: step "Publish ke Instagram" merah karena token. Yang penting step **"Siapkan media + commit" ✅ ijo** → konten tetap jadi & ke-commit.
- Reel WAJIB di bawah 100MB (limit GitHub) → `render_reel` di-cap `crf 23 + maxrate 6M`; workflow guard skip reel kalau >99MB (carousel tetap commit).

### Akun & brand
| Akun IG | FB Page | Niche | Pipeline |
|---|---|---|---|
| **@faktaviral.idn** (brand FAKTAVIRAL, cosmic indigo+cyan) | "Fakta Viral" | fakta unik viral | `fakta-poster/` |
| **@beruangfinance** (brand kuning + beruang berdasi) | (bikin) | tips/berita/lucu keuangan | `beruang-finance/` |
- Owner punya banyak akun IG asli (faktaviral.idn, beruangfinance, berstock.id, pauss.beluga, hendrypangg) + FB Page. Strategi: akun RESMI beda niche, bukan bot farm. "Saling post" = cross-promo natural manual, BUKAN auto-mutual-repost (kena banned).

### `beruang-finance/` (BARU sesi ini)
- `bf_generator.py` — Claude (`claude-sonnet-4-6`) generate {type(tips/berita/lucu), kicker, hook, points[3], takeaway, caption, query}. Emoji di-strip dari teks visual (caption boleh emoji). Caption MAKS 5 hashtag.
- `bf_image_maker.py` — carousel 1080×1080 (cover/points/outro), brand kuning `(255,198,0)` + ink coklat `(58,38,22)`, foto Pexels + scrim coklat. Bear logo di outro. Brand `BERUANG FINANCE`, HANDLE `beruangfinance`.
- `bf_video_maker.py` — reel 1080×1920. `make_reel_overlay(hook,kicker,lines)` + `render_reel(...,seg=10,max_segments=2)` = 20 detik, progress bar kuning, KARTU GELAP di belakang teks biar kebaca.
- `bf_daily.py` — orchestrator (CTYPE/TOPIC env) → carousel + reel 20s. `brand/bear.png` = beruang berdasi (copy dari Financial-tracker `assets/logo-berbisnis.png`).
- Workflow `.github/workflows/beruang-finance.yml` (input: ctype, topic).
- Brand assets profil/cover di-render via `/tmp/make_bf_brand.py` (kuning terang + beruang berdasi). Bio: "Beruang Finance · Tips Keuangan" + "Melek duit, pelan-pelan".

### `fakta-poster/` reel — upgrade sesi ini
- Reel **20 detik** (2 klip × 10s, ganti tiap 10 detik), bukan 45s lagi.
- Teks di **kartu gelap semi-transparan** (anti nabrak footage terang), anchor **tengah-atas** (eye-catching).
- **3 layer**: main (chrome+hook, t=0) → fact inti (fade ~1.5s) → **detail/penjelasan KENAPA = "slide 2"** (muncul ~detik 10, pas klip ke-2). `make_reel_overlay(...,out_detail, detail=)` + `render_reel(...,detail_png=,detail_at=10)`.
- CTA "Follow" **diangkat dari dasar** (`sub_y -= s(170)`) biar gak ketutup UI Reels IG.
- Caption MAKS 5 hashtag.

### `fetch-footage.yml` (BARU) — `fakta-poster/fetch_footage.py`
Ambil klip+foto Pexels mentah per query, commit ke `fakta-poster/footage/<slug>/` → buat render overlay custom (mis. konten berita ber-data terverifikasi seperti reel "Rupiah ≠ krisis 1998").

### Multi-akun IG auto-post — `fakta-poster/publish_ig.py`
- Support banyak akun via 1 secret `IG_ACCOUNTS` (JSON array `[{name,ig_user_id,token}]`), fallback ke `IG_USER_ID`/`IG_ACCESS_TOKEN` tunggal. 1 akun gagal ≠ stop yang lain. Stagger jeda antar-akun.

### IG Graph API token (untuk auto-upload) — status & cara
- **Meta app "fakta viral bot"**: App ID `1048502251194046` (App Secret = RAHASIA, di App Dashboard → Settings → Basic).
- **@faktaviral.idn**: IG_USER_ID = `17841431673727855` · FB Page "Fakta Viral" id `1113692745165301`.
- Permission token: `instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, business_management`.
- **Cara dapat token 60 hari**: Graph API Explorer → Generate (token 1 jam) → ambil IG id via `me/accounts?fields=name,instagram_business_account` → tukar long-lived:
  `GET https://graph.facebook.com/v25.0/oauth/access_token?grant_type=fb_exchange_token&client_id=1048502251194046&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN`
- Set GH Secrets `IG_USER_ID` + `IG_ACCESS_TOKEN` (https://github.com/hendrypangg12/Claude/settings/secrets/actions).
- ⚠️ Token expired tiap ~60 hari → perlu refresh manual (TODO: auto-refresh / System User token biar permanen). JANGAN pernah commit token/App Secret ke repo — Secrets only.
- 7 Juni: owner udah ganti password FB + lagi proses set token 60 hari (lanjutan: pasang ke GH Secret → test run `post_mode: both`).

## SESSION MEMORY — update 8 Juni 2026 (BACA INI buat lanjutan terbaru)

> Banyak fitur besar dibangun sesi ini. Branch dev sesi ini = `claude/new-session-7ysra`, semua di-merge ke
> default `claude/halo-bYUsl` (wajib di default branch biar schedule + workflow_dispatch jalan).

### Strategi konten (keputusan owner)
- **@beruangfinance = AUTO-POST** (5 slot/hari: 07:17, 11:17, 15:17, 18:17, 21:17 WIB — sengaja beda menit dari faktaviral biar gak nabrak antrian GitHub).
- **@faktaviral.idn = TIDAK auto-post.** Tiap pagi (06:09 & 07:09 WIB) sistem auto-generate **2 konten "trending" terverifikasi** → commit ke dashboard sebagai PREVIEW (mode=none, gak ke-post). Owner review pagi → post manual. Owner mau konten BERKUALITAS (berita hangat / fakta yg lagi rame), bukan kuantitas.
- Owner suka momen viral; SUDAH BERKALI-KALI minta repost gosip/defamasi (rumor Prabowo–Teddy) + hapus watermark → SELALU DITOLAK (UU ITE, banned, brand "FAKTA" ancur). Tawarin alternatif aman tiap kali.

### Token IG — status PENTING
- ⚠️ **Error `(#10) Application does not have permission`** muncul di publish IG faktaviral (8 Juni), padahal #19/#20 sebelumnya sukses. Pemicu: owner ganti password FB → izin token ke-reset. **FIX: regenerate token** (centang SEMUA scope: `instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, business_management, pages_manage_posts`), pastiin akun **Bisnis** (bukan Creator), grant Page, tukar long-lived, update Secret `IG_ACCESS_TOKEN`. **Token belum di-fix per akhir sesi.**
- **@beruangfinance** butuh Secrets BARU: `IG_USER_ID_BF` + `IG_ACCESS_TOKEN_BF`. Owner sempat dapat `me/accounts` → `data: []` (Page belum ke-grant / akun belum Professional+link Page). **Belum beres per akhir sesi.**
- Token wajib ada `pages_manage_posts` biar auto-post FB jalan.

### Fitur baru yang DIBANGUN (semua di repo, branch default)
1. **Reel auto-musik** — `fakta-poster/music/` = 5 lagu Kevin MacLeod (CC-BY, lihat `CREDITS.txt`). `render_reel(...,music=)` di `fakta_video_maker.py` & `bf_video_maker.py` mixing lagu acak + fade-out. `daily_fakta.py`/`bf_daily.py` tulis `caption_reel.txt` (=caption + kredit musik); `publish_ig.py` pakai caption_reel buat reel. Owner mau reel manual (biar bisa lagu trending) — auto-musik buat yang auto.
2. **Auto-post Facebook Page** — `fakta-poster/facebook_uploader.py` + `publish_fb.py`. Carousel→album, reel→video. Page ke-deteksi otomatis dari `IG_USER_ID` (match instagram_business_account). Step "Publish ke Facebook" di kedua workflow, `continue-on-error: true` (IG tetap jalan kalau token FB belum siap). Secrets: reuse `IG_ACCESS_TOKEN`/`IG_ACCESS_TOKEN_BF` + opsional `FB_PAGE_ID`/`FB_PAGE_ID_BF`. NB: post via IG API TIDAK auto-crosspost ke FB — makanya butuh publisher ini.
3. **Mesin BERITA terverifikasi** — `fakta-poster/fakta_news.py`. Google CSE search (web) → verifikasi `totalResults >= NEWS_MIN_COVERAGE` (default 20, = "udah muncul 20+ kali / rame") + `dateRestrict` (trending=w1, keuangan/aktor=w2) biar fresh → Claude tulis carousel GROUNDED ke headline asli + sumber. `NEWS_CATEGORIES={trending,keuangan,aktor}` di `daily_fakta.py` (route ke fakta_news, fallback ke generate_fakta). DILARANG rumor pribadi/defamasi. Butuh Secrets `GOOGLE_API_KEY`+`GOOGLE_CSE_ID` (udah ditambah ke env workflow daily-fakta). **BELUM dites real** — minta owner Run `category:trending, post_mode:none` lalu cek log.
4. **30+ kategori faktaviral** — `NICHE_LABELS` di `fakta_image_maker.py` diperluas (sains…militer + keuangan/aktor/trending). Input `category` workflow diubah `choice`→`string` (bebas).
5. **Dashboard "Content Studio"** — `docs/dashboard.html` (PWA, 2 tab faktaviral/beruang). MONITOR (baca manifest) + GENERATE (workflow_dispatch via GitHub PAT yg disimpan di localStorage HP, tap ⚙️). Pilih kategori + aksi (Preview/Post). URL: **https://hendrypangg12.github.io/Claude/dashboard.html** (GitHub Pages dari docs/). `build_manifest.py` scan `*/published/` → `docs/faktaviral-manifest.json` + `docs/beruang-manifest.json`, dipanggil di commit-step kedua workflow (auto-update).
6. **Gating workflow** — step "Siapkan media + commit" SEKARANG selalu jalan (ungated) → konten selalu ke dashboard buat preview. Step publish digate `(github.event.inputs.post_mode || steps.slot.outputs.mode) != 'none'` (mode efektif). Schedule faktaviral pakai mode=none → preview doang.

### Catatan teknis lokal (sesi ini)
- **ffmpeg lokal**: `pip install imageio-ffmpeg` → `python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"` (container fresh, `/tmp/ffmpeg` gak ada).
- **Pexels foto** bisa di-download langsung via URL `images.pexels.com/photos/<id>/pexels-photo-<id>.jpeg` (hotlink, tanpa API key). PEXELS_API_KEY cuma di Secrets.
- **BMKG**: data resmi gempa real-time di `https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json` (+ `gempaterkini.json`); shakemap di `https://static.bmkg.go.id/<Shakemap>` (field "Shakemap" dari JSON).
- Bikin konten berita gempa M7,7/7,8 Mindanao (8 Juni) pakai template news Berstock + faktaviral cosmic (cover foto Pexels + slide shakemap BMKG). Render slide custom = import helper dari `fakta_image_maker` (_bg/_photo_bg/_brand_chip/_dots/_font/_save, R=2160, SIZE=1080, PAD=74).
- Title-card overlay reel (kotak putih + hashtag highlight cyan) + watermark "Follow @faktaviral.idn" → burn ke video pakai ffmpeg overlay PNG. Owner suka format ini.

## SESSION MEMORY — update 9 Juni 2026 (dini hari) — BERITA HANGAT + FOTO ASLI

> Lanjutan langsung dari sesi 8 Juni. Branch dev = `claude/new-session-7ysra`, semua di-merge ke default
> `claude/halo-bYUsl`. Owner mau konten BERITA viral yang HANGAT + visual SESUAI berita. SUDAH JADI & DITES.

### Masalah yang dibereskan: "berita trending selalu nyangkut ke 'tubuh manusia'"
- Penyebab: kategori berita (trending/keuangan/aktor) gagal verifikasi (Google CSE **403 terus**) → fallback ke fakta evergreen, dan fallback lama manggil `generate_fakta(category="trending")` = kategori palsu → bypass logika variasi → "tubuh terus".
- Fix #1 (`daily_fakta.py`): fallback pakai `fb_cat = None if category in NEWS_CATEGORIES else category` → mode Bebas + `avoid_categories` → gak ngulang topik.
- Fix #2 (UTAMA): **`web_search` jadi sumber berita UTAMA** (lihat bawah) → gak gantung ke Google Cloud lagi.

### Mesin berita BARU — `fakta-poster/fakta_news.py` (`generate_news`)
Urutan sumber: **(1) web_search Claude → (2) Google CSE + NewsAPI snippet → (3) fakta evergreen**.
1. **`_claude_web_news(category, avoid)`** = SUMBER UTAMA. Pakai server-side tool Anthropic
   `{"type":"web_search_20260209","name":"web_search","max_uses":5}`, model `claude-sonnet-4-6`,
   pakai `ANTHROPIC_API_KEY` (yg udah jalan) — **TANPA Google Cloud/NewsAPI**. Loop `stop_reason=="pause_turn"`
   (append `resp.content` ke messages, ulang). Ambil JSON dari text block terakhir (`_parse_json` punya
   fallback regex `\{.*\}`). Server-side tools cukup di-pass sbg dict mentah → SDK versi apa pun jalan.
2. **FRESHNESS = di bawah 4 JAM** (target utama; owner minta makin ketat: 1-3 hari → 6 jam → **4 jam**).
   Fallback ladder ke maks ~8 jam kalau <4 jam belum rame. KUNCI prompt: "di antara kandidat yang
   SAMA-SAMA rame & kredibel, PILIH YANG PALING BARU (umur jam terkecil)". Inject tanggal hari ini (WIB).
   ⚠️ TENSION nyata: <4 jam + "diberitakan 20+ media besar" sering bentrok (berita baru blm dikutip banyak).
   Owner udah dikasih tau; sistem ambil yg paling fresh-tapi-terverifikasi.
3. **SYARAT VIRAL** (logika owner): <4-6 jam, udah muncul 20+ kali di search, dari media terkenal
   (detik, Kompas, CNN/CNBC Indonesia, BBC, Tempo). BUKAN rumor pribadi/fitnah (UU ITE — stance lama tetap).

### FOTO ASLI berita (carousel + reel) — fitur besar sesi ini ✅ DITES JALAN
Owner WAJIB visual = foto/video KEJADIAN ASLI (mis. presiden pidato → foto pidato itu), bukan stok generik.
- web_search wajib balikin **`source_urls`** (2-4 URL artikel asli) di JSON output (field ditambah ke `SYSTEM`).
- **`_og_image(url)` + `_resolve_news_image(urls)`** di `fakta_news.py`: fetch artikel → ambil
  `og:image`/`twitter:image` = **foto yang dipakai outlet beritanya**. Return `_image_url`, `_image_article`,
  `_source_urls` di dict hasil. (snippet-path juga: fallback ke `it["link"]`.)
- **`media_fetcher.download_image(url, out)`**: download via Pillow → simpan JPG, **tolak <400px** (anti logo/ikon).
- **`fakta_video_maker.image_to_clip(img, out, dur=20)`**: ffmpeg `zoompan` Ken Burns 1080×1920 → 1 foto jadi
  klip reel bergerak (biar reel berita nampilin foto asli, bukan stok).
- **`daily_fakta.py`**: download `hero` dari `_image_url` (di LUAR gate PEXELS). Carousel cover (p1) WAJIB hero;
  p2/p3 prefer stok→hero. Reel: kalau ada hero → `reel_bg=[image_to_clip(hero)]` (else stok video). `meta.json`
  nyimpen `sumber` + `foto_asli` (bool). DITES: KPK OTT Bupati Muara Enim → `"foto_asli": true` ✅.
- ⚠️ Awalnya VIDEO mentah TIDAK di-download. TAPI **owner MINTA video kejadian asli** (9 Juni siang) → DIBANGUN:
  **`fakta-poster/news_video.py` `fetch_news_video(url,out,max_sec=18)`** (yt-dlp, cap 90MB, potong 18s, buang audio).
  web_search balikin **`video_url`** (link YouTube outlet berita resmi). `daily_fakta.py` prioritas reel:
  **video asli > foto asli (Ken Burns) > stok**. Kredit "🎥 Video: via <sumber>" ditambah ke `caption_reel.txt`.
  meta nyimpen `video_asli` (bool). `yt-dlp` ditambah ke `fakta-poster/requirements.txt`. Best-effort: kalau
  YouTube blokir IP CI / link gak ada → fallback otomatis ke foto. **TETAP TOLAK hapus watermark/kredit orang.**
  Owner sadar risiko copyright/Content ID video (strike/banned) = keputusan editorial dia. **BELUM dites di CI.**

### Jadwal & verifikasi
- **daily-fakta.yml**: tambah cron **`0 3 * * *` (10:00 WIB)** selain 06:09 & 07:09. Semua → cat=trending,
  **mode=none (PREVIEW, gak auto-post)** masuk dashboard buat review manual. (faktaviral tetap NO auto-post.)
- **Tes sukses (run #32)**: web_search nemu "baling-baling Wings Air diikat cable tie" (real, sumber CNN/Okezone/RRI),
  lalu "KPK OTT Bupati Muara Enim Edison" (sumber Kompas/Detik/ANTARA/VIVA, foto_asli=true). Log nunjukin
  `via web_search` + `✓ pakai FOTO ASLI berita`.
- og:image extraction udah dites lokal (network OK): berhasil narik gambar dari detik.com & cnnindonesia.com.

### TODO lanjutan (besok)
- Tes generate sekali lagi buat liat hasil <4 jam + foto asli barengan (owner blm sempat, mau tidur jam 1).
- (Opsional) opsi "keras: <4 jam atau skip" kalau owner mau.
- (Opsional polish) label cover berita masih "TAU GAK SIH?" — buat berita mending "LAGI VIRAL"/"BREAKING".
- Google CSE 403 masih ada tapi gak ngeganggu lagi (web_search jadi sumber utama). Boleh diabaikan / fix nanti.

## SESSION MEMORY — update 11 Juni 2026 — AUTO-POST IG LIVE ✅ (token #10 BERES)

> Token IG akhirnya FIXED & auto-post jalan. BACA ini buat status terbaru auto-posting.

### Token IG — RESOLVED (akhirnya!)
- Owner generate ulang token via Graph API Explorer (app "fakta viral bot" 1048502251194046) → centang scope
  lengkap (instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement,
  business_management) + **grant Page "Fakta Viral" + "Beruang Finance"** → Extend Access Token (Token Debugger)
  jadi **PERMANEN ("Expires: Never")**. Update ke GH Secrets.
- **1 token dipakai 2 akun** (granular scope `instagram_content_publish` = `17841431673727855` faktaviral +
  `17841473550306699` beruang). Secrets ke-set SEMUA: `IG_ACCESS_TOKEN`/`IG_USER_ID` (faktaviral) +
  `IG_ACCESS_TOKEN_BF`/`IG_USER_ID_BF=17841473550306699` (beruang).
- **IG ID: faktaviral=17841431673727855, beruang=17841473550306699.**
- ⚠️ `pages_manage_posts` GAK tersedia di app (use-case Instagram doang) → **Facebook Page auto-post GAGAL**
  (#200/#100), tapi step FB `continue-on-error` jadi gak ngegagalin run. Mau FB beneran = perlu App Review Meta.

### Auto-post status (LIVE)
- **daily-fakta.yml**: jadwal DINYALAIN lagi (06:09/07:09/10:00 WIB) + `mode=both` (carousel+reel) = **AUTO-POST**
  (bukan preview lagi). Owner pilih: konten **trending**, format **carousel+reel**. ⚠️ trending auto-post TANPA
  review = ada risiko topik sensitif → owner sadar, pantau.
- **DITES SUKSES (run #41)**: `[default] ✅ carousel id 18107651899948402` + `✅ reel id 18105421024804362`,
  "Sukses: 1 akun". Error #10 HILANG.
- **beruang-finance.yml**: tetep auto-post 5x/hari (07:17/11:17/15:17/18:17/21:17 WIB). Secret BF udah lengkap →
  harusnya jalan mulai jadwal berikutnya (BELUM dites manual per update ini).
- Owner mau: kalau beruang sukses, baru urus Facebook Pages (perlu pages_manage_posts/App Review).

### Konten manual yang dibuat sesi ini (render LOKAL, gak makan API)
- Carousel + **reel 15/45 detik** soal **korupsi MBG** (dapur tutup, dana belum cair, investor nagih) — gaya
  DARK CINEMATIC (charcoal + emas, BUKAN biru "norak") + foto asli berita (og:image Kompas/Liputan6/Detik,
  dikredit) + musik `investigations.mp3`. Script: `/tmp/make_mbg_*.py` (pakai imageio-ffmpeg + fakta_image_maker).
- Infografis **Harga BBM Pertamina 10 Juni 2026** (Pertamax 12.300→16.250, verified Kompas/CNBC) versi faktaviral
  (charcoal+emas, foto SPBU Kompas, tag @faktaviral.idn). Script `/tmp/make_bbm.py`.
- ⚠️ DITOLAK (konsisten): repost daftar 24 nama "pejabat terseret BAP MBG" dari akun lain (cuma 3 resmi tersangka:
  Dadan Hindayana, Sony Sonjaya, Lodewyk Pusung; sisanya BELUM tersangka → UU ITE/pencemaran). Tawarin versi aman.

### 11 Juni (lanjutan malam) — BERUANG LIVE + banyak polish
- **Beruang auto-post DITES SUKSES** (run #23 dari dashboard): `Publish ke Instagram (@beruangfinance) ✅`.
  IG ID beruang = `17841473550306699`, faktaviral = `17841431673727855`. 1 token permanen dipakai 2 akun.
- **Jadwal faktaviral DIROMBAK** (owner minta): 6 slot/hari, cron UTC=WIB-7:
  07:17 reel · 08:17 carousel · 12:11 reel · **16:11 EVERGREEN reel** · 18:00 carousel · **21:00 EVERGREEN carousel**.
  Evergreen = `cat=""` (Bebas, no web_search → murah ~Rp300). Trending ~Rp2rb/post (web_search). Resolver di `daily-fakta.yml`.
- **Anti rate-limit 429**: `concurrency: {group: ig-content-gen, cancel-in-progress: false}` di KEDUA workflow →
  faktaviral & beruang GAK jalan barengan (antri). Plus `max_retries=6` di semua Anthropic client.
- **Foto ASLI berita di SEMUA slide** (bukan cuma slide 1): `daily_fakta.py` ambil banyak og:image dari `_source_urls`
  (`_og_image`) → `hero_imgs[]`, tiap slide pakai foto asli (variasi kalau >1 sumber, else diulang). Stok cuma fallback.
- **Dashboard** (`docs/dashboard.html`, versi LIVE di halo = genPanel DINAMIS, bukan static): default Aksi diubah jadi
  **"Generate + Post (feed+reel+story)"** (dulu "Preview" → makanya konten dari dashboard "gak ke-post"). Plus
  **anti double-tap** (tombol mati 90s) → cegah 1 generate jadi 2 post.
- **Auto-story DIMATIIN** (`POST_STORY: "false"` di 2 workflow). Alasan: owner mau story = "Add post to story" yang
  CLICKABLE ke postingan, TAPI **IG API gak bisa** repost-feed-ke-story clickable (cuma manual di app). Fungsi
  `publish_story` (image/video) tetap ada di `instagram_uploader.py`/`publish_ig.py` tinggal nyalain `POST_STORY=true`.
- **Prompt caching** dipasang di loop web_search (`fakta_news.py`): `cache_control={"type":"ephemeral"}` (automatic),
  fallback `use_cache=False` kalau SDK lama (TypeError). Manfaat MODEST (cuma loop pause_turn; jadwal jarak jam → cache expired antar-run).
- **Konten kontroversial DITOLAK lagi**: daftar 24 nama BAP MBG + reframe "nama disebut Sony JC" → tetap UU ITE. Owner
  setuju "viral yang penting" TAPI stance nama-pribadi/defamasi tetap ditolak. Owner sadar konten sensitif (kekerasan
  anak dll) auto-post trending = risiko, pilih lanjut.

### Biaya API (info ke owner)
- Cuma **Anthropic** yang bayar (Pexels/NewsAPI/GitHub/IG-FB gratis). Sonnet 4.6: $3/1jt input, $15/1jt output;
  web_search ~$10/1000 search. Per generate: faktaviral ~$0.10-0.15, beruang ~$0.02. Jadwal sekarang ~$0.80/hari ≈ ~$25/bln.
- **Saldo 11 Juni: $10.33** (auto-reload MASIH MATI → owner disuruh nyalain biar gak berhenti mendadak; spend bulan ini $7.05).

### TODO lanjutan
- Facebook Pages auto-post masih GAGAL (#200 pages_manage_posts gak ada di app) → perlu App Review Meta. Step FB
  `continue-on-error` jadi tiap run nampil "1 error" palsu (IG tetep sukses). Bisa di-silence/matiin kalau owner mau.
- Owner perlu NYALAIN auto-reload Anthropic + (opsional) top-up biar auto-post gak berhenti pas saldo habis (~24 Juni).
- Story clickable = manual ("Add post to story" di app) tiap abis post.

### 12 Juni — REDESAIN BERSIH + video dari situs berita
- **Carousel DIREDESAIN** ke gaya BERSIH ala @fakta.indo / @indo_psikologi (owner mau "rapih, ga lebay"):
  `fakta_image_maker.py` compose_cover/fact/outro ditulis ulang. Cover = **foto full-bleed + judul KUNING+PUTIH**
  (kata kunci kuning, sisanya putih, helper `_split_hl` heuristik potong di koma/45% kata; bisa di-override field
  `highlight` dari generator nanti) + kredit "Sumber: X" + watermark `faktaviral.idn` + chip emas `FAKTAVIRAL`.
  Slide isi = **foto atas + panel gelap teks bawah** (auto-fit). Outro = takeaway + pill "Follow" emas. Palet baru
  `GOLD=(255,214,0)`. BUANG cosmic/bintang/"TAU GAK SIH?"/dots/cyan. `daily_fakta.py` passing `source=_sumber`.
- **VIDEO ASLI dari situs berita (bukan YouTube)**: penemuan penting — Kompas/Detik dll sering host **MP4 langsung**
  di CDN (mis. `assets-studiohub.kompas.com/.../*.mp4`) → bisa di-download via `requests` BIASA (gak kena bot-block
  YouTube, gak butuh cookies!). Probe og:video/twitter:player:stream/.mp4/.m3u8 di halaman artikel. DEMO sukses:
  reel konpers Shin Tae-yong (video Kompas + overlay bersih 9:16 blur-fill + kredit "Video: Kompas TV"). **BELUM
  diintegrasi ke auto-pipeline** (TODO: web_search/og kasih video_url situs berita → download → reel).
- **YouTube auto-download = GAGAL** di server (SSL proxy lokal + "confirm you're not a bot" 403 di CI). Workflow
  `clipper.yml` ("AI Video Clipper", udah ada di repo: transcribe→Claude pilih momen→9:16+caption) support
  `YT_COOKIES` secret. Owner dipandu cara export cookies (ekstensi "Get cookies.txt LOCALLY" di komputer; iOS gak bisa).

## SESSION MEMORY — update 13 Juni 2026 — FB AUTO-POST + AKUN KE-3 "STORY KANTOR"

> Branch dev sesi ini = `claude/new-session-7ysra`, semua di-merge ke default `claude/halo-bYUsl`.
> NOTE buat AI: **selalu auto-save memory ke CLAUDE.md tiap abis ngerjain project** (permintaan owner).

### Facebook Page auto-post — AKHIRNYA JALAN (faktaviral) ✅
- Dinding Meta tembus TANPA App Review/Tech Provider: di App Dashboard "fakta viral bot" (App ID `1048502251194046`)
  → **Kasus penggunaan "Kelola segala sesuatu di Halaman Anda" (Pages API)** → izin `pages_manage_posts` statusnya
  **"Siap untuk pengujian" (Standard Access)** = cukup buat admin app sendiri. JANGAN klik "Continue/Tech Provider"
  (irreversible + minta verifikasi bisnis). Generate token di Graph API Explorer (centang `pages_manage_posts`,
  `pages_read_engagement`, `pages_show_list`) → grant Page → Extend (permanen) → update Secret.
- **IG→FB crosspost toggle (Settings IG → Sharing to Facebook) cuma jalan buat post MANUAL, BUKAN API auto-post**
  (limitasi Meta). Makanya wajib `publish_fb.py` + `pages_manage_posts`.
- **ID PENTING:** FB user Hendry Pang `28092466593674265`. **FB Page: Fakta Viral=`1113692745165301`,
  Beruang Finance=`1144300008769890`.** IG: faktaviral=`17841431673727855`, beruang=`17841473550306699`.
- **Secrets baru:** `FB_PAGE_ID=1113692745165301`, `FB_PAGE_ID_BF=1144300008769890` (+ token di IG_ACCESS_TOKEN/
  IG_ACCESS_TOKEN_BF, 1 token permanen buat semua).
- **DITES SUKSES faktaviral**: carousel+reel ke IG **dan** FB Page "Fakta Viral" (`FB: ✅ album/carousel id...`).
- **`facebook_uploader.resolve_page` FIX**: prioritas diubah → **page_id eksplisit (FB_PAGE_ID/_BF) MENANG** dari
  tebakan IG-link. + log diagnostik "FB: Page yang kebaca token → ...".
- ⚠️ **BERUANG FB MASIH NYASAR ke Page Fakta Viral** per akhir sesi. Diagnosa (dari log): token `me/accounts`
  **cuma balikin "Fakta Viral"** — Page "Beruang Finance" GAK ke-grant ke token. `FB_PAGE_ID_BF` udah BENER;
  masalahnya **token belum grant Page Beruang**. FIX: regenerate token, di popup FB **centang DUA Page (opt in to all)**,
  pastiin owner **Admin** Page Beruang. Owner regenerate tapi **belum re-run** buat verifikasi → TODO besok.

### Anti-ulang topik (dedup) — diperkuat ke level SUBJEK
- Masalah: auto-post ngulang topik (World Cup berkali-kali; "Venus" 2x dalam semalam) karena avoid cuma cek JUDUL identik.
- FIX: `fakta_news._avoid_instruction` (berita) + `fakta_generator` avoid_line (evergreen) → sekarang **hindari
  SUBJEK/TEMA yang sama** (contoh eksplisit World Cup/Venus/gurita), bukan cuma kalimat. Berlaku carousel & reel.
- Dedup baca ±60 post terakhir dari `published/` (ke-commit) + history.json → cuma tau AUTO-post, bukan render manual lokal.

### Robustness generator (anti gagal)
- `bf_generator` + `fakta_generator` + `sk_generator`: `_parse_json` dikasih **regex fallback** + **auto-ulang 3x**
  (Claude sesekali balikin JSON cacat → dulu bikin `bf_daily` gagal total).
- `fakta_news.generate_news`/`_claude_web_news` dapat param **`topic`** → trending+topik nyari BERITA soal topik itu
  (fix bug dulu trending+topik malah keluar "sejarah" evergreen).

### Beruang carousel — REDESAIN bersih (ala faktaviral)
- `bf_image_maker.py` ditulis ulang: cover foto full-bleed + judul KUNING/PUTIH (`_split_hl`), slide isi foto-atas+panel
  3 poin (auto-fit), outro takeaway + pill Follow + beruang. Reuse `_photo_cover/_grad/_split_hl` dari fakta_image_maker.
  Palet `YELLOW=(255,198,0)`. Buang scrim coklat tebal/dots/swipe lama.

### Dashboard — tombol Generate anti double-tap (beneran)
- `docs/dashboard.html`: dulu tombol kebuka lagi after 90s (timer) padahal run 3-5 menit → bisa ke-tap 2x = double post.
  Sekarang flag `genBusy` + `genDone()` → tombol **mati sampai run BENERAN selesai** (trackWf deteksi), guard re-tap
  walau panel re-render. Konsisten di tab Clipper.

### AKUN KE-3 BARU: "Story Kantor" (@storykantor.idn) — sindiran/relatable kerja, GAYA FOLKATIVE
- Owner mau akun ke-3. Pilihan: (1) sindiran kerja ✅dipilih, (2) zodiak, (3) quote galau. Nama final **storykantor.idn**.
- Referensi = **Folkative**: post **putih bersih + teks hitam bold gede**, brand kecil kanan-atas, minimalis "ga lebay".
- Folder **`story-kantor/`**: `sk_generator.py` (Claude `claude-sonnet-4-6`, output {topic,hook,lines[2],caption},
  retry+regex, DILARANG kasar/SARA/nyebut nama), `sk_image_maker.py` (BG putih `(252,252,250)` + INK `(24,24,26)`,
  brand "STORY KANTOR" kecil bold kanan-atas, handle kiri-bawah + counter kanan-bawah; `compose_statement(text,out,idx,
  total,last)`; `make_profile()` = foto profil HITAM + wordmark "STORY KANTOR" putih bold 2 baris), `sk_daily.py`
  (carousel 3 slide teks, NO foto/video). Workflow `.github/workflows/story-kantor.yml` (3 slot/hari menit :37;
  publish **skip mulus kalau `IG_USER_ID_SK` kosong**; reuse IG_ACCESS_TOKEN; concurrency grup `ig-content-gen`).
- Owner UDAH pasang foto profil hitam. Name disaranin "Story Kantor | Relatable Anak Kantoran", Bio dikasih 3 opsi.
- **TODO biar auto-post LIVE: owner kasih `IG_USER_ID_SK`** (IG User ID @storykantor.idn) → set Secret. Story Kantor
  BELUM diintegrasi ke dashboard/`build_manifest.py` (cuma via Actions Run manual / nanti).

### Cron GitHub makin gak reliable
- 13 Juni pagi: slot faktaviral **07:17 & 08:17 ke-skip total** (kemarin masih jalan). Murni keandalan GitHub jelek.
- Solusi disaranin: **trigger eksternal cron-job.org** (panggil API workflow_dispatch pakai PAT) biar tepat waktu.
  Sementara: **Run manual dari dashboard**. (Belum dipasang per akhir sesi.)

### Konten manual sesi ini (render LOKAL, gak ke-commit)
- **Carousel BBM subsidi langka** (faktaviral) pakai FOOTAGE ASLI owner: video SPBU Pertamina ditempel "BBM DALAM
  PENGIRIMAN" plat B (Jakarta) → extract frame pakai ffmpeg → `compose_cover/fact/outro`. Headline "BBM subsidi
  menjadi langka, warga Jakarta dipaksa beli Pertamax". Framing AMAN (kritik situasi, gak nuduh nama → UU ITE aman).
- **Reel Earth Hour** (faktaviral): "Jakarta padamkan lampu 1 jam malam ini" — VERIFIED via web_search (Sabtu 13 Juni
  20.30-21.30 WIB, Hari Lingkungan Hidup, simbolis di Monas/Bundaran HI/Balai Kota, **BUKAN mati listrik beneran**).
  Foto kota malam (Pexels hotlink) → `image_to_clip` Ken Burns → `make_reel_overlay`+`render_reel` + musik.
- **Banyak slide Story Kantor**: cari muka, sabtu kerja, sebelum tidur, weekend/Sunday-scaries (semua single-slide putih).
- **Render lokal**: ffmpeg via `imageio-ffmpeg` (set env `FFMPEG`=imageio exe; ffprobe gak ada → `_duration` return 0,
  aman). Pexels foto via hotlink `images.pexels.com/photos/<id>/...`. Frame video: `ffmpeg -i src -vf fps=1 ...`.

### 14 Juni — dedup "peristiwa sama angle beda" + logo + cron makin parah
- **Bug dobel lagi**: event lari Jakarta keluar 2x ("45rb pelari banjiri jalan" + "Jakarta macet gara-gara event").
  Peristiwa SAMA, angle beda (lari vs macet) → dedup lama lolos. FIX `fakta_news._avoid_instruction`: suruh
  **identifikasi PERISTIWA INTI dulu**, larang semua angle dari peristiwa yang sama (contoh eksplisit lari→macet).
- **Madu keluar 2x** ("Madu...berusia 3.000 tahun" 13 & 14 Juni, nyaris identik) → prompt-avoid gak cukup.
  **DEDUP LEVEL KODE** ditambah di `daily_fakta.py`: `_is_dup(hook, recent)` = overlap kata penting (≥4 kata sama
  atau Jaccard≥0.5) vs ~60 post terakhir → kalau mirip, **REGENERATE (maks 3x), gak jadi upload**. 2 lapis (kode +
  prompt). Di-skip kalau owner maksa topik. NB: belum dipasang di `bf_daily`/`sk_daily` (beruang/story-kantor) — TODO kalau perlu.
- **15 Juni: IHSG keluar 2x** (jam beda) — lolos karena overlap kata pas di bawah ambang. FIX: `_acronyms()` di `_is_dup`
  → kalau 2 hook share AKRONIM kapital subjek sama (IHSG/BBM/MBG/KPK/TNI/DPR) langsung dianggap dobel. Story Kantor
  auto-post mulai jalan (ada commit `story-kantor/published/...`).
- **16 Juni: madu keluar 3x** ("makam Firaun" vs "3.000 tahun" — fakta beda, subjek SAMA, cuma share kata "madu"). FIX:
  lapis dedup ke-4 di `daily_fakta.py` = **subjek visual (`query`)**. Simpan `query` di meta.json (mis. "honey") →
  `_subj_dup()` tolak kalau subjek udah dipakai di ~60 post terakhir (`_recent_subjects`). Ada `_Q_GENERIC` (buang
  query generik spt money/people/world). Nangkep madu (honey) & air mata/nangis (eye/tears). Total 4 lapis dedup:
  (1) hook nyaris-identik, (2) akronim, (3) subjek query, (4) prompt peristiwa-inti. Cuma jalan utk post yg `query`-nya
  udah ke-simpan (mulai efektif setelah 1 siklus). NB: masih cuma di faktaviral, belum beruang/story-kantor.
- **Akar ke-2 = cron pile-up**: cron pagi (00:17/01:17 UTC = 07:17/08:17 WIB) **konsisten ke-skip** (jam sibuk GitHub).
  Owner run manual → cron telat nyusul → 3 post trending numpuk 2 jam → semua ngejar berita terpanas (event lari).
  Solusi permanen disaranin lagi: **cron-job.org** (BELUM dipasang). Sementara: run manual dari dashboard.
- **Logo Fakta Viral baru**: owner ganti ke **hitam + "FAKTA" putih + "VIRAL" kuning/emas + garis bawah emas**
  (rekomendasi `fv_black`). Putih+kuning DITOLAK (kontras rendah). Mock-up dirender lokal pakai `_font` + GOLD=(255,214,0).
- **Konten manual sesi ini**: carousel + REEL misteri akun IG **@moapies** (28 juta post, private, bio "Tag me in the
  post you found me to get accepted" — VERIFIED via web_search, akun viral nyata, teori dilabel "teori", + caution
  jangan asal tag/follow). Reel pakai screenshot owner sbg bg (Ken Burns) + `make_reel_overlay`/`render_reel` + musik
  investigations.mp3. Reels > carousel buat topik misteri (jangkauan Explore).

### 19-28 Juni — SALDO ANTHROPIC HABIS → MODE HEMAT (RSS tanpa Anthropic)
- **Auto-post mati total sejak ~19 Juni**: semua run `failure` → error `400 "Your credit balance is too low"`.
  Saldo Anthropic HABIS (auto-reload mati dari dulu). Generate butuh Anthropic → gagal → gak ada yg ke-post.
  Owner mau HEMAT biaya, gak mau top-up dulu.
- **MODE HEMAT dibangun** — auto-post berita TANPA Anthropic (gratis): **`fakta-poster/rss_news.py`**
  `fetch_rss_item(category, avoid)` → ambil berita dari **RSS CNN Indonesia + ANTARA** (gratis, no key;
  detik diblok proxy, tempo XML rusak). Feeds: trending=nasional/teknologi, keuangan=ekonomi, aktor=hiburan.
  Foto pakai **og:image** halaman artikel (penuh ~1200px; enclosure RSS cuma 360px ditolak <400). Output dict
  kompatibel generate_fakta + generate_content (beruang). Ada **filter `_BLOCK`** (skip konten sensitif:
  bunuh diri/perkosa/mutilasi/narkoba + iklan: transmart/diskon/promo) krn no-AI gak ada yg nyaring. Anti-dobel `_dup`.
- **Wiring**: `daily_fakta.py` & `bf_daily.py` cek env **`NO_AI=true`** → pakai RSS (faktaviral=trending,
  beruang=keuangan), foto berita asli tiap slide, beruang carousel-only (no reel). Workflow `daily-fakta.yml` +
  `beruang-finance.yml` di-set `NO_AI: "true"` (HAPUS baris itu buat balik ke AI berkualitas).
- ⚠️ **Trade-off** (dikasih tau owner): RSS mentah = kurang kurasi (kadang berita crime/dark lolos walau udah difilter),
  gak ditulis ulang. Story Kantor BELUM ada mode hemat (butuh AI buat quote relatable — gak ada RSS-nya).
- DITES LOKAL render OK: carousel "Purbaya bongkar mesin baru Prabowo ekonomi 8%" (foto asli CNN + judul faktaviral, no AI).

## Snake game

Single-file browser game: a Nokia 3310-style Snake clone. Everything (HTML, CSS, game logic) lives in `index.html`. There is no build system, no package manager, no test runner, and no external dependencies.

History note: the repo previously hosted Flappy Bird, then Tetris, then was replaced by Snake (see `git log`). When asked to swap the game, replace `index.html` wholesale rather than layering games side-by-side.

## Running / iterating

- Open `index.html` directly in a browser, or serve the directory (`python3 -m http.server`) and visit it. There is no dev server, no hot reload, no transpile step.
- After edits, just reload the browser. There are no tests or linters configured — visual/manual play-testing is the only verification.
- High score persists in `localStorage` under the key `nokia-snake-hi`; clear it from devtools if you need a fresh run.

## Architecture (inside `index.html`)

The game logic is a single IIFE at the bottom of the file. Key pieces to understand before changing behavior:

- **Grid model.** The canvas is `240×200` with `CELL = 10`, giving a fixed `24×20` grid. Coordinates throughout the code are grid cells, not pixels — only the draw helpers multiply by `CELL`. Changing canvas size or `CELL` requires they stay divisible.
- **`state` object.** Single source of truth for snake body, current/pending direction, food, score, hi-score, status, and timing accumulator. The status state machine is `ready → playing → paused ⇄ playing → over` (with `over → ready` via `reset()`).
- **Direction buffering.** Input writes to `state.pendingDir`; `tick()` commits it to `state.dir`. `setDir()` rejects 180° reversals. This is what prevents a fast double-tap from making the snake collide with itself — preserve this pattern when adding input sources.
- **Fixed-timestep loop.** `loop(t)` uses `requestAnimationFrame` for rendering but advances game logic in discrete `state.tickMs` steps via an accumulator. Difficulty scaling lives in `tick()`: each food eaten subtracts 3ms, floored at 55ms. Don't move speed logic into the render path.
- **Self-collision rule.** When the next head cell equals the food, the tail does NOT vacate this turn, so the collision check uses the full body; otherwise it uses `snake.slice(1)`. This subtlety matters if you refactor movement.
- **Rendering.** `drawBackground` paints the LCD-green palette plus a checkerboard dither and inner border; `drawSnakeSegment` draws the nested-square retro look; overlay screens (`ready`/`paused`/`over`) go through `drawCenteredText`. The Game Boy-ish palette constants (`BG_LIGHT`, `BG_DIM`, `FG_DARK`, `FG_MID`) are the canonical colors — reuse them rather than introducing new hex values.
- **Input surfaces.** Three parallel input paths feed `setDir`/`togglePause`/`reset`: keyboard (`keydown`), on-screen keypad (`.key` click handlers), and canvas touch swipes. Any new control should route through these same functions, not mutate `state` directly.

## Conventions

- Keep the project a single self-contained `index.html`. Don't introduce a build step, framework, or split files unless explicitly asked.
- Match the existing Nokia/Game Boy aesthetic (LCD green palette, pixelated rendering via `image-rendering: pixelated`, monospace HUD font) when adding UI.
- `git log` shows feature work lands via PRs from `claude/<feature>-<id>` branches into `main`. Develop on the branch you've been given and push there.
