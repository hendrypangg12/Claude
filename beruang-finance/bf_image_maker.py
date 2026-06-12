"""Compose 1080x1080 IG carousel untuk Beruang Finance — GAYA BERSIH (ala fakta.indo
/ faktaviral): foto full-bleed + judul minimal kuning+putih, sedikit teks, rapih.

Tetap brand Beruang (kuning + beruang berdasi). Reuse helper generik dari
fakta_image_maker (font/wrap/foto/gradasi/split-highlight)."""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fakta-poster"))
from fakta_image_maker import (  # noqa: E402
    _font, _wrap, _tracked, _photo_cover, _grad, _split_hl, s, R, SIZE, PAD,
)

BEAR_PATH = Path(__file__).resolve().parent / "brand" / "bear.png"

BRAND_TEXT = "BERUANG FINANCE"
HANDLE = os.environ.get("BF_HANDLE", "beruangfinance")

# palette bersih: kuning Beruang + putih + ink coklat
YELLOW = (255, 198, 0)
INK = (40, 26, 10)            # teks di atas kuning
WHITE = (245, 247, 250)
MUTED = (206, 208, 214)
PANEL = (16, 14, 12)          # panel gelap slide isi

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


def _yellow_bg() -> Image.Image:
    """Fallback kalau gak ada foto: kuning polos halus (gak norak)."""
    top, bot = (255, 214, 70), YELLOW
    base = Image.new("RGB", (1, R))
    px = base.load()
    for y in range(R):
        t = y / (R - 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return base.resize((R, R)).convert("RGB")


def _brand_chip(draw, x=PAD, y=PAD) -> None:
    f = _font("extrabold", 26)
    tw = f.getlength(BRAND_TEXT)
    px, py = s(18), s(11)
    draw.rounded_rectangle([s(x), s(y), s(x) + tw + 2 * px, s(y) + f.size + 2 * py],
                           radius=s(10), fill=YELLOW)
    draw.text((s(x) + px, s(y) + py - s(4)), BRAND_TEXT, font=f, fill=INK)


def _watermark(draw) -> None:
    f = _font("extrabold", 28)
    draw.text((R - s(PAD) - f.getlength(HANDLE), R - s(PAD) - f.size), HANDLE,
              font=f, fill=(255, 255, 255, 205))


def _headline(draw, yellow, white, font, bottom_y, max_w, lh) -> int:
    """Judul 2 warna (kuning+putih), wrap, anchor BAWAH. Return tinggi blok."""
    words = [(w, YELLOW) for w in yellow.split()] + [(w, WHITE) for w in white.split()]
    sp = font.getlength(" ")
    lines, cur, cw = [], [], 0
    for w, c in words:
        ww = font.getlength(w)
        if cur and cw + sp + ww > max_w:
            lines.append(cur); cur, cw = [], 0
        cur.append((w, c)); cw += (sp if cw else 0) + ww
    if cur:
        lines.append(cur)
    y = bottom_y - len(lines) * lh
    for ln in lines:
        x = s(PAD)
        for w, c in ln:
            draw.text((x, y), w, font=font, fill=c)
            x += font.getlength(w) + sp
        y += lh
    return len(lines) * lh


def _save(canvas, out_path) -> str:
    canvas.resize((SIZE, SIZE), Image.LANCZOS).save(out_path, "JPEG", quality=92)
    return out_path


# --------------------------------------------------------------------------

def compose_cover(hook, ctype, kicker, out_path, bg_path=None) -> str:
    """Cover: foto full-bleed + label kecil + judul kuning/putih (anchor bawah)."""
    try:
        canvas = _photo_cover(bg_path) if bg_path else _yellow_bg()
    except Exception:
        canvas = _yellow_bg()
    canvas = _grad(canvas, bottom=0.40, top=0.24)
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)

    hf = _font("extrabold", 66)
    lh = int(hf.size * 1.08)
    yellow, white = _split_hl(hook)
    bottom = R - s(155)
    hh = _headline(draw, yellow, white, hf, bottom, R - 2 * s(PAD), lh)

    # label kecil di atas judul (mis. "TIPS KEUANGAN") — tipis & rapih
    label = TYPE_LABELS.get((ctype or "").lower()) or (kicker or "").upper()
    if label:
        lf = _font("extrabold", 28)
        _tracked(draw, (s(PAD), bottom - hh - s(52)), label[:28], lf, YELLOW, 2)
    _watermark(draw)
    return _save(canvas, out_path)


def compose_points(points, header, out_path, bg_path=None) -> str:
    """Slide isi: foto di ATAS, 3 poin di panel gelap bawah. Ala fakta.indo."""
    photo_h = int(R * 0.46)
    canvas = Image.new("RGB", (R, R), PANEL)
    if bg_path:
        try:
            img = ImageOps.exif_transpose(Image.open(bg_path).convert("RGB"))
            img = ImageOps.fit(img, (R, photo_h + s(60)), method=Image.LANCZOS, centering=(0.5, 0.4))
            canvas.paste(img, (0, 0))
            a = Image.new("L", (1, R), 0); px = a.load()
            for y in range(R):
                px[0, y] = 0 if y < photo_h - s(80) else min(255, int(255 * (y - (photo_h - s(80))) / s(140)))
            canvas = Image.composite(Image.new("RGB", (R, R), PANEL), canvas, a.resize((R, R)))
        except Exception:
            pass
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)

    top = photo_h + s(70)
    hf = _font("extrabold", 44)
    draw.text((s(PAD), top), header, font=hf, fill=YELLOW)
    top += hf.size + s(28)

    max_w = R - 2 * s(PAD) - s(46)
    bottom_lim = R - s(110)
    pts = [p for p in (points or []) if str(p).strip()][:3]

    # AUTO-FIT: kecilin font sampai 3 poin muat di area aman
    pf = _font("semibold", 40)
    for fs in (40, 38, 36, 34, 32, 30, 28):
        pf = _font("semibold", fs)
        lh = int(pf.size * 1.24)
        total = sum(len(_wrap(p, pf, max_w)) * lh + s(26) for p in pts)
        if top + total <= bottom_lim:
            break
    lh = int(pf.size * 1.24)
    y = top
    for p in pts:
        draw.ellipse([s(PAD), y + s(12), s(PAD) + s(18), y + s(30)], fill=YELLOW)  # bullet
        for ln in _wrap(p, pf, max_w):
            draw.text((s(PAD) + s(46), y), ln, font=pf, fill=WHITE)
            y += lh
        y += s(26)
    _watermark(draw)
    return _save(canvas, out_path)


def compose_outro(takeaway, out_path, bg_path=None) -> str:
    """Outro: foto + takeaway + pill Follow kuning + beruang kecil."""
    try:
        canvas = _photo_cover(bg_path) if bg_path else _yellow_bg()
    except Exception:
        canvas = _yellow_bg()
    canvas = _grad(canvas, bottom=0.28, top=0.22)
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip(draw)

    cf = _font("bold", 40)
    ct = f"Follow @{HANDLE}"
    ctw = cf.getlength(ct)
    px, py = s(30), s(18)
    pill_h = cf.size + 2 * py
    pill_y = R - s(180) - pill_h

    tf = _font("semibold", 50)
    lh = int(tf.size * 1.2)
    lines = _wrap(takeaway or "Yuk mulai atur duit dari sekarang.", tf, R - 2 * s(PAD))
    bottom = pill_y - s(50)
    y = bottom - len(lines) * lh
    for ln in lines:
        draw.text((s(PAD), y), ln, font=tf, fill=WHITE); y += lh

    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px, pill_y + pill_h],
                           radius=s(16), fill=YELLOW)
    draw.text((s(PAD) + px, pill_y + py - s(5)), ct, font=cf, fill=INK)

    sf = _font("medium", 26)
    draw.text((s(PAD), pill_y + pill_h + s(20)), "Melek duit, pelan-pelan", font=sf, fill=MUTED)

    bear = _bear(s(150))
    canvas.paste(bear, (R - s(PAD) - bear.width, s(PAD) + s(36)), bear)
    return _save(canvas, out_path)
