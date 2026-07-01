from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, math

R = 2
SIZE = 1080
S = SIZE * R
PAD = 60

_HERE = os.path.dirname(__file__)
FONT_DIR = os.path.join(_HERE, "fonts")
if not os.path.isdir(FONT_DIR):
    FONT_DIR = os.path.join(_HERE, "..", "daily-news-poster", "fonts")

THEMES = {
    "fashion":    {"p": (15, 10, 35),   "a": (255, 215, 0),   "l": (245, 240, 255), "d": (8, 5, 20),   "m": (180, 150, 255)},
    "makanan":    {"p": (18, 12, 8),    "a": (255, 190, 0),   "l": (255, 248, 235), "d": (8, 5, 2),    "m": (220, 80, 30)},
    "kuliner":    {"p": (18, 12, 8),    "a": (255, 190, 0),   "l": (255, 248, 235), "d": (8, 5, 2),    "m": (220, 80, 30)},
    "kecantikan": {"p": (45, 12, 28),   "a": (255, 180, 200), "l": (255, 245, 250), "d": (20, 5, 15),  "m": (255, 100, 150)},
    "beauty":     {"p": (45, 12, 28),   "a": (255, 180, 200), "l": (255, 245, 250), "d": (20, 5, 15),  "m": (255, 100, 150)},
    "elektronik": {"p": (5, 15, 45),    "a": (0, 200, 255),   "l": (235, 245, 255), "d": (2, 5, 20),   "m": (0, 120, 220)},
    "teknologi":  {"p": (5, 15, 45),    "a": (0, 200, 255),   "l": (235, 245, 255), "d": (2, 5, 20),   "m": (0, 120, 220)},
    "default":    {"p": (12, 18, 42),   "a": (255, 196, 0),   "l": (245, 248, 255), "d": (5, 8, 22),   "m": (80, 140, 255)},
}


def _th(niche):
    return THEMES.get(niche.lower(), THEMES["default"])


def _f(weight, sz):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Poppins-{weight}.ttf"), int(sz * R))


def _save(img, path):
    img.resize((SIZE, SIZE), Image.LANCZOS).save(path, "JPEG", quality=95)


def _sq(img, sz=None):
    w, h = img.size
    m = min(w, h)
    c = img.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2))
    return c.resize((sz or S, sz or S), Image.LANCZOS)


def _wrap(text, font, max_w):
    words = text.split()
    lines, cur = [], []
    for word in words:
        test = cur + [word]
        if font.getbbox(" ".join(test))[2] > max_w:
            if cur:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                lines.append(word)
                cur = []
        else:
            cur = test
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]


def _put(draw, text, font, x, y, mw, color, center=False, lh=1.25):
    lines = _wrap(text, font, mw)
    lh_px = int(font.size * lh)
    for i, line in enumerate(lines):
        tx = x
        if center:
            lw = font.getbbox(line)[2]
            tx = x + (mw - lw) // 2
        draw.text((tx, y + i * lh_px), line, font=font, fill=color)
    return y + len(lines) * lh_px


def _grad_v(img, y0, y1, c0, a0, c1, a1):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = y1 - y0
    for i in range(h):
        t = i / max(h - 1, 1)
        a = int(a0 + (a1 - a0) * t)
        col = tuple(int(c0[j] + (c1[j] - c0[j]) * t) for j in range(3))
        d.line([(0, y0 + i), (img.size[0], y0 + i)], fill=(*col, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _chip(draw, x, y, text, font, bg, fg, radius=None):
    bx = font.getbbox(text)
    px, py = int(20 * R), int(9 * R)
    w2, h2 = bx[2] + 2 * px, bx[3] + 2 * py
    r = radius if radius is not None else int(20 * R)
    draw.rounded_rectangle([x, y, x + w2, y + h2], radius=r, fill=bg)
    draw.text((x + px, y + py), text, font=font, fill=fg)
    return x + w2, y + h2


def _decor_circle(img, cx, cy, cr, color, alpha=25):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(*color, alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _pill(draw, cx, cy, text, font, bg, fg, min_w=0):
    bx = font.getbbox(text)
    px, py = int(28 * R), int(11 * R)
    w = max(bx[2] + 2 * px, min_w)
    h = bx[3] + 2 * py
    x0, y0 = cx - w // 2, cy - h // 2
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h // 2, fill=bg)
    draw.text((cx - bx[2] // 2, cy - bx[3] // 2 - int(1 * R)), text, font=font, fill=fg)


def _seg_bar(draw, y, total, current, p_color, off_color, seg_w=None, seg_h=None, gap=None):
    seg_w = seg_w or int(80 * R)
    seg_h = seg_h or int(8 * R)
    gap = gap or int(10 * R)
    total_w = total * seg_w + (total - 1) * gap
    x0 = (S - total_w) // 2
    for i in range(total):
        x = x0 + i * (seg_w + gap)
        col = p_color if i == current else off_color
        draw.rounded_rectangle([x, y, x + seg_w, y + seg_h], radius=seg_h // 2, fill=col)


# ── SLIDE 1: COVER — full bleed + double vignette + gold ticker + price pill ──
def _slide1(photo, product_name, price, tagline, niche, t, out_dir):
    img = _sq(photo)
    img = _grad_v(img, 0, int(S * 0.45), t["d"], 180, t["d"], 0)
    img = _grad_v(img, int(S * 0.38), S, t["d"], 0, t["d"], 245)
    d = ImageDraw.Draw(img)

    stripe_h = int(54 * R)
    d.rectangle([0, 0, S, stripe_h], fill=t["a"])
    d.text((int(PAD * R), int(10 * R)), niche.upper(), font=_f("Bold", 14), fill=t["p"])
    d.text((S - int(PAD * R), int(10 * R)), "1 / 6", font=_f("Bold", 14), fill=t["p"], anchor="rt")

    y = int(S * 0.52)
    fn = _f("ExtraBold", 52)
    lines = _wrap(product_name.upper(), fn, S - int(PAD * R) * 2)
    lh = int(fn.size * 1.05)
    for i, line in enumerate(lines):
        d.text((int(PAD * R), y + i * lh), line, font=fn, fill=(255, 255, 255))
    y += len(lines) * lh + int(16 * R)

    _put(d, tagline, _f("Medium", 20), int(PAD * R), y, S - int(PAD * R) * 2, (200, 195, 185))

    _pill(d, S - int(120 * R), S - int(70 * R), price, _f("ExtraBold", 22), t["a"], t["p"])

    path = os.path.join(out_dir, "slide_1_cover.jpg")
    _save(img, path)
    return path


# ── SLIDE 2: SPLIT — 55% photo left / 45% color panel right ──
def _slide2(photo, product_name, hook, niche, t, out_dir):
    img = Image.new("RGB", (S, S), t["p"])
    sq = _sq(photo)
    split = int(S * 0.55)
    img.paste(sq.crop((0, 0, split, S)), (0, 0))
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d2 = ImageDraw.Draw(ov)
    for i in range(int(60 * R)):
        a = int(180 * (1 - i / (60 * R)) ** 1.5)
        d2.line([(split - i, 0), (split - i, S)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    d = ImageDraw.Draw(img)
    rx = split + int(40 * R)
    rw = S - rx - int(35 * R)

    _chip(d, rx, int(70 * R), niche.upper(), _f("Bold", 12), t["a"], t["p"])

    y = int(S * 0.22)
    y = _put(d, f'"{hook}"', _f("ExtraBold", 30), rx, y, rw, (255, 255, 255), lh=1.35)

    y += int(30 * R)
    d.line([(rx, y), (rx + int(60 * R), y)], fill=t["a"], width=int(4 * R))
    y += int(30 * R)

    _put(d, product_name, _f("SemiBold", 20), rx, y, rw, t["a"], lh=1.3)

    d.text((rx, S - int(60 * R)), "2 / 6", font=_f("Bold", 12), fill=(130, 125, 150))
    path = os.path.join(out_dir, "slide_2_hook.jpg")
    _save(img, path)
    return path


# ── SLIDE 3-5: DARK CINEMATIC — full bleed very dark + huge bg number + feature ──
def _slide3_5(photo, feat, desc, idx, t, out_dir):
    sq = _sq(photo)
    img = _grad_v(sq, 0, S, t["d"], 200, t["d"], 240)
    d = ImageDraw.Draw(img)

    sn = idx + 3
    num_font = _f("ExtraBold", 260)
    num_str = f"0{idx + 1}"
    bx = num_font.getbbox(num_str)
    nx = S - bx[2] - int(40 * R)
    ny = int(S * 0.02)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((nx, ny), num_str, font=num_font, fill=(*t["a"], 28))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)

    d.rectangle([int(PAD * R), int(S * 0.18), int(PAD * R) + int(6 * R), int(S * 0.18) + int(130 * R)], fill=t["a"])

    tx = int(PAD * R) + int(24 * R)
    y = int(S * 0.18)
    y = _put(d, feat.upper(), _f("ExtraBold", 36), tx, y, S - tx - int(PAD * R), (255, 255, 255), lh=1.2)
    y += int(24 * R)
    _put(d, desc, _f("Regular", 22), tx, y, S - tx - int(PAD * R), (185, 180, 200), lh=1.5)

    _seg_bar(d, S - int(80 * R), 6, sn - 1, t["a"], (*t["a"][:3], 60))

    d.text((int(PAD * R), S - int(55 * R)), f"{sn} / 6", font=_f("Bold", 13), fill=(130, 125, 150))
    fname = f"slide_{sn}_feat{idx + 1}.jpg"
    path = os.path.join(out_dir, fname)
    _save(img, path)
    return path


# ── SLIDE 6: CTA — dramatic dark + accent circles + price hero + ORDER button ──
def _slide6(photo, cta, price, contact, niche, t, out_dir):
    img = Image.new("RGB", (S, S), t["d"])
    img = _decor_circle(img, int(S * 0.85), int(S * 0.15), int(S * 0.32), t["a"], 22)
    img = _decor_circle(img, int(S * 0.10), int(S * 0.80), int(S * 0.25), t["m"], 18)
    img = _decor_circle(img, int(S * 0.50), int(S * 0.55), int(S * 0.18), t["a"], 10)

    ts = int(S * 0.30)
    thumb = _sq(photo, ts)
    mask = Image.new("L", (ts, ts), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ts, ts], radius=int(32 * R), fill=255)
    img.paste(thumb, (S - int(PAD * R) - ts, S - int(PAD * R) - ts), mask)

    sh = int(48 * R)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, S, sh], fill=t["a"])
    d.text((int(PAD * R), int(12 * R)), "DAPATKAN SEKARANG", font=_f("Bold", 14), fill=t["p"])
    d.text((S - int(PAD * R), int(12 * R)), "6 / 6", font=_f("Bold", 14), fill=t["p"], anchor="rt")

    p = int(PAD * R)
    y = sh + int(60 * R)

    fn_cta = _f("ExtraBold", 40)
    lines = _wrap(cta.upper(), fn_cta, S - p * 2 - ts - int(30 * R))
    lh = int(fn_cta.size * 1.1)
    for i, line in enumerate(lines):
        d.text((p, y + i * lh), line, font=fn_cta, fill=(255, 255, 255))
    y += len(lines) * lh + int(40 * R)

    d.line([(p, y), (p + int(100 * R), y)], fill=t["a"], width=int(4 * R))
    y += int(40 * R)

    fn_price = _f("ExtraBold", 72)
    d.text((p, y), price, font=fn_price, fill=t["a"])
    bpy = fn_price.getbbox(price)[3]
    y += bpy + int(50 * R)

    btn_w, btn_h = int(320 * R), int(76 * R)
    d.rounded_rectangle([p, y, p + btn_w, y + btn_h], radius=btn_h // 2, fill=t["a"])
    d.text((p + btn_w // 2, y + btn_h // 2 - int(2 * R)),
           "ORDER SEKARANG →", font=_f("Bold", 20), fill=t["p"], anchor="mm")

    ct = contact or "DM / WA untuk order"
    d.text((p, S - int(55 * R)), ct, font=_f("Medium", 18), fill=(170, 165, 185))

    path = os.path.join(out_dir, "slide_6_cta.jpg")
    _save(img, path)
    return path


def make_slides(photo_path, product_name, price, hook, tagline,
                features, feature_descs, cta, niche, out_dir, contact=""):
    photo = Image.open(photo_path).convert("RGB")
    t = _th(niche)
    paths = []

    paths.append(_slide1(photo, product_name, price, tagline, niche, t, out_dir))
    paths.append(_slide2(photo, product_name, hook, niche, t, out_dir))
    for i in range(3):
        feat = features[i] if i < len(features) else f"Keunggulan {i+1}"
        desc = feature_descs[i] if i < len(feature_descs) else ""
        paths.append(_slide3_5(photo, feat, desc, i, t, out_dir))
    paths.append(_slide6(photo, cta, price, contact, niche, t, out_dir))

    return paths
