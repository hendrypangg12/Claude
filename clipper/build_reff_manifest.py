"""Bangun docs/reffcover-manifest.json dari clipper/published-reff/<ts>/meta.json.

Dipanggil di workflow abis commit. RAW_BASE = base URL raw.githubusercontent ke
folder clipper/published-reff (di SHA commit ini) biar link video stabil.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ROOT / "clipper" / "published-reff"
OUT = ROOT / "docs" / "reffcover-manifest.json"

DEFAULT_RAW = ("https://raw.githubusercontent.com/hendrypangg12/Claude/"
               "claude/halo-bYUsl/clipper/published-reff")


def main() -> None:
    raw_base = os.environ.get("RAW_BASE", DEFAULT_RAW).rstrip("/")
    posts = []
    if PUBLISHED.is_dir():
        for d in sorted(PUBLISHED.iterdir(), reverse=True):
            mf = d / "meta.json"
            if not d.is_dir() or not mf.is_file():
                continue
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
            clips = []
            for c in m.get("clips", []):
                f = c.get("file")
                if not f or not (d / f).exists():
                    continue
                clips.append({
                    "file": f,
                    "url": f"{raw_base}/{d.name}/{f}",
                    "source_url": c.get("url", ""),
                    "source_title": c.get("source_title", ""),
                    "creator": c.get("creator", ""),
                    "reff_start": c.get("reff_start"),
                    "reff_end": c.get("reff_end"),
                    "confidence": c.get("confidence", 0),
                    "caption": c.get("caption", ""),
                })
            if not clips:
                continue
            posts.append({
                "id": d.name,
                "date": m.get("date", ""),
                "time": m.get("time", ""),
                "song": m.get("song", ""),
                "clips": clips,
            })
    OUT.write_text(json.dumps({"brand": "reffcover", "posts": posts},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"reffcover: {len(posts)} job → {OUT}")


if __name__ == "__main__":
    main()
