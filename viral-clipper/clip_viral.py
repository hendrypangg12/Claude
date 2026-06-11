#!/usr/bin/env python3
"""Download a public reel/short and stamp it with BERSTOCK.ID branding + source credit.

Usage:
    python clip_viral.py "<url>" [--brand BERSTOCK.ID] [--credit @handle] [--no-credit]

Produces:
    out/<timestamp>/source.mp4   original download
    out/<timestamp>/branded.mp4  branded, ready to post
    out/<timestamp>/meta.json    metadata

Needs ffmpeg + ffprobe on PATH (or set FFMPEG / FFPROBE env vars) and yt-dlp.

⚠️  RIGHTS: only re-post content you actually have the right to use. This tool adds a
"via @creator" credit by default, but credit is NOT permission. Reposting other
people's content can infringe copyright and violate Instagram's Terms — that risks
takedowns, strikes, or a permanent ban on your account. When in doubt, ask the
creator first, or transform the clip (commentary/insight) instead of reposting raw.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIB = timezone(timedelta(hours=7))
HERE = Path(__file__).resolve().parent
# Reuse the Poppins fonts already bundled with the news poster (same repo).
FONT_DIRS = [HERE / "fonts", HERE.parent / "daily-news-poster" / "fonts"]
SYS_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

GOLD = (255, 196, 0, 255)
INK = (15, 18, 26, 255)
WHITE = (245, 247, 251, 255)


def _bin(name: str, env: str) -> str:
    return os.environ.get(env) or shutil.which(name) or name


FFMPEG = _bin("ffmpeg", "FFMPEG")
FFPROBE = _bin("ffprobe", "FFPROBE")


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


def pick_handle(info: dict) -> str:
    """Best-effort @username for the credit (yt-dlp's uploader_id is often numeric)."""
    ch = info.get("channel")
    if ch and " " not in ch:
        return ch
    m = re.search(r"\bby\s+([A-Za-z0-9_.]+)", info.get("title") or "")
    if m:
        return m.group(1)
    uid = str(info.get("uploader_id") or "")
    if uid and not uid.isdigit():
        return uid
    return info.get("uploader") or ""


def download(url: str, out_dir: Path):
    import yt_dlp

    ff_dir = str(Path(FFMPEG).parent) if os.path.sep in FFMPEG else None
    opts = {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "noprogress": True,
    }
    if ff_dir:
        opts["ffmpeg_location"] = ff_dir
    # YouTube sering blokir IP server ("confirm you're not a bot"). Cookies dari browser login
    # naikin peluang lolos: set env YT_COOKIES (path file cookies.txt format Netscape).
    cookies = os.environ.get("YT_COOKIES", "").strip()
    if cookies and os.path.exists(cookies):
        opts["cookiefile"] = cookies
    # client android/web sering lebih lolos drpd default
    opts["extractor_args"] = {"youtube": {"player_client": ["android", "web"]}}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
    files = sorted(out_dir.glob("source.*"))
    vids = [f for f in files if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not vids:
        raise RuntimeError("Download produced no video file")
    return vids[0], info


def probe_size(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)]
    ).decode().strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def make_overlay(w: int, h: int, brand: str, credit: str | None, out_png: Path) -> Path:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = max(int(w * 0.045), 28)

    # brand chip, top-left
    bf = _font("Poppins-ExtraBold.ttf", max(int(w * 0.038), 30))
    tw = bf.getlength(brand)
    px, py = int(bf.size * 0.45), int(bf.size * 0.34)
    d.rounded_rectangle(
        [margin, margin, margin + tw + 2 * px, margin + bf.size + 2 * py],
        radius=int(bf.size * 0.32), fill=GOLD,
    )
    d.text((margin + px, margin + py - int(bf.size * 0.12)), brand, font=bf, fill=INK)

    # credit chip, lower-left (kept above the IG caption zone)
    if credit:
        cf = _font("Poppins-SemiBold.ttf", max(int(w * 0.030), 24))
        text = f"via {credit}"
        ctw = cf.getlength(text)
        cx, cy = margin, int(h * 0.84)
        cpx, cpy = int(cf.size * 0.5), int(cf.size * 0.34)
        d.rounded_rectangle(
            [cx, cy, cx + ctw + 2 * cpx, cy + cf.size + 2 * cpy],
            radius=int(cf.size * 0.45), fill=(0, 0, 0, 150),
        )
        d.text((cx + cpx, cy + cpy - int(cf.size * 0.12)), text, font=cf, fill=WHITE)

    img.save(out_png)
    return out_png


def brand_video(src: Path, overlay: Path, out_mp4: Path) -> Path:
    cmd = [
        FFMPEG, "-y", "-i", str(src), "-i", str(overlay),
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_mp4


def main() -> int:
    ap = argparse.ArgumentParser(description="Brand a downloaded reel/short for BERSTOCK.ID")
    ap.add_argument("url")
    ap.add_argument("--brand", default=os.environ.get("BRAND", "BERSTOCK.ID"))
    ap.add_argument("--credit", default=None, help="override the credit handle")
    ap.add_argument("--no-credit", action="store_true", help="omit the 'via @creator' credit")
    args = ap.parse_args()

    now = datetime.now(WIB)
    out_dir = Path("out") / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/3] Downloading...")
    src, info = download(args.url, out_dir)
    uploader = pick_handle(info)
    if args.credit:
        handle = args.credit if args.credit.startswith("@") else f"@{args.credit}"
    elif uploader:
        handle = uploader if str(uploader).startswith("@") else f"@{uploader}"
    else:
        handle = ""
    print(f"      source: {src.name} | by {handle or 'unknown'}")

    w, h = probe_size(src)
    print(f"[2/3] Branding ({w}x{h})...")
    overlay = make_overlay(w, h, args.brand, None if args.no_credit else (handle or None),
                           out_dir / "overlay.png")
    out_mp4 = brand_video(src, overlay, out_dir / "branded.mp4")

    meta = {
        "id": out_dir.name,
        "url": args.url,
        "uploader": uploader,
        "credit": None if args.no_credit else handle,
        "duration": info.get("duration"),
        "width": w,
        "height": h,
        "title": info.get("title"),
        "created": now.isoformat(),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[3/3] Done → {out_mp4}")
    print("\n  ⚠️  Pastikan kamu punya hak/izin untuk repost. Credit BUKAN pengganti izin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
