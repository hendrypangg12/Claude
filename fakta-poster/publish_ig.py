"""Publish a generated fakta to one OR many official Instagram accounts.

Reads media from a local folder (PUB_DIR) but tells Instagram to fetch them from
public raw URLs (RAW_DIR). Skips gracefully if no creds are set.

Akun bisa 1 atau banyak (semua akun RESMI milik sendiri — bukan bot farm):

  IG_ACCOUNTS   JSON array (1 secret nampung semua akun). Tiap item:
                  {"name": "faktaviral", "ig_user_id": "1784...", "token": "EAA..."}
                Contoh:
                  [{"name":"faktaviral","ig_user_id":"178...","token":"EAA1..."},
                   {"name":"faktasains","ig_user_id":"179...","token":"EAA2..."}]

  (fallback 1-akun, biar setup lama tetap jalan)
  IG_USER_ID, IG_ACCESS_TOKEN

  PUB_DIR       folder lokal: post_1..3.jpg / reel.mp4 / caption.txt
  RAW_DIR       base url publik folder yang sama
  POST_MODE     "both" (default) | "carousel" | "reel" | "none"
  STAGGER_SEC   jeda antar-akun biar natural (default 30 detik; 0 = tanpa jeda)
"""
import json
import os
import random
import sys
import time
from pathlib import Path

from instagram_uploader import publish_carousel, publish_image, publish_reel, publish_story


def _load_accounts() -> list[dict]:
    """Daftar akun dari IG_ACCOUNTS (JSON) atau fallback ke IG_USER_ID tunggal."""
    raw = os.environ.get("IG_ACCOUNTS", "").strip()
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"IG_ACCOUNTS bukan JSON valid → {exc}")
            return []
        accounts = []
        for i, a in enumerate(data):
            uid = str(a.get("ig_user_id", "")).strip()
            tok = str(a.get("token", "")).strip()
            if uid and tok:
                accounts.append({"name": a.get("name") or f"akun-{i+1}", "ig_user_id": uid, "token": tok})
            else:
                print(f"  (lewati akun '{a.get('name', i)}' — ig_user_id/token kosong)")
        return accounts
    # fallback: 1 akun dari env lama
    uid = os.environ.get("IG_USER_ID", "").strip()
    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if uid and tok:
        return [{"name": "default", "ig_user_id": uid, "token": tok}]
    return []


def _publish_one(acc: dict, pub: Path, raw: str, mode: str, caption: str) -> list[tuple]:
    ig_id, token, name = acc["ig_user_id"], acc["token"], acc["name"]
    posted: list[tuple] = []
    # mode hemat: slot 'reel' tapi gak ada video → fallback ke carousel biar tetap ke-post
    if mode == "reel" and not (pub / "reel.mp4").exists() and (pub / "post_1.jpg").exists():
        print(f"  [{name}] reel gak ada → fallback carousel")
        mode = "carousel"
    if mode in ("both", "carousel"):
        imgs = [f"{raw}/post_{i}.jpg" for i in (1, 2, 3) if (pub / f"post_{i}.jpg").exists()]
        if len(imgs) == 1:
            print(f"  [{name}] 1 foto (bukan carousel)...")
            pid = publish_image(ig_id, token, imgs[0], caption)
            print(f"  [{name}] ✅ image id: {pid}")
            posted.append(("image", pid))
        elif imgs:
            print(f"  [{name}] carousel: {len(imgs)} slide...")
            pid = publish_carousel(ig_id, token, imgs, caption)
            print(f"  [{name}] ✅ carousel id: {pid}")
            posted.append(("carousel", pid))
    if mode in ("both", "reel") and (pub / "reel.mp4").exists():
        print(f"  [{name}] reel...")
        # reel pakai caption ber-kredit musik kalau ada (carousel tetap caption biasa)
        reel_caption = caption
        if (pub / "caption_reel.txt").exists():
            reel_caption = (pub / "caption_reel.txt").read_text(encoding="utf-8")
        cover = f"{raw}/post_1.jpg" if (pub / "post_1.jpg").exists() else None
        rid = publish_reel(ig_id, token, f"{raw}/reel.mp4", reel_caption, cover_url=cover)
        print(f"  [{name}] ✅ reel id: {rid}")
        posted.append(("reel", rid))
    # STORY: tiap auto-post, share juga ke Story (reel 9:16 kalau ada, else cover).
    # Non-fatal: kalau story gagal, feed tetap ke-post. Matiin via POST_STORY=false.
    if os.environ.get("POST_STORY", "true").strip().lower() == "true":
        try:
            if (pub / "reel.mp4").exists():
                sid = publish_story(ig_id, token, video_url=f"{raw}/reel.mp4")
            elif (pub / "post_1.jpg").exists():
                sid = publish_story(ig_id, token, image_url=f"{raw}/post_1.jpg")
            else:
                sid = None
            if sid:
                print(f"  [{name}] ✅ story id: {sid}")
                posted.append(("story", sid))
        except Exception as exc:
            print(f"  [{name}] (story gagal: {exc}) — feed tetap ke-post")
    return posted


def main() -> int:
    accounts = _load_accounts()
    if not accounts:
        print("Belum ada akun (IG_ACCOUNTS / IG_USER_ID kosong) → skip auto-upload (mode manual).")
        return 0

    mode = os.environ.get("POST_MODE", "both").strip().lower()
    if mode == "none":
        print("POST_MODE=none → generate aja, gak auto-post.")
        return 0

    pub = Path(os.environ["PUB_DIR"])
    raw = os.environ["RAW_DIR"].rstrip("/")
    caption = (pub / "caption.txt").read_text(encoding="utf-8") if (pub / "caption.txt").exists() else ""
    stagger = int(os.environ.get("STAGGER_SEC", "30"))

    print(f"Publish ke {len(accounts)} akun: {[a['name'] for a in accounts]}")
    ok, fail = 0, 0
    for idx, acc in enumerate(accounts):
        try:
            done = _publish_one(acc, pub, raw, mode, caption)
            if done:
                ok += 1
            else:
                print(f"  [{acc['name']}] tidak ada yang dipublish.")
        except Exception as exc:  # 1 akun gagal jangan hentikan yang lain
            fail += 1
            print(f"  [{acc['name']}] ❌ gagal: {exc}")
        # jeda natural antar akun (jangan posting barengan persis detiknya)
        if stagger and idx < len(accounts) - 1:
            wait = stagger + random.randint(0, stagger)
            print(f"  ...tunggu {wait}s sebelum akun berikutnya")
            time.sleep(wait)

    print(f"Selesai. Sukses: {ok} akun · Gagal: {fail} akun.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
