"""Beruang Finance → 1 carousel IG (3 slide) pakai foto Pexels.

Env:
  CTYPE     tips | berita | lucu  (kosong = Claude pilih)
  TOPIC     topik spesifik (opsional)
  ANTHROPIC_API_KEY, PEXELS_API_KEY
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fakta-poster"))
from bf_generator import generate_content
from bf_image_maker import compose_cover, compose_points, compose_outro, TYPE_LABELS

WIB = timezone(timedelta(hours=7))

HEADER = {"tips": "CARANYA", "berita": "FAKTANYA", "lucu": "RELATE GAK?"}


def _recent_hooks(out_root: Path, limit: int = 40) -> list[str]:
    hooks: list[str] = []
    for root in (Path("published"), out_root):
        if not root.exists():
            continue
        for d in sorted(root.iterdir(), reverse=True):
            meta = d / "meta.json"
            if meta.is_file():
                try:
                    hooks.append(json.loads(meta.read_text(encoding="utf-8")).get("hook", ""))
                except Exception:
                    pass
    seen, out = set(), []
    for h in hooks:
        if h and h not in seen:
            seen.add(h); out.append(h)
    return out[:limit]


def main() -> int:
    load_dotenv()
    now = datetime.now(WIB)
    out_root = Path("out")
    out_dir = out_root / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    ctype = os.environ.get("CTYPE", "").strip().lower() or None
    topic = os.environ.get("TOPIC", "").strip() or None

    print("[1/3] Generate konten (Claude)...")
    c = generate_content(ctype=ctype, topic=topic, avoid=_recent_hooks(out_root))
    print(f"      → [{c['type']}] {c['hook']}")

    photos: list[str] = []
    videos: list[str] = []
    if os.environ.get("PEXELS_API_KEY"):
        from media_fetcher import fetch_photos, fetch_videos
        try:
            photos = fetch_photos(c["query"] or "money", str(out_dir), count=3)
            print(f"      foto: {len(photos)} ({c['query']})")
        except Exception as exc:
            print(f"      (foto gagal: {exc}) → background kuning polos")
        try:
            videos = fetch_videos(c["query"] or "money", str(out_dir), count=2)
            print(f"      video: {len(videos)} klip ({c['query']})")
        except Exception as exc:
            print(f"      (video gagal: {exc}) → skip reel")
    else:
        print("      (PEXELS_API_KEY kosong → background kuning polos, no reel)")

    p1 = photos[0] if len(photos) > 0 else None
    p2 = photos[1] if len(photos) > 1 else p1
    p3 = photos[2] if len(photos) > 2 else p1

    print("[2/3] Compose carousel...")
    compose_cover(c["hook"], c["type"], c["kicker"], str(out_dir / "post_1.jpg"), bg_path=p1)
    compose_points(c["points"], HEADER.get(c["type"], "POIN PENTING"),
                   str(out_dir / "post_2.jpg"), bg_path=p2)
    compose_outro(c["takeaway"], str(out_dir / "post_3.jpg"), bg_path=p3)
    (out_dir / "caption.txt").write_text(c["caption"], encoding="utf-8")

    # reel 20 detik (2 klip x 10s) kalau ada video Pexels
    if videos:
        print("      Compose reel 20 detik...")
        try:
            from bf_video_maker import make_reel_overlay, render_reel
            mo, fo = make_reel_overlay(c["hook"], c["kicker"], c["points"],
                                       str(out_dir / "reel_main.png"), str(out_dir / "reel_fact.png"))
            render_reel(videos, mo, fo, str(out_dir / "reel.mp4"),
                        seg=10, max_segments=2, fact_at=2.0)
            print("      → reel.mp4 (20s)")
        except Exception as exc:
            print(f"      (reel gagal: {exc})")

    meta = {"id": out_dir.name, "date": now.strftime("%Y-%m-%d"), "type": c["type"],
            "hook": c["hook"], "label": TYPE_LABELS.get(c["type"], "")}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[3/3] Done → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
