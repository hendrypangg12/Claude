"""Publish ke Facebook Page via Graph API.

Carousel  → tiap foto di-upload (published=false) → digabung jadi 1 post di /feed.
Reel/video → /{page}/videos pakai file_url (remote URL publik).

Page token diturunin dari USER token (butuh scope pages_manage_posts + pages_show_list).
Page-nya dipilih OTOMATIS = Page yang nyambung ke IG_USER_ID (biar gak salah Page).
"""
import json
import time

import requests

GRAPH = "https://graph.facebook.com/v23.0"


def _post(path: str, params: dict, tries: int = 3) -> dict:
    last = None
    for attempt in range(tries):
        r = requests.post(f"{GRAPH}/{path}", data=params, timeout=120)
        if r.ok:
            return r.json()
        last = f"{r.status_code}: {r.text[:400]}"
        time.sleep(6 * (attempt + 1))  # transient (media URL belum kebaca) → retry
    raise RuntimeError(f"FB API POST {path} gagal → {last}")


def _get(path: str, params: dict) -> dict:
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"FB API GET {path} gagal → {r.status_code}: {r.text[:400]}")
    return r.json()


def resolve_page(user_token: str, ig_user_id: str = "", page_id: str = "") -> tuple[str, str, str]:
    """Cari (page_id, page_token, page_name). Prioritas: page_id eksplisit (paling kuat —
    kalau user udah nyebut Page mana, itu yang dipakai), lalu Page yang link ke ig_user_id,
    lalu Page pertama yang punya akses post."""
    data = _get("me/accounts", {
        "fields": "id,name,access_token,instagram_business_account",
        "access_token": user_token,
    }).get("data", [])
    if not data:
        raise RuntimeError("Token ini gak punya akses Page mana pun "
                           "(pastiin scope pages_show_list + pages_manage_posts, & Page ke-grant).")

    # DIAGNOSTIK: tampilkan Page apa aja yang token bisa akses (nama gak disensor GitHub)
    print("FB: Page yang kebaca token →",
          ", ".join(f"{p.get('name','?')}({'token-OK' if p.get('access_token') else 'NO-token'})"
                    for p in data))
    print(f"FB: page_id diminta = {'(kosong)' if not page_id else 'ada (cek match di bawah)'}")
    if page_id and not any(str(p.get('id')) == str(page_id) for p in data):
        print(f"FB: ⚠️ page_id yang diminta TIDAK ada di daftar Page token → jatuh ke fallback")

    # 1) page_id eksplisit (FB_PAGE_ID/FB_PAGE_ID_BF) = niat user, menang dari tebakan IG-link
    if page_id:
        for p in data:
            if str(p.get("id")) == str(page_id) and p.get("access_token"):
                return p["id"], p["access_token"], p.get("name", "")
    # 2) Page yang IG-nya == ig_user_id
    if ig_user_id:
        for p in data:
            iba = (p.get("instagram_business_account") or {}).get("id")
            if iba and str(iba) == str(ig_user_id) and p.get("access_token"):
                return p["id"], p["access_token"], p.get("name", "")
    # 3) Page pertama yang ada token
    for p in data:
        if p.get("access_token"):
            return p["id"], p["access_token"], p.get("name", "")
    raise RuntimeError("Nemu Page tapi gak ada Page access token (cek pages_manage_posts).")


def publish_photos(page_id: str, page_token: str, image_urls: list[str], message: str) -> str:
    """Multi-foto jadi 1 post (album). 1 foto pun tetap lewat /feed biar caption nempel."""
    fbids = []
    for url in image_urls:
        res = _post(f"{page_id}/photos", {
            "url": url, "published": "false", "access_token": page_token,
        })
        fbids.append(res["id"])
    attached = json.dumps([{"media_fbid": i} for i in fbids])
    return _post(f"{page_id}/feed", {
        "message": message, "attached_media": attached, "access_token": page_token,
    }).get("id")


def publish_video(page_id: str, page_token: str, video_url: str, description: str) -> str:
    """Upload video ke Page pakai remote file_url. FB auto-anggap Reels kalau vertikal."""
    return _post(f"{page_id}/videos", {
        "file_url": video_url, "description": description, "access_token": page_token,
    }).get("id")
