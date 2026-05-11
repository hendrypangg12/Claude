"""Daily news → Instagram pipeline.

Usage:  python daily_post.py
Reads configuration from .env (or the surrounding environment).
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from caption_generator import generate_caption, pick_best_article
from image_fetcher import fetch_image, fetch_image_from_url
from image_maker import compose
from news_fetcher import fetch_candidates_intl
from rss_fetcher import fetch_candidates_rss


def _gather_candidates() -> list[dict]:
    """Pull articles from configured sources.

    NEWS_SOURCE env var: "auto" (both, default), "rss_id", or "newsapi_intl".
    """
    mode = os.environ.get("NEWS_SOURCE", "auto").lower()
    candidates: list[dict] = []

    if mode in ("auto", "rss_id"):
        try:
            candidates.extend(fetch_candidates_rss())
        except Exception as exc:
            print(f"      (RSS source failed: {exc})")

    if mode in ("auto", "newsapi_intl"):
        try:
            candidates.extend(fetch_candidates_intl())
        except Exception as exc:
            print(f"      (NewsAPI source failed: {exc})")

    if not candidates:
        raise RuntimeError("All news sources returned no candidates")
    return candidates


def main() -> int:
    load_dotenv()

    out_dir = Path("out") / datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/5] Gathering candidate articles...")
    candidates = _gather_candidates()
    print(f"      → {len(candidates)} candidates collected")

    print("      Asking Claude to pick the best one...")
    article, reason = pick_best_article(candidates)
    print(f"      → [{article['source']}] {article['title']}")
    print(f"      Reason: {reason}")

    print("[2/5] Generating caption with Claude...")
    caption = generate_caption(
        article["title"], article["description"], article["source"]
    )
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")

    print("[3/5] Fetching article image...")
    raw_image_path = str(out_dir / "raw.jpg")
    article_image_url = article.get("image_url") or ""
    fetched = False
    if article_image_url:
        try:
            fetch_image_from_url(article_image_url, raw_image_path)
            print(f"      → from article: {article_image_url[:80]}")
            fetched = True
        except Exception as exc:
            print(f"      (article image failed: {exc})")
    if not fetched:
        if os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"):
            print("      Falling back to Google Images...")
            query = " ".join(article["title"].split()[:6])
            fetch_image(query, raw_image_path)
        else:
            raise RuntimeError(
                "No article image_url available and Google Images fallback not configured"
            )

    print("[4/5] Composing post...")
    final_image_path = str(out_dir / "post.jpg")
    compose(raw_image_path, article["title"], article["source"], final_image_path)
    print(f"      → {final_image_path}")

    if os.environ.get("DRY_RUN", "true").lower() == "true":
        print("[5/5] Semi-manual mode (DRY_RUN=true) → skipping Instagram upload.")
        print(f"\n  Image:   {final_image_path}")
        print(f"  Caption: {out_dir / 'caption.txt'}")
        print("\n  Download these files and upload manually via Instagram app.")
        return 0

    print("[5/5] Publishing to Instagram...")
    from instagram_uploader import publish_to_instagram

    result = publish_to_instagram(final_image_path, caption)
    print(f"      → Published. Media ID: {result.get('id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
