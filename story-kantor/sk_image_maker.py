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

# palet BERSIH (ala post Folkative): putih + teks hitam. Minimal, ga lebay.
BG = (252, 252, 250)
INK = (24, 24, 26)
MUTED = (165, 165, 168)


def compose_statement(text, out_path, idx=0, total=3, last=False) -> str:
    canvas = Image.new("RGB", (R, R), BG)
    d = ImageDraw.Draw(canvas, "RGBA")

    # brand KECIL bold di kanan atas (ga lebay) — gaya Folkative
    bf = _font("extrabold", 24)
    d.text((R - s(PAD) - bf.getlength(BRAND_TEXT), s(PAD)), BRAND_TEXT, font=bf, fill=INK)

    # statement utama: auto-fit, rata kiri, tengah vertikal
    max_w = R - 2 * s(PAD)
    reserve = s(420) if last else s(300)
    f = _font("semibold", 70)
    lines = _wrap(text, f, max_w)
    for fs in (74, 68, 62, 56, 52, 48, 44, 40, 36):
        f = _font("semibold", fs)
        lh = int(f.size * 1.26)
        lines = _wrap(text, f, max_w)
        if len(lines) * lh <= R - reserve:
            break
    lh = int(f.size * 1.26)
    block_h = len(lines) * lh
    y = (R - block_h) // 2 + (-s(30) if last else s(6))
    for ln in lines:
        d.text((s(PAD), y), ln, font=f, fill=INK)
        y += lh

    # slide terakhir: ajakan follow minimalis (teks, bukan pill norak)
    if last:
        cf = _font("bold", 32)
        d.text((s(PAD), R - s(160) - cf.size), f"Follow @{HANDLE}", font=cf, fill=INK)

    # handle kiri-bawah (kalau bukan slide terakhir) + counter kanan-bawah
    hf = _font("medium", 25)
    if not last:
        d.text((s(PAD), R - s(PAD) - hf.size), "@" + HANDLE, font=hf, fill=MUTED)
    if total > 1:
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
    canvas.resize((size, size), Image.LANCZOS).save(out_path, "JPEG", quality=94)
    return out_path
