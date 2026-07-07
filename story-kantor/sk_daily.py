"""Story Kantor → 1 carousel IG (3 slide teks, gaya Folkative). Tanpa foto/video.

Env:
  TOPIC   topik spesifik (opsional, mis. 'lembur')
  ANTHROPIC_API_KEY
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from sk_generator import generate_content
from sk_image_maker import compose_statement, compose_statement_vertical, BRAND_TEXT
from sk_video_maker import pick_music, music_credit, render_reel

WIB = timezone(timedelta(hours=7))


def _recent_hooks(out_root: Path, limit: int = 40) -> list[str]:
    hooks: list[str] = []
    for root in (Path("published"), out_root):
        if not root.exists():
            continue
        for dd in sorted(root.iterdir(), reverse=True):
            meta = dd / "meta.json"
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

    topic = os.environ.get("TOPIC", "").strip() or None

    if os.environ.get("NO_AI", "").lower() in ("1", "true", "yes"):
        print("[1/2] Mode HEMAT (bank quote, tanpa AI)...")
        from sk_quotes import pick_quote
        c = pick_quote(avoid=_recent_hooks(out_root))
    else:
        print("[1/2] Generate konten (Claude)...")
        c = generate_content(topic=topic, avoid=_recent_hooks(out_root))
    print(f"      → [{c['topic']}] {c['hook']}")

    # SATU foto aja — statement paling ngena (hook), bukan carousel 3-slide.
    print("[2/2] Compose 1 foto (gaya Folkative)...")
    compose_statement(c["hook"], str(out_dir / "post_1.jpg"), idx=0, total=1, last=True)
    (out_dir / "caption.txt").write_text(c["caption"], encoding="utf-8")

    # CAMPUR tapi JANGAN DOUBLE-POST: tiap generate cuma jadi 1 post ke IG —
    # foto ATAU reel (dipilih acak), gak pernah dua-duanya buat konten yang sama.
    made_reel = False
    if random.random() < 0.5:
        try:
            vert = str(out_dir / "_vertical.jpg")
            compose_statement_vertical(c["hook"], vert)
            music = pick_music()
            render_reel(vert, str(out_dir / "reel.mp4"), music=music)
            os.remove(vert)
            caption_reel = c["caption"] + ("\n\n" + music_credit(music) if music else "")
            (out_dir / "caption_reel.txt").write_text(caption_reel, encoding="utf-8")
            made_reel = True
            print("      + reel.mp4 (musik: " + ("ada" if music else "tanpa") + ") — slot ini POST REEL")
        except Exception as exc:
            print(f"      (reel gagal dibuat, fallback slot FOTO: {exc})")
    if not made_reel:
        print("      slot ini POST FOTO (reel dilewati biar gak double-post)")

    meta = {"id": out_dir.name, "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
            "topic": c["topic"], "hook": c["hook"], "label": "STORY KANTOR", "slides": 1,
            "posted_as": "reel" if made_reel else "foto"}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"      Done → {out_dir} (1 foto)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
