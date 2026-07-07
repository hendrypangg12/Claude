"""Story Kantor → 1 carousel IG (3 slide teks, gaya Folkative). Tanpa foto/video.

Env:
  TOPIC   topik spesifik (opsional, mis. 'lembur')
  ANTHROPIC_API_KEY
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from sk_generator import generate_content
from sk_image_maker import compose_statement, BRAND_TEXT

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

    meta = {"id": out_dir.name, "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
            "topic": c["topic"], "hook": c["hook"], "label": "STORY KANTOR", "slides": 1}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"      Done → {out_dir} (1 foto)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
