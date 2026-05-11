"""Fetch top trending international news from NewsAPI."""
import os
import requests


def fetch_candidates_intl(page_size: int = 10) -> list[dict]:
    """Return a list of NewsAPI top-headline candidates."""
    api_key = os.environ["NEWSAPI_KEY"].strip()
    country = os.environ.get("NEWS_COUNTRY_INTL", "us").strip()
    category = os.environ.get("NEWS_CATEGORY", "general").strip()

    resp = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={
            "country": country,
            "category": category,
            "pageSize": page_size,
            "apiKey": api_key,
        },
        timeout=20,
    )
    resp.raise_for_status()
    articles = resp.json().get("articles", [])

    out = []
    for article in articles:
        if article.get("title") and article.get("description"):
            out.append({
                "title": article["title"],
                "description": article["description"],
                "url": article.get("url", ""),
                "source": (article.get("source") or {}).get("name", ""),
                "image_url": article.get("urlToImage") or "",
            })
    return out


def fetch_top_headline_intl() -> dict:
    """Return just the first usable international headline (fallback path)."""
    candidates = fetch_candidates_intl()
    if not candidates:
        raise RuntimeError("No articles returned from NewsAPI")
    return candidates[0]
