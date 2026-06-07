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
