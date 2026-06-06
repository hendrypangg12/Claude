"""Compose premium 1080x1080 Instagram carousel slides for a news post.

Brand: BERSTOCK.ID — navy + gold editorial look.
Everything is rendered at 2x then downscaled (supersampling) so type and
shapes come out crisp. Bundled Poppins fonts (fonts/) keep the result
identical on a laptop and in GitHub Actions.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

# ---- geometry (logical px @ 1080) ----
SIZE = 1080
SS = 2                 # supersample factor
R = SIZE * SS          # render canvas size
PAD = 72               # logical padding

# ---- palette ----
NAVY_DEEP = (11, 15, 23)
NAVY = (20, 26, 38)
GOLD = (255, 196, 0)
WHITE = (245, 247, 251)
MUTED = (150, 162, 182)
FAINT = (118, 130, 148)
INK = (15, 18, 26)      # text on gold

BRAND_TEXT = "BERSTOCK.ID"

NICHE_LABELS = {
    "pagi": "PEMERINTAHAN",
    "saham": "SAHAM IDX",
    "market": "MARKET UPDATE",
    "startup": "STARTUP & BISNIS",
    "ai": "AI & TEKNOLOGI",
}

_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_FILES = {
    "extrabold": "Poppins-ExtraBold.ttf",
    "bold": "Poppins-Bold.ttf",
    "semibold": "Poppins-SemiBold.ttf",
    "medium": "Poppins-Medium.ttf",
    "regular": "Poppins-Regular.ttf",
}
_SYS_FALLBACK = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_font_cache: dict = {}


def s(v) -> int:
    """Logical px -> render px."""
    return int(round(v * SS))


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    key = (weight, size)
    if key in _font_cache:
        return _font_cache[key]
    path = _FONT_DIR / _FONT_FILES.get(weight, _FONT_FILES["bold"])
    font = None
    try:
        font = ImageFont.truetype(str(path), s(size))
    except OSError:
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


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
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
    """Draw text with letter-spacing (logical px). Returns end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + s(tracking)
    return x


def _tracked_width(text, font, tracking) -> float:
    if not text:
        return 0
    return sum(font.getlength(ch) + s(tracking) for ch in text) - s(tracking)


# --------------------------------------------------------------------------
# backgrounds
# --------------------------------------------------------------------------

def _vgrad(top, bottom, w, h) -> Image.Image:
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
    return base.resize((w, h))


def _branded_bg() -> Image.Image:
    """Clean navy gradient + subtle gold ring accents (no photo)."""
    canvas = _vgrad(NAVY, NAVY_DEEP, R, R).convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    cx, cy = R - s(120), R - s(90)
    for rad, alpha in ((560, 20), (420, 14), (280, 10)):
        rr = s(rad)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     outline=(255, 196, 0, alpha), width=s(2))
    draw.rectangle([0, 0, R, s(6)], fill=GOLD)
    return canvas


def _cover_photo(path: str) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img, (R, R), method=Image.LANCZOS, centering=(0.5, 0.4))
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Color(img).enhance(1.12)
    return img


def _scrim(max_alpha=240) -> Image.Image:
    """Navy gradient scrim: faint at top, opaque toward the bottom."""
    a = Image.new("L", (1, R), 0)
    px = a.load()
    start = int(R * 0.34)
    for y in range(R):
        if y <= start:
            px[0, y] = int(max_alpha * 0.12 * (y / max(start, 1)))
        else:
            t = (y - start) / max(R - start, 1)
            px[0, y] = int(max_alpha * (0.12 + 0.88 * (t ** 1.45)))
    scrim = Image.new("RGBA", (R, R), (8, 11, 18, 255))
    scrim.putalpha(a.resize((R, R)))
    return scrim


def _is_low_quality(path: str) -> bool:
    try:
        with Image.open(path) as im:
            w, h = im.size
        return min(w, h) < 360
    except Exception:
        return True


# --------------------------------------------------------------------------
# shared chrome
# --------------------------------------------------------------------------

def _brand_chip(draw, x=PAD, y=PAD) -> int:
    f = _font("extrabold", 26)
    tw = f.getlength(BRAND_TEXT)
    px, py = s(20), s(12)
    h = f.size + 2 * py
    draw.rounded_rectangle([s(x), s(y), s(x) + tw + 2 * px, s(y) + h],
                           radius=s(10), fill=GOLD)
    draw.text((s(x) + px, s(y) + py - s(4)), BRAND_TEXT, font=f, fill=INK)
    return s(y) + h


def _dots(draw, active, total=3, y_center=None) -> None:
    if y_center is None:
        f = _font("extrabold", 26)
        y_center = s(PAD) + (f.size + 2 * s(12)) // 2
    r = s(7)
    gap = s(12)
    x = R - s(PAD)
    for i in reversed(range(total)):
        if i == active:
            col = GOLD
            rr = r
        else:
            col = (255, 255, 255, 95)
            rr = s(6)
        cx = x - rr
        draw.ellipse([cx - rr, y_center - rr, cx + rr, y_center + rr], fill=col)
        x = cx - rr - gap


def _swipe(draw, font, y_top, color=GOLD) -> None:
    """Draw a right-aligned 'Geser ›' with a hand-drawn arrow (Poppins lacks →)."""
    text = "Geser"
    tw = font.getlength(text)
    shaft = s(26)
    head = s(9)
    total = tw + s(14) + shaft + head
    x = R - s(PAD) - total
    draw.text((x, y_top), text, font=font, fill=color)
    ay = y_top + int(font.size * 0.58)
    ax = x + tw + s(14)
    draw.line([(ax, ay), (ax + shaft, ay)], fill=color, width=s(3))
    draw.polygon([(ax + shaft, ay - head), (ax + shaft + head, ay),
                  (ax + shaft, ay + head)], fill=color)


def _save(canvas: Image.Image, out_path: str) -> str:
    canvas.resize((SIZE, SIZE), Image.LANCZOS).save(out_path, "JPEG", quality=92)
    return out_path


# --------------------------------------------------------------------------
# slides
# --------------------------------------------------------------------------

def compose(background_path, headline, source, out_path, niche=None) -> str:
    """Slide 1: full-bleed photo + gradient scrim + headline."""
    if _is_low_quality(background_path):
        canvas = _branded_bg()
    else:
        try:
            photo = _cover_photo(background_path).convert("RGBA")
            canvas = Image.alpha_composite(photo, _scrim()).convert("RGB")
        except Exception:
            canvas = _branded_bg()

    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 0)

    kicker = NICHE_LABELS.get((niche or "").lower(), "BERITA HARI INI")
    kf = _font("bold", 23)
    hf = _font("extrabold", 60)
    srcf = _font("medium", 23)
    swf = _font("semibold", 24)

    max_w = R - 2 * s(PAD)
    lines = _wrap(headline, hf, max_w)
    line_h = int(hf.size * 1.07)
    block_h = line_h * len(lines)

    src_y = R - s(PAD) - srcf.size
    hl_bottom = src_y - s(44)
    hl_top = hl_bottom - block_h
    kicker_y = hl_top - s(50)

    # kicker: gold dot + tracked label
    dot_r = s(6)
    draw.ellipse([s(PAD), kicker_y + kf.size // 2 - dot_r,
                  s(PAD) + 2 * dot_r, kicker_y + kf.size // 2 + dot_r], fill=GOLD)
    _tracked(draw, (s(PAD) + 3 * dot_r, kicker_y), kicker, kf, GOLD, 2)

    y = hl_top
    for ln in lines:
        draw.text((s(PAD), y), ln, font=hf, fill=WHITE)
        y += line_h

    if source:
        draw.text((s(PAD), src_y), f"Sumber: {source}", font=srcf, fill=(220, 224, 230))
    _swipe(draw, swf, src_y - s(2))
    return _save(canvas, out_path)


def compose_slide_points(background_path, points, out_path, niche=None) -> str:
    """Slide 2: 'Poin Penting' over a clean branded background."""
    canvas = _branded_bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 1)

    tf = _font("extrabold", 50)
    ty = s(220)
    draw.text((s(PAD), ty), "POIN PENTING", font=tf, fill=WHITE)
    uw = tf.getlength("POIN PENTING")
    uy = ty + tf.size + s(12)
    draw.rounded_rectangle([s(PAD), uy, s(PAD) + uw, uy + s(9)], radius=s(4), fill=GOLD)

    bf = _font("semibold", 39)
    nf = _font("extrabold", 33)
    badge_r = s(31)
    text_x = s(PAD) + 2 * badge_r + s(28)
    max_w = R - text_x - s(PAD)
    lh = int(bf.size * 1.12)

    y = uy + s(64)
    for i, p in enumerate([p for p in points if p][:3], start=1):
        lines = _wrap(p, bf, max_w)
        first_center = y + bf.size // 2
        bx = s(PAD) + badge_r
        draw.ellipse([bx - badge_r, first_center - badge_r,
                      bx + badge_r, first_center + badge_r], fill=GOLD)
        num = str(i)
        nw = nf.getlength(num)
        draw.text((bx - nw / 2, first_center - nf.size / 2 - s(3)), num, font=nf, fill=INK)
        ty2 = y
        for ln in lines:
            draw.text((text_x, ty2), ln, font=bf, fill=WHITE)
            ty2 += lh
        y += max(2 * badge_r, len(lines) * lh) + s(42)

    swf = _font("semibold", 24)
    _swipe(draw, swf, R - s(PAD) - swf.size)
    return _save(canvas, out_path)


def compose_slide_takeaway(background_path, takeaway, source, out_path, niche=None) -> str:
    """Slide 3: takeaway + follow CTA over a clean branded background."""
    canvas = _branded_bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 2)

    qf = _font("extrabold", 150)
    draw.text((s(PAD) - s(10), s(150)), "“", font=qf, fill=(255, 196, 0, 55))

    kf = _font("bold", 25)
    _tracked(draw, (s(PAD), s(300)), "INTINYA", kf, GOLD, 3)

    tf = _font("semibold", 46)
    max_w = R - 2 * s(PAD)
    lines = _wrap(takeaway, tf, max_w)
    y = s(354)
    lh = int(tf.size * 1.2)
    for ln in lines:
        draw.text((s(PAD), y), ln, font=tf, fill=WHITE)
        y += lh

    # bottom block (built from the bottom up)
    srcf = _font("medium", 22)
    subf = _font("medium", 24)
    cf = _font("bold", 30)

    src_y = R - s(PAD) - srcf.size
    sub_y = src_y - s(22) - subf.size
    px, py = s(26), s(16)
    pill_h = cf.size + 2 * py
    pill_y = sub_y - s(20) - pill_h

    ct = "Follow @berstock.id"
    ctw = cf.getlength(ct)
    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px, pill_y + pill_h],
                           radius=s(14), fill=GOLD)
    draw.text((s(PAD) + px, pill_y + py - s(4)), ct, font=cf, fill=INK)
    draw.text((s(PAD), sub_y), "berita & insight harian terkurasi", font=subf, fill=MUTED)
    if source:
        draw.text((s(PAD), src_y), f"Sumber: {source}", font=srcf, fill=FAINT)
    return _save(canvas, out_path)
