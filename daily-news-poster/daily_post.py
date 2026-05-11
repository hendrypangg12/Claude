"""Daily news → Instagram pipeline.

Usage:  python daily_post.py
Reads configuration from .env (or the surrounding environment).
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from caption_generator import generate_caption
from image_fetcher import fetch_image
from image_maker import compose
from news_fetcher import fetch_top_headline


def main() -> int:
    load_dotenv()

    out_dir = Path("out") / datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/5] Fetching top headline...")
    article = fetch_top_headline()
    print(f"      → {article['title']}")

    print("[2/5] Generating caption with Claude...")
    caption = generate_caption(
        article["title"], article["description"], article["source"]
    )
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")

    print("[3/5] Searching Google Images...")
    raw_image_path = str(out_dir / "raw.jpg")
    # Use first ~6 meaningful words of the title as the search query.
    query = " ".join(article["title"].split()[:6])
    fetch_image(query, raw_image_path)

    print("[4/5] Composing post...")
    final_image_path = str(out_dir / "post.jpg")
    compose(raw_image_path, article["title"], article["source"], final_image_path)
    print(f"      → {final_image_path}")

    if os.environ.get("DRY_RUN", "").lower() == "true":
        print("[5/5] DRY_RUN=true → skipping Instagram upload.")
        print(f"\nPreview the post at: {final_image_path}")
        print(f"Caption saved to:    {out_dir / 'caption.txt'}")
        return 0

    print("[5/5] Publishing to Instagram...")
    from instagram_uploader import publish_to_instagram

    result = publish_to_instagram(final_image_path, caption)
    print(f"      → Published. Media ID: {result.get('id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
