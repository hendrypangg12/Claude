"""Compose 1080x1080 IG carousel slides for a 'fakta unik' (curiosity) page.

Separate brand from BERSTOCK.ID — cosmic indigo + cyan look. Rendered at 2x then
downscaled (supersampling) for crisp type. Reuses the Poppins fonts bundled with
the news poster (../daily-news-poster/fonts).
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

# ---- geometry ----
SIZE = 1080
SS = 2
R = SIZE * SS
PAD = 74

# ---- brand (ganti via env BRAND / HANDLE kalau perlu) ----
BRAND_TEXT = os.environ.get("BRAND", "FAKTAVIRAL")   # logo chip
HANDLE = os.environ.get("HANDLE", "faktaviral.idn")   # @username buat CTA

# ---- palette (cosmic indigo + cyan) ----
INDIGO = (32, 27, 64)
INDIGO_DEEP = (13, 11, 28)
CYAN = (96, 224, 255)
CYAN_INK = (8, 16, 22)        # text on cyan
WHITE = (244, 246, 251)
MUTED = (164, 162, 196)
FAINT = (120, 120, 158)
# ---- palet BERSIH (gaya fakta.indo): emas + putih ----
GOLD = (255, 214, 0)
INK_GOLD = (18, 16, 12)        # text di atas emas

NICHE_LABELS = {
    "sains": "SAINS",
    "sejarah": "SEJARAH",
    "tubuh": "TUBUH MANUSIA",
    "otak": "OTAK & PIKIRAN",
    "psikologi": "PSIKOLOGI",
    "hewan": "DUNIA HEWAN",
    "laut": "DUNIA LAUT",
    "serangga": "SERANGGA",
    "dinosaurus": "DINOSAURUS",
    "tumbuhan": "TUMBUHAN",
    "luarangkasa": "LUAR ANGKASA",
    "teknologi": "TEKNOLOGI",
    "internet": "INTERNET & MEDSOS",
    "geografi": "GEOGRAFI",
    "negara": "NEGARA & DUNIA",
    "alam": "ALAM",
    "cuaca": "CUACA & IKLIM",
    "makanan": "MAKANAN",
    "kuliner": "KULINER DUNIA",
    "kesehatan": "KESEHATAN",
    "olahraga": "OLAHRAGA",
    "hiburan": "FILM & HIBURAN",
    "musik": "MUSIK",
    "budaya": "BUDAYA & TRADISI",
    "bahasa": "BAHASA",
    "ekonomi": "EKONOMI",
    "uang": "UANG & FINANSIAL",
    "keuangan": "KEUANGAN VIRAL",
    "aktor": "SELEBRITI",
    "trending": "LAGI VIRAL",
    "rekor": "REKOR DUNIA",
    "misteri": "MISTERI & MITOS",
    "transportasi": "TRANSPORTASI",
    "bangunan": "BANGUNAN MEGAH",
    "militer": "MILITER & PERANG",
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


def _photo_bg(path: str, base: float = 0.14, peak: float = 0.93) -> Image.Image:
    """Topic photo fitted to the square + indigo scrim for legible text.

    base = darkening floor (low = photo prominent for cover; high = text-heavy slides)."""
    img = Image.open(path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img, (R, R), method=Image.LANCZOS, centering=(0.5, 0.42))
    img = ImageEnhance.Color(img).enhance(1.06)
    img = img.convert("RGBA")

    a = Image.new("L", (1, R), 0)
    px = a.load()
    for y in range(R):
        t = y / (R - 1)
        v = base + (peak - base) * (t ** 1.4)
        px[0, y] = int(255 * min(v, 0.96))
    scrim = Image.new("RGBA", (R, R), (*INDIGO_DEEP, 255))
    scrim.putalpha(a.resize((R, R)))
    out = Image.alpha_composite(img, scrim).convert("RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    draw.rectangle([0, 0, R, s(6)], fill=CYAN)
    return out


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

# ===== GAYA BERSIH (ala fakta.indo): foto dominan + judul minimal kuning+putih =====

def _photo_cover(path: str) -> Image.Image:
    """Foto full-bleed ke square, boost tipis. TANPA scrim berat (biar foto dominan)."""
    img = Image.open(path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img, (R, R), method=Image.LANCZOS, centering=(0.5, 0.38))
    img = ImageEnhance.Color(img).enhance(1.05)
    img = ImageEnhance.Contrast(img).enhance(1.03)
    return img.convert("RGB")


def _grad(canvas, *, bottom=0.0, top=0.0) -> Image.Image:
    """Tambah gradasi gelap di bawah (`bottom` start-frac) &/atau atas (`top` end-frac)."""
    a = Image.new("L", (1, R), 0)
    px = a.load()
    for y in range(R):
        t = y / (R - 1)
        v = 0.0
        if bottom and t >= bottom:
            v = max(v, ((t - bottom) / (1 - bottom)) ** 1.25 * 0.94)
        if top and t <= top:
            v = max(v, (1 - t / top) ** 1.1 * 0.5)
        px[0, y] = int(255 * min(v, 0.95))
    dark = Image.new("RGB", (R, R), (8, 9, 12))
    return Image.composite(dark, canvas.convert("RGB"), a.resize((R, R)))


def _brand_chip_gold(draw, x=PAD, y=PAD) -> None:
    f = _font("extrabold", 26)
    tw = f.getlength(BRAND_TEXT)
    px, py = s(18), s(11)
    draw.rounded_rectangle([s(x), s(y), s(x) + tw + 2 * px, s(y) + f.size + 2 * py],
                           radius=s(10), fill=GOLD)
    draw.text((s(x) + px, s(y) + py - s(4)), BRAND_TEXT, font=f, fill=INK_GOLD)


def _watermark(draw) -> None:
    f = _font("extrabold", 28)
    draw.text((R - s(PAD) - f.getlength(HANDLE), R - s(PAD) - f.size), HANDLE,
              font=f, fill=(255, 255, 255, 205))


def _split_hl(hook, highlight=None):
    """(teks_kuning, teks_putih). Pakai `highlight` kalau ada di hook; else heuristik:
    potong di koma pertama, atau ~45% kata pertama jadi kuning (ala fakta.indo)."""
    h = (hook or "").strip()
    if highlight and highlight.strip() and highlight.strip().lower() in h.lower():
        j = h.lower().index(highlight.strip().lower()) + len(highlight.strip())
        return h[:j].strip(), h[j:].strip()
    if "," in h[:len(h) - 1]:
        i = h.index(",")
        return h[:i + 1].strip(), h[i + 1:].strip()
    w = h.split()
    k = max(1, round(len(w) * 0.45))
    return " ".join(w[:k]), " ".join(w[k:])


def _headline(draw, yellow, white, font, bottom_y, max_w, lh) -> int:
    """Judul 2 warna (kuning+putih), wrap, anchor BAWAH. Return tinggi blok."""
    words = [(w, GOLD) for w in yellow.split()] + [(w, WHITE) for w in white.split()]
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


def compose_cover(hook, category, out_path, bg_path=None, highlight=None, source=None) -> str:
    try:
        canvas = _photo_cover(bg_path) if bg_path else _bg()
    except Exception:
        canvas = _bg()
    canvas = _grad(canvas, bottom=0.40, top=0.24)
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip_gold(draw)
    hf = _font("extrabold", 66)
    lh = int(hf.size * 1.08)
    yellow, white = _split_hl(hook, highlight)
    bottom = R - s(155)
    hh = _headline(draw, yellow, white, hf, bottom, R - 2 * s(PAD), lh)
    if source:
        sf = _font("medium", 28)
        draw.text((s(PAD), bottom - hh - s(50)), f"Sumber: {source}", font=sf, fill=(210, 212, 218))
    _watermark(draw)
    return _save(canvas, out_path)


def compose_fact(fact, detail, out_path, bg_path=None, source=None) -> str:
    """Slide isi: foto di ATAS, teks paragraf di bawah (panel gelap). Ala fakta.indo."""
    photo_h = int(R * 0.50)
    canvas = Image.new("RGB", (R, R), (13, 14, 17))
    if bg_path:
        try:
            img = ImageOps.exif_transpose(Image.open(bg_path).convert("RGB"))
            img = ImageOps.fit(img, (R, photo_h + s(60)), method=Image.LANCZOS, centering=(0.5, 0.4))
            canvas.paste(img, (0, 0))
            # fade foto -> panel
            a = Image.new("L", (1, R), 0); px = a.load()
            for y in range(R):
                px[0, y] = 0 if y < photo_h - s(80) else min(255, int(255 * (y - (photo_h - s(80))) / s(140)))
            canvas = Image.composite(Image.new("RGB", (R, R), (13, 14, 17)), canvas, a.resize((R, R)))
        except Exception:
            pass
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip_gold(draw)
    top = photo_h + s(78)
    draw.rectangle([s(PAD), top, s(PAD) + s(92), top + s(8)], fill=GOLD)  # aksen emas
    top += s(38)
    # auto-fit biar teks gak mentok bawah
    bottom_lim = R - s(120)
    for fs in (48, 45, 42, 39, 36, 33):
        ff = _font("semibold", fs); df = _font("medium", int(fs * 0.76))
        flh = int(ff.size * 1.22); dlh = int(df.size * 1.34)
        flines = _wrap(fact, ff, R - 2 * s(PAD))
        dlines = _wrap(detail, df, R - 2 * s(PAD)) if detail else []
        h = len(flines) * flh + (s(24) + len(dlines) * dlh if dlines else 0)
        if top + h <= bottom_lim:
            break
    y = top
    for ln in flines:
        draw.text((s(PAD), y), ln, font=ff, fill=WHITE); y += flh
    if dlines:
        y += s(24)
        for ln in dlines:
            draw.text((s(PAD), y), ln, font=df, fill=(202, 204, 212)); y += dlh
    if source:
        cf = _font("medium", 26)
        draw.text((s(PAD), R - s(PAD) - cf.size), f"Sumber: {source}", font=cf, fill=(150, 152, 160))
    _watermark(draw)
    return _save(canvas, out_path)


def compose_outro(takeaway, out_path, bg_path=None) -> str:
    try:
        canvas = _photo_cover(bg_path) if bg_path else _bg()
    except Exception:
        canvas = _bg()
    canvas = _grad(canvas, bottom=0.28, top=0.20)
    draw = ImageDraw.Draw(canvas, "RGBA")
    _brand_chip_gold(draw)
    cf = _font("bold", 40)
    ct = f"Follow @{HANDLE}"
    ctw = cf.getlength(ct)
    px, py = s(30), s(18)
    pill_h = cf.size + 2 * py
    pill_y = R - s(150) - pill_h
    tf = _font("semibold", 50)
    lh = int(tf.size * 1.2)
    lines = _wrap(takeaway or "Pantau terus update terbaru di sini.", tf, R - 2 * s(PAD))
    bottom = pill_y - s(54)
    y = bottom - len(lines) * lh
    for ln in lines:
        draw.text((s(PAD), y), ln, font=tf, fill=WHITE); y += lh
    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px, pill_y + pill_h],
                           radius=s(16), fill=GOLD)
    draw.text((s(PAD) + px, pill_y + py - s(5)), ct, font=cf, fill=INK_GOLD)
    return _save(canvas, out_path)
