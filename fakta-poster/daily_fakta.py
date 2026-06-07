"""Daily 'fakta unik' → Instagram carousel pipeline (original content, no copyright).

Usage:  python daily_fakta.py
Reads ANTHROPIC_API_KEY from .env / environment. Optional env:
  CATEGORY   one of sains|sejarah|tubuh|hewan|luarangkasa|teknologi (else Claude picks)
  DRY_RUN    "true" (default) — just generate files, no upload
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from fakta_generator import generate_fakta
from fakta_image_maker import compose_cover, compose_fact, compose_outro

WIB = timezone(timedelta(hours=7))
HISTORY = Path("history.json")  # persisted hooks for cross-run dedup (out/ is gitignored)
MUSIC_DIR = Path("music")       # lagu royalty-free (taruh sendiri) → di-acak per reel


def _pick_music() -> str | None:
    """Acak 1 lagu dari music/ (mp3/m4a/wav). None kalau folder kosong → reel senyap."""
    if not MUSIC_DIR.is_dir():
        return None
    tracks = [p for p in MUSIC_DIR.iterdir()
              if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg")]
    return str(random.choice(tracks)) if tracks else None


def _music_credit(path: str) -> str:
    """Baris kredit CC-BY buat track Kevin MacLeod (wajib di caption reel)."""
    title = Path(path).stem.replace("-", " ").replace("_", " ").title()
    return f"🎵 Musik: \"{title}\" — Kevin MacLeod (incompetech.com) · Lisensi CC BY 4.0"


def _load_history() -> list[str]:
    if HISTORY.exists():
        try:
            return [str(h) for h in json.loads(HISTORY.read_text(encoding="utf-8")) if h]
        except Exception:
            return []
    return []


def _save_history(hooks: list[str]) -> None:
    HISTORY.write_text(json.dumps(hooks[-200:], ensure_ascii=False, indent=2), encoding="utf-8")


def _recent_hooks(out_root: Path, limit: int = 40) -> list[str]:
    """Recent hooks so Claude doesn't repeat itself (history.json + out/ + published/)."""
    hooks: list[str] = list(_load_history())
    # committed published metas = persistent cross-run dedup (survives CI fresh checkout)
    for root in (Path("published"), out_root):
        if not root.exists():
            continue
        for d in sorted(root.iterdir(), reverse=True):
            meta = d / "meta.json"
            if not meta.is_file():
                continue
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                hooks.append(m.get("hook") or m.get("fact") or "")
            except Exception:
                continue
    # de-dup, keep order, drop empties
    seen, out = set(), []
    for h in hooks:
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out[:60]


def main() -> int:
    load_dotenv()
    now = datetime.now(WIB)
    out_root = Path("out")
    out_dir = out_root / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    category = os.environ.get("CATEGORY", "").strip().lower() or None
    topic = os.environ.get("TOPIC", "").strip() or None

    print("[1/3] Generating fakta with Claude...")
    fakta = generate_fakta(category=category, avoid=_recent_hooks(out_root), topic=topic)
    print(f"      → [{fakta['category']}] {fakta['hook']}")
    _save_history(_load_history() + [fakta["hook"]])

    # Optional topic media from Pexels (free, legal). Falls back to cosmic bg.
    photos: list[str] = []
    video_paths: list[str] = []
    query = fakta.get("query") or fakta["category"]
    if os.environ.get("PEXELS_API_KEY"):
        from media_fetcher import fetch_photos, fetch_videos
        try:
            photos = fetch_photos(query, str(out_dir), count=3)
            print(f"      photo bg: {len(photos)} foto ({query})")
        except Exception as exc:
            print(f"      (photo fetch gagal: {exc}) → pakai kosmik")
        try:
            video_paths = fetch_videos(query, str(out_dir))
            print(f"      video bg: {len(video_paths)} klip ({query})")
        except Exception as exc:
            print(f"      (video fetch gagal: {exc}) → skip reel")
    else:
        print("      (PEXELS_API_KEY belum di-set → background kosmik, no reel)")

    # 1 foto per slide (kalau kurang, pakai foto yang ada / fallback kosmik)
    p1 = photos[0] if len(photos) > 0 else None
    p2 = photos[1] if len(photos) > 1 else p1
    p3 = photos[2] if len(photos) > 2 else p1

    print("[2/3] Composing carousel...")
    compose_cover(fakta["hook"], fakta["category"], str(out_dir / "post_1.jpg"), bg_path=p1)
    compose_fact(fakta["fact"], fakta["detail"], str(out_dir / "post_2.jpg"), bg_path=p2)
    compose_outro(fakta["takeaway"], str(out_dir / "post_3.jpg"), bg_path=p3)
    (out_dir / "caption.txt").write_text(fakta["caption"], encoding="utf-8")

    if video_paths:
        print("      Composing reel...")
        try:
            from fakta_video_maker import make_reel_overlay, render_reel
            main_ov, fact_ov, detail_ov = make_reel_overlay(
                fakta["hook"], fakta["category"], fakta["fact"],
                str(out_dir / "reel_main.png"), str(out_dir / "reel_fact.png"),
                str(out_dir / "reel_detail.png"), detail=fakta.get("detail", ""),
            )
            music = _pick_music()
            render_reel(video_paths, main_ov, fact_ov, str(out_dir / "reel.mp4"),
                        seg=10, max_segments=2, fact_at=1.5,
                        detail_png=detail_ov, detail_at=10, music=music)
            if music:
                # caption khusus reel = caption + kredit musik (carousel pakai caption.txt biasa)
                (out_dir / "caption_reel.txt").write_text(
                    fakta["caption"] + "\n\n" + _music_credit(music), encoding="utf-8")
            tag = f", musik: {Path(music).name}" if music else ", senyap (folder music/ kosong)"
            print(f"      → reel.mp4 (20s, slide-2 di detik 10{tag})")
        except Exception as exc:
            print(f"      (reel gagal: {exc})")

    meta = {
        "id": out_dir.name,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "category": fakta["category"],
        "hook": fakta["hook"],
        "fact": fakta["fact"],
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[3/3] Done → {out_dir}")
    print("      Slides: post_1.jpg (cover) · post_2.jpg (fakta) · post_3.jpg (outro)")
    print("      Caption: caption.txt")
    if os.environ.get("DRY_RUN", "true").lower() != "true":
        print("      (Upload IG belum diaktifkan — post manual atau wire ke instagram_uploader.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
