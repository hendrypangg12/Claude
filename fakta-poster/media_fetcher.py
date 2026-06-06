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


def fetch_photo(query: str, out_path: str) -> str:
    # no orientation restriction → most RELEVANT photo first (we crop to square anyway)
    r = requests.get(
        PHOTO_URL,
        headers={"Authorization": _key()},
        params={"query": query, "per_page": 15},
        timeout=20,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"No Pexels photo for {query!r}")
    src = photos[0]["src"]
    return _download(src.get("large2x") or src.get("large") or src["original"], out_path)


def fetch_photos(query: str, out_dir: str, count: int = 3) -> list[str]:
    """Download up to `count` relevant photos → out_dir/bgp_N.jpg (1 per slide)."""
    r = requests.get(
        PHOTO_URL,
        headers={"Authorization": _key()},
        params={"query": query, "per_page": 15},
        timeout=20,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    paths: list[str] = []
    for p in photos:
        if len(paths) >= count:
            break
        src = p.get("src", {})
        url = src.get("large2x") or src.get("large") or src.get("original")
        if not url:
            continue
        try:
            out = os.path.join(out_dir, f"bgp_{len(paths)}.jpg")
            _download(url, out)
            paths.append(out)
        except Exception:
            continue
    if not paths:
        raise RuntimeError(f"No Pexels photo for {query!r}")
    return paths


def _best_video_link(v: dict, min_h: int = 720) -> str | None:
    """Pick a decent-resolution file (any orientation) ~1280px tall; we crop to 9:16."""
    best = None
    for f in v.get("video_files", []):
        w, h = f.get("width") or 0, f.get("height") or 0
        if not f.get("link") or h < min_h:
            continue
        score = abs(h - 1280)  # prefer ~HD, not 4K-huge nor tiny
        if best is None or score < best[0]:
            best = (score, f["link"])
    if best is None:
        files = v.get("video_files", [])
        if files and files[0].get("link"):
            best = (99999, files[0]["link"])
    return best[1] if best else None


def fetch_videos(query: str, out_dir: str, count: int = 3) -> list[str]:
    """Download up to `count` of the MOST RELEVANT stock clips for `query`.

    No orientation filter (octopus/etc. clips are mostly landscape) — we crop to
    9:16 in ffmpeg. Pexels ranks by relevance, so the top few stay on-topic."""
    r = requests.get(
        VIDEO_URL,
        headers={"Authorization": _key()},
        params={"query": query, "per_page": 15, "size": "medium"},
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
