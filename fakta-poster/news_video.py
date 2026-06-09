"""Download VIDEO kejadian asli dari URL publik (yt-dlp) buat reel BERITA.

Best-effort: dipakai kalau owner mau reel pakai footage asli (bukan foto/stok).
Kalau gagal (YouTube blokir IP CI, bukan video, kegedean) → RAISE, caller fallback
ke foto Ken Burns / stok. SELALU kasih kredit 'via <sumber>' di caption (jangan hapus
watermark sumber). Reposting video orang = risiko copyright → keputusan editorial owner.
"""
import os
import shutil
import subprocess
from pathlib import Path

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"

MAX_SRC_BYTES = 90 * 1024 * 1024  # jangan download video raksasa di CI


def fetch_news_video(url: str, out_dir: str, max_sec: int = 18) -> str:
    """Download video dari `url`, potong ke `max_sec` detik → out_dir/news_video.mp4.
    Return path. Raise kalau gagal (caller boleh fallback ke foto)."""
    import yt_dlp

    od = Path(out_dir)
    od.mkdir(parents=True, exist_ok=True)
    ff_dir = str(Path(FFMPEG).parent) if os.path.sep in FFMPEG else None
    opts = {
        "outtmpl": str(od / "newsrc.%(ext)s"),
        # cap resolusi biar file kecil & cepat (reel cuma 1080 lebar)
        "format": "best[ext=mp4][height<=1280]/best[ext=mp4]/best",
        "quiet": True,
        "noplaylist": True,
        "noprogress": True,
        "max_filesize": MAX_SRC_BYTES,
        "retries": 2,
    }
    if ff_dir:
        opts["ffmpeg_location"] = ff_dir
    with yt_dlp.YoutubeDL(opts) as y:
        y.extract_info(url, download=True)

    vids = [f for f in od.glob("newsrc.*")
            if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not vids:
        raise RuntimeError("yt-dlp tidak menghasilkan file video")
    src = vids[0]

    # potong ke max_sec (re-encode → kompatibel buat render_reel; buang audio aslinya)
    out = od / "news_video.mp4"
    subprocess.run(
        [FFMPEG, "-y", "-i", str(src), "-t", str(max_sec),
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", str(out)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        src.unlink()  # hapus source mentah, simpan yang udah dipotong
    except OSError:
        pass
    return str(out)
