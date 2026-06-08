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


def image_to_clip(img_path: str, out_path: str, dur: int = 20) -> str:
    """Ubah 1 FOTO (mis. foto asli berita) jadi klip 1080x1920 dgn zoom pelan (Ken Burns).
    Dipakai biar reel BERITA nampilin foto kejadian asli, bukan stok generik. Raise kalau gagal."""
    frames = max(int(dur * 30), 30)
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0004,1.12)':d={frames}:s=1080x1920:fps=30,"
        "setsar=1,format=yuv420p"
    )
    subprocess.run(
        [FFMPEG, "-y", "-loop", "1", "-i", img_path, "-t", str(dur),
         "-vf", vf, "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", out_path],
        check=True, stdout=_DEVNULL, stderr=_DEVNULL,
    )
    return out_path


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


def make_reel_overlay(hook: str, category: str, fact: str, out_main: str, out_fact: str,
                      out_detail: str, detail: str = ""):
    """Tiga layer: `main` (chrome + kicker + hook + CTA, t=0), `fact` (fakta inti,
    fade-in awal), `detail` (penjelasan KENAPA — muncul belakangan = 'slide 2').
    Teks di-anchor agak ke ATAS (tengah-atas) biar eye-catching. Return 3 png."""
    main = Image.alpha_composite(Image.new("RGBA", (RW, RH), (0, 0, 0, 0)), _reel_scrim())
    dmain = ImageDraw.Draw(main, "RGBA")
    fact_layer = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    dfact = ImageDraw.Draw(fact_layer, "RGBA")
    detail_layer = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    ddet = ImageDraw.Draw(detail_layer, "RGBA")

    _brand_chip(dmain)

    kf = _font("extrabold", 38)
    hf = _font("extrabold", 60)
    ff = _font("semibold", 40)
    df = _font("medium", 34)
    max_w = RW - 2 * s(PAD)

    hook_lines = _wrap(hook, hf, max_w)
    fact_lines = []
    for raw in fact.split("\n"):
        fact_lines.extend(_wrap(raw, ff, max_w) if raw.strip() else [""])
    detail_lines = []
    for raw in (detail or "").split("\n"):
        detail_lines.extend(_wrap(raw, df, max_w) if raw.strip() else [""])
    hook_lh = int(hf.size * 1.07)
    fact_lh = int(ff.size * 1.24)
    detail_lh = int(df.size * 1.32)

    cat_h = _font("bold", 22).size + 2 * s(9)

    # ANCHOR di tengah-atas (≈ 30% dari atas) — bukan mepet bawah
    start_y = int(RH * 0.30)
    hook_block = len(hook_lines) * hook_lh
    fact_block = len(fact_lines) * fact_lh
    fact_top = start_y + cat_h + s(22) + kf.size + s(28) + hook_block + s(28)
    fact_end = fact_top + fact_block
    d_top = fact_end + s(28)
    detail_block = len(detail_lines) * detail_lh if detail_lines else 0
    content_end = (d_top + detail_block) if detail_lines else fact_end
    pad_p = s(36)
    PANEL = (10, 12, 24, 180)  # 1 kartu gelap semi-transparan → teks selalu kebaca

    # SATU panel utuh (incl. area penjelasan/slide-2) di main → no seam, selalu kebaca
    dmain.rounded_rectangle([s(PAD) - pad_p, start_y - pad_p,
                             RW - s(PAD) + pad_p, content_end + pad_p],
                            radius=s(30), fill=PANEL)

    label = NICHE_LABELS.get((category or "").lower(), (category or "FAKTA").upper())
    _category_pill(dmain, label, s(PAD), start_y)
    _tracked(dmain, (s(PAD), start_y + cat_h + s(22)), "TAU GAK SIH?", kf, WHITE, 1)

    y = start_y + cat_h + s(22) + kf.size + s(28)
    for ln in hook_lines:
        dmain.text((s(PAD), y), ln, font=hf, fill=WHITE)
        y += hook_lh
    y = fact_top
    for ln in fact_lines:        # fakta inti → fade-in awal
        dfact.text((s(PAD), y), ln, font=ff, fill=WHITE)
        y += fact_lh
    if detail_lines:             # penjelasan KENAPA → 'slide 2' (teks di detail layer)
        y = d_top
        for ln in detail_lines:
            ddet.text((s(PAD), y), ln, font=df, fill=(228, 232, 247))
            y += detail_lh

    # CTA bawah (selalu tampil)
    cf = _font("bold", 32)
    subf = _font("medium", 26)
    sub_y = RH - s(PAD) - subf.size - s(170)  # diangkat — hindari ketutup UI Reels IG
    px_, py_ = s(26), s(16)
    pill_h = cf.size + 2 * py_
    pill_y = sub_y - s(22) - pill_h
    ct = f"Follow @{HANDLE}"
    ctw = cf.getlength(ct)
    dmain.rounded_rectangle([s(PAD), pill_y, s(PAD) + ctw + 2 * px_, pill_y + pill_h],
                            radius=s(14), fill=CYAN)
    dmain.text((s(PAD) + px_, pill_y + py_ - s(4)), ct, font=cf, fill=CYAN_INK)
    dmain.text((s(PAD), sub_y), "1 fakta unik tiap hari", font=subf, fill=MUTED)

    main.resize((VW, VH), Image.LANCZOS).save(out_main)
    fact_layer.resize((VW, VH), Image.LANCZOS).save(out_fact)
    detail_layer.resize((VW, VH), Image.LANCZOS).save(out_detail)
    return out_main, out_fact, out_detail


def _duration(path: str) -> float:
    try:
        out = subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path]
        ).decode().strip()
        return float(out)
    except Exception:
        return 0.0


def _segment(src: str, dst: str, seconds: int) -> str:
    """Make a segment of EXACTLY `seconds` (loop if clip shorter, trim if longer)."""
    cmd = [
        FFMPEG, "-y", "-stream_loop", "-1", "-i", src, "-t", str(seconds),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
               "crop=1080:1920,setsar=1,fps=30",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", dst,
    ]
    subprocess.run(cmd, check=True, stdout=_DEVNULL, stderr=_DEVNULL)
    return dst


def render_reel(bg_videos, main_png: str, fact_png: str, out_mp4: str,
                seg: int = 15, max_segments: int = 3, fact_at: float = 2.5,
                detail_png: str | None = None, detail_at: float | None = None,
                music: str | None = None, music_vol: float = 0.55) -> str:
    """Reel dari klip BEDA tiap `seg` detik + progress bar + teks bertahap.

    Hook tampil dari awal; fakta inti fade-in di `fact_at`; penjelasan (detail_png)
    muncul belakangan di `detail_at` (default = awal klip ke-2 = 'slide 2').

    `music` (opsional): path lagu royalty-free → di-loop/trim ke durasi reel, di-fade-out
    di akhir, volume diturunin (`music_vol`). Kalau None → reel tetap senyap (-an)."""
    if isinstance(bg_videos, str):
        bg_videos = [bg_videos]
    workdir = os.path.dirname(out_mp4) or "."

    clips = bg_videos[:max_segments]
    segs: list[str] = []
    if len(clips) <= 1:
        try:
            segs.append(_segment(clips[0], os.path.join(workdir, "_seg_0.mp4"), 2 * seg))
        except Exception as exc:
            raise RuntimeError(f"No usable background video: {exc}")
    else:
        for i, src in enumerate(clips):
            dst = os.path.join(workdir, f"_seg_{i}.mp4")
            try:
                _segment(src, dst, seg)
                segs.append(dst)
            except Exception:
                continue
    if not segs:
        raise RuntimeError("No usable background video")

    dur = 2 * seg if len(clips) <= 1 else len(segs) * seg

    list_file = os.path.join(workdir, "_concat.txt")
    with open(list_file, "w") as f:
        for p in segs:
            f.write(f"file '{os.path.abspath(p)}'\n")
    concat = os.path.join(workdir, "_bg.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                    "-c", "copy", concat], check=True, stdout=_DEVNULL, stderr=_DEVNULL)

    has_detail = bool(detail_png)
    if detail_at is None:
        detail_at = seg if len(segs) > 1 else dur * 0.55  # default = mulai klip ke-2
    # main (t=0) → fact fade-in (fact_at) → detail 'slide 2' (detail_at) → progress bar
    fc = (
        "[0:v][1:v]overlay=0:0[a];"
        f"[2:v]fade=t=in:st={fact_at}:d=0.6:alpha=1[f];"
        f"[a][f]overlay=0:0:enable='gte(t,{fact_at})'[b];"
    )
    if has_detail:
        fc += (
            f"[3:v]fade=t=in:st={detail_at}:d=0.6:alpha=1[g];"
            f"[b][g]overlay=0:0:enable='gte(t,{detail_at})'[c];"
        )
        prog_src = "[c]"
    else:
        prog_src = "[b]"
    fc += (
        f"{prog_src}drawbox=x=0:y=0:w=iw:h=12:color=0x60E0FF@0.22:t=fill,"
        f"drawbox=x=0:y=0:w='iw*t/{dur}':h=12:color=0x60E0FF:t=fill[v]"
    )
    cmd = [FFMPEG, "-y", "-i", concat, "-loop", "1", "-i", main_png, "-loop", "1", "-i", fact_png]
    if has_detail:
        cmd += ["-loop", "1", "-i", detail_png]

    use_music = bool(music) and os.path.isfile(music or "")
    if use_music:
        music_idx = 4 if has_detail else 3  # 0=bg,1=main,2=fact,(3=detail) → musik nyusul
        # loop lagu (kalau lebih pendek dari reel), turunin volume, fade-out 2s di akhir
        fade_st = max(0.0, dur - 2.0)
        fc += (
            f";[{music_idx}:a]volume={music_vol},"
            f"afade=t=out:st={fade_st}:d=2,atrim=0:{dur},asetpts=PTS-STARTPTS[aud]"
        )
        cmd += ["-stream_loop", "-1", "-i", music]

    cmd += ["-filter_complex", fc, "-map", "[v]"]
    cmd += (["-map", "[aud]", "-c:a", "aac", "-b:a", "128k"] if use_music else ["-an"])
    cmd += [
        "-t", str(dur), "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
        "-maxrate", "6M", "-bufsize", "12M",
        "-movflags", "+faststart", out_mp4,
    ]
    subprocess.run(cmd, check=True, stdout=_DEVNULL, stderr=_DEVNULL)

    for p in segs + [list_file, concat]:
        try:
            os.remove(p)
        except OSError:
            pass
    return out_mp4
