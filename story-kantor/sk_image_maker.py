"""Compose carousel 'Story Kantor' — gaya Folkative: hitam bersih + teks putih gede,
wordmark brand di-spasiin (letterspaced). Tiap slide = 1 statement relatable.

Reuse helper generik dari fakta_image_maker (font/wrap/tracking/skala)."""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fakta-poster"))
from fakta_image_maker import _font, _wrap, _tracked, s, R, SIZE, PAD  # noqa: E402

BRAND_TEXT = os.environ.get("SK_BRAND", "STORY KANTOR")
HANDLE = os.environ.get("SK_HANDLE", "storykantor.idn")

# palet Folkative: hitam pekat + putih, aksen emas tipis
BG = (12, 12, 14)
WHITE = (244, 244, 247)
MUTED = (138, 138, 146)
ACCENT = (255, 205, 0)


def _wordmark(draw, text, cx_right, y, size=26, tracking=8, fill=WHITE):
    """Tulis brand di-spasiin (letterspaced) rata-kanan ke cx_right. Return lebar."""
    f = _font("extrabold", size)
    w = sum(f.getlength(ch) + s(tracking) for ch in text) - s(tracking)
    _tracked(draw, (cx_right - w, y), text, f, fill, tracking)
    return w


def compose_statement(text, out_path, idx=0, total=3, last=False) -> str:
    canvas = Image.new("RGB", (R, R), BG)
    d = ImageDraw.Draw(canvas, "RGBA")

    # brand wordmark (letterspaced) — kanan atas + aksen bar kiri atas
    _wordmark(d, BRAND_TEXT, R - s(PAD), s(PAD), size=24, tracking=7, fill=WHITE)
    d.rectangle([s(PAD), s(PAD) + s(2), s(PAD) + s(56), s(PAD) + s(11)], fill=ACCENT)

    # statement utama: auto-fit, rata kiri, di tengah vertikal
    max_w = R - 2 * s(PAD)
    reserve = s(440) if last else s(330)
    f = _font("semibold", 70)
    lines = _wrap(text, f, max_w)
    for fs in (74, 68, 62, 56, 52, 48, 44, 40, 36):
        f = _font("semibold", fs)
        lh = int(f.size * 1.24)
        lines = _wrap(text, f, max_w)
        if len(lines) * lh <= R - reserve:
            break
    lh = int(f.size * 1.24)
    block_h = len(lines) * lh
    y = (R - block_h) // 2 + (-s(40) if last else s(10))
    for ln in lines:
        d.text((s(PAD), y), ln, font=f, fill=WHITE)
        y += lh

    # slide terakhir: pill Follow emas
    if last:
        cf = _font("bold", 34)
        ct = f"Follow @{HANDLE}"
        ctw = cf.getlength(ct)
        px, py = s(28), s(16)
        pill_h = cf.size + 2 * py
        pill_y = R - s(150) - pill_h
        d.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px, pill_y + pill_h],
                            radius=s(14), fill=ACCENT)
        d.text((s(PAD) + px, pill_y + py - s(5)), ct, font=cf, fill=(18, 16, 10))

    # handle kiri-bawah (kalau bukan slide terakhir) + counter kanan-bawah
    hf = _font("medium", 26)
    if not last:
        d.text((s(PAD), R - s(PAD) - hf.size), "@" + HANDLE, font=hf, fill=MUTED)
    cnt = f"{idx + 1}/{total}"
    cf2 = _font("medium", 24)
    d.text((R - s(PAD) - cf2.getlength(cnt), R - s(PAD) - cf2.size), cnt, font=cf2, fill=MUTED)

    canvas.resize((SIZE, SIZE), Image.LANCZOS).save(out_path, "JPEG", quality=92)
    return out_path


def make_profile(out_path, size=1080) -> str:
    """Foto profil: HITAM polos + wordmark 'STORY KANTOR' putih bold di-spasiin (ala Folkative)."""
    ss = 2
    R2 = size * ss
    canvas = Image.new("RGB", (R2, R2), (9, 9, 11))
    d = ImageDraw.Draw(canvas)
    parts = BRAND_TEXT.split()  # 2 baris: "STORY" / "KANTOR"
    fs = int(size * 0.13)
    ft = _font("extrabold", fs)   # _font pakai skala SS=2 internal → ukuran pas di R2
    track = int(size * 0.03)
    line_h = int(ft.size * 1.16)

    total_h = len(parts) * line_h
    y = (R2 - total_h) // 2
    for p in parts:
        w = sum(ft.getlength(c) + track for c in p) - track
        x = (R2 - w) // 2
        for ch in p:
            d.text((x, y), ch, font=ft, fill=WHITE)
            x += ft.getlength(ch) + track
        y += line_h
    # aksen emas tipis di bawah wordmark
    bw = int(R2 * 0.16)
    d.rectangle([(R2 - bw) // 2, y + int(size * 0.02), (R2 + bw) // 2, y + int(size * 0.025)], fill=ACCENT)
    canvas.resize((size, size), Image.LANCZOS).save(out_path, "JPEG", quality=94)
    return out_path
