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


def _best_video_link(v: dict, min_h: int = 960) -> str | None:
    """Pick a portrait-ish file (height >= min_h) closest to 1920 tall."""
    best = None
    for f in v.get("video_files", []):
        w, h = f.get("width") or 0, f.get("height") or 0
        if not f.get("link") or not h:
            continue
        portrait = h >= w
        score = (0 if portrait else 1, abs(h - 1920))
        if h >= min_h and (best is None or score < best[0]):
            best = (score, f["link"])
    if best is None:
        files = v.get("video_files", [])
        if files and files[0].get("link"):
            best = ((9, 9), files[0]["link"])
    return best[1] if best else None


def fetch_videos(query: str, out_dir: str, count: int = 5,
                 orientation: str = "portrait") -> list[str]:
    """Download up to `count` distinct stock clips for `query` → out_dir/bg_N.mp4.

    Multiple clips let us build a varied 30-45s reel (vs looping one short clip)."""
    r = requests.get(
        VIDEO_URL,
        headers={"Authorization": _key()},
        params={"query": query, "per_page": 15, "orientation": orientation, "size": "medium"},
        timeout=20,
    )
    r.raise_for_status()
    videos = r.json().get("videos", [])
    paths: list[str] = []
    for v in videos:
        if len(paths) >= count:
            break
        link = _best_video_link(v)
        if not link:
            continue
        try:
            p = os.path.join(out_dir, f"bg_{len(paths)}.mp4")
            _download(link, p)
            paths.append(p)
        except Exception:
            continue
    if not paths:
        raise RuntimeError(f"No Pexels video for {query!r}")
    return paths
