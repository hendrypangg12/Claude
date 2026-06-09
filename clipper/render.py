"""Render a single 9:16 clip: cut the segment, reframe to 1080x1920 (fill + center
crop, works for any source aspect), burn in the karaoke captions, and stamp a brand
chip. Uses ffmpeg (path from FFMPEG env or PATH)."""
import os
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Poppins can't render colour emoji → strip them from burned text (keep in caption).
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U00002190-\U000021FF️‍]")


def _clean(s: str) -> str:
    return _EMOJI.sub("", s or "").strip()

HERE = Path(__file__).resolve().parent
FONT_DIRS = [HERE / "fonts", HERE.parent / "daily-news-poster" / "fonts"]
SYS_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

GOLD = (255, 196, 0, 255)
CYAN = (34, 211, 238, 255)        # faktaviral accent
INK = (8, 18, 26, 255)
WHITE = (245, 247, 251, 255)

W, H = 1080, 1920


def _bin(name: str, env: str) -> str:
    return os.environ.get(env) or shutil.which(name) or name


FFMPEG = _bin("ffmpeg", "FFMPEG")


def _font(file: str, size: int) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        p = d / file
        if p.exists():
            return ImageFont.truetype(str(p), size)
    for p in SYS_FONTS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_tokens(d: ImageDraw.ImageDraw, text: str, font, max_w: float):
    """Greedy word-wrap → list of token-lists that each fit within max_w."""
    space = d.textlength(" ", font=font)

    def width(toks):
        return (sum(d.textlength(t, font=font) for t in toks)
                + space * (len(toks) - 1)) if toks else 0

    lines, cur = [], []
    for w in (text or "").split():
        if not cur or width(cur + [w]) <= max_w:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
    if cur:
        lines.append(cur)
    return lines, space


def make_overlay_png(out_png: Path, brand: str = "FAKTAVIRAL.IDN",
                     title: str = "", credit: str | None = None) -> Path:
    """Per-clip overlay: brand chip (top) + burned-in HOOK title card (the @creator
    headline) + 'via @creator' credit. @handles are highlighted cyan."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # brand chip (cyan), small, very top
    bf = _font("Poppins-ExtraBold.ttf", 40)
    bw = bf.getlength(brand)
    bpx, bpy = 24, 13
    bx, by = (W - (bw + 2 * bpx)) / 2, int(H * 0.12)   # turun dari tepi atas (lolos UI TikTok/IG)
    d.rounded_rectangle([bx, by, bx + bw + 2 * bpx, by + bf.size + 2 * bpy],
                        radius=26, fill=CYAN)
    d.text((bx + bpx, by + bpy - 5), brand, font=bf, fill=INK)

    # HOOK title — CapCut style: black bold UPPERCASE on white boxes, lower-middle.
    if _clean(title):
        ttl = _clean(title).upper()
        max_w = 840
        for size in (62, 58, 54, 50, 46, 42):
            tf = _font("Poppins-ExtraBold.ttf", size)
            lines, _ = _wrap_tokens(d, ttl, tf, max_w)
            if len(lines) <= 4:
                break
        bpx2, bpy2 = 22, 10
        gap = int(tf.size * 0.16)
        row_h = tf.size + 2 * bpy2
        block_h = len(lines) * row_h + (len(lines) - 1) * gap
        y = int(H * 0.60) - block_h // 2          # center block around 60% height

        # small teal quote accent, top-left of the block
        qf = _font("Poppins-ExtraBold.ttf", 48)
        qx = (W - max_w) / 2 - 6
        d.rounded_rectangle([qx, y - 58, qx + 60, y - 6], radius=12, fill=CYAN)
        d.text((qx + 14, y - 78), "”", font=qf, fill=INK)

        for toks in lines:
            text = " ".join(toks)
            tw = d.textlength(text, font=tf)
            bx0, bx1 = (W - tw) / 2 - bpx2, (W + tw) / 2 + bpx2
            d.rounded_rectangle([bx0, y, bx1, y + row_h], radius=14,
                                fill=(255, 255, 255, 236))
            d.text(((W - tw) / 2, y + bpy2 - 4), text, font=tf, fill=(15, 18, 26, 255))
            y += row_h + gap

    # creator credit chip, lower-left (above the Reels caption zone)
    if credit:
        handle = credit if str(credit).startswith("@") else f"@{credit}"
        cf = _font("Poppins-SemiBold.ttf", 32)
        text = f"via {handle}"
        ctw = cf.getlength(text)
        cx, cy = 70, int(H * 0.75)
        cpx, cpy = 18, 12
        d.rounded_rectangle([cx, cy, cx + ctw + 2 * cpx, cy + cf.size + 2 * cpy],
                            radius=24, fill=(0, 0, 0, 150))
        d.text((cx + cpx, cy + cpy - 4), text, font=cf, fill=WHITE)

    img.save(out_png)
    return out_png


# backward-compat alias
def make_brand_png(out_png: Path, brand: str = "FAKTAVIRAL.IDN",
                   credit: str | None = None) -> Path:
    return make_overlay_png(out_png, brand=brand, title="", credit=credit)


def build_pan_script(face: dict, out_path: Path) -> tuple[Path, int] | None:
    """Turn a face track into a sendcmd script that pans crop x to keep the face
    centered. Returns (script_path, init_x) or None when there's no room to pan
    (portrait/near-vertical source) or no track."""
    track = (face or {}).get("track") or []
    sw, sh = (face or {}).get("src_w", 0), (face or {}).get("src_h", 0)
    if not track or sw <= 0 or sh <= 0:
        return None
    scale_factor = max(W / sw, H / sh)
    scaled_w = sw * scale_factor
    max_x = scaled_w - W
    if max_x < 4:                       # already ~9:16 wide → nothing to pan
        return None

    def _x(frac: float) -> int:
        return int(max(0.0, min(max_x, frac * scaled_w - W / 2.0)))

    lines = [f"{t:.2f} crop x {_x(frac)};" for t, frac in track]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, _x(track[0][1])


def make_tag_overlay(out_png: Path, w: int, h: int, brand: str = "FAKTAVIRAL.IDN",
                     credit: str | None = None) -> Path:
    """Brand watermark sized to the SOURCE video (for 'download utuh' mode — keeps
    original aspect, just stamps FAKTAVIRAL.IDN top + 'via @creator' bottom)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = max(0.4, w / 1080.0)
    bf = _font("Poppins-ExtraBold.ttf", max(20, int(40 * s)))
    bw = bf.getlength(brand)
    px, py = int(24 * s), int(13 * s)
    bx, by = (w - (bw + 2 * px)) / 2, int(h * 0.12)   # turun dari tepi atas (lolos UI TikTok/IG)
    d.rounded_rectangle([bx, by, bx + bw + 2 * px, by + bf.size + 2 * py],
                        radius=int(26 * s), fill=CYAN)
    d.text((bx + px, by + py - int(5 * s)), brand, font=bf, fill=INK)
    if credit:
        handle = credit if str(credit).startswith("@") else f"@{credit}"
        cf = _font("Poppins-SemiBold.ttf", max(16, int(30 * s)))
        text = f"via {handle}"
        ctw = cf.getlength(text)
        cpx, cpy = int(16 * s), int(11 * s)
        cx, cy = int(40 * s), int(h * 0.80)   # angkat dari dasar (lolos username TikTok/IG)
        d.rounded_rectangle([cx, cy, cx + ctw + 2 * cpx, cy + cf.size + 2 * cpy],
                            radius=int(22 * s), fill=(0, 0, 0, 150))
        d.text((cx + cpx, cy + cpy - int(4 * s)), text, font=cf, fill=WHITE)
    img.save(out_png)
    return out_png


def make_hook_overlay(out_png: Path, w: int, h: int, title: str) -> Path:
    """CapCut white-box HOOK title sized to the source video — shown only for the
    first few seconds (grab attention). Black bold UPPERCASE on white boxes."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if not _clean(title):
        img.save(out_png)
        return out_png
    d = ImageDraw.Draw(img)
    s = max(0.4, w / 1080.0)
    ttl = _clean(title).upper()
    max_w = int(w * 0.84)
    for size in (int(64 * s), int(58 * s), int(52 * s), int(46 * s), int(40 * s)):
        tf = _font("Poppins-ExtraBold.ttf", max(20, size))
        lines, _ = _wrap_tokens(d, ttl, tf, max_w)
        if len(lines) <= 4:
            break
    bpx, bpy = int(22 * s), int(10 * s)
    gap = int(tf.size * 0.16)
    row_h = tf.size + 2 * bpy
    block_h = len(lines) * row_h + (len(lines) - 1) * gap
    y = int(h * 0.34) - block_h // 2
    qf = _font("Poppins-ExtraBold.ttf", int(48 * s))
    qx = (w - max_w) / 2 - 6
    d.rounded_rectangle([qx, y - int(58 * s), qx + int(60 * s), y - int(6 * s)],
                        radius=int(12 * s), fill=CYAN)
    d.text((qx + int(14 * s), y - int(78 * s)), "”", font=qf, fill=INK)
    for toks in lines:
        text = " ".join(toks)
        tw = d.textlength(text, font=tf)
        d.rounded_rectangle([(w - tw) / 2 - bpx, y, (w + tw) / 2 + bpx, y + row_h],
                            radius=int(14 * s), fill=(255, 255, 255, 236))
        d.text(((w - tw) / 2, y + bpy - int(4 * s)), text, font=tf, fill=(15, 18, 26, 255))
        y += row_h + gap
    img.save(out_png)
    return out_png


def render_full(source: Path, overlay_png: Path, out_mp4: Path,
                hook_png: Path | None = None, hook_dur: float = 3.0) -> Path:
    """'Download utuh' mode: keep the original video (no reframe/cut), burn the brand
    watermark, and optionally a HOOK title card for the first `hook_dur` seconds."""
    inputs = ["-i", str(source), "-i", str(overlay_png)]
    chain = "[0:v][1:v]overlay=0:0:format=auto[ov]"
    cur = "[ov]"
    if hook_png:
        inputs += ["-i", str(hook_png)]
        chain += f";{cur}[2:v]overlay=0:0:format=auto:enable='lte(t,{hook_dur})'[o]"
        cur = "[o]"
    cmd = [FFMPEG, "-y"] + inputs + ["-filter_complex", chain, "-map", cur, "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_mp4)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_mp4


def build_zoom_expr(emphasis: list[float] | None, fps: int,
                    amp: float = 0.16, half: float = 0.55) -> str | None:
    """ffmpeg zoompan z-expression: 1.0 baseline, smooth punch to 1+amp around each
    emphasis second. Commas escaped (\\,) for the filtergraph parser."""
    es = [e for e in (emphasis or []) if e is not None and e >= 0]
    if not es:
        return None
    t = f"(on/{fps})"
    terms = [f"(1-abs({t}-{e:.2f})/{half})" for e in es]
    inner = terms[0]
    for tm in terms[1:]:
        inner = f"max({inner}\\,{tm})"
    return f"1+{amp}*max(0\\,{inner})"


def make_progress_png(out_png: Path, color=CYAN) -> Path:
    """A full-width bar (slid in via overlay-x to read as a progress fill)."""
    bar = Image.new("RGBA", (W, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(bar)
    d.rounded_rectangle([0, 2, W - 1, 14], radius=6, fill=color)
    bar.save(out_png)
    return out_png


def make_endcard_png(out_png: Path, brand: str = "FAKTAVIRAL.IDN",
                     handle: str = "@faktaviral.idn") -> Path:
    """Full-screen branded outro shown for the last ~2s of the clip."""
    img = Image.new("RGBA", (W, H), (13, 11, 28, 255))     # cosmic deep
    d = ImageDraw.Draw(img)
    bf = _font("Poppins-ExtraBold.ttf", 92)
    bw = bf.getlength(brand)
    d.text(((W - bw) / 2, H * 0.40), brand, font=bf, fill=CYAN)
    sf = _font("Poppins-ExtraBold.ttf", 54)
    sub = "FOLLOW"
    d.text(((W - sf.getlength(sub)) / 2, H * 0.40 - 90), sub, font=sf, fill=WHITE)
    hf = _font("Poppins-SemiBold.ttf", 46)
    hw = hf.getlength(handle)
    hy = H * 0.40 + 130
    d.rounded_rectangle([(W - hw) / 2 - 30, hy, (W + hw) / 2 + 30, hy + hf.size + 28],
                        radius=30, fill=CYAN)
    d.text(((W - hw) / 2, hy + 12), handle, font=hf, fill=INK)
    tf = _font("Poppins-SemiBold.ttf", 40)
    tip = "buat momen viral tiap hari"
    d.text(((W - tf.getlength(tip)) / 2, hy + 120), tip, font=tf, fill=(160, 170, 200, 255))
    img.save(out_png)
    return out_png


def render_clip(source: Path, start: float, end: float, ass_path: Path | None,
                brand_png: Path, out_mp4: Path, *, face: dict | None = None,
                emphasis: list[float] | None = None, fps: int = 30,
                select_expr: str | None = None, out_dur: float | None = None,
                music: Path | None = None, sfx: Path | None = None,
                sfx_times: list[float] | None = None,
                progress_png: Path | None = None,
                endcard_png: Path | None = None) -> Path:
    dur = max(0.5, end - start)
    odur = float(out_dur or dur)        # effective output length (compressed if tightened)
    fonts_dir = next((str(d) for d in FONT_DIRS if d.exists()), str(FONT_DIRS[0]))
    pan = build_pan_script(face, out_mp4.with_suffix(".pan.txt")) if face else None
    if pan:
        script, init_x = pan
        crop = f"sendcmd=f='{script}',crop={W}:{H}:x={init_x}:y=0"
    else:
        crop = f"crop={W}:{H}"

    # ---- video chain ----
    pre = f"select='{select_expr}',setpts=N/FRAME_RATE/TB," if select_expr else ""
    parts = [f"[0:v]{pre}scale={W}:{H}:force_original_aspect_ratio=increase,setsar=1,{crop}[c]"]
    cur = "[c]"
    zexpr = build_zoom_expr(emphasis, fps)
    if zexpr:
        parts.append(f"{cur}zoompan=z='{zexpr}':d=1:x='iw/2-(iw/zoom/2)':"
                     f"y='ih*0.45-(ih/zoom/2)':s={W}x{H}:fps={fps}[zm]")
        cur = "[zm]"
    if ass_path:
        parts.append(f"{cur}subtitles='{ass_path}':fontsdir='{fonts_dir}'[sv]")
        cur = "[sv]"

    inputs = ["-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(source), "-i", str(brand_png)]
    idx = 2
    parts.append(f"{cur}[1:v]overlay=0:0:format=auto[o1]")
    cur = "[o1]"
    n = 1
    if progress_png:
        inputs += ["-i", str(progress_png)]
        parts.append(f"{cur}[{idx}:v]overlay=x='-{W}+{W}*t/{odur:.3f}':y={H - 18}[o{n + 1}]")
        cur = f"[o{n + 1}]"; idx += 1; n += 1
    if endcard_png:
        inputs += ["-i", str(endcard_png)]
        st = max(0.0, odur - 2.0)
        parts.append(f"{cur}[{idx}:v]overlay=0:0:enable='between(t,{st:.2f},{odur:.2f})'[o{n + 1}]")
        cur = f"[o{n + 1}]"; idx += 1; n += 1
    vlabel = cur

    # ---- audio chain ----
    if select_expr or music or (sfx and sfx_times):
        a = [f"[0:a]aselect='{select_expr}',asetpts=N/SR/TB[a0]"] if select_expr \
            else ["[0:a]anull[a0]"]
        mix = ["[a0]"]
        if music:
            inputs += ["-i", str(music)]
            fst = max(0.1, odur - 1.5)
            a.append(f"[{idx}:a]atrim=0:{odur:.2f},volume=0.13,"
                     f"afade=t=out:st={fst:.2f}:d=1.5[am]")
            mix.append("[am]"); idx += 1
        if sfx and sfx_times:
            inputs += ["-i", str(sfx)]
            ns = len(sfx_times)
            a.append(f"[{idx}:a]asplit={ns}" + "".join(f"[s{i}]" for i in range(ns)))
            for i, tt in enumerate(sfx_times):
                ms = int(max(0.0, tt) * 1000)
                a.append(f"[s{i}]adelay={ms}|{ms}[sd{i}]"); mix.append(f"[sd{i}]")
            idx += 1
        a.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0,"
                 f"volume=1.4[a]")
        parts += a
        amap = ["-map", "[a]"]
    else:
        amap = ["-map", "0:a?"]

    cmd = [FFMPEG, "-y"] + inputs + ["-filter_complex", ";".join(parts),
           "-map", vlabel] + amap + [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        "-t", f"{odur:.2f}", str(out_mp4)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_mp4
