"""Render a vertical 1080x1920 'fakta unik' Reel: stock video bg + text overlay + brand.

Reuses fonts/palette from fakta_image_maker. Needs ffmpeg (set FFMPEG env or PATH).
The overlay is rendered at 2x then downscaled for crisp type, and includes a baked
gradient scrim so text stays legible over any video.
"""
import os
import shutil
import subprocess

from PIL import Image, ImageDraw

from fakta_image_maker import (
    BRAND_TEXT, CYAN, CYAN_INK, INDIGO_DEEP, MUTED, NICHE_LABELS, PAD, WHITE,
    _brand_chip, _category_pill, _font, _tracked, _wrap, s,
)

VW, VH = 1080, 1920
RW, RH = VW * 2, VH * 2  # 2x render space (matches fakta_image_maker SS=2)

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def _reel_scrim() -> Image.Image:
    a = Image.new("L", (1, RH), 0)
    px = a.load()
    for y in range(RH):
        ty = y / (RH - 1)
        top = 0.22 * (1 - ty / 0.16) if ty < 0.16 else 0.0
        bot = (((ty - 0.40) / 0.60) ** 1.3) * 0.90 if ty > 0.40 else 0.0
        px[0, y] = int(255 * min(max(top, bot), 0.92))
    scrim = Image.new("RGBA", (RW, RH), (*INDIGO_DEEP, 255))
    scrim.putalpha(a.resize((RW, RH)))
    return scrim


def make_reel_overlay(hook: str, category: str, fact: str, out_png: str) -> str:
    canvas = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, _reel_scrim())
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle([0, 0, RW, s(6)], fill=CYAN)

    _brand_chip(draw)

    kf = _font("extrabold", 38)
    hf = _font("extrabold", 60)
    ff = _font("semibold", 40)
    max_w = RW - 2 * s(PAD)

    hook_lines = _wrap(hook, hf, max_w)
    fact_lines = _wrap(fact, ff, max_w)
    hook_lh = int(hf.size * 1.07)
    fact_lh = int(ff.size * 1.26)

    # bottom CTA
    cf = _font("bold", 32)
    subf = _font("medium", 26)
    sub_y = RH - s(PAD) - subf.size - s(2)
    px_, py_ = s(26), s(16)
    pill_h = cf.size + 2 * py_
    pill_y = sub_y - s(22) - pill_h

    # text block sits above the CTA
    block_bottom = pill_y - s(70)
    block_h = (len(hook_lines) * hook_lh) + s(30) + (len(fact_lines) * fact_lh)
    cat_h = _font("bold", 22).size + 2 * s(9)
    kicker_h = kf.size
    top_extra = cat_h + s(22) + kicker_h + s(28)
    start_y = block_bottom - block_h - top_extra

    label = NICHE_LABELS.get((category or "").lower(), (category or "FAKTA").upper())
    _category_pill(draw, label, s(PAD), start_y)
    _tracked(draw, (s(PAD), start_y + cat_h + s(22)), "TAU GAK SIH?", kf, WHITE, 1)

    y = start_y + cat_h + s(22) + kicker_h + s(28)
    for ln in hook_lines:
        draw.text((s(PAD), y), ln, font=hf, fill=WHITE)
        y += hook_lh
    y += s(30)
    for ln in fact_lines:
        draw.text((s(PAD), y), ln, font=ff, fill=(214, 220, 240))
        y += fact_lh

    ct = f"Follow @{BRAND_TEXT.lower()}"
    ctw = cf.getlength(ct)
    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px_, pill_y + pill_h],
                           radius=s(14), fill=CYAN)
    draw.text((s(PAD) + px_, pill_y + py_ - s(4)), ct, font=cf, fill=CYAN_INK)
    draw.text((s(PAD), sub_y), "1 fakta unik tiap hari", font=subf, fill=MUTED)

    canvas.resize((VW, VH), Image.LANCZOS).save(out_png)
    return out_png


def render_reel(bg_video: str, overlay_png: str, out_mp4: str, duration: int = 12) -> str:
    cmd = [
        FFMPEG, "-y", "-i", bg_video, "-i", overlay_png,
        "-filter_complex",
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1[bg];[bg][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]", "-t", str(duration), "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-an", "-movflags", "+faststart", out_mp4,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_mp4
