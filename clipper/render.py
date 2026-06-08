"""Render a single 9:16 clip: cut the segment, reframe to 1080x1920 (fill + center
crop, works for any source aspect), burn in the karaoke captions, and stamp a brand
chip. Uses ffmpeg (path from FFMPEG env or PATH)."""
import os
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Poppins can't render colour emoji → strip them from burned text (keep in caption).
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U00002190-\U000021FF️‍]")


def _clean(s: str) -> str:
    return _EMOJI.sub("", s or "").strip()

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


def _wrap_tokens(d: ImageDraw.ImageDraw, text: str, font, max_w: float):
    """Greedy word-wrap → list of token-lists that each fit within max_w."""
    space = d.textlength(" ", font=font)

    def width(toks):
        return (sum(d.textlength(t, font=font) for t in toks)
                + space * (len(toks) - 1)) if toks else 0

    lines, cur = [], []
    for w in (text or "").split():
        if not cur or width(cur + [w]) <= max_w:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
    if cur:
        lines.append(cur)
    return lines, space


def make_overlay_png(out_png: Path, brand: str = "FAKTAVIRAL.IDN",
                     title: str = "", credit: str | None = None) -> Path:
    """Per-clip overlay: brand chip (top) + burned-in HOOK title card (the @creator
    headline) + 'via @creator' credit. @handles are highlighted cyan."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # brand chip (cyan), small, very top
    bf = _font("Poppins-ExtraBold.ttf", 40)
    bw = bf.getlength(brand)
    bpx, bpy = 24, 13
    bx, by = (W - (bw + 2 * bpx)) / 2, 60
    d.rounded_rectangle([bx, by, bx + bw + 2 * bpx, by + bf.size + 2 * bpy],
                        radius=26, fill=CYAN)
    d.text((bx + bpx, by + bpy - 5), brand, font=bf, fill=INK)

    # HOOK title — CapCut style: black bold UPPERCASE on white boxes, lower-middle.
    if _clean(title):
        ttl = _clean(title).upper()
        max_w = 840
        for size in (62, 58, 54, 50, 46, 42):
            tf = _font("Poppins-ExtraBold.ttf", size)
            lines, _ = _wrap_tokens(d, ttl, tf, max_w)
            if len(lines) <= 4:
                break
        bpx2, bpy2 = 22, 10
        gap = int(tf.size * 0.16)
        row_h = tf.size + 2 * bpy2
        block_h = len(lines) * row_h + (len(lines) - 1) * gap
        y = int(H * 0.60) - block_h // 2          # center block around 60% height

        # small teal quote accent, top-left of the block
        qf = _font("Poppins-ExtraBold.ttf", 48)
        qx = (W - max_w) / 2 - 6
        d.rounded_rectangle([qx, y - 58, qx + 60, y - 6], radius=12, fill=CYAN)
        d.text((qx + 14, y - 78), "”", font=qf, fill=INK)

        for toks in lines:
            text = " ".join(toks)
            tw = d.textlength(text, font=tf)
            bx0, bx1 = (W - tw) / 2 - bpx2, (W + tw) / 2 + bpx2
            d.rounded_rectangle([bx0, y, bx1, y + row_h], radius=14,
                                fill=(255, 255, 255, 236))
            d.text(((W - tw) / 2, y + bpy2 - 4), text, font=tf, fill=(15, 18, 26, 255))
            y += row_h + gap

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


# backward-compat alias
def make_brand_png(out_png: Path, brand: str = "FAKTAVIRAL.IDN",
                   credit: str | None = None) -> Path:
    return make_overlay_png(out_png, brand=brand, title="", credit=credit)


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


def render_clip(source: Path, start: float, end: float, ass_path: Path | None,
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
    # karaoke caption is optional (off when source video already has burned-in text)
    subs = f",subtitles='{ass_path}':fontsdir='{fonts_dir}'" if ass_path else ""
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,setsar=1,"
        f"{crop}{subs}[v];"
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
