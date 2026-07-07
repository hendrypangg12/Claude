"""Orchestrator niche 'reff cover': 1 lagu → cari N video cover → potong reff tiap satu
→ kumpulin ke 1 folder out/<timestamp>/ (banyak clip, siap posting).

Env:
  SONG          judul lagu (wajib, mis. "Jogja Istimewa")
  NUM_COVERS    berapa cover yang dicoba (default 5)
  BRAND         watermark brand (default FAKTAVIRAL.IDN — ganti sesuai niche musik)
  GOOGLE_API_KEY, ANTHROPIC_API_KEY, YT_COOKIES
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reff_clip import make_reff_clip
from search_covers import search_covers

WIB = timezone(timedelta(hours=7))


def _recent_video_ids(published: Path, limit: int = 300) -> set[str]:
    """Video ID yang UDAH pernah dipotong (dari meta.json run sebelumnya) — anti ulang."""
    ids: set[str] = set()
    if not published.exists():
        return ids
    for d in sorted(published.iterdir(), reverse=True)[:limit]:
        meta = d / "meta.json"
        if not meta.is_file():
            continue
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            continue
        for c in m.get("clips", []):
            url = c.get("url", "")
            if "v=" in url:
                ids.add(url.split("v=", 1)[1].split("&", 1)[0])
    return ids


def main() -> int:
    song = os.environ.get("SONG", "").strip()
    if not song:
        print("ERROR: set env SONG, mis. SONG='Jogja Istimewa'")
        return 2
    num_covers = int(os.environ.get("NUM_COVERS", "5"))
    brand = os.environ.get("BRAND", "FAKTAVIRAL.IDN")

    now = datetime.now(WIB)
    out_dir = Path("out") / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    avoid = _recent_video_ids(Path("published-reff"))
    print(f"[1/2] Cari cover \"{song}\" di YouTube (skip {len(avoid)} yang udah pernah)...")
    covers = search_covers(song, max_results=num_covers, avoid_ids=avoid)
    print(f"      ketemu {len(covers)} kandidat")
    if not covers:
        print("Gak ada cover baru ketemu. Selesai (0 klip).")
        (out_dir / "meta.json").write_text(json.dumps(
            {"id": out_dir.name, "song": song, "clips": [], "created": now.isoformat()},
            ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    print(f"[2/2] Proses tiap cover → potong reff...")
    clips = []
    for i, c in enumerate(covers, 1):
        try:
            clip = make_reff_clip(c["url"], out_dir, i, brand=brand)
        except Exception as exc:  # 1 cover gagal jangan hentikan yang lain
            print(f"      [{i}] gagal diproses: {exc}")
            continue
        if clip:
            clips.append(clip)
            print(f"      ✓ clip-{i} [{clip['reff_start']:.0f}-{clip['reff_end']:.0f}s] "
                  f"conf={clip['confidence']} — {clip['source_title'][:50]}")

    meta = {
        "id": out_dir.name,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "song": song,
        "brand": brand,
        "clips": clips,
        "created": now.isoformat(),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(f"\nDONE → {out_dir} ({len(clips)}/{len(covers)} cover jadi klip reff)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
