# AI Video Clipper 🎬

Kasih **1 link video** (YouTube / TikTok / Instagram / X / Facebook) → sistem otomatis:

1. **Download** video (yt-dlp, support hampir semua platform).
2. **Transcribe** Bahasa Indonesia dengan timestamp per kata (faster-whisper — lokal, gratis, gak butuh API bayar).
3. **Pilih momen paling viral** pakai Claude (`claude-sonnet-4-6`) — kayak Opus Clip.
4. **Potong** tiap momen jadi clip **9:16** + **caption auto kata-per-kata** (ala TikTok) + brand chip.
5. Hasil + caption siap-posting muncul di **dashboard**.

## Cara pakai (dari HP)

1. Buka **GitHub → repo `Claude` → tab Actions → workflow "AI Video Clipper" → Run workflow**.
2. Isi:
   - **url** — paste link videonya.
   - **num_clips** — mau berapa clip (default 4).
   - **language** — `id` (default), `en`, atau `auto`.
   - **brand** — tulisan di pojok (default `BERSTOCK.ID`).
3. Tunggu jalan (download + transcribe makan waktu; video panjang bisa 10-20 menit).
   - ⚠️ Step **"Publish"** gak ada — clipper cuma BIKIN clip, gak auto-post.
   - Yang penting step **"Generate clips" + "Commit"** ✅ ijo.
4. Buka **https://hendrypangg12.github.io/Claude/clipper.html** → semua clip nongol, bisa
   **preview**, **salin caption**, dan **download** langsung dari HP.

## Jalan lokal (opsional)

```bash
cd clipper
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # wajib
# ffmpeg: pip install imageio-ffmpeg, lalu set FFMPEG ke hasilnya, ATAU apt install ffmpeg
python clip_app.py "https://youtu.be/xxxx" --num 4 --lang id
# hasil → out/<timestamp>/clip-*.mp4 + caption-*.txt + meta.json
```

## Isi folder

| File | Fungsi |
|---|---|
| `clip_app.py` | Orchestrator (download → transcribe → pilih → render). |
| `transcribe.py` | yt-dlp download + faster-whisper (word timestamps). |
| `pick_clips.py` | Claude pilih momen viral → `{start,end,score,title,hook,caption}`. |
| `captions.py` | Bikin ASS karaoke (kata aktif highlight emas). |
| `face_track.py` | Track wajah (OpenCV) → drive crop dinamis 9:16. |
| `render.py` | ffmpeg: cut + reframe 9:16 (face-track) + burn caption + brand chip. |
| `build_clipper_manifest.py` | Update `docs/clipper-manifest.json` buat dashboard. |

## Catatan

- **Whisper model**: default `small` (env `WHISPER_MODEL`). `base`/`tiny` lebih cepat tapi
  kurang akurat; `medium` lebih akurat tapi lambat di CPU GitHub Actions.
- **Reframe 9:16 + face-tracking**: crop vertikal otomatis ngikutin wajah pembicara
  (OpenCV Haar, di-smooth biar gak goyang). Kalau gak ketemu wajah → balik ke center-crop.
  Matiin pakai `--no-track` atau env `FACE_TRACK=0`.
- **Transkrip panjang** (>~1.5 jam) dipotong sebelum dikasih ke Claude.
- **Hak cipta**: clipper ini buat motong video yang KAMU punya / izinkan. Mau repost punya
  orang? Pastiin ada izin — kredit ≠ izin.
