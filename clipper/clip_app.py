#!/usr/bin/env python3
"""AI Video Clipper — kasih 1 link, sistem auto-download, transcribe, pilih momen
paling viral pakai Claude, lalu potong jadi clip 9:16 + caption kata-per-kata.

Usage:
    python clip_app.py "<url>" [--num 4] [--lang id] [--brand BERSTOCK.ID]

Env:
    ANTHROPIC_API_KEY  (wajib)   WHISPER_MODEL=small   FFMPEG=/path/ffmpeg

Output → out/<timestamp>/:
    source.mp4, transcript.json, meta.json,
    clip-1.mp4 ... clip-N.mp4, caption-1.txt ... caption-N.txt
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from captions import build_ass
import random

from edit import plan_edit
from face_track import track_face, video_fps
from pick_clips import pick_clips
from render import make_endcard_png, make_overlay_png, make_progress_png, render_clip
from transcribe import download, pick_handle, transcribe

WIB = timezone(timedelta(hours=7))
HERE = Path(__file__).resolve().parent
MUSIC_DIR = HERE.parent / "fakta-poster" / "music"
SFX_WHOOSH = HERE / "sfx" / "whoosh.wav"


def main() -> int:
    ap = argparse.ArgumentParser(description="AI viral video clipper (9:16 + auto caption)")
    ap.add_argument("url", nargs="?", default=os.environ.get("VIDEO_URL", ""))
    ap.add_argument("--num", type=int, default=int(os.environ.get("NUM_CLIPS", "4")))
    ap.add_argument("--lang", default=os.environ.get("LANG_CODE", "id"))
    ap.add_argument("--brand", default=os.environ.get("BRAND", "FAKTAVIRAL.IDN"))
    ap.add_argument("--no-track", action="store_true",
                    help="matikan face-tracking (pakai center-crop statis)")
    ap.add_argument("--no-caption", action="store_true",
                    help="matikan caption karaoke (kalau video ori udah ada teks)")
    ap.add_argument("--no-zoom", action="store_true",
                    help="matikan zoom punch-in ke wajah di momen penegasan")
    ap.add_argument("--no-music", action="store_true", help="matikan musik latar + SFX whoosh")
    ap.add_argument("--no-tighten", action="store_true", help="matikan buang silence + filler")
    ap.add_argument("--no-polish", action="store_true", help="matikan end card + progress bar")
    args = ap.parse_args()
    track_on = not args.no_track and os.environ.get("FACE_TRACK", "1") != "0"
    cap_on = not args.no_caption and os.environ.get("CAPTIONS", "1") != "0"
    zoom_on = not args.no_zoom and os.environ.get("ZOOM", "1") != "0"
    music_on = not args.no_music and os.environ.get("MUSIC", "1") != "0"
    tighten_on = not args.no_tighten and os.environ.get("TIGHTEN", "1") != "0"
    polish_on = not args.no_polish and os.environ.get("POLISH", "1") != "0"

    if not args.url:
        print("ERROR: kasih link video. Contoh: python clip_app.py \"https://...\"")
        return 2

    now = datetime.now(WIB)
    out_dir = Path("out") / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Download: {args.url}")
    src, info = download(args.url, out_dir)
    title = info.get("title") or ""
    creator = pick_handle(info)
    print(f"      {src.name} | {title[:60]} | by {creator or '?'} | {info.get('duration')}s")

    print(f"[2/4] Transcribe (lang={args.lang}, model={os.environ.get('WHISPER_MODEL', 'small')})...")
    transcript = transcribe(src, language=args.lang)
    (out_dir / "transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      {len(transcript['words'])} kata, {len(transcript['segments'])} segmen")

    print(f"[3/4] Pilih {args.num} momen viral pakai Claude...")
    clips = pick_clips(transcript, num_clips=args.num, video_title=title, creator=creator)
    print(f"      dapet {len(clips)} momen")

    print("[4/4] Render: reframe + zoom + caption + tighten + musik + polish...")
    fps = video_fps(src)
    handle = "@" + args.brand.lower().replace(" ", "")
    progress_png = make_progress_png(out_dir / "bar.png") if polish_on else None
    endcard_png = (make_endcard_png(out_dir / "endcard.png", brand=args.brand, handle=handle)
                   if polish_on else None)
    tracks = sorted(MUSIC_DIR.glob("*.mp3")) if music_on else []
    sfx = SFX_WHOOSH if (music_on and SFX_WHOOSH.exists()) else None

    rendered = []
    for i, c in enumerate(clips, 1):
        out_mp4 = out_dir / f"clip-{i}.mp4"
        overlay = make_overlay_png(out_dir / f"overlay-{i}.png", brand=args.brand,
                                   title=c["title"], credit=creator)
        # words relative to this clip
        cw = [{"start": w["start"] - c["start"], "end": w["end"] - c["start"], "word": w["word"]}
              for w in transcript["words"]
              if w["start"] >= c["start"] - 0.05 and w["end"] <= c["end"] + 0.4]
        plan = plan_edit(cw, c["end"] - c["start"]) if tighten_on else None
        remap = plan["remap"] if plan else (lambda x: x)
        out_dur = plan["new_dur"] if plan else (c["end"] - c["start"])
        select_expr = plan["select"] if plan else None
        ass_words = ([{"start": remap(w["start"]), "end": remap(w["end"]), "word": w["word"]}
                      for w in cw] if plan else cw)
        ass = (build_ass(ass_words, 0.0, out_dur, out_dir / f"clip-{i}.ass")
               if cap_on else None)
        emph = ([round(remap(e - c["start"]), 2) for e in c.get("emphasis", [])]
                if (zoom_on or music_on) else [])
        face = track_face(src, c["start"], c["end"]) if track_on else None
        music = random.choice(tracks) if tracks else None
        try:
            render_clip(src, c["start"], c["end"], ass, overlay, out_mp4,
                        face=face, emphasis=(emph if zoom_on else None), fps=fps,
                        select_expr=select_expr, out_dur=out_dur,
                        music=music, sfx=sfx, sfx_times=(emph if (sfx and emph) else None),
                        progress_png=progress_png, endcard_png=endcard_png)
        except Exception as e:  # noqa: BLE001 — satu clip gagal jangan stop sisanya
            print(f"      clip-{i} gagal render: {e}")
            continue
        cap = c["caption"] or c["title"]
        if music:                        # CC-BY attribution wajib dicantumkan
            cap += f"\n\n🎵 {music.stem} – Kevin MacLeod (incompetech.com) CC BY 4.0"
        (out_dir / f"caption-{i}.txt").write_text(cap, encoding="utf-8")
        c["file"] = out_mp4.name
        rendered.append(c)
        print(f"      ✓ clip-{i} [{c['start']:.0f}-{c['end']:.0f}s] score {c['score']} — {c['title'][:48]}")

    meta = {
        "id": out_dir.name,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "url": args.url,
        "title": title,
        "creator": creator,
        "language": transcript.get("language"),
        "duration": transcript.get("duration"),
        "brand": args.brand,
        "clips": rendered,
        "created": now.isoformat(),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nDONE → {out_dir}  ({len(rendered)} clip siap posting)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
