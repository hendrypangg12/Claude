"""Lalu — daily Folkative-style quote pipeline.

Usage:  python daily_quote.py
"""
import json
import os
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

from quote_generator import THEMES, generate_caption, generate_quote
from quote_image_maker import compose_quote

WIB = timezone(timedelta(hours=7))


def main() -> int:
    load_dotenv()

    slot = os.environ.get("SLOT", "pagi").strip().lower()
    if slot not in THEMES:
        slot = "pagi"
    theme = random.choice(THEMES[slot])

    now = datetime.now(WIB)
    folder_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path("out") / folder_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Generating quote… (slot={slot}, theme={theme!r})")
    text = generate_quote(theme)
    print(f"      → {text}")

    print("[2/3] Composing image…")
    image_path = str(out_dir / "post_1.jpg")
    compose_quote(text, image_path)
    print(f"      → {image_path}")

    print("[3/3] Generating caption…")
    caption = generate_caption(text, theme)
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
    print(f"      → {out_dir / 'caption.txt'}")

    meta = {
        "id": folder_id,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "headline": text,
        "source": "lalu",
        "niche": slot,
        "theme": theme,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
