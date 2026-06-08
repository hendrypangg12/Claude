"""Bangun docs/clipper-manifest.json dari clipper/published/<ts>/meta.json.

Dipanggil di workflow abis commit. RAW_BASE = base URL raw.githubusercontent ke
folder clipper/published (di SHA commit ini) biar link video stabil.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ROOT / "clipper" / "published"
OUT = ROOT / "docs" / "clipper-manifest.json"

DEFAULT_RAW = ("https://raw.githubusercontent.com/hendrypangg12/Claude/"
               "claude/halo-bYUsl/clipper/published")


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
                    "title": c.get("title", ""),
                    "hook": c.get("hook", ""),
                    "score": c.get("score", 0),
                    "start": c.get("start"),
                    "end": c.get("end"),
                    "caption": c.get("caption", ""),
                })
            if not clips:
                continue
            posts.append({
                "id": d.name,
                "date": m.get("date", ""),
                "time": m.get("time", ""),
                "title": m.get("title", ""),
                "source_url": m.get("url", ""),
                "clips": clips,
            })
    OUT.write_text(json.dumps({"brand": "clipper", "posts": posts},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"clipper: {len(posts)} job → {OUT}")


if __name__ == "__main__":
    main()
