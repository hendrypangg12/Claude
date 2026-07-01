from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import os

R = 2
SIZE = 1080
S = SIZE * R
PAD = 56

_HERE = os.path.dirname(__file__)
FONT_DIR = os.path.join(_HERE, "fonts")
if not os.path.isdir(FONT_DIR):
    FONT_DIR = os.path.join(_HERE, "..", "daily-news-poster", "fonts")

THEMES = {
    "makanan":    {"bg": (14, 8, 4),   "bg2": (28, 14, 6),   "acc": (255, 110, 10),  "acc2": (255, 200, 50), "light": (255, 248, 235)},
    "kuliner":    {"bg": (14, 8, 4),   "bg2": (28, 14, 6),   "acc": (255, 110, 10),  "acc2": (255, 200, 50), "light": (255, 248, 235)},
    "fashion":    {"bg": (10, 8, 18),  "bg2": (22, 16, 40),  "acc": (255, 215, 80),  "acc2": (200, 160, 255),"light": (248, 245, 255)},
    "kecantikan": {"bg": (20, 8, 14),  "bg2": (40, 12, 26),  "acc": (255, 160, 190), "acc2": (255, 220, 230),"light": (255, 248, 252)},
    "beauty":     {"bg": (20, 8, 14),  "bg2": (40, 12, 26),  "acc": (255, 160, 190), "acc2": (255, 220, 230),"light": (255, 248, 252)},
    "elektronik": {"bg": (4, 8, 20),   "bg2": (8, 18, 44),   "acc": (0, 200, 255),   "acc2": (80, 160, 255), "light": (240, 248, 255)},
    "teknologi":  {"bg": (4, 8, 20),   "bg2": (8, 18, 44),   "acc": (0, 200, 255),   "acc2": (80, 160, 255), "light": (240, 248, 255)},
    "default":    {"bg": (8, 10, 20),  "bg2": (16, 22, 48),  "acc": (255, 196, 0),   "acc2": (255, 140, 30), "light": (248, 250, 255)},
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


def _put(draw, text, font, x, y, mw, color, center=False, lh=1.2):
    lines = _wrap(text, font, mw)
    lh_px = int(font.size * lh)
    for i, line in enumerate(lines):
        tx = x
        if center:
            lw = font.getbbox(line)[2]
            tx = x + (mw - lw) // 2
        draw.text((tx, y + i * lh_px), line, font=font, fill=color)
    return y + len(lines) * lh_px


def _grad_bg(size, c1, c2):
    img = Image.new("RGB", size, c1)
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    w, h = size
    for i in range(h):
        t = i / max(h - 1, 1)
        col = tuple(int(c1[j] + (c2[j] - c1[j]) * t) for j in range(3))
        d.line([(0, i), (w, i)], fill=(*col, 255))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _place_product(base, product_rgba, cx, cy, scale=0.75):
    pw = int(S * scale)
    w, h = product_rgba.size
    ratio = pw / max(w, h)
    nw, nh = int(w * ratio), int(h * ratio)
    prod = product_rgba.resize((nw, nh), Image.LANCZOS)
    x, y = cx - nw // 2, cy - nh // 2
    base.paste(prod, (x, y), prod)
    return base


def _chip(draw, x, y, text, font, bg, fg):
    bx = font.getbbox(text)
    px, py = int(18 * R), int(8 * R)
    w2, h2 = bx[2] + 2 * px, bx[3] + 2 * py
    draw.rounded_rectangle([x, y, x + w2, y + h2], radius=int(16 * R), fill=bg)
    draw.text((x + px, y + py), text, font=font, fill=fg)
    return x + w2, y + h2


def _pill_btn(draw, x, y, w, text, font, bg, fg):
    h = int(font.size * 1.8)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    bx = font.getbbox(text)
    draw.text((x + w // 2 - bx[2] // 2, y + h // 2 - bx[3] // 2 - int(1 * R)),
              text, font=font, fill=fg)
    return y + h


def _seg_bar(draw, y, total, current, acc, dim):
    sw, sh, gap = int(72 * R), int(7 * R), int(10 * R)
    total_w = total * sw + (total - 1) * gap
    x0 = (S - total_w) // 2
    for i in range(total):
        x = x0 + i * (sw + gap)
        col = acc if i == current else dim
        draw.rounded_rectangle([x, y, x + sw, y + sh], radius=sh // 2, fill=col)


def _slide1(prod_rgba, product_name, price, hook, niche, t, out_dir):
    img = _grad_bg((S, S), t["bg"], t["bg2"])
    d = ImageDraw.Draw(img)
    for yi in range(0, S, int(80 * R)):
        for xi in range(0, S, int(80 * R)):
            d.ellipse([xi, yi, xi + int(3 * R), yi + int(3 * R)], fill=(*t["acc"], 18))
    img = _place_product(img, prod_rgba, int(S * 0.68), int(S * 0.52), scale=0.82)
    d = ImageDraw.Draw(img)
    _chip(d, int(PAD * R), int(PAD * R), niche.upper(), _f("Bold", 13), t["acc"], t["bg"])
    d.text((S - int(PAD * R), int(PAD * R) + int(6 * R)), "1 / 6",
           font=_f("Bold", 13), fill=(180, 175, 200), anchor="rt")
    words = hook.split()
    split_at = min(3, max(1, len(words) // 2))
    line1 = " ".join(words[:split_at]).upper()
    line2 = " ".join(words[split_at:]).upper()
    y = int(S * 0.30)
    mw = int(S * 0.56)
    y = _put(d, line1, _f("ExtraBold", 52), int(PAD * R), y, mw, t["acc"], lh=1.05)
    y = _put(d, line2, _f("ExtraBold", 48), int(PAD * R), y, mw, (255, 255, 255), lh=1.05)
    y += int(36 * R)
    _pill_btn(d, int(PAD * R), y, int(220 * R), price, _f("ExtraBold", 22), t["acc"], t["bg"])
    path = os.path.join(out_dir, "slide_1_cover.jpg")
    _save(img, path)
    return path


def _slide2(prod_rgba, product_name, tagline, t, out_dir):
    img = _grad_bg((S, S), t["bg2"], t["bg"])
    img = _place_product(img, prod_rgba, S // 2, int(S * 0.50), scale=0.88)
    d = ImageDraw.Draw(img)
    fn_label = _f("ExtraBold", 50)
    words = product_name.upper().split()
    split = max(1, len(words) // 2)
    line1 = " ".join(words[:split])
    line2 = " ".join(words[split:])
    y = int(PAD * R)
    bx1 = fn_label.getbbox(line1)
    d.text((S // 2 - bx1[2] // 2, y), line1, font=fn_label, fill=t["acc"])
    if line2:
        y2 = y + int(fn_label.size * 1.05)
        bx2 = fn_label.getbbox(line2)
        d.text((S // 2 - bx2[2] // 2, y2), line2, font=fn_label, fill=(255, 255, 255))
    fn_tag = _f("Medium", 20)
    mw = int(S * 0.75)
    lines_tag = _wrap(tagline, fn_tag, mw)
    lh_tag = int(fn_tag.size * 1.3)
    ty = S - int(PAD * R) - len(lines_tag) * lh_tag - int(50 * R)
    d.rectangle([0, ty - int(24 * R), S, S], fill=(*t["bg"], 170))
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines_tag):
        bx = fn_tag.getbbox(line)
        d.text((S // 2 - bx[2] // 2, ty + i * lh_tag), line, font=fn_tag, fill=(210, 205, 195))
    d.text((S - int(PAD * R), S - int(52 * R)), "2 / 6",
           font=_f("Bold", 13), fill=(130, 125, 150), anchor="rb")
    path = os.path.join(out_dir, "slide_2_hook.jpg")
    _save(img, path)
    return path


def _slide3_5(prod_rgba, feat, desc, idx, t, out_dir):
    img = _grad_bg((S, S), t["bg"], t["bg2"])
    img = _place_product(img, prod_rgba, int(S * 0.72), int(S * 0.54), scale=0.72)
    d = ImageDraw.Draw(img)
    sn = idx + 3
    fn_num = _f("ExtraBold", 240)
    num_str = f"0{idx + 1}"
    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((int(PAD * R) - int(20 * R), int(S * 0.30)), num_str,
                             font=fn_num, fill=(*t["acc"], 22))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)
    bar_x = int(PAD * R)
    bar_y = int(S * 0.20)
    d.rectangle([bar_x, bar_y, bar_x + int(8 * R), bar_y + int(140 * R)], fill=t["acc"])
    tx = bar_x + int(28 * R)
    mw_left = int(S * 0.52)
    words = feat.upper().split()
    split = max(1, len(words) // 2)
    y = bar_y
    fn_ft = _f("ExtraBold", 38)
    y = _put(d, " ".join(words[:split]), fn_ft, tx, y, mw_left, t["acc"], lh=1.1)
    if words[split:]:
        y = _put(d, " ".join(words[split:]), fn_ft, tx, y, mw_left, (255, 255, 255), lh=1.1)
    y += int(28 * R)
    _put(d, desc, _f("Regular", 20), tx, y, mw_left, (185, 180, 200), lh=1.5)
    _seg_bar(d, S - int(72 * R), 6, sn - 1, t["acc"], (*t["acc"][:3], 50))
    d.text((int(PAD * R), S - int(50 * R)), f"{sn} / 6",
           font=_f("Bold", 13), fill=(130, 125, 150))
    path = os.path.join(out_dir, f"slide_{sn}_feat{idx + 1}.jpg")
    _save(img, path)
    return path


def _slide6(prod_rgba, cta, price, contact, niche, t, out_dir):
    img = _grad_bg((S, S), t["bg2"], t["bg"])
    img = _place_product(img, prod_rgba, int(S * 0.66), int(S * 0.55), scale=0.80)
    sh = int(50 * R)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, S, sh], fill=t["acc"])
    d.text((int(PAD * R), int(12 * R)), "DAPATKAN SEKARANG",
           font=_f("Bold", 14), fill=t["bg"])
    d.text((S - int(PAD * R), int(12 * R)), "6 / 6",
           font=_f("Bold", 14), fill=t["bg"], anchor="rt")
    p = int(PAD * R)
    mw_left = int(S * 0.52)
    y = sh + int(60 * R)
    words = cta.upper().split()
    split = max(1, len(words) // 2)
    fn_cta = _f("ExtraBold", 44)
    y = _put(d, " ".join(words[:split]), fn_cta, p, y, mw_left, t["acc"], lh=1.05)
    if words[split:]:
        y = _put(d, " ".join(words[split:]), fn_cta, p, y, mw_left, (255, 255, 255), lh=1.05)
    y += int(40 * R)
    d.line([(p, y), (p + int(90 * R), y)], fill=t["acc"], width=int(5 * R))
    y += int(40 * R)
    fn_price = _f("ExtraBold", 68)
    d.text((p, y), price, font=fn_price, fill=t["acc"])
    y += fn_price.getbbox(price)[3] + int(44 * R)
    _pill_btn(d, p, y, int(300 * R), "ORDER SEKARANG →", _f("Bold", 19), t["acc"], t["bg"])
    ct = contact or "DM / WA untuk order"
    d.text((p, S - int(52 * R)), ct, font=_f("Medium", 17), fill=(160, 155, 180))
    path = os.path.join(out_dir, "slide_6_cta.jpg")
    _save(img, path)
    return path


def make_slides(photo_path, product_name, price, hook, tagline,
                features, feature_descs, cta, niche, out_dir, contact=""):
    photo = Image.open(photo_path).convert("RGB")
    t = _th(niche)
    prod_rgba = remove(photo)
    paths = []
    paths.append(_slide1(prod_rgba, product_name, price, hook, niche, t, out_dir))
    paths.append(_slide2(prod_rgba, product_name, tagline, t, out_dir))
    for i in range(3):
        feat = features[i] if i < len(features) else f"Keunggulan {i+1}"
        desc = feature_descs[i] if i < len(feature_descs) else ""
        paths.append(_slide3_5(prod_rgba, feat, desc, i, t, out_dir))
    paths.append(_slide6(prod_rgba, cta, price, contact, niche, t, out_dir))
    return paths
