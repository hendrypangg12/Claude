"""Fetch a relevant image via Google Custom Search API."""
import os
import requests


def fetch_image(query: str, out_path: str) -> str:
    """Search Google Images for `query`, download first result to `out_path`.
    Returns the saved file path. Filters to CC-licensed images by default."""
    api_key = os.environ["GOOGLE_API_KEY"]
    cse_id = os.environ["GOOGLE_CSE_ID"]
    license_filter = os.environ.get(
        "IMAGE_LICENSE_FILTER",
        "cc_publicdomain,cc_attribute,cc_sharealike",
    )

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "searchType": "image",
        "num": 5,
        "imgSize": "large",
        "safe": "active",
    }
    if license_filter and license_filter.lower() != "any":
        params["rights"] = license_filter

    resp = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise RuntimeError(f"No images found for query: {query!r}")

    # Try items in order until one downloads successfully.
    last_error = None
    for item in items:
        image_url = item.get("link")
        if not image_url:
            continue
        try:
            img_resp = requests.get(
                image_url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            img_resp.raise_for_status()
            with open(out_path, "wb") as fp:
                fp.write(img_resp.content)
            return out_path
        except Exception as exc:  # try the next candidate
            last_error = exc
            continue
    raise RuntimeError(f"All image candidates failed to download: {last_error}")
