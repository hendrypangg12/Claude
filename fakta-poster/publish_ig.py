"""Publish a generated fakta to Instagram (carousel + reel).

Reads media from a local folder (PUB_DIR) but tells Instagram to fetch them from
public raw URLs (RAW_DIR). Skips gracefully if IG creds aren't set.

Env:
  IG_USER_ID, IG_ACCESS_TOKEN   IG business id + token (required to publish)
  PUB_DIR                       local folder with post_1..3.jpg / reel.mp4 / caption.txt
  RAW_DIR                       public base url for that same folder
  POST_MODE                     "both" (default) | "carousel" | "reel"
"""
import os
import sys
from pathlib import Path

from instagram_uploader import publish_carousel, publish_reel


def main() -> int:
    ig_id = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not ig_id or not token:
        print("IG_USER_ID / IG_ACCESS_TOKEN belum di-set → skip auto-upload (mode manual).")
        return 0

    pub = Path(os.environ["PUB_DIR"])
    raw = os.environ["RAW_DIR"].rstrip("/")
    mode = os.environ.get("POST_MODE", "both").strip().lower()
    caption = (pub / "caption.txt").read_text(encoding="utf-8") if (pub / "caption.txt").exists() else ""

    posted = []
    if mode in ("both", "carousel"):
        imgs = [f"{raw}/post_{i}.jpg" for i in (1, 2, 3) if (pub / f"post_{i}.jpg").exists()]
        if imgs:
            print(f"[carousel] publishing {len(imgs)} slides...")
            pid = publish_carousel(ig_id, token, imgs, caption)
            print(f"[carousel] ✅ posted, media id: {pid}")
            posted.append(("carousel", pid))

    if mode in ("both", "reel") and (pub / "reel.mp4").exists():
        print("[reel] publishing reel.mp4 ...")
        cover = f"{raw}/post_1.jpg" if (pub / "post_1.jpg").exists() else None
        rid = publish_reel(ig_id, token, f"{raw}/reel.mp4", caption, cover_url=cover)
        print(f"[reel] ✅ posted, media id: {rid}")
        posted.append(("reel", rid))

    if not posted:
        print("Tidak ada yang dipublish.")
        return 1
    print(f"Selesai. {len(posted)} konten ter-publish: {[p[0] for p in posted]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
