"""Publish to Instagram via the Graph API (graph.facebook.com).

Needs a connected IG Business account id (IG_USER_ID) + an access token with
instagram_content_publish (IG_ACCESS_TOKEN). Media must be reachable at PUBLIC URLs.
"""
import time

import requests

GRAPH = "https://graph.facebook.com/v23.0"


def _post(path: str, params: dict, tries: int = 3) -> dict:
    last = None
    for attempt in range(tries):
        r = requests.post(f"{GRAPH}/{path}", data=params, timeout=90)
        if r.ok:
            return r.json()
        last = f"{r.status_code}: {r.text[:400]}"
        # transient (e.g. media URL not yet reachable) → wait & retry
        time.sleep(6 * (attempt + 1))
    raise RuntimeError(f"IG API POST {path} failed → {last}")


def _get(path: str, params: dict) -> dict:
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"IG API GET {path} failed → {r.status_code}: {r.text[:400]}")
    return r.json()


def _wait_ready(creation_id: str, token: str, max_wait: int = 300, interval: int = 6) -> None:
    waited = 0
    while waited < max_wait:
        res = _get(creation_id, {"fields": "status_code", "access_token": token})
        status = res.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Media processing ERROR for {creation_id}")
        time.sleep(interval)
        waited += interval
    raise RuntimeError(f"Media not ready after {max_wait}s")


def publish_carousel(ig_id: str, token: str, image_urls: list[str], caption: str) -> str:
    children = []
    for url in image_urls:
        res = _post(f"{ig_id}/media", {
            "image_url": url, "is_carousel_item": "true", "access_token": token,
        })
        children.append(res["id"])
    container = _post(f"{ig_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    })["id"]
    _wait_ready(container, token, max_wait=120)
    return _post(f"{ig_id}/media_publish", {"creation_id": container, "access_token": token}).get("id")


def publish_reel(ig_id: str, token: str, video_url: str, caption: str, cover_url: str | None = None) -> str:
    params = {"media_type": "REELS", "video_url": video_url, "caption": caption,
              "share_to_feed": "true", "access_token": token}
    if cover_url:
        params["cover_url"] = cover_url
    container = _post(f"{ig_id}/media", params)["id"]
    _wait_ready(container, token, max_wait=420)  # video processing can take a while
    return _post(f"{ig_id}/media_publish", {"creation_id": container, "access_token": token}).get("id")
