"""Bangun manifest JSON buat dashboard monitoring (faktaviral + beruang finance).

Scan folder published/<ts>/ tiap brand → tulis docs/<brand>-manifest.json berisi
daftar post (id, tanggal, jam, label, judul, ada reel/carousel). Dashboard baca ini.

Dipanggil dari workflow (abis commit) + bisa dijalankan manual.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _entry(d: Path) -> dict | None:
    meta_f = d / "meta.json"
    if not meta_f.is_file():
        return None
    try:
        m = json.loads(meta_f.read_text(encoding="utf-8"))
    except Exception:
        return None
    slides = sum(1 for i in (1, 2, 3) if (d / f"post_{i}.jpg").exists())
    if not slides:
        return None
    # fallback date/time dari nama folder "YYYY-MM-DD_HH-MM-SS"
    date_f, time_f = m.get("date", ""), m.get("time", "")
    if (not date_f or not time_f) and "_" in d.name:
        dpart, _, tpart = d.name.partition("_")
        date_f = date_f or dpart
        time_f = time_f or tpart.replace("-", ":")[:5]
    return {
        "id": d.name,
        "date": date_f,
        "time": time_f,
        # label tampilan: pakai label/category/type apa pun yang ada
        "label": (m.get("label") or m.get("category") or m.get("type") or "").upper(),
        "title": m.get("hook") or m.get("headline") or m.get("fact") or "",
        "slides": slides,
        "reel": (d / "reel.mp4").exists(),
    }


def build(published: Path, brand: str, out: Path) -> int:
    posts = []
    if published.is_dir():
        for d in sorted(published.iterdir(), reverse=True):
            if d.is_dir():
                e = _entry(d)
                if e:
                    posts.append(e)
    out.write_text(json.dumps({"brand": brand, "posts": posts}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"{brand}: {len(posts)} post → {out}")
    return len(posts)


def main() -> None:
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    build(ROOT / "fakta-poster" / "published", "faktaviral", docs / "faktaviral-manifest.json")
    build(ROOT / "beruang-finance" / "published", "beruang", docs / "beruang-manifest.json")


if __name__ == "__main__":
    main()
