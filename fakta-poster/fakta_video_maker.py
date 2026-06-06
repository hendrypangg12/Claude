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
    BRAND_TEXT, CYAN, CYAN_INK, HANDLE, INDIGO_DEEP, MUTED, NICHE_LABELS, PAD, WHITE,
    _brand_chip, _category_pill, _font, _tracked, _wrap, s,
)

VW, VH = 1080, 1920
RW, RH = VW * 2, VH * 2  # 2x render space (matches fakta_image_maker SS=2)

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"
_DEVNULL = subprocess.DEVNULL


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

    ct = f"Follow @{HANDLE}"
    ctw = cf.getlength(ct)
    draw.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px_, pill_y + pill_h],
                           radius=s(14), fill=CYAN)
    draw.text((s(PAD) + px_, pill_y + py_ - s(4)), ct, font=cf, fill=CYAN_INK)
    draw.text((s(PAD), sub_y), "1 fakta unik tiap hari", font=subf, fill=MUTED)

    canvas.resize((VW, VH), Image.LANCZOS).save(out_png)
    return out_png


def _duration(path: str) -> float:
    try:
        out = subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path]
        ).decode().strip()
        return float(out)
    except Exception:
        return 0.0


def _normalize(src: str, dst: str, max_sec: int = 10) -> str:
    """Crop/scale a clip to 1080x1920 @30fps, capped at max_sec, uniform codec."""
    cmd = [
        FFMPEG, "-y", "-i", src, "-t", str(max_sec),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
               "crop=1080:1920,setsar=1,fps=30",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", dst,
    ]
    subprocess.run(cmd, check=True, stdout=_DEVNULL, stderr=_DEVNULL)
    return dst


def render_reel(bg_videos, overlay_png: str, out_mp4: str,
                min_dur: int = 30, max_dur: int = 45, per_clip: int = 15) -> str:
    """Build a 30-45s reel: normalize + concat clips, loop to fill, then overlay text."""
    if isinstance(bg_videos, str):
        bg_videos = [bg_videos]
    workdir = os.path.dirname(out_mp4) or "."

    norm, total = [], 0.0
    for i, src in enumerate(bg_videos):
        dst = os.path.join(workdir, f"_norm_{i}.mp4")
        try:
            _normalize(src, dst, max_sec=per_clip)
        except Exception:
            continue
        d = _duration(dst)
        if d > 0:
            norm.append(dst)
            total += d
    if not norm:
        raise RuntimeError("No usable background video")

    list_file = os.path.join(workdir, "_concat.txt")
    with open(list_file, "w") as f:
        for p in norm:
            f.write(f"file '{os.path.abspath(p)}'\n")
    concat = os.path.join(workdir, "_bg.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                    "-c", "copy", concat], check=True, stdout=_DEVNULL, stderr=_DEVNULL)

    # target within [min_dur, max_dur]; loop the concat to fill if footage is short
    target = int(max(min_dur, min(max_dur, round(total)))) if total >= min_dur else min_dur
    cmd = [
        FFMPEG, "-y", "-stream_loop", "-1", "-i", concat, "-i", overlay_png,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]", "-t", str(target), "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-an", "-movflags", "+faststart", out_mp4,
    ]
    subprocess.run(cmd, check=True, stdout=_DEVNULL, stderr=_DEVNULL)

    for p in norm + [list_file, concat]:
        try:
            os.remove(p)
        except OSError:
            pass
    return out_mp4
