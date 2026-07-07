"""Reel 'Story Kantor' sederhana: 1 statement card vertikal (1080x1920) + zoom pelan
(Ken Burns) + musik royalty-free opsional (bank musik yang sama dipakai faktaviral/beruang).

Beda dari fakta_video_maker (yang overlay 2-3 layer teks di atas video stok) — di sini
teksnya UDAH baked di gambar (sk_image_maker.compose_statement_vertical), jadi cukup
1 foto statis + zoom, gak perlu compositing macam-macam.
"""
import os
import random
import shutil
import subprocess
from pathlib import Path

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
MUSIC_DIR = Path(__file__).resolve().parent.parent / "fakta-poster" / "music"
_DEVNULL = subprocess.DEVNULL


def pick_music() -> str | None:
    if not MUSIC_DIR.is_dir():
        return None
    tracks = [p for p in MUSIC_DIR.iterdir()
              if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg")]
    return str(random.choice(tracks)) if tracks else None


def music_credit(path: str) -> str:
    title = Path(path).stem.replace("-", " ").replace("_", " ").title()
    return f"🎵 Musik: \"{title}\" — Kevin MacLeod (incompetech.com) · Lisensi CC BY 4.0"


def render_reel(image_path: str, out_path: str, dur: int = 12,
                music: str | None = None, music_vol: float = 0.5) -> str:
    """Foto vertikal statis (udah 1080x1920) → reel dgn zoom pelan + musik opsional."""
    frames = max(int(dur * 30), 30)
    # x/y dipusatkan (default zoompan crop dari pojok kiri-atas → bisa motong teks/brand di tepi)
    vf = (
        f"zoompan=z='min(zoom+0.0004,1.06)':d={frames}:s=1080x1920:fps=30:"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',setsar=1,format=yuv420p"
    )
    cmd = [FFMPEG, "-y", "-loop", "1", "-i", image_path]
    if music and os.path.isfile(music):
        fade_st = max(0.0, dur - 2.0)
        cmd += ["-stream_loop", "-1", "-i", music, "-t", str(dur), "-vf", vf,
                "-filter_complex",
                f"[1:a]volume={music_vol},afade=t=out:st={fade_st}:d=2,"
                f"atrim=0:{dur},asetpts=PTS-STARTPTS[aud]",
                "-map", "0:v", "-map", "[aud]",
                "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-shortest", out_path]
    else:
        cmd += ["-t", str(dur), "-vf", vf, "-c:v", "libx264", "-r", "30",
                "-pix_fmt", "yuv420p", "-an", out_path]
    subprocess.run(cmd, check=True, stdout=_DEVNULL, stderr=_DEVNULL)
    return out_path
