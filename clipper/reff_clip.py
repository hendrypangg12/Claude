"""Proses 1 video cover lagu → 1 klip reff/chorus (9:16, brand + kredit sumber).

Beda dari clip_app.py (yang bikin banyak klip 'momen viral' dari 1 video panjang) —
di sini fokusnya 1 lagu → 1 potongan reff aja, dari video COVER (bukan konten talking).
"""
from pathlib import Path

from pick_reff import pick_reff
from render import make_overlay_png, render_clip
from transcribe import download, pick_handle, transcribe


def make_reff_clip(url: str, out_dir: Path, index: int, brand: str = "FAKTAVIRAL.IDN"):
    """Return dict metadata kalau sukses, atau None kalau video ini gak kedeteksi ada
    reff (skip, lanjut ke cover berikutnya — bukan error fatal)."""
    vdir = out_dir / f"_src-{index}"
    vdir.mkdir(parents=True, exist_ok=True)

    print(f"      [{index}] download: {url}")
    src, info = download(url, vdir)
    title = info.get("title") or ""
    creator = pick_handle(info)
    duration = info.get("duration")

    print(f"      [{index}] transcribe...")
    transcript = transcribe(src, language="id")

    print(f"      [{index}] cari reff...")
    reff = pick_reff(transcript, video_title=title)
    if not reff:
        print(f"      [{index}] gak kedeteksi ada reff — skip")
        return None

    out_mp4 = out_dir / f"clip-{index}.mp4"
    overlay = make_overlay_png(out_dir / f"overlay-{index}.png", brand=brand,
                               title="", credit=creator)
    render_clip(src, reff["start"], reff["end"], None, overlay, out_mp4)

    cred = f"@{creator}" if creator else ""
    caption = ((f"Cover: {cred}\n" if cred else "")
               + f"Sumber: {url}\n\n"
               + f"Follow buat potongan reff cover lainnya!\n\n"
               + "#cover #reff #musik #coversong")
    (out_dir / f"caption-{index}.txt").write_text(caption, encoding="utf-8")

    return {
        "file": out_mp4.name,
        "url": url,
        "source_title": title,
        "creator": creator,
        "duration": duration,
        "reff_start": reff["start"],
        "reff_end": reff["end"],
        "confidence": reff["confidence"],
        "caption": caption,
    }
