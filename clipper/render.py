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
CYAN = (34, 211, 238, 255)        # faktaviral accent
INK = (8, 18, 26, 255)
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


def make_brand_png(out_png: Path, brand: str = "FAKTAVIRAL.IDN",
                   credit: str | None = None) -> Path:
    """Transparent 1080x1920 overlay: faktaviral brand chip up top, a 'via @creator'
    credit chip lower-left, and a small 'Follow @faktaviral.idn' line under the brand."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # brand chip (cyan), top-center
    f = _font("Poppins-ExtraBold.ttf", 46)
    tw = f.getlength(brand)
    px, py = 28, 16
    x = (W - (tw + 2 * px)) / 2
    y = 96
    d.rounded_rectangle([x, y, x + tw + 2 * px, y + f.size + 2 * py],
                        radius=30, fill=CYAN)
    d.text((x + px, y + py - 6), brand, font=f, fill=INK)

    # follow tagline under the brand
    sf = _font("Poppins-SemiBold.ttf", 30)
    sub = "Follow buat momen viral tiap hari"
    sw = sf.getlength(sub)
    sy = y + f.size + 2 * py + 14
    d.rounded_rectangle([(W - sw) / 2 - 16, sy, (W + sw) / 2 + 16, sy + sf.size + 16],
                        radius=22, fill=(0, 0, 0, 140))
    d.text(((W - sw) / 2, sy + 6), sub, font=sf, fill=WHITE)

    # creator credit chip, lower-left (above the Reels caption zone)
    if credit:
        handle = credit if str(credit).startswith("@") else f"@{credit}"
        cf = _font("Poppins-SemiBold.ttf", 32)
        text = f"via {handle}"
        ctw = cf.getlength(text)
        cx, cy = 70, int(H * 0.80)
        cpx, cpy = 18, 12
        d.rounded_rectangle([cx, cy, cx + ctw + 2 * cpx, cy + cf.size + 2 * cpy],
                            radius=24, fill=(0, 0, 0, 150))
        d.text((cx + cpx, cy + cpy - 4), text, font=cf, fill=WHITE)

    img.save(out_png)
    return out_png


def build_pan_script(face: dict, out_path: Path) -> tuple[Path, int] | None:
    """Turn a face track into a sendcmd script that pans crop x to keep the face
    centered. Returns (script_path, init_x) or None when there's no room to pan
    (portrait/near-vertical source) or no track."""
    track = (face or {}).get("track") or []
    sw, sh = (face or {}).get("src_w", 0), (face or {}).get("src_h", 0)
    if not track or sw <= 0 or sh <= 0:
        return None
    scale_factor = max(W / sw, H / sh)
    scaled_w = sw * scale_factor
    max_x = scaled_w - W
    if max_x < 4:                       # already ~9:16 wide → nothing to pan
        return None

    def _x(frac: float) -> int:
        return int(max(0.0, min(max_x, frac * scaled_w - W / 2.0)))

    lines = [f"{t:.2f} crop x {_x(frac)};" for t, frac in track]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, _x(track[0][1])


def render_clip(source: Path, start: float, end: float, ass_path: Path,
                brand_png: Path, out_mp4: Path, face: dict | None = None) -> Path:
    dur = max(0.5, end - start)
    fonts_dir = next((str(d) for d in FONT_DIRS if d.exists()), str(FONT_DIRS[0]))
    pan = build_pan_script(face, out_mp4.with_suffix(".pan.txt")) if face else None
    # subtitles + fontsdir paths: our paths have no ':' so plain single-quoting is safe
    if pan:
        script, init_x = pan
        crop = f"sendcmd=f='{script}',crop={W}:{H}:x={init_x}:y=0"
    else:
        crop = f"crop={W}:{H}"          # static center crop (fallback)
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,setsar=1,"
        f"{crop},"
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
