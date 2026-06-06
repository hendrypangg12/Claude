"""Daily 'fakta unik' → Instagram carousel pipeline (original content, no copyright).

Usage:  python daily_fakta.py
Reads ANTHROPIC_API_KEY from .env / environment. Optional env:
  CATEGORY   one of sains|sejarah|tubuh|hewan|luarangkasa|teknologi (else Claude picks)
  DRY_RUN    "true" (default) — just generate files, no upload
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from fakta_generator import generate_fakta
from fakta_image_maker import compose_cover, compose_fact, compose_outro

WIB = timezone(timedelta(hours=7))
HISTORY = Path("history.json")  # persisted hooks for cross-run dedup (out/ is gitignored)


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
    """Recent hooks/facts so Claude doesn't repeat itself (local out/ + history.json)."""
    hooks: list[str] = list(_load_history())
    if out_root.exists():
        for d in sorted(out_root.iterdir(), reverse=True):
            meta = d / "meta.json"
            if not meta.is_file():
                continue
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                hooks.append(m.get("hook") or m.get("fact") or "")
            except Exception:
                continue
            if len(hooks) >= limit + len(_load_history()):
                break
    # de-dup, keep order, drop empties
    seen, out = set(), []
    for h in hooks:
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def main() -> int:
    load_dotenv()
    now = datetime.now(WIB)
    out_root = Path("out")
    out_dir = out_root / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    category = os.environ.get("CATEGORY", "").strip().lower() or None

    print("[1/3] Generating fakta with Claude...")
    fakta = generate_fakta(category=category, avoid=_recent_hooks(out_root))
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
            overlay = make_reel_overlay(
                fakta["hook"], fakta["category"], fakta["fact"], str(out_dir / "reel_overlay.png")
            )
            render_reel(video_paths, overlay, str(out_dir / "reel.mp4"))
            print("      → reel.mp4")
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
