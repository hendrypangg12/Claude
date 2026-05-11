"""Fetch top trending news from NewsAPI."""
import os
import requests


def fetch_top_headline() -> dict:
    """Return the top trending article: {title, description, url, source}."""
    api_key = os.environ["NEWSAPI_KEY"]
    country = os.environ.get("NEWS_COUNTRY", "id")
    category = os.environ.get("NEWS_CATEGORY", "general")

    resp = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={
            "country": country,
            "category": category,
            "pageSize": 10,
            "apiKey": api_key,
        },
        timeout=20,
    )
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    if not articles:
        raise RuntimeError(f"No articles returned for country={country} category={category}")

    # Pick the first article that has both a title and a description.
    for article in articles:
        if article.get("title") and article.get("description"):
            return {
                "title": article["title"],
                "description": article["description"],
                "url": article.get("url", ""),
                "source": (article.get("source") or {}).get("name", ""),
            }
    raise RuntimeError("No article with both title and description found")
