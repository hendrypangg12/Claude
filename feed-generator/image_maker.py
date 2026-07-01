from PIL import Image, ImageDraw, ImageFont
import os

R = 2          # supersampling
SIZE = 1080
S = SIZE * R
PAD = 64

_HERE = os.path.dirname(__file__)
FONT_DIR = os.path.join(_HERE, "fonts")
if not os.path.isdir(FONT_DIR):
    FONT_DIR = os.path.join(_HERE, "..", "daily-news-poster", "fonts")

THEMES = {
    "fashion":    {"p": (50, 20, 90),   "a": (255, 200, 50),  "l": (248, 245, 255), "t": (25, 10, 45)},
    "makanan":    {"p": (155, 40, 10),  "a": (255, 160, 0),   "l": (255, 248, 240), "t": (40, 10, 5)},
    "kuliner":    {"p": (155, 40, 10),  "a": (255, 160, 0),   "l": (255, 248, 240), "t": (40, 10, 5)},
    "kecantikan": {"p": (150, 40, 80),  "a": (255, 180, 190), "l": (255, 248, 252), "t": (60, 15, 35)},
    "beauty":     {"p": (150, 40, 80),  "a": (255, 180, 190), "l": (255, 248, 252), "t": (60, 15, 35)},
    "elektronik": {"p": (10, 40, 120),  "a": (0, 160, 240),   "l": (240, 245, 255), "t": (5, 15, 50)},
    "teknologi":  {"p": (10, 40, 120),  "a": (0, 160, 240),   "l": (240, 245, 255), "t": (5, 15, 50)},
    "default":    {"p": (20, 45, 130),  "a": (255, 196, 0),   "l": (248, 250, 255), "t": (10, 15, 50)},
}


def _th(niche):
    return THEMES.get(niche.lower(), THEMES["default"])


def _f(weight, sz):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Poppins-{weight}.ttf"), int(sz * R))


def _save(img, path):
    img.resize((SIZE, SIZE), Image.LANCZOS).save(path, "JPEG", quality=93)


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


def _grad(img, fy=0.35, color=(0, 0, 0), alpha=220):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d, h = ImageDraw.Draw(overlay), img.size[1]
    start = int(h * fy)
    for i in range(start, h):
        a = int(alpha * ((i - start) / max(h - start, 1)) ** 0.65)
        d.line([(0, i), (img.size[0], i)], fill=(*color, a))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _chip(draw, x, y, text, font, bg, fg):
    bx = font.getbbox(text)
    px, py = int(18 * R), int(8 * R)
    w2, h2 = bx[2] + 2 * px, bx[3] + 2 * py
    draw.rounded_rectangle([x, y, x + w2, y + h2], radius=int(18 * R), fill=bg)
    draw.text((x + px, y + py), text, font=font, fill=fg)
    return x + w2, y + h2


def _overlay_circle(img, cx, cy, cr, color, a=18):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(*color, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def make_slides(photo_path, product_name, price, hook, tagline,
                features, feature_descs, cta, niche, out_dir):
    photo = Image.open(photo_path).convert("RGB")
    t = _th(niche)
    p, tw = int(PAD * R), S - int(PAD * R) * 2
    paths = []

    # Slide 1: COVER
    img = _grad(_sq(photo), 0.30, t["p"], 238)
    d = ImageDraw.Draw(img)
    _chip(d, p, p, f"  {niche.upper()}  ", _f("SemiBold", 13), t["a"], t["p"])
    d.text((S - p, p + int(8 * R)), "1 / 6", font=_f("Bold", 13), fill=(255, 255, 255), anchor="rt")
    y = int(S * 0.54)
    y = _put(d, product_name.upper(), _f("ExtraBold", 46), p, y, tw, (255, 255, 255), lh=1.1)
    y += int(14 * R)
    _put(d, tagline, _f("Medium", 21), p, y, tw, (218, 212, 195))
    path = os.path.join(out_dir, "slide_1_cover.jpg")
    _save(img, path)
    paths.append(path)

    # Slide 2: HOOK
    img = Image.new("RGB", (S, S), t["l"])
    d = ImageDraw.Draw(img)
    d.rectangle([p, int(S * 0.1), p + int(7 * R), int(S * 0.9)], fill=t["a"])
    tx = p + int(30 * R)
    y = int(S * 0.15)
    y = _put(d, f'"{hook}"', _f("ExtraBold", 48), tx, y, S - tx - p, t["p"], lh=1.3)
    y += int(36 * R)
    _put(d, "— produk pilihan terbaik kami", _f("Medium", 19), tx, y, S - tx - p, (130, 125, 150))
    cs = int(S * 0.34)
    thumb = _sq(photo, cs)
    mask = Image.new("L", (cs, cs), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, cs, cs], fill=255)
    cx, cy = S - p - cs, int(S * 0.53)
    img.paste(thumb, (cx, cy), mask)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - int(5 * R), cy - int(5 * R), cx + cs + int(5 * R), cy + cs + int(5 * R)],
              outline=t["a"], width=int(5 * R))
    d.text((S - p, S - p), "2 / 6", font=_f("Bold", 13), fill=t["p"], anchor="rb")
    path = os.path.join(out_dir, "slide_2_hook.jpg")
    _save(img, path)
    paths.append(path)

    # Slides 3-5: FEATURES
    sq = _sq(photo)
    for i, (feat, desc) in enumerate(zip(features[:3], feature_descs[:3])):
        sn = i + 3
        img = Image.new("RGB", (S, S), (255, 255, 255))
        ph = int(S * 0.50)
        strip = _grad(sq.crop((0, 0, S, ph)), 0.50, t["p"], 165)
        img.paste(strip, (0, 0))
        d = ImageDraw.Draw(img)
        d.text((p, ph - int(12 * R)), f"0{i + 1}", font=_f("ExtraBold", 80), fill=t["a"], anchor="lb")
        y = ph + int(30 * R)
        y = _put(d, feat.upper(), _f("Bold", 30), p, y, tw, t["p"])
        y += int(18 * R)
        _put(d, desc, _f("Regular", 21), p, y, tw, (90, 88, 110), lh=1.45)
        dy = S - int(54 * R)
        dx = S // 2 - int(76 * R)
        for j in range(6):
            active = j == sn - 1
            r2 = int(11 * R) if active else int(7 * R)
            col = t["a"] if active else (200, 198, 210)
            d.ellipse([dx + j * int(26 * R) - r2 // 2, dy - r2 // 2,
                       dx + j * int(26 * R) + r2 // 2, dy + r2 // 2], fill=col)
        d.text((S - p, S - p), f"{sn} / 6", font=_f("Bold", 13), fill=(175, 172, 188), anchor="rb")
        path = os.path.join(out_dir, f"slide_{sn}_feat{i + 1}.jpg")
        _save(img, path)
        paths.append(path)

    # Slide 6: CTA
    img = Image.new("RGB", (S, S), t["p"])
    img = _overlay_circle(img, int(S * .88), int(S * .12), int(S * .28), t["a"], 18)
    img = _overlay_circle(img, int(S * .08), int(S * .88), int(S * .22), t["a"], 14)
    d = ImageDraw.Draw(img)
    y = int(S * 0.10)
    y = _put(d, cta.upper(), _f("ExtraBold", 44), p, y, tw, (255, 255, 255), lh=1.1)
    y += int(50 * R)
    d.line([(p, y), (p + int(130 * R), y)], fill=t["a"], width=int(5 * R))
    y += int(52 * R)
    y = _put(d, price, _f("ExtraBold", 66), p, y, tw, t["a"])
    ts = int(S * 0.27)
    thumb = _sq(photo, ts)
    mask = Image.new("L", (ts, ts), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ts, ts], radius=int(28 * R), fill=255)
    img.paste(thumb, (S - p - ts, S - p - ts), mask)
    d = ImageDraw.Draw(img)
    d.text((p, S - p), "DM / WA untuk order >>", font=_f("SemiBold", 20), fill=(210, 208, 200), anchor="lb")
    d.text((S - p, p + int(8 * R)), "6 / 6", font=_f("Bold", 13), fill=(190, 188, 200), anchor="rt")
    path = os.path.join(out_dir, "slide_6_cta.jpg")
    _save(img, path)
    paths.append(path)

    return paths
