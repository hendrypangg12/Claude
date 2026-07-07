"""Cari video cover lagu di YouTube via YouTube Data API v3 (resmi, bukan scraping).

Butuh GOOGLE_API_KEY dengan "YouTube Data API v3" ke-enable di Google Cloud Console
(project yang sama boleh dipakai bareng Google Custom Search punya fakta-poster, tapi
API-nya harus di-enable terpisah — API key doang gak otomatis dapet akses semua API).
"""
import os

import requests

API_URL = "https://www.googleapis.com/youtube/v3/search"


def search_covers(song: str, max_results: int = 8, avoid_ids: set[str] | None = None) -> list[dict]:
    """Return [{'video_id','url','title','channel'}] — video cover teratas buat 1 lagu.

    Cari query "{song} cover" biar condong ke video cover (bukan video resmi/label),
    di-filter buang video yang video_id-nya udah pernah dipakai (avoid_ids).
    """
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY kosong — butuh YouTube Data API v3 key")
    avoid_ids = avoid_ids or set()

    params = {
        "part": "snippet",
        "q": f"{song} cover",
        "type": "video",
        "maxResults": min(max_results * 2, 25),  # ambil ekstra, ntar difilter avoid_ids
        "videoDuration": "short",   # < 4 menit — cover akustik/cepat, ngirit transcribe
        "relevanceLanguage": "id",
        "safeSearch": "moderate",
        "key": key,
    }
    r = requests.get(API_URL, params=params, timeout=30)
    if not r.ok:
        raise RuntimeError(f"YouTube search gagal {r.status_code}: {r.text[:300]}")
    items = r.json().get("items", [])

    out = []
    for it in items:
        vid = (it.get("id") or {}).get("videoId")
        if not vid or vid in avoid_ids:
            continue
        sn = it.get("snippet", {})
        out.append({
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": sn.get("title", ""),
            "channel": sn.get("channelTitle", ""),
        })
        if len(out) >= max_results:
            break
    return out
