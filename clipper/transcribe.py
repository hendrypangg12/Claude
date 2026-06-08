"""Download a video from ANY link (YouTube / TikTok / Instagram / X / FB / ...) and
transcribe it with WORD-LEVEL timestamps using faster-whisper.

No paid speech API — faster-whisper runs locally (CPU) and is free. The word
timestamps drive both the viral-moment picker and the karaoke-style captions.
"""
import os
import re
import shutil
from pathlib import Path


def _bin(name: str, env: str) -> str:
    return os.environ.get(env) or shutil.which(name) or name


FFMPEG = _bin("ffmpeg", "FFMPEG")


def pick_handle(info: dict) -> str:
    """Best-effort @username of the original creator (for credit). yt-dlp's
    uploader_id is often numeric, so fall back through channel/title/uploader."""
    ch = info.get("channel")
    if ch and " " not in ch:
        return ch
    m = re.search(r"\bby\s+([A-Za-z0-9_.]+)", info.get("title") or "")
    if m:
        return m.group(1)
    uid = str(info.get("uploader_id") or "")
    if uid and not uid.isdigit():
        return uid.lstrip("@")
    return (info.get("uploader") or "").strip()


def download(url: str, out_dir: Path):
    """Download the best MP4 for any supported URL. Returns (video_path, info dict)."""
    import yt_dlp

    ff_dir = str(Path(FFMPEG).parent) if os.path.sep in FFMPEG else None
    opts = {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio/best/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
        "noprogress": True,
        "retries": 3,
        # YouTube sering blokir IP datacenter (GitHub Actions) dgn "Sign in to confirm
        # you're not a bot". Coba beberapa client (android/ios/tv) yg lebih jarang kena.
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "tv", "web"]}},
    }
    cookies = os.environ.get("YT_COOKIES", "").strip()
    if cookies:
        cf = out_dir / "cookies.txt"
        cf.write_text(cookies, encoding="utf-8")
        opts["cookiefile"] = str(cf)
    if ff_dir:
        opts["ffmpeg_location"] = ff_dir
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Sign in to confirm" in msg or "not a bot" in msg or "cookies" in msg.lower():
            raise RuntimeError(
                "YouTube nolak download dari server GitHub (IP-nya dikira bot). "
                "Solusi: (1) pakai link TikTok / Instagram (biasanya lolos), atau "
                "(2) pasang cookies YouTube via secret YT_COOKIES, atau "
                "(3) coba lagi beberapa menit (kadang lolos)."
            ) from e
        raise
    vids = [f for f in sorted(out_dir.glob("source.*"))
            if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not vids:
        raise RuntimeError("Download gagal — gak ada file video yang ke-download dari link itu.")
    return vids[0], info


def transcribe(video: Path, language: str = "id", model_size: str | None = None) -> dict:
    """Transcribe with word timestamps.

    language: "id" (default), "en", or "auto" to let Whisper detect.
    model_size: tiny|base|small|medium (default from WHISPER_MODEL env, else "small").
    """
    from faster_whisper import WhisperModel

    model_size = model_size or os.environ.get("WHISPER_MODEL", "small")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    lang = None if language in ("auto", "", None) else language

    segments, info = model.transcribe(
        str(video),
        language=lang,
        word_timestamps=True,
        vad_filter=True,                       # buang silence biar timestamp rapi
        vad_parameters={"min_silence_duration_ms": 400},
    )

    seg_list, words = [], []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            seg_list.append({"start": float(seg.start), "end": float(seg.end), "text": text})
        for w in (seg.words or []):
            tok = (w.word or "").strip()
            if tok:
                words.append({"start": float(w.start), "end": float(w.end), "word": tok})

    return {
        "language": info.language,
        "duration": float(info.duration or 0),
        "segments": seg_list,
        "words": words,
    }
