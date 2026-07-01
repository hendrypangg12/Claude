"""Mode HEMAT: ambil berita dari RSS (GRATIS, TANPA Anthropic).

Dipakai daily_fakta.py / bf_daily.py kalau env NO_AI=true → auto-post berita
tanpa biaya API. Output dict-nya kompatibel sama generate_fakta/generate_content.

Gambar diambil langsung dari <enclosure> RSS (foto artikelnya) → kredit "Sumber: X".
"""
import html
import random
import re

import requests
import xml.etree.ElementTree as ET

# Feed RSS gratis (no API key). BANYAK sumber biar tahan kalau 1-2 feed mati/keblok.
FEEDS = {
    "trending": [
        "https://www.cnnindonesia.com/nasional/rss",
        "https://www.antaranews.com/rss/terkini.xml",
        "https://rss.detik.com/index.php/detikcom",
        "https://www.tribunnews.com/rss",
        "https://nasional.sindonews.com/rss",
        "https://www.suara.com/rss/terkini",
        "https://www.cnnindonesia.com/teknologi/rss",
    ],
    "keuangan": [
        "https://www.cnnindonesia.com/ekonomi/rss",
        "https://www.antaranews.com/rss/ekonomi.xml",
        "https://finance.detik.com/rss",
        "https://ekbis.sindonews.com/rss",
        "https://www.suara.com/rss/bisnis",
    ],
    "aktor": [
        "https://www.cnnindonesia.com/hiburan/rss",
        "https://www.antaranews.com/rss/hiburan.xml",
        "https://hot.detik.com/rss",
        "https://www.suara.com/rss/entertainment",
    ],
}

_SRC = {
    "cnnindonesia.com": "CNN Indonesia", "antaranews.com": "ANTARA",
    "kompas.com": "Kompas", "detik.com": "detikcom", "tempo.co": "Tempo",
}

_HDR = {"User-Agent": "Mozilla/5.0 (compatible; FaktaBot/1.0)"}


def _clean(t: str) -> str:
    t = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", t or "", flags=re.S)  # buka CDATA dulu
    return html.unescape(re.sub(r"<[^>]+>", "", t)).strip()


def _src_name(link: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/]+)", link or "")
    host = (m.group(1) if m else "").replace("www.", "")
    for dom, name in _SRC.items():
        if dom in host:
            return name
    return host or "media"


def _img(item) -> str:
    """Foto artikel dari RSS: <enclosure url=>, media:content/thumbnail."""
    enc = item.find("enclosure")
    if enc is not None and enc.get("url"):
        return enc.get("url").strip()
    for tag in ("{http://search.yahoo.com/mrss/}content",
                "{http://search.yahoo.com/mrss/}thumbnail"):
        m = item.find(tag)
        if m is not None and m.get("url"):
            return m.get("url").strip()
    return ""


def _words(s: str) -> set:
    return set(w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 3)


# Tanpa AI gak ada yang nyaring → blokir manual: konten sensitif (bahaya brand/UU ITE)
# + advertorial/iklan (CNN ekonomi banyak Transmart). Item yang match = di-SKIP.
_BLOCK = re.compile(
    r"(bunuh diri|gantung diri|mutilasi|mayat|jenazah|pembunuhan|dibunuh|"
    r"perkosa|pemerkosaan|pelecehan|cabul|mesum|bugil|porno|prostitusi|"
    r"pedofil|bocah tewas|balita tewas|narkoba|sabu|ganja|"
    r"transmart|full day sale|flash sale|diskon|promo|advertorial|harga spesial|"
    r"kupon|giveaway|brand story)", re.I)


def _blocked(title: str, summary: str) -> bool:
    return bool(_BLOCK.search(f"{title} {summary}"))


def _dup(title: str, avoid: list[str]) -> bool:
    tw = _words(title)
    if not tw:
        return False
    for a in avoid or []:
        aw = _words(a)
        if aw and len(tw & aw) >= 4:
            return True
    return False


def _norm(title: str, link: str, summary: str, image: str) -> dict | None:
    title = _clean(title)
    link = (link or "").strip()
    if not title or not link.startswith("http"):
        return None
    if any(x in link for x in ("/video/", "/foto/", "/infografi", "/galeri", "/photo")):
        return None  # skip galeri/video (kita mau artikel teks + 1 foto)
    return {"title": title, "link": link, "summary": _clean(summary),
            "image": (image or "").strip(), "source": _src_name(link)}


def _fetch_feed(url: str) -> list[dict]:
    txt = ""
    for _ in range(2):  # retry sekali kalau feed ngambek
        try:
            r = requests.get(url, timeout=12, headers=_HDR)
            if r.ok and "<item" in r.text:
                txt = r.text
                break
        except Exception:
            pass
    if not txt:
        return []
    out: list[dict] = []
    # 1) parser XML normal
    try:
        root = ET.fromstring(txt)
        for it in root.iter("item"):
            n = _norm(it.findtext("title"), (it.findtext("link") or ""),
                      it.findtext("description"), _img(it))
            if n:
                out.append(n)
    except Exception:
        out = []
    # 2) fallback REGEX (kalau XML rusak / entity aneh spt Tempo)
    if not out:
        for m in re.finditer(r"<item\b[^>]*>(.*?)</item>", txt, re.S | re.I):
            b = m.group(1)

            def g(tag):
                mm = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", b, re.S | re.I)
                return mm.group(1) if mm else ""

            link = g("link").strip()
            if not link.startswith("http"):
                mm = re.search(r'<link[^>]+href=["\']([^"\']+)', b)
                link = mm.group(1) if mm else ""
            em = (re.search(r'<enclosure[^>]+url=["\']([^"\']+)', b)
                  or re.search(r'url=["\']([^"\']+\.(?:jpg|jpeg|png))', b, re.I))
            n = _norm(g("title"), link, g("description"), em.group(1) if em else "")
            if n:
                out.append(n)
    return out


_OG_RE = [
    re.compile(r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)', re.I),
]


def _og_image(url: str) -> str:
    """Foto ukuran penuh dari halaman artikel (lebih gede dari thumbnail RSS)."""
    try:
        html_ = requests.get(url, timeout=12, headers=_HDR).text[:200000]
        for rx in _OG_RE:
            m = rx.search(html_)
            if m:
                img = m.group(1).strip().replace("&amp;", "&")
                if img.startswith("//"):
                    img = "https:" + img
                if img.startswith("http") and not img.lower().endswith(".svg"):
                    return img
    except Exception:
        pass
    return ""


_SKIP_P = re.compile(
    r"(baca juga|lihat juga|simak juga|saksikan|video pilihan|advertis|adsbygoogle|"
    r"gambas|copyright|all rights|terkait:|berikut ini|halaman selanjutnya)", re.I)


def _article_text(url: str, max_p: int = 6) -> list[str]:
    """Ambil paragraf ISI artikel (biar berita LENGKAP, bukan cuma judul). Tanpa AI."""
    try:
        html_ = requests.get(url, timeout=12, headers=_HDR).text
    except Exception:
        return []
    paras = []
    for m in re.findall(r"<p[^>]*>(.*?)</p>", html_, re.S | re.I):
        t = _clean(m)
        if len(t) < 50 or t.count(" ") < 6 or _SKIP_P.search(t):
            continue
        # buang paragraf yg isinya kode/JS/UI (bukan prosa berita)
        if re.search(r"(function|const |var |let |document\.|window\.|querySelector|=>|"
                     r"addEventListener|cookie|\{|\}|//|;$)", t):
            continue
        paras.append(t)
        if len(paras) >= max_p:
            break
    return paras


def _caption(title: str, body: str, source: str, category: str) -> str:
    tags = {
        "keuangan": "#keuangan #ekonomi #beritaviral #beruangfinance #finansial",
        "aktor": "#selebriti #hiburan #beritaviral #gosip #viral",
    }.get(category, "#beritaviral #faktaviral #beritaterkini #viral #indonesia")
    txt = (body or title).strip()
    if len(txt) > 1000:                        # potong di AKHIR KALIMAT, jangan tengah kata
        cut = txt[:1000]
        p = max(cut.rfind(". "), cut.rfind(".\n"), cut.rfind("!\n"), cut.rfind("?\n"))
        txt = (cut[:p + 1] if p > 400 else cut.rsplit(" ", 1)[0] + "…")
    return f"{title}\n\n{txt}\n\nSumber: {source}\n\n{tags}"


def _points(summary: str, title: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", summary or "")
    pts = [p.strip() for p in parts if len(p.strip()) > 15][:3]
    return pts or [summary.strip() or title]


def fetch_rss_item(category: str = "trending", avoid: list[str] | None = None) -> dict:
    """Ambil 1 berita FRESH dari RSS (skip yang mirip avoid). Tanpa Anthropic.
    Output kompatibel dgn generate_fakta + generate_content (beruang)."""
    cat = category if category in FEEDS else "trending"
    items: list[dict] = []
    seen = set()
    for feed in FEEDS[cat]:
        for it in _fetch_feed(feed):
            key = it["title"][:60].lower()
            if key not in seen:
                seen.add(key)
                items.append(it)
    if not items:
        raise RuntimeError(f"RSS kosong untuk kategori '{cat}'")

    # buang konten sensitif + iklan + galeri foto/video (isinya tipis)
    safe = [it for it in items
            if not _blocked(it["title"], it["summary"])
            and not re.match(r"\s*(FOTO|VIDEO|INFOGRAFI|GALERI)\b", it["title"], re.I)]
    pool = (safe or items)[:20]
    random.shuffle(pool)   # ACAK sumber biar gak ANTARA/CNN terus — variasi media
    pick = next((it for it in pool if not _dup(it["title"], avoid or [])), pool[0])
    title, summary, source = pick["title"], pick["summary"], pick["source"]
    image = _og_image(pick["link"]) or pick["image"]   # og:image (full) dulu, enclosure cadangan
    # AMBIL ISI ARTIKEL LENGKAP (bukan cuma judul) → berita gak setengah2
    paras = _article_text(pick["link"]) or ([summary] if summary else [title])
    fact = paras[0][:260]
    detail = " ".join(paras[1:3])[:340] if len(paras) > 1 else paras[0][260:560]
    body = "\n\n".join(paras[:6])   # caption: berita lebih lengkap (s/d 6 paragraf)
    pts = [p[:150] for p in paras[:3]] if len(paras) >= 2 else _points(summary, title)
    return {
        "category": cat,
        "hook": title,
        "fact": fact,
        "detail": detail,
        "takeaway": "Sumber lengkap ada di caption.",
        "caption": _caption(title, body, source, cat),
        "query": " ".join(re.findall(r"[A-Za-z]+", title)[:2]) or "news",
        # buat beruang (carousel 3 poin)
        "kicker": "BERITA",
        "type": "berita",
        "points": pts,
        # metadata
        "_sumber": source,
        "_published": "",
        "_video_url": "",
        "_image_url": image,
        "_image_article": pick["link"],
        "_source_urls": [pick["link"]],
        "_via": "rss",
    }
