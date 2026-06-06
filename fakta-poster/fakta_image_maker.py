"""Compose 1080x1080 IG carousel slides for a 'fakta unik' (curiosity) page.

Separate brand from BERSTOCK.ID — cosmic indigo + cyan look. Rendered at 2x then
downscaled (supersampling) for crisp type. Reuses the Poppins fonts bundled with
the news poster (../daily-news-poster/fonts).
"""
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---- geometry ----
SIZE = 1080
SS = 2
R = SIZE * SS
PAD = 74

# ---- brand (ganti nama di sini / lewat env BRAND saat akun udah ada) ----
BRAND_TEXT = os.environ.get("BRAND", "FAKTANYA")

# ---- palette (cosmic indigo + cyan) ----
INDIGO = (32, 27, 64)
INDIGO_DEEP = (13, 11, 28)
CYAN = (96, 224, 255)
CYAN_INK = (8, 16, 22)        # text on cyan
WHITE = (244, 246, 251)
MUTED = (164, 162, 196)
FAINT = (120, 120, 158)

NICHE_LABELS = {
    "sains": "SAINS",
    "sejarah": "SEJARAH",
    "tubuh": "TUBUH MANUSIA",
    "hewan": "DUNIA HEWAN",
    "luarangkasa": "LUAR ANGKASA",
    "teknologi": "TEKNOLOGI",
}

_FONT_DIRS = [Path(__file__).resolve().parent / "fonts",
              Path(__file__).resolve().parent.parent / "daily-news-poster" / "fonts"]
_SYS_FALLBACK = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
_FONT_FILES = {
    "extrabold": "Poppins-ExtraBold.ttf",
    "bold": "Poppins-Bold.ttf",
    "semibold": "Poppins-SemiBold.ttf",
    "medium": "Poppins-Medium.ttf",
}
_font_cache: dict = {}


def s(v) -> int:
    return int(round(v * SS))


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    key = (weight, size)
    if key in _font_cache:
        return _font_cache[key]
    fname = _FONT_FILES.get(weight, _FONT_FILES["bold"])
    font = None
    for d in _FONT_DIRS:
        p = d / fname
        if p.exists():
            font = ImageFont.truetype(str(p), s(size))
            break
    if font is None:
        for fp in _SYS_FALLBACK:
            try:
                font = ImageFont.truetype(fp, s(size))
                break
            except OSError:
                continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def _wrap(text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if font.getlength(cand) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _tracked(draw, xy, text, font, fill, tracking) -> float:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + s(tracking)
    return x


def _stars(draw) -> None:
    """Subtle deterministic starfield for the cosmic vibe."""
    seed = 1234567
    for _ in range(70):
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        x = seed % R
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        y = seed % R
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        rad = s(1 + (seed % 3))
        alpha = 26 + (seed % 60)
        draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(255, 255, 255, alpha))


def _bg() -> Image.Image:
    base = Image.new("RGB", (1, R))
    px = base.load()
    for y in range(R):
        t = y / (R - 1)
        px[0, y] = (
            int(INDIGO[0] + (INDIGO_DEEP[0] - INDIGO[0]) * t),
            int(INDIGO[1] + (INDIGO_DEEP[1] - INDIGO[1]) * t),
            int(INDIGO[2] + (INDIGO_DEEP[2] - INDIGO[2]) * t),
        )
    canvas = base.resize((R, R)).convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    _stars(draw)
    # faint cyan glow ring, bottom-right
    cx, cy = R - s(140), R - s(110)
    for rad, a in ((520, 22), (380, 16), (250, 12)):
        rr = s(rad)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(96, 224, 255, a), width=s(2))
    draw.rectangle([0, 0, R, s(6)], fill=CYAN)
    return canvas


def _brand_chip(draw, x=PAD, y=PAD) -> int:
    f = _font("extrabold", 26)
    tw = f.getlength(BRAND_TEXT)
    px, py = s(20), s(12)
    h = f.size + 2 * py
    draw.rounded_rectangle([s(x), s(y), s(x) + tw + 2 * px, s(y) + h], radius=s(10), fill=CYAN)
    draw.text((s(x) + px, s(y) + py - s(4)), BRAND_TEXT, font=f, fill=CYAN_INK)
    return s(y) + h


def _dots(draw, active, total=3) -> None:
    f = _font("extrabold", 26)
    yc = s(PAD) + (f.size + 2 * s(12)) // 2
    x = R - s(PAD)
    for i in reversed(range(total)):
        rr = s(7) if i == active else s(6)
        col = CYAN if i == active else (255, 255, 255, 95)
        cx = x - rr
        draw.ellipse([cx - rr, yc - rr, cx + rr, yc + rr], fill=col)
        x = cx - rr - s(12)


def _category_pill(draw, label, x, y) -> int:
    f = _font("bold", 22)
    tw = f.getlength(label)
    px, py = s(18), s(9)
    h = f.size + 2 * py
    draw.rounded_rectangle([x, y, x + tw + 2 * px, y + h], radius=s(20),
                           outline=CYAN, width=s(2))
    draw.text((x + px, y + py - s(3)), label, font=f, fill=CYAN)
    return h


def _swipe(draw, font, y_top, color=CYAN) -> None:
    text = "Geser"
    tw = font.getlength(text)
    shaft, head = s(26), s(9)
    total = tw + s(14) + shaft + head
    x = R - s(PAD) - total
    draw.text((x, y_top), text, font=font, fill=color)
    ay = y_top + int(font.size * 0.58)
    ax = x + tw + s(14)
    draw.line([(ax, ay), (ax + shaft, ay)], fill=color, width=s(3))
    draw.polygon([(ax + shaft, ay - head), (ax + shaft + head, ay), (ax + shaft, ay + head)], fill=color)


def _sparkle(draw, cx, cy, L, color) -> None:
    """A crisp 4-point star (sparkle) — replaces emoji which Poppins can't render."""
    I = int(L * 0.26)
    pts = [
        (cx, cy - L), (cx + I, cy - I), (cx + L, cy), (cx + I, cy + I),
        (cx, cy + L), (cx - I, cy + I), (cx - L, cy), (cx - I, cy - I),
    ]
    draw.polygon(pts, fill=color)


def _save(canvas, out_path) -> str:
    canvas.resize((SIZE, SIZE), Image.LANCZOS).save(out_path, "JPEG", quality=92)
    return out_path


# --------------------------------------------------------------------------

def compose_cover(hook, category, out_path) -> str:
    canvas = _bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 0)

    kf = _font("extrabold", 40)
    hf = _font("extrabold", 64)
    max_w = R - 2 * s(PAD)
    lines = _wrap(hook, hf, max_w)
    line_h = int(hf.size * 1.06)
    block_h = line_h * len(lines)

    # vertically center the lower content block
    start = (R - block_h) // 2 - s(20)
    label = NICHE_LABELS.get((category or "").lower(), (category or "FAKTA").upper())
    cat_h = _category_pill(draw, label, s(PAD), start - s(150))
    _tracked(draw, (s(PAD), start - s(150) + cat_h + s(26)), "TAU GAK SIH?", kf, WHITE, 1)

    y = start
    for ln in lines:
        draw.text((s(PAD), y), ln, font=hf, fill=WHITE)
        y += line_h

    swf = _font("semibold", 24)
    _swipe(draw, swf, R - s(PAD) - swf.size)
    return _save(canvas, out_path)


def compose_fact(fact, detail, out_path) -> str:
    canvas = _bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 1)

    tf = _font("extrabold", 48)
    ty = s(210)
    draw.text((s(PAD), ty), "FAKTANYA", font=tf, fill=CYAN)
    uw = tf.getlength("FAKTANYA")
    uy = ty + tf.size + s(12)
    draw.rounded_rectangle([s(PAD), uy, s(PAD) + uw, uy + s(9)], radius=s(4), fill=CYAN)

    ff = _font("semibold", 44)
    df = _font("medium", 34)
    max_w = R - 2 * s(PAD)

    y = uy + s(60)
    for ln in _wrap(fact, ff, max_w):
        draw.text((s(PAD), y), ln, font=ff, fill=WHITE)
        y += int(ff.size * 1.2)

    if detail:
        y += s(26)
        for ln in _wrap(detail, df, max_w):
            draw.text((s(PAD), y), ln, font=df, fill=MUTED)
            y += int(df.size * 1.32)

    swf = _font("semibold", 24)
    _swipe(draw, swf, R - s(PAD) - swf.size)
    return _save(canvas, out_path)


def compose_outro(takeaway, out_path) -> str:
    canvas = _bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 2)

    _sparkle(draw, s(PAD) + s(40), s(250), s(48), CYAN)
    _sparkle(draw, s(PAD) + s(104), s(212), s(22), WHITE)

    tf = _font("semibold", 48)
    max_w = R - 2 * s(PAD)
    y = s(360)
    for ln in _wrap(takeaway or "Sekarang kamu tau hal baru hari ini.", tf, max_w):
        draw.text((s(PAD), y), ln, font=tf, fill=WHITE)
        y += int(tf.size * 1.2)

    # CTA
    cf = _font("bold", 30)
    subf = _font("medium", 24)
    sub_y = R - s(PAD) - subf.size - s(4)
    px, py = s(26), s(16)
    pill_h = cf.size + 2 * py
    pill_y = sub_y - s(22) - pill_h
    ct = f"Follow @{BRAND_TEXT.lower()}"
    ctw = cf.getlength(ct)
    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px, pill_y + pill_h],
                           radius=s(14), fill=CYAN)
    draw.text((s(PAD) + px, pill_y + py - s(4)), ct, font=cf, fill=CYAN_INK)
    draw.text((s(PAD), sub_y), "1 fakta unik tiap hari", font=subf, fill=MUTED)
    return _save(canvas, out_path)
