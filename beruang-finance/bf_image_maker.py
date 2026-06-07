"""Compose 1080x1080 IG carousel untuk Beruang Finance (kuning + beruang berdasi).

Pakai foto stock (Pexels) sebagai background dengan scrim coklat hangat biar teks
kebaca + brand kuning. Reuse helper generik dari fakta_image_maker (font/wrap/dll)."""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fakta-poster"))
from fakta_image_maker import _font, _wrap, _tracked, s, R, SIZE, PAD  # noqa: E402

BEAR_PATH = Path(__file__).resolve().parent / "brand" / "bear.png"

BRAND_TEXT = "BERUANG FINANCE"
HANDLE = os.environ.get("BF_HANDLE", "beruangfinance")

# palette: kuning terang + coklat tua
YELLOW = (255, 198, 0)
YELLOW_HI = (255, 224, 90)
INK = (58, 38, 22)          # coklat tua (teks di atas kuning / brand)
BROWN_DEEP = (28, 18, 10)   # scrim foto
WHITE = (250, 248, 242)
CREAM = (228, 222, 208)

TYPE_LABELS = {"tips": "TIPS KEUANGAN", "berita": "BERITA", "lucu": "RELATABLE"}

_bear_cache: dict = {}


def _bear(maxw: int) -> Image.Image:
    if maxw in _bear_cache:
        return _bear_cache[maxw]
    b = Image.open(BEAR_PATH).convert("RGBA")
    r = maxw / b.width
    b = b.resize((maxw, int(b.height * r)), Image.LANCZOS)
    _bear_cache[maxw] = b
    return b


def _photo_bg(path: str, base: float = 0.14, peak: float = 0.92) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path).convert("RGB"))
    img = ImageOps.fit(img, (R, R), method=Image.LANCZOS, centering=(0.5, 0.4))
    img = ImageEnhance.Color(img).enhance(1.05)
    img = img.convert("RGBA")
    a = Image.new("L", (1, R), 0)
    px = a.load()
    for y in range(R):
        t = y / (R - 1)
        px[0, y] = int(255 * min(base + (peak - base) * (t ** 1.4), 0.96))
    scrim = Image.new("RGBA", (R, R), (*BROWN_DEEP, 255))
    scrim.putalpha(a.resize((R, R)))
    out = Image.alpha_composite(img, scrim).convert("RGB")
    ImageDraw.Draw(out, "RGBA").rectangle([0, 0, R, s(6)], fill=YELLOW)
    return out


def _yellow_bg() -> Image.Image:
    base = Image.new("RGB", (1, R))
    px = base.load()
    for y in range(R):
        t = y / (R - 1)
        px[0, y] = tuple(int(YELLOW_HI[i] + (YELLOW[i] - YELLOW_HI[i]) * t) for i in range(3))
    return base.resize((R, R)).convert("RGB")


def _brand_chip(draw, x=PAD, y=PAD) -> int:
    f = _font("extrabold", 24)
    tw = f.getlength(BRAND_TEXT)
    px, py = s(20), s(12)
    h = f.size + 2 * py
    draw.rounded_rectangle([s(x), s(y), s(x) + tw + 2 * px, s(y) + h], radius=s(10), fill=INK)
    draw.text((s(x) + px, s(y) + py - s(4)), BRAND_TEXT, font=f, fill=YELLOW)
    return s(y) + h


def _dots(draw, active, total=3) -> None:
    f = _font("extrabold", 24)
    yc = s(PAD) + (f.size + 2 * s(12)) // 2
    x = R - s(PAD)
    for i in reversed(range(total)):
        rr = s(7) if i == active else s(6)
        col = YELLOW if i == active else (255, 255, 255, 110)
        cx = x - rr
        draw.ellipse([cx - rr, yc - rr, cx + rr, yc + rr], fill=col)
        x = cx - rr - s(12)


def _category_pill(draw, label, x, y) -> int:
    f = _font("bold", 22)
    tw = f.getlength(label)
    px, py = s(18), s(9)
    h = f.size + 2 * py
    draw.rounded_rectangle([x, y, x + tw + 2 * px, y + h], radius=s(20), fill=YELLOW)
    draw.text((x + px, y + py - s(3)), label, font=f, fill=INK)
    return h


def _swipe(draw, font, y_top, color=YELLOW) -> None:
    text = "Geser"
    tw = font.getlength(text)
    shaft, head = s(26), s(9)
    x = R - s(PAD) - (tw + s(14) + shaft + head)
    draw.text((x, y_top), text, font=font, fill=color)
    ay = y_top + int(font.size * 0.58)
    ax = x + tw + s(14)
    draw.line([(ax, ay), (ax + shaft, ay)], fill=color, width=s(3))
    draw.polygon([(ax + shaft, ay - head), (ax + shaft + head, ay), (ax + shaft, ay + head)], fill=color)


def _bullet(draw, x, y, color=YELLOW) -> None:
    r = s(9)
    draw.ellipse([x, y, x + 2 * r, y + 2 * r], fill=color)


def _save(canvas, out_path) -> str:
    canvas.resize((SIZE, SIZE), Image.LANCZOS).save(out_path, "JPEG", quality=92)
    return out_path


# --------------------------------------------------------------------------

def compose_cover(hook, ctype, kicker, out_path, bg_path=None) -> str:
    canvas = _photo_bg(bg_path, base=0.12) if bg_path else _yellow_bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 0)

    kf = _font("extrabold", 38)
    hf = _font("extrabold", 62)
    max_w = R - 2 * s(PAD)
    lines = _wrap(hook, hf, max_w)
    line_h = int(hf.size * 1.06)
    block_h = line_h * len(lines)
    start = (R - block_h) // 2 + s(20)

    label = TYPE_LABELS.get((ctype or "").lower(), "BERUANG FINANCE")
    cat_h = _category_pill(draw, label, s(PAD), start - s(150))
    _tracked(draw, (s(PAD), start - s(150) + cat_h + s(26)),
             (kicker or "MELEK DUIT").upper(), kf, WHITE if bg_path else INK, 1)

    fill = WHITE if bg_path else INK
    y = start
    for ln in lines:
        draw.text((s(PAD), y), ln, font=hf, fill=fill)
        y += line_h

    _swipe(draw, _font("semibold", 24), R - s(PAD) - s(24))
    return _save(canvas, out_path)


def compose_points(points, header, out_path, bg_path=None) -> str:
    canvas = _photo_bg(bg_path, base=0.6) if bg_path else _yellow_bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 1)

    tf = _font("extrabold", 46)
    ty = s(210)
    draw.text((s(PAD), ty), header, font=tf, fill=YELLOW)
    uw = tf.getlength(header)
    uy = ty + tf.size + s(12)
    draw.rounded_rectangle([s(PAD), uy, s(PAD) + uw, uy + s(9)], radius=s(4), fill=YELLOW)

    pf = _font("semibold", 40)
    max_w = R - 2 * s(PAD) - s(44)
    y = uy + s(64)
    for p in points:
        _bullet(draw, s(PAD), y + s(10))
        lines = _wrap(p, pf, max_w)
        for i, ln in enumerate(lines):
            draw.text((s(PAD) + s(44), y), ln, font=pf, fill=WHITE)
            y += int(pf.size * 1.22)
        y += s(22)

    _swipe(draw, _font("semibold", 24), R - s(PAD) - s(24))
    return _save(canvas, out_path)


def compose_outro(takeaway, out_path, bg_path=None) -> str:
    canvas = _photo_bg(bg_path, base=0.62) if bg_path else _yellow_bg()
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)
    _dots(draw, 2)

    tf = _font("semibold", 48)
    max_w = R - 2 * s(PAD)
    y = s(330)
    for ln in _wrap(takeaway or "Yuk mulai atur duit dari sekarang.", tf, max_w):
        draw.text((s(PAD), y), ln, font=tf, fill=WHITE)
        y += int(tf.size * 1.2)

    # bear logo kecil (pojok kanan atas)
    bear = _bear(s(150))
    canvas.paste(bear, (R - s(PAD) - bear.width, s(PAD) + s(40)), bear)

    cf = _font("bold", 30)
    subf = _font("medium", 24)
    sub_y = R - s(PAD) - subf.size - s(4)
    px, py = s(26), s(16)
    pill_h = cf.size + 2 * py
    pill_y = sub_y - s(22) - pill_h
    ct = f"Follow @{HANDLE}"
    ctw = cf.getlength(ct)
    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px, pill_y + pill_h],
                           radius=s(14), fill=YELLOW)
    draw.text((s(PAD) + px, pill_y + py - s(4)), ct, font=cf, fill=INK)
    draw.text((s(PAD), sub_y), "Melek duit, pelan-pelan", font=subf, fill=CREAM)
    return _save(canvas, out_path)
