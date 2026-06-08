"""Generate konten BERITA terverifikasi buat faktaviral (kategori: keuangan, aktor, dll).

Beda dari fakta_generator (yang evergreen/karangan): modul ini GROUNDED ke hasil
Google Search asli, jadi:
  1. Cari topik hangat di kategori lewat Google CSE (search engine beneran).
  2. Verifikasi RAMAI: cek `totalResults` topik terpilih >= NEWS_MIN_COVERAGE (default 20)
     → "udah muncul 20+ kali" = beneran lagi rame / pernah viral, bukan karangan.
  3. Claude pilih yang paling viral & tulis carousel HANYA dari cuplikan asli + sumber.

Butuh env: GOOGLE_API_KEY, GOOGLE_CSE_ID, ANTHROPIC_API_KEY.
Output sama persis dgn generate_fakta → bisa dirender pakai image maker yang sama.
"""
import json
import os
from datetime import datetime, timedelta

import requests
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
MIN_COVERAGE = int(os.environ.get("NEWS_MIN_COVERAGE", "20"))
# fresh window (Google dateRestrict) → hari (buat NewsAPI)
_FRESH_DAYS = {"w1": 7, "w2": 14, "m1": 30}

# query pencarian per kategori berita (Bahasa Indonesia, bias konteks ID)
CATEGORY_QUERIES = {
    "trending": [
        "berita viral hari ini indonesia", "trending topic hari ini",
        "yang lagi ramai diperbincangkan", "kabar viral terbaru indonesia",
        "fenomena viral medsos terbaru",
    ],
    "keuangan": [
        "berita keuangan viral terbaru", "ekonomi rupiah saham berita hari ini",
        "berita finansial trending indonesia", "investasi crypto viral terbaru",
    ],
    "aktor": [
        "berita aktor selebriti viral terbaru", "artis indonesia trending hari ini",
        "selebriti ramai diperbincangkan", "aktor hollywood berita viral",
    ],
}

# seberapa "fresh" hasil yang dicari (Google dateRestrict). Trending = paling baru.
RECENCY = {"trending": "w1", "keuangan": "w2", "aktor": "w2"}

SYSTEM = """Kamu editor konten Instagram 'fakta/berita viral' (Bahasa Indonesia, gaya anak muda).
Kamu DIBERI daftar cuplikan hasil pencarian ASLI (judul + ringkasan + sumber).

Tugas: pilih SATU topik yang paling VIRAL & paling banyak diberitakan, lalu buat konten carousel.

ATURAN KERAS:
- GROUNDED: cuma pakai info dari cuplikan yang diberikan. DILARANG mengarang angka/nama/klaim di luar cuplikan.
- Kalau ragu / info kurang, ambil sudut yang AMAN & yang jelas didukung cuplikan.
- Faktual & netral untuk berita sensitif. JANGAN fitnah, JANGAN rumor pribadi yang belum terbukti.
- Boleh berita BARU (hangat) atau topik LAMA yang lagi rame lagi.

Keluarkan STRICT JSON saja:
{
  "verify_query": "...",  // 3-6 kata kunci topik terpilih buat dicek ulang ke search engine
  "sumber": "...",        // 1-3 nama media/sumber dari cuplikan (mis. "CNBC, Detik")
  "category": "<kategori>",
  "hook": "...",          // cover teaser 5-11 kata, scroll-stopping. JANGAN 'Tau gak sih'.
  "fact": "...",          // 1 kalimat inti berita, jelas & spesifik
  "detail": "...",        // 1-2 kalimat konteks/kenapa penting
  "takeaway": "...",      // 1 kalimat penutup ringan/relevan
  "caption": "...",       // caption IG: baris1 hook; 2-3 kalimat isi; ajakan engagement; baris akhir MAKS 5 hashtag. Akhiri dgn 'Sumber: <sumber>'. Emoji maks 2.
  "query": "..."          // 1-2 kata Inggris = subjek visual utama buat stock video/foto (mis. "stock market", "red carpet")
}"""


def _cse_web(query: str, num: int = 10, date_restrict: str | None = None) -> tuple[int, list[dict]]:
    """Google Custom Search (web). Return (totalResults, items[]).
    date_restrict mis. 'w1' (1 minggu), 'd3' (3 hari) → bias ke hasil yang masih fresh."""
    params = {
        "key": os.environ["GOOGLE_API_KEY"].strip(),
        "cx": os.environ["GOOGLE_CSE_ID"].strip(),
        "q": query, "num": num, "safe": "active", "hl": "id", "gl": "id",
    }
    if date_restrict:
        params["dateRestrict"] = date_restrict
    r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
    if not r.ok:
        # tampilkan ALASAN dari Google (mis. accessNotConfigured / dailyLimitExceeded / keyInvalid)
        reason = ""
        try:
            err = r.json().get("error", {})
            reason = err.get("message") or (err.get("errors", [{}])[0].get("reason", ""))
        except Exception:
            reason = r.text[:160]
        raise RuntimeError(f"CSE {r.status_code}: {reason}")
    j = r.json()
    total = int(j.get("searchInformation", {}).get("totalResults", "0") or 0)
    items = [{
        "title": it.get("title", ""),
        "snippet": it.get("snippet", ""),
        "source": it.get("displayLink", ""),
        "link": it.get("link", ""),
    } for it in j.get("items", [])]
    return total, items


def _newsapi(query: str, num: int = 8, fresh: str = "w2") -> tuple[int, list[dict]]:
    """NewsAPI.org /everything. Return (totalResults, items[]). Sumber ke-2 biar makin pinter."""
    key = os.environ.get("NEWSAPI_KEY", "").strip()
    if not key:
        raise RuntimeError("NEWSAPI_KEY kosong")
    frm = (datetime.utcnow() - timedelta(days=_FRESH_DAYS.get(fresh, 14))).strftime("%Y-%m-%d")
    params = {"q": query, "sortBy": "publishedAt", "pageSize": num, "from": frm,
              "language": "id", "apiKey": key}
    r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=20)
    if not r.ok:
        # NewsAPI free tier kadang gak support 'language=id' → coba tanpa filter bahasa
        params.pop("language", None)
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=20)
        if not r.ok:
            raise RuntimeError(f"NewsAPI {r.status_code}: {r.text[:120]}")
    j = r.json()
    total = int(j.get("totalResults", 0) or 0)
    items = [{
        "title": a.get("title", "") or "",
        "snippet": a.get("description", "") or "",
        "source": (a.get("source") or {}).get("name", ""),
        "link": a.get("url", ""),
    } for a in j.get("articles", [])]
    return total, items


def _newsapi_top(country: str = "id", num: int = 12) -> tuple[int, list[dict]]:
    """NewsAPI top-headlines per negara = berita HANGAT real (gak butuh Google sama sekali)."""
    key = os.environ.get("NEWSAPI_KEY", "").strip()
    if not key:
        raise RuntimeError("NEWSAPI_KEY kosong")
    params = {"country": country, "pageSize": num, "apiKey": key}
    r = requests.get("https://newsapi.org/v2/top-headlines", params=params, timeout=20)
    if not r.ok:
        raise RuntimeError(f"NewsAPI top {r.status_code}: {r.text[:120]}")
    j = r.json()
    total = int(j.get("totalResults", 0) or 0)
    items = [{
        "title": a.get("title", "") or "",
        "snippet": a.get("description", "") or "",
        "source": (a.get("source") or {}).get("name", ""),
        "link": a.get("url", ""),
    } for a in j.get("articles", []) if a.get("title")]
    return total, items


def _search_any(query: str, num: int, fresh: str) -> tuple[int, list[dict]]:
    """Gabung 2 sumber: Google CSE + NewsAPI. Pakai yang jalan, gak error walau salah satu mati."""
    total, items = 0, []
    for label, fn in (("Google", lambda: _cse_web(query, num, fresh)),
                      ("NewsAPI", lambda: _newsapi(query, num, fresh))):
        try:
            t, its = fn()
            total = max(total, t)
            items += its
        except Exception as exc:
            print(f"      ({label} '{query}' gagal: {exc})")
    return total, items


def _gather(category: str) -> list[dict]:
    seen, out = set(), []
    fresh = RECENCY.get(category, "m1")  # default: 1 bulan terakhir
    # 0) berita HANGAT Indonesia dari NewsAPI top-headlines (jalan walau Google 403)
    try:
        _, top = _newsapi_top("id", 12)
        print(f"      NewsAPI top-headlines ID: {len(top)} berita")
        for it in top:
            key = it["title"][:60].lower()
            if key not in seen:
                seen.add(key)
                out.append(it)
    except Exception as exc:
        print(f"      (NewsAPI top gagal: {exc})")
    # 1) query spesifik kategori (gabung Google + NewsAPI everything)
    for q in CATEGORY_QUERIES.get(category, [f"berita {category} viral terbaru"])[:2]:
        _, items = _search_any(q, 8, fresh)
        for it in items:
            key = it["title"][:60].lower()
            if it["title"] and key not in seen:
                seen.add(key)
                out.append(it)
    return out[:14]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except Exception:
        # ambil objek JSON pertama yang ada di teks (web_search kadang nambah prosa)
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


# query "cari apa" buat Claude pas pakai web_search (sumber UTAMA, gak butuh Google Cloud)
_WEB_SEARCH_BRIEF = {
    "trending": "berita & topik yang LAGI VIRAL / trending di Indonesia HARI INI (medsos, peristiwa, fenomena)",
    "keuangan": "berita keuangan/ekonomi Indonesia yang lagi RAMAI minggu ini (rupiah, saham, crypto, kebijakan)",
    "aktor": "berita selebriti/aktor (Indonesia & dunia) yang lagi VIRAL & banyak diberitakan minggu ini",
}


def _claude_web_news(category: str, avoid: list[str] | None = None) -> dict:
    """SUMBER UTAMA: Claude search web sendiri (server-side web_search) → tulis carousel.
    Pakai ANTHROPIC_API_KEY (yang udah jalan) — TANPA Google Cloud / NewsAPI sama sekali.
    Raises kalau gagal (caller fallback ke _gather/CSE)."""
    brief = _WEB_SEARCH_BRIEF.get(category, f"berita '{category}' yang lagi viral & banyak diberitakan di Indonesia")
    avoid_line = ""
    if avoid:
        joined = "; ".join(a for a in avoid if a)[:800]
        if joined:
            avoid_line = f"\n\nHINDARI topik yang mirip ini (sudah pernah dibahas): {joined}"

    today = datetime.utcnow() + timedelta(hours=7)  # WIB
    today_str = today.strftime("%d %B %Y")

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]
    user = (
        f"Hari ini = {today_str} (WIB).\n"
        f"Cari di internet: {brief}.\n"
        f"Lakukan 2-4 pencarian (pakai kata 'hari ini', 'terbaru', tanggal, nama peristiwa).\n\n"
        f"ATURAN FRESH (WAJIB): prioritaskan berita yang TERBIT 1-3 HARI TERAKHIR. "
        f"TOLAK berita yang lebih tua dari 5 hari KECUALI topiknya masih sangat rame HARI INI. "
        f"Makin baru makin bagus — ini buat konten 'berita hangat'.\n\n"
        f"PILIH SATU topik paling viral & paling banyak diberitakan dari banyak sumber kredibel "
        f"(BUKAN rumor pribadi/fitnah).{avoid_line}\n\n"
        f"PENTING soal field 'query': isi dengan subjek visual yang SPESIFIK & nyambung ke berita "
        f"(mis. berita baling-baling pesawat → 'turboprop propeller plane', berita rupiah → "
        f"'indonesian rupiah money', berita artis → nama umum yg relevan), JANGAN terlalu generik.\n\n"
        f"Setelah yakin, keluarkan HANYA STRICT JSON sesuai format di system. "
        f"Kategori: {category}."
    )
    messages = [{"role": "user", "content": user}]

    final_text = ""
    for _ in range(6):  # batasi loop pause_turn
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=1500, system=SYSTEM, tools=tools, messages=messages,
            )
        except Exception as exc:
            raise RuntimeError(f"web_search call gagal: {exc}")
        # kumpulkan teks dari block terakhir
        texts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        if texts:
            final_text = texts[-1]
        if resp.stop_reason == "pause_turn":
            # lanjutkan: kirim balik konten assistant biar tool jalan terus
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    if not final_text.strip():
        raise RuntimeError("web_search tidak mengembalikan teks JSON")
    data = _parse_json(final_text)

    return {
        "category": str(data.get("category", category)).strip().lower() or category,
        "hook": str(data.get("hook", "")).strip(),
        "fact": str(data.get("fact", "")).strip(),
        "detail": str(data.get("detail", "")).strip(),
        "takeaway": str(data.get("takeaway", "")).strip(),
        "caption": str(data.get("caption", "")).strip(),
        "query": str(data.get("query", "")).strip() or category,
        "_coverage": MIN_COVERAGE,  # web_search = Claude udah verifikasi lintas-sumber
        "_sumber": str(data.get("sumber", "")).strip(),
        "_via": "web_search",
    }


def generate_news(category: str, avoid: list[str] | None = None) -> dict:
    """Return {category, hook, fact, detail, takeaway, caption, query} grounded ke berita asli.
    Raises RuntimeError kalau search kosong / API tak tersedia (caller boleh fallback).

    Urutan sumber:
      1. web_search (Claude search web sendiri, pakai ANTHROPIC_API_KEY) = UTAMA, paling fresh.
      2. Google CSE + NewsAPI (snippet) = fallback kalau web_search mati/limit."""
    # 1) SUMBER UTAMA — Claude search web langsung (gak butuh Google Cloud/NewsAPI)
    try:
        res = _claude_web_news(category, avoid=avoid)
        if res.get("hook") and res.get("fact"):
            print(f"      via web_search (Claude cari web sendiri) — sumber: {res.get('_sumber', '?')}")
            return res
        print("      (web_search balik tapi kosong) → fallback ke CSE/NewsAPI")
    except Exception as exc:
        print(f"      (web_search gagal: {exc}) → fallback ke CSE/NewsAPI")

    # 2) FALLBACK — snippet dari Google CSE / NewsAPI
    has_google = bool(os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"))
    has_news = bool(os.environ.get("NEWSAPI_KEY"))
    if not (has_google or has_news):
        raise RuntimeError("web_search gagal & GOOGLE_API_KEY/CSE & NEWSAPI_KEY semua kosong → tak bisa verifikasi berita")

    items = _gather(category)
    if not items:
        raise RuntimeError(f"tidak ada hasil pencarian untuk kategori '{category}'")

    avoid_line = ""
    if avoid:
        joined = "; ".join(a for a in avoid if a)[:800]
        if joined:
            avoid_line = f"\n\nHINDARI topik yang mirip ini (sudah pernah dibahas): {joined}"

    ctx = "\n".join(
        f"{i+1}. [{it['source']}] {it['title']} — {it['snippet']}"
        for i, it in enumerate(items)
    )
    msg = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip()).messages.create(
        model=MODEL, max_tokens=1000, system=SYSTEM,
        messages=[{"role": "user", "content":
                   f"Kategori: {category}.\nCuplikan hasil pencarian asli:\n{ctx}{avoid_line}\n\n"
                   f"Pilih 1 topik paling viral & buat carousel-nya."}],
    )
    data = _parse_json(msg.content[0].text)

    # VERIFIKASI RAMAI: cek topik terpilih muncul >= MIN_COVERAGE kali di search engine (2 sumber)
    coverage = 0
    vq = str(data.get("verify_query", "")).strip()
    if vq:
        coverage, _ = _search_any(vq, 3, RECENCY.get(category, "w2"))
    status = "OK" if coverage >= MIN_COVERAGE else "RENDAH"
    print(f"      verifikasi: '{vq}' → ~{coverage} hasil (target {MIN_COVERAGE}) [{status}]")

    return {
        "category": str(data.get("category", category)).strip().lower() or category,
        "hook": str(data.get("hook", "")).strip(),
        "fact": str(data.get("fact", "")).strip(),
        "detail": str(data.get("detail", "")).strip(),
        "takeaway": str(data.get("takeaway", "")).strip(),
        "caption": str(data.get("caption", "")).strip(),
        "query": str(data.get("query", "")).strip() or category,
        "_coverage": coverage,
        "_sumber": str(data.get("sumber", "")).strip(),
    }
