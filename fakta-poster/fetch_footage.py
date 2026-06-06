"""Fetch raw Pexels stock clips for a topic and save them to a folder, so a reel
can be rendered with a custom overlay (data terverifikasi, gaya FAKTAVIRAL).

Reads PEXELS_API_KEY from env. Env:
  QUERIES  comma-separated subjects (mis. "rupiah money,stock market chart,bank")
           — 1 klip terbaik diambil per query → footage variatif tapi tetap nyambung.
  OUT_DIR  folder tujuan (default: footage/<slug>)
  PER      kalau cuma 1 query, ambil sebanyak ini (default 3).
"""
import os
import sys
import re

from media_fetcher import _best_video_link, _download, VIDEO_URL, PHOTO_URL
import requests


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "footage"


def _search(query: str, want: int) -> list[str]:
    r = requests.get(
        VIDEO_URL,
        headers={"Authorization": os.environ["PEXELS_API_KEY"].strip()},
        params={"query": query, "per_page": 15, "size": "medium"},
        timeout=25,
    )
    r.raise_for_status()
    links: list[str] = []
    for v in r.json().get("videos", []):
        if len(links) >= want:
            break
        link = _best_video_link(v)
        if link:
            links.append(link)
    return links


def _search_photos(query: str, want: int) -> list[str]:
    r = requests.get(
        PHOTO_URL,
        headers={"Authorization": os.environ["PEXELS_API_KEY"].strip()},
        params={"query": query, "per_page": 15},
        timeout=25,
    )
    r.raise_for_status()
    links: list[str] = []
    for p in r.json().get("photos", []):
        if len(links) >= want:
            break
        src = p.get("src", {})
        url = src.get("large2x") or src.get("large") or src.get("original")
        if url:
            links.append(url)
    return links


def main() -> int:
    queries = [q.strip() for q in os.environ.get("QUERIES", "").split(",") if q.strip()]
    if not queries:
        print("ERROR: set QUERIES env"); return 1
    per = int(os.environ.get("PER", "3"))
    out_dir = os.environ.get("OUT_DIR") or os.path.join("footage", _slug(queries[0]))
    os.makedirs(out_dir, exist_ok=True)

    saved: list[str] = []
    if len(queries) == 1:
        links = _search(queries[0], per)
    else:
        links = []
        for q in queries:               # 1 klip terbaik per subjek = variatif
            got = _search(q, 1)
            if got:
                links.append(got[0])
    for i, link in enumerate(links):
        try:
            p = os.path.join(out_dir, f"clip_{i}.mp4")
            _download(link, p)
            saved.append(p)
            print(f"  ok  {os.path.basename(p)}  <- {link[:70]}")
        except Exception as exc:
            print(f"  skip ({exc})")
    # photos juga (1 per slide carousel) — subjek sama biar nyambung
    photo_links: list[str] = []
    if len(queries) == 1:
        photo_links = _search_photos(queries[0], per)
    else:
        for q in queries:
            got = _search_photos(q, 1)
            if got:
                photo_links.append(got[0])
    photos: list[str] = []
    for i, link in enumerate(photo_links):
        try:
            p = os.path.join(out_dir, f"photo_{i}.jpg")
            _download(link, p)
            photos.append(p)
            print(f"  ok  {os.path.basename(p)}")
        except Exception as exc:
            print(f"  skip photo ({exc})")

    if not saved:
        print("ERROR: no footage downloaded"); return 1
    print(f"DONE: {len(saved)} klip + {len(photos)} foto -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
