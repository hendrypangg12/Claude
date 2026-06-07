"""Render reel 1080x1920 Beruang Finance: footage stock + overlay kuning + teks bertahap.

Reuse engine ffmpeg dari fakta_video_maker (_segment), tapi brand & progress bar kuning."""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fakta-poster"))
import fakta_video_maker as fv  # noqa: E402
from fakta_image_maker import _font, _wrap, s  # noqa: E402

BEAR_PATH = Path(__file__).resolve().parent / "brand" / "bear.png"
VW, VH = 1080, 1920
RW, RH = VW * 2, VH * 2

YELLOW = (255, 198, 0)
INK = (58, 38, 22)
WHITE = (250, 248, 242)
CREAM = (228, 222, 208)
BROWN_DEEP = (24, 16, 9)
HANDLE = os.environ.get("BF_HANDLE", "beruangfinance")


def _scrim() -> Image.Image:
    a = Image.new("L", (1, RH), 0)
    px = a.load()
    for y in range(RH):
        ty = y / (RH - 1)
        top = 0.30 * (1 - ty / 0.18) if ty < 0.18 else 0.0
        bot = (((ty - 0.38) / 0.62) ** 1.25) * 0.92 if ty > 0.38 else 0.0
        px[0, y] = int(255 * min(max(top, bot), 0.93))
    scrim = Image.new("RGBA", (RW, RH), (*BROWN_DEEP, 255))
    scrim.putalpha(a.resize((RW, RH)))
    return scrim


def make_reel_overlay(hook, kicker, lines, out_main, out_fact):
    """main = chrome + kicker + hook + CTA (t=0); fact = bullet list (fade in nanti)."""
    main = Image.alpha_composite(Image.new("RGBA", (RW, RH), (0, 0, 0, 0)), _scrim())
    dm = ImageDraw.Draw(main, "RGBA")
    fact = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    df = ImageDraw.Draw(fact, "RGBA")
    PAD = 70

    # brand chip
    bf = _font("extrabold", 34)
    tw = bf.getlength("BERUANG FINANCE")
    pxb, pyb = s(22), s(13)
    dm.rounded_rectangle([s(PAD), s(64), s(PAD) + tw + 2 * pxb, s(64) + bf.size + 2 * pyb],
                         radius=s(12), fill=YELLOW)
    dm.text((s(PAD) + pxb, s(64) + pyb - s(4)), "BERUANG FINANCE", font=bf, fill=INK)
    # bear top-right
    b = Image.open(BEAR_PATH).convert("RGBA")
    bw = s(190); b = b.resize((bw, int(b.height * bw / b.width)), Image.LANCZOS)
    main.alpha_composite(b, (RW - s(PAD) - bw, s(56)))

    # kicker + hook + bullets — anchor upper-mid + panel gelap di belakang (biar kebaca)
    kf = _font("extrabold", 44)
    hf = _font("extrabold", 78)
    lf = _font("semibold", 46)
    max_w = RW - 2 * s(PAD)
    hlines = _wrap(hook, hf, max_w)
    bullets = [_wrap(item, lf, max_w - s(50)) for item in lines]

    y0 = s(540)
    kick_h = int(kf.size * 1.2) + s(10)
    bul_h = sum(len(bl) * int(lf.size * 1.24) + s(20) for bl in bullets)
    block_end = y0 + kick_h + len(hlines) * int(hf.size * 1.05) + s(50) + bul_h
    pad_p = s(40)
    dm.rounded_rectangle([s(PAD) - pad_p, y0 - pad_p, RW - s(PAD) + pad_p, block_end + pad_p],
                         radius=s(30), fill=(18, 12, 6, 188))

    y = y0
    dm.text((s(PAD), y), (kicker or "TIPS KEUANGAN").upper(), font=kf, fill=YELLOW)
    y += kick_h
    for ln in hlines:
        dm.text((s(PAD), y), ln, font=hf, fill=WHITE)
        y += int(hf.size * 1.05)

    # fact bullets (own layer → fade-in)
    y += s(50)
    for bl in bullets:
        df.ellipse([s(PAD), y + s(14), s(PAD) + s(18), y + s(32)], fill=YELLOW)
        for ln in bl:
            df.text((s(PAD) + s(50), y), ln, font=lf, fill=WHITE)
            y += int(lf.size * 1.24)
        y += s(20)

    # CTA bottom
    cf = _font("bold", 36)
    subf = _font("medium", 30)
    sub_y = RH - s(PAD) - subf.size - s(4)
    px_, py_ = s(28), s(18)
    pill_h = cf.size + 2 * py_
    pill_y = sub_y - s(24) - pill_h
    ct = f"Follow @{HANDLE}"
    ctw = cf.getlength(ct)
    dm.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px_, pill_y + pill_h],
                         radius=s(16), fill=YELLOW)
    dm.text((s(PAD) + px_, pill_y + py_ - s(4)), ct, font=cf, fill=INK)
    dm.text((s(PAD), sub_y), "Melek duit, pelan-pelan", font=subf, fill=CREAM)

    main.resize((VW, VH), Image.LANCZOS).save(out_main)
    fact.resize((VW, VH), Image.LANCZOS).save(out_fact)
    return out_main, out_fact


def render_reel(bg_videos, main_png, fact_png, out_mp4, seg=15, max_segments=3, fact_at=2.5):
    """Sama seperti fakta render tapi progress bar KUNING (brand Beruang Finance)."""
    if isinstance(bg_videos, str):
        bg_videos = [bg_videos]
    workdir = os.path.dirname(out_mp4) or "."
    clips = bg_videos[:max_segments]
    segs = []
    if len(clips) <= 1:
        segs.append(fv._segment(clips[0], os.path.join(workdir, "_bseg0.mp4"), 2 * seg))
    else:
        for i, src in enumerate(clips):
            try:
                segs.append(fv._segment(src, os.path.join(workdir, f"_bseg{i}.mp4"), seg))
            except Exception:
                continue
    if not segs:
        raise RuntimeError("No usable background video")
    dur = 2 * seg if len(clips) <= 1 else len(segs) * seg
    lst = os.path.join(workdir, "_blist.txt")
    with open(lst, "w") as f:
        for p in segs:
            f.write(f"file '{os.path.abspath(p)}'\n")
    concat = os.path.join(workdir, "_bbg.mp4")
    subprocess.run([fv.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", concat],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fc = (
        "[0:v][1:v]overlay=0:0[a];"
        f"[2:v]fade=t=in:st={fact_at}:d=0.6:alpha=1[f];"
        f"[a][f]overlay=0:0:enable='gte(t,{fact_at})'[b];"
        "[b]drawbox=x=0:y=0:w=iw:h=12:color=0xFFC600@0.25:t=fill,"
        f"drawbox=x=0:y=0:w='iw*t/{dur}':h=12:color=0xFFC600:t=fill[v]"
    )
    subprocess.run([fv.FFMPEG, "-y", "-i", concat, "-loop", "1", "-i", main_png,
                    "-loop", "1", "-i", fact_png, "-filter_complex", fc, "-map", "[v]",
                    "-t", str(dur), "-r", "30", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "21", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", out_mp4],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for p in segs + [lst, concat]:
        try:
            os.remove(p)
        except OSError:
            pass
    return out_mp4
