"""Render a single 9:16 clip: cut the segment, reframe to 1080x1920 (fill + center
crop, works for any source aspect), burn in the karaoke captions, and stamp a brand
chip. Uses ffmpeg (path from FFMPEG env or PATH)."""
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT_DIRS = [HERE / "fonts", HERE.parent / "daily-news-poster" / "fonts"]
SYS_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

GOLD = (255, 196, 0, 255)
INK = (15, 18, 26, 255)
WHITE = (245, 247, 251, 255)

W, H = 1080, 1920


def _bin(name: str, env: str) -> str:
    return os.environ.get(env) or shutil.which(name) or name


FFMPEG = _bin("ffmpeg", "FFMPEG")


def _font(file: str, size: int) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        p = d / file
        if p.exists():
            return ImageFont.truetype(str(p), size)
    for p in SYS_FONTS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_brand_png(out_png: Path, brand: str = "BERSTOCK.ID") -> Path:
    """A transparent 1080x1920 overlay with a gold brand chip near the top."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font("Poppins-ExtraBold.ttf", 46)
    tw = f.getlength(brand)
    px, py = 28, 16
    x = (W - (tw + 2 * px)) / 2
    y = 96
    d.rounded_rectangle([x, y, x + tw + 2 * px, y + f.size + 2 * py],
                        radius=30, fill=GOLD)
    d.text((x + px, y + py - 6), brand, font=f, fill=INK)
    img.save(out_png)
    return out_png


def render_clip(source: Path, start: float, end: float, ass_path: Path,
                brand_png: Path, out_mp4: Path) -> Path:
    dur = max(0.5, end - start)
    fonts_dir = next((str(d) for d in FONT_DIRS if d.exists()), str(FONT_DIRS[0]))
    # subtitles + fontsdir paths: our paths have no ':' so plain single-quoting is safe
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,"
        f"subtitles='{ass_path}':fontsdir='{fonts_dir}'[v];"
        f"[v][1:v]overlay=0:0:format=auto[o]"
    )
    cmd = [
        FFMPEG, "-y",
        "-ss", f"{start:.2f}", "-i", str(source), "-t", f"{dur:.2f}",
        "-i", str(brand_png),
        "-filter_complex", vf,
        "-map", "[o]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_mp4
