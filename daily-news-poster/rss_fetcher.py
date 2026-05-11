"""Fetch the top trending Indonesian headline from RSS feeds."""
import feedparser
import html
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

WIB = timezone(timedelta(hours=7))
MAX_AGE_HOURS_DEFAULT = 6  # only consider articles published within this window

DEFAULT_FEEDS = [
    "https://rss.detik.com/index.php/detikcom",
    "https://www.antaranews.com/rss/terkini.xml",
    "https://www.cnnindonesia.com/nasional/rss",
]

NICHE_FEEDS = {
    "pagi": [
        # Government economic policy: kebijakan BI / Kemenkeu / OJK / harga BBM / subsidi / pajak.
        "https://rss.detik.com/index.php/finance",
        "https://rss.detik.com/index.php/detikcom",
        "https://www.antaranews.com/rss/ekonomi.xml",
        "https://www.antaranews.com/rss/terkini.xml",
        "https://www.cnnindonesia.com/ekonomi/rss",
        "https://www.cnnindonesia.com/nasional/rss",
    ],
    "saham": [
        "https://rss.detik.com/index.php/finance",
        "https://www.antaranews.com/rss/ekonomi.xml",
        "https://www.cnnindonesia.com/ekonomi/rss",
    ],
    "market": [
        "https://rss.detik.com/index.php/finance",
        "https://www.cnnindonesia.com/ekonomi/rss",
        "https://www.antaranews.com/rss/ekonomi.xml",
    ],
    "startup": [
        "https://rss.detik.com/index.php/finance",
        "https://rss.detik.com/index.php/inet",
        "https://www.antaranews.com/rss/ekonomi.xml",
        "https://www.cnnindonesia.com/teknologi/rss",
    ],
}


def _feeds_for_niche() -> list[str]:
    niche = os.environ.get("NICHE", "").strip().lower()
    return NICHE_FEEDS.get(niche, DEFAULT_FEEDS)


def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _entry_published(entry) -> datetime | None:
    """Best-effort parse of an entry's publish time as aware UTC."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return None


def _extract_image(entry) -> str:
    """Pull the best available image URL from an RSS entry."""
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key) or []
        for item in media:
            if item.get("url"):
                return item["url"]
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image/") and enc.get("href"):
            return enc["href"]
    summary = entry.get("summary", "") or entry.get("description", "") or ""
    m = re.search(r'<img[^>]+src="([^"]+)"', summary)
    return m.group(1) if m else ""


def fetch_candidates_rss(limit_per_feed: int = 5) -> list[dict]:
    """Return recent candidate articles from Indonesian feeds, freshest first."""
    try:
        max_age_h = int(os.environ.get("MAX_ARTICLE_AGE_HOURS", str(MAX_AGE_HOURS_DEFAULT)))
    except ValueError:
        max_age_h = MAX_AGE_HOURS_DEFAULT
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=max_age_h)

    candidates = []
    for url in _feeds_for_niche():
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue
        for entry in parsed.entries[:limit_per_feed]:
            title = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", "")) or _clean(entry.get("description", ""))
            if not title or not summary:
                continue
            published = _entry_published(entry)
            if published and published < cutoff:
                continue
            candidates.append({
                "title": title,
                "description": summary[:500],
                "url": entry.get("link", ""),
                "source": parsed.feed.get("title", url),
                "image_url": _extract_image(entry),
                "published_at": published.isoformat() if published else "",
                "age_minutes": int((now_utc - published).total_seconds() // 60) if published else None,
            })

    candidates.sort(
        key=lambda c: c.get("age_minutes") if c.get("age_minutes") is not None else 99999
    )
    return candidates


def fetch_top_headline_rss() -> dict:
    """Return just the first usable Indonesian headline (fallback path)."""
    candidates = fetch_candidates_rss()
    if not candidates:
        raise RuntimeError("All Indonesian RSS feeds returned no usable entries")
    return candidates[0]
