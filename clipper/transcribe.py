"""Download a video from ANY link (YouTube / TikTok / Instagram / X / FB / ...) and
transcribe it with WORD-LEVEL timestamps using faster-whisper.

No paid speech API — faster-whisper runs locally (CPU) and is free. The word
timestamps drive both the viral-moment picker and the karaoke-style captions.
"""
import os
import shutil
from pathlib import Path


def _bin(name: str, env: str) -> str:
    return os.environ.get(env) or shutil.which(name) or name


FFMPEG = _bin("ffmpeg", "FFMPEG")


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
    }
    if ff_dir:
        opts["ffmpeg_location"] = ff_dir
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
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
