"""Fetch the top trending Indonesian headline from RSS feeds."""
import feedparser
import html
import re

FEEDS = [
    "https://rss.detik.com/index.php/detikcom",
    "https://www.antaranews.com/rss/terkini.xml",
    "https://www.cnnindonesia.com/nasional/rss",
]


def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)  # strip HTML tags from RSS summaries
    return text.strip()


def fetch_candidates_rss(limit_per_feed: int = 5) -> list[dict]:
    """Return a list of recent candidate articles from Indonesian feeds."""
    candidates = []
    for url in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue
        for entry in parsed.entries[:limit_per_feed]:
            title = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", "")) or _clean(entry.get("description", ""))
            if not title or not summary:
                continue
            candidates.append({
                "title": title,
                "description": summary[:500],
                "url": entry.get("link", ""),
                "source": parsed.feed.get("title", url),
            })
    return candidates


def fetch_top_headline_rss() -> dict:
    """Return just the first usable Indonesian headline (fallback path)."""
    candidates = fetch_candidates_rss()
    if not candidates:
        raise RuntimeError("All Indonesian RSS feeds returned no usable entries")
    return candidates[0]
