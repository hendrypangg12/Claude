"""Fetch a relevant background from Pexels (free, commercial-use, no copyright issue).

Needs PEXELS_API_KEY (free: https://www.pexels.com/api/). Both functions raise on
failure so the caller can fall back to the plain cosmic background.
"""
import os

import requests

PHOTO_URL = "https://api.pexels.com/v1/search"
VIDEO_URL = "https://api.pexels.com/videos/search"


def _key() -> str:
    return os.environ["PEXELS_API_KEY"].strip()


def _download(url: str, out_path: str) -> str:
    r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    with open(out_path, "wb") as fp:
        fp.write(r.content)
    return out_path


def fetch_photo(query: str, out_path: str, orientation: str = "landscape") -> str:
    r = requests.get(
        PHOTO_URL,
        headers={"Authorization": _key()},
        params={"query": query, "per_page": 12, "orientation": orientation},
        timeout=20,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"No Pexels photo for {query!r}")
    src = photos[0]["src"]
    return _download(src.get("large2x") or src.get("large") or src["original"], out_path)


def fetch_video(query: str, out_path: str, orientation: str = "portrait") -> str:
    r = requests.get(
        VIDEO_URL,
        headers={"Authorization": _key()},
        params={"query": query, "per_page": 12, "orientation": orientation, "size": "medium"},
        timeout=20,
    )
    r.raise_for_status()
    videos = r.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No Pexels video for {query!r}")

    # Prefer a portrait-ish file with height >= 1080, smallest that qualifies.
    best = None
    for v in videos:
        for f in v.get("video_files", []):
            w, h = f.get("width") or 0, f.get("height") or 0
            if not f.get("link") or not h:
                continue
            portrait = h >= w
            score = (0 if portrait else 1, abs(h - 1920))
            if h >= 960 and (best is None or score < best[0]):
                best = (score, f["link"])
    if best is None:  # fall back to whatever the first video offers
        files = videos[0].get("video_files", [])
        if not files:
            raise RuntimeError("Pexels video had no downloadable files")
        best = ((0, 0), files[0]["link"])
    return _download(best[1], out_path)
