"""Publish konten yang udah digenerate ke Facebook Page (carousel + reel).

Pakai media dari folder lokal (PUB_DIR) tapi nyuruh FB ambil dari URL publik (RAW_DIR).
Skip mulus kalau token gak ada. Page dipilih otomatis = Page yang link ke IG_USER_ID.

Env:
  FB_TOKEN / IG_ACCESS_TOKEN   USER token (butuh pages_show_list + pages_manage_posts)
  IG_USER_ID                   buat nyari Page yang nyambung ke akun IG ini (opsional tapi disaranin)
  FB_PAGE_ID                   paksa Page tertentu (opsional)
  PUB_DIR                      folder lokal: post_1..3.jpg / reel.mp4 / caption.txt
  RAW_DIR                      base url publik folder yang sama
  POST_MODE                    both | carousel | reel | none
"""
import os
import sys
from pathlib import Path

from facebook_uploader import publish_photos, publish_video, resolve_page


def main() -> int:
    token = (os.environ.get("FB_TOKEN") or os.environ.get("IG_ACCESS_TOKEN", "")).strip()
    if not token:
        print("FB: token kosong (FB_TOKEN/IG_ACCESS_TOKEN) → skip post FB.")
        return 0

    mode = os.environ.get("POST_MODE", "both").strip().lower()
    if mode == "none":
        print("FB: POST_MODE=none → skip.")
        return 0

    ig_user_id = os.environ.get("IG_USER_ID", "").strip()
    page_id_env = os.environ.get("FB_PAGE_ID", "").strip()
    try:
        page_id, page_token, page_name = resolve_page(token, ig_user_id, page_id_env)
    except Exception as exc:
        print(f"FB: gagal nemu Page → {exc}")
        return 1
    print(f"FB: target Page '{page_name}' (id {page_id})")

    pub = Path(os.environ["PUB_DIR"])
    raw = os.environ["RAW_DIR"].rstrip("/")
    caption = (pub / "caption.txt").read_text(encoding="utf-8") if (pub / "caption.txt").exists() else ""

    ok = 0
    if mode in ("both", "carousel"):
        imgs = [f"{raw}/post_{i}.jpg" for i in (1, 2, 3) if (pub / f"post_{i}.jpg").exists()]
        if imgs:
            try:
                pid = publish_photos(page_id, page_token, imgs, caption)
                print(f"FB: ✅ album/carousel id: {pid}")
                ok += 1
            except Exception as exc:
                print(f"FB: ❌ carousel gagal → {exc}")

    if mode in ("both", "reel") and (pub / "reel.mp4").exists():
        reel_caption = caption
        if (pub / "caption_reel.txt").exists():
            reel_caption = (pub / "caption_reel.txt").read_text(encoding="utf-8")
        try:
            vid = publish_video(page_id, page_token, f"{raw}/reel.mp4", reel_caption)
            print(f"FB: ✅ video/reel id: {vid}")
            ok += 1
        except Exception as exc:
            print(f"FB: ❌ reel gagal → {exc}")

    print(f"FB: selesai ({ok} item ke-post).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
