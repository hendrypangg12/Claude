"""Daily 'fakta unik' → Instagram carousel pipeline (original content, no copyright).

Usage:  python daily_fakta.py
Reads ANTHROPIC_API_KEY from .env / environment. Optional env:
  CATEGORY   one of sains|sejarah|tubuh|hewan|luarangkasa|teknologi (else Claude picks)
  DRY_RUN    "true" (default) — just generate files, no upload
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from fakta_generator import generate_fakta
from fakta_image_maker import compose_cover, compose_fact, compose_outro

# kategori yang harus GROUNDED ke berita real (diverifikasi lewat search engine)
NEWS_CATEGORIES = {"trending", "keuangan", "aktor"}

WIB = timezone(timedelta(hours=7))
HISTORY = Path("history.json")  # persisted hooks for cross-run dedup (out/ is gitignored)
MUSIC_DIR = Path("music")       # lagu royalty-free (taruh sendiri) → di-acak per reel


def _pick_music() -> str | None:
    """Acak 1 lagu dari music/ (mp3/m4a/wav). None kalau folder kosong → reel senyap."""
    if not MUSIC_DIR.is_dir():
        return None
    tracks = [p for p in MUSIC_DIR.iterdir()
              if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg")]
    return str(random.choice(tracks)) if tracks else None


def _music_credit(path: str) -> str:
    """Baris kredit CC-BY buat track Kevin MacLeod (wajib di caption reel)."""
    title = Path(path).stem.replace("-", " ").replace("_", " ").title()
    return f"🎵 Musik: \"{title}\" — Kevin MacLeod (incompetech.com) · Lisensi CC BY 4.0"


def _load_history() -> list[str]:
    if HISTORY.exists():
        try:
            return [str(h) for h in json.loads(HISTORY.read_text(encoding="utf-8")) if h]
        except Exception:
            return []
    return []


def _save_history(hooks: list[str]) -> None:
    HISTORY.write_text(json.dumps(hooks[-200:], ensure_ascii=False, indent=2), encoding="utf-8")


def _recent_categories(out_root: Path, limit: int = 4) -> list[str]:
    """Kategori yang baru dipakai → biar mode 'Bebas' gak ngulang topik yang sama."""
    cats: list[str] = []
    for root in (Path("published"), out_root):
        if not root.exists():
            continue
        for d in sorted(root.iterdir(), reverse=True):
            meta = d / "meta.json"
            if meta.is_file():
                try:
                    c = str(json.loads(meta.read_text(encoding="utf-8")).get("category", "")).strip()
                except Exception:
                    c = ""
                if c:
                    cats.append(c)
    seen, out = set(), []
    for c in cats:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:limit]


def _recent_hooks(out_root: Path, limit: int = 40) -> list[str]:
    """Recent hooks so Claude doesn't repeat itself (history.json + out/ + published/)."""
    hooks: list[str] = list(_load_history())
    # committed published metas = persistent cross-run dedup (survives CI fresh checkout)
    for root in (Path("published"), out_root):
        if not root.exists():
            continue
        for d in sorted(root.iterdir(), reverse=True):
            meta = d / "meta.json"
            if not meta.is_file():
                continue
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                hooks.append(m.get("hook") or m.get("fact") or "")
            except Exception:
                continue
    # de-dup, keep order, drop empties
    seen, out = set(), []
    for h in hooks:
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out[:60]


_STOP = set((
    "yang kamu kita gue gua lo lu kau ini itu ada bisa akan udah sudah lagi juga buat untuk "
    "dengan dari pada ke di dan atau tapi saat hari pagi siang sore malam lebih paling banget "
    "the a an is are of in on to bikin jadi gak nggak tak tetap masih para ribu juta"
).split())


def _norm_words(s: str) -> set:
    import re
    return set(w for w in re.findall(r"[a-z0-9]+", (s or "").lower())
               if len(w) > 2 and w not in _STOP)


def _acronyms(s: str) -> set:
    """Akronim kapital (IHSG, BBM, MBG, KPK, TNI, DPR...) = biasanya SUBJEK berita."""
    import re
    return set(w.lower() for w in re.findall(r"\b[A-Z]{3,}\b", s or ""))


def _is_dup(hook: str, recent: list[str], thresh: float = 0.5) -> bool:
    """True kalau `hook` mirip salah satu post lama. 2 sinyal:
    1. share AKRONIM subjek yang sama (IHSG vs IHSG) → dobel walau kalimat beda.
    2. overlap kata penting tinggi ('Madu...3.000 tahun' vs 'Madu...bisa 3.000 tahun')."""
    hw = _norm_words(hook)
    ha = _acronyms(hook)
    if len(hw) < 2:
        return False
    for r in recent:
        if ha and (ha & _acronyms(r)):     # subjek akronim sama = dobel (mis. IHSG 2x)
            return True
        rw = _norm_words(r)
        if not rw:
            continue
        inter = len(hw & rw)
        union = len(hw | rw) or 1
        if inter >= 4 or inter / union >= thresh:
            return True
    return False


def main() -> int:
    load_dotenv()
    now = datetime.now(WIB)
    out_root = Path("out")
    out_dir = out_root / now.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    category = os.environ.get("CATEGORY", "").strip().lower() or None
    topic = os.environ.get("TOPIC", "").strip() or None

    print("[1/3] Generating fakta with Claude...")
    recent = _recent_hooks(out_root)

    def _gen(av):
        """1 kali generate (berita kalau kategori berita, else evergreen). Selalu balikin dict."""
        if category in NEWS_CATEGORIES:
            try:
                from fakta_news import generate_news
                foc = f" — fokus topik '{topic}'" if topic else ""
                print(f"      mode BERITA (verifikasi search engine) — kategori {category}{foc}...")
                return generate_news(category, avoid=av, topic=topic or None)
            except Exception as exc:
                print(f"      (berita gagal: {exc}) → fallback ke fakta evergreen")
        fb_cat = None if category in NEWS_CATEGORIES else category
        return generate_fakta(category=fb_cat, avoid=av, topic=topic,
                              avoid_categories=_recent_categories(out_root))

    # GUARD ANTI-DOBEL (level kode): kalau hook mirip post lama → REGENERATE, gak jadi di-upload.
    # Di-skip kalau owner maksa topik spesifik (emang mau topik itu).
    fakta = None
    av = list(recent)
    for attempt in range(3):
        cand = _gen(av)
        if cand is None:
            continue
        if topic or not _is_dup(cand.get("hook", ""), recent):
            fakta = cand
            break
        print(f"      ⚠️ DOBEL: '{cand['hook']}' mirip post lama → regenerate ({attempt + 1}/3)")
        av = av + [cand.get("hook", "")]   # tolak yang mirip, masukin ke avoid biar gak ngulang
        fakta = cand                       # simpan terakhir sbg fallback kalau 3x tetap mirip
    if fakta is None:
        raise RuntimeError("gagal generate konten")
    print(f"      → [{fakta['category']}] {fakta['hook']}")
    if fakta.get("_published"):
        print(f"      🕒 berita terbit: {fakta['_published']}")
    _save_history(_load_history() + [fakta["hook"]])

    # FOTO ASLI berita (og:image dari sumber) → carousel & reel sesuai kejadian asli.
    # Ambil BEBERAPA foto asli (dari banyak artikel sumber) → tiap slide tetap nyambung berita,
    # bukan cuma slide 1. Fakta evergreen = kosong (nanti pakai stok/kosmik).
    hero_imgs: list[str] = []
    img_urls: list[str] = []
    if fakta.get("_image_url"):
        img_urls.append(fakta["_image_url"])
    for u in (fakta.get("_source_urls") or []):
        try:
            from fakta_news import _og_image
            oi = _og_image(u)
            if oi and oi not in img_urls:
                img_urls.append(oi)
        except Exception:
            pass
    for i, u in enumerate(img_urls[:4]):
        try:
            from media_fetcher import download_image
            hero_imgs.append(download_image(u, str(out_dir / f"news_{i}.jpg")))
        except Exception:
            continue
    hero: str | None = hero_imgs[0] if hero_imgs else None
    if hero_imgs:
        print(f"      ✓ {len(hero_imgs)} FOTO ASLI berita (sumber: {fakta.get('_sumber', '?')}) → semua slide")
    elif fakta.get("_image_url"):
        print("      (download foto asli gagal) → pakai stok/kosmik")

    # Optional topic media from Pexels (free, legal). Falls back to cosmic bg.
    photos: list[str] = []
    video_paths: list[str] = []
    query = fakta.get("query") or fakta["category"]
    if os.environ.get("PEXELS_API_KEY"):
        from media_fetcher import fetch_photos, fetch_videos
        try:
            photos = fetch_photos(query, str(out_dir), count=3)
            print(f"      photo bg: {len(photos)} foto ({query})")
        except Exception as exc:
            print(f"      (photo fetch gagal: {exc}) → pakai kosmik")
        try:
            video_paths = fetch_videos(query, str(out_dir))
            print(f"      video bg: {len(video_paths)} klip ({query})")
        except Exception as exc:
            print(f"      (video fetch gagal: {exc}) → skip reel")
    else:
        print("      (PEXELS_API_KEY belum di-set → background kosmik, no reel)")

    # 1 foto per slide. FOTO ASLI berita diutamakan di SEMUA slide (kalau ada >1 sumber → variasi;
    # kalau cuma 1 → diulang). Stok cuma dipakai kalau gak ada foto asli sama sekali (fakta evergreen).
    def _slide_bg(i: int):
        if hero_imgs:
            return hero_imgs[i] if i < len(hero_imgs) else hero_imgs[0]
        if photos:
            return photos[i] if i < len(photos) else photos[0]
        return None
    p1, p2, p3 = _slide_bg(0), _slide_bg(1), _slide_bg(2)

    print("[2/3] Composing carousel...")
    src = fakta.get("_sumber") or None
    compose_cover(fakta["hook"], fakta["category"], str(out_dir / "post_1.jpg"), bg_path=p1,
                  highlight=fakta.get("highlight"), source=src)
    compose_fact(fakta["fact"], fakta["detail"], str(out_dir / "post_2.jpg"), bg_path=p2, source=src)
    compose_outro(fakta["takeaway"], str(out_dir / "post_3.jpg"), bg_path=p3)
    (out_dir / "caption.txt").write_text(fakta["caption"], encoding="utf-8")

    # VIDEO kejadian asli (yt-dlp dari sumber publik) — PALING diutamakan buat reel berita.
    # Best-effort: kalau gagal (YouTube blokir CI / link gak ada) → fallback foto/stok.
    news_vid: str | None = None
    vurl = fakta.get("_video_url")
    if vurl:
        try:
            from news_video import fetch_news_video
            news_vid = fetch_news_video(vurl, str(out_dir), max_sec=18)
            print(f"      ✓ VIDEO kejadian ASLI (via {fakta.get('_sumber', '?')}) — {vurl[:55]}")
        except Exception as exc:
            print(f"      (download video berita gagal: {exc}) → fallback foto/stok")

    # prioritas reel: video asli > foto asli (Ken Burns) > stok video
    reel_bg = video_paths
    if hero:
        try:
            from fakta_video_maker import image_to_clip
            clip = image_to_clip(hero, str(out_dir / "news_clip.mp4"), dur=20)
            reel_bg = [clip]
            print("      reel pakai FOTO ASLI berita (zoom pelan)")
        except Exception as exc:
            print(f"      (bikin klip dari foto berita gagal: {exc}) → stok video")
    if news_vid:
        reel_bg = [news_vid]

    if reel_bg:
        print("      Composing reel...")
        try:
            from fakta_video_maker import make_reel_overlay, render_reel
            main_ov, fact_ov, detail_ov = make_reel_overlay(
                fakta["hook"], fakta["category"], fakta["fact"],
                str(out_dir / "reel_main.png"), str(out_dir / "reel_fact.png"),
                str(out_dir / "reel_detail.png"), detail=fakta.get("detail", ""),
            )
            music = _pick_music()
            render_reel(reel_bg, main_ov, fact_ov, str(out_dir / "reel.mp4"),
                        seg=10, max_segments=2, fact_at=1.5,
                        detail_png=detail_ov, detail_at=10, music=music)
            # caption khusus reel = caption + KREDIT video (kalau pakai footage asli) + kredit musik
            extra = []
            if news_vid and fakta.get("_sumber"):
                extra.append(f"🎥 Video: via {fakta['_sumber']}")
            if music:
                extra.append(_music_credit(music))
            if extra:
                (out_dir / "caption_reel.txt").write_text(
                    fakta["caption"] + "\n\n" + "\n".join(extra), encoding="utf-8")
            src_tag = "VIDEO asli" if news_vid else ("FOTO asli" if hero else "stok")
            tag = f", musik: {Path(music).name}" if music else ", senyap"
            print(f"      → reel.mp4 (20s, bg: {src_tag}{tag})")
        except Exception as exc:
            print(f"      (reel gagal: {exc})")

    meta = {
        "id": out_dir.name,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "category": fakta["category"],
        "hook": fakta["hook"],
        "fact": fakta["fact"],
        "sumber": fakta.get("_sumber", ""),
        "tanggal_berita": fakta.get("_published", ""),
        "foto_asli": bool(hero),
        "video_asli": bool(news_vid),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[3/3] Done → {out_dir}")
    print("      Slides: post_1.jpg (cover) · post_2.jpg (fakta) · post_3.jpg (outro)")
    print("      Caption: caption.txt")
    if os.environ.get("DRY_RUN", "true").lower() != "true":
        print("      (Upload IG belum diaktifkan — post manual atau wire ke instagram_uploader.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
