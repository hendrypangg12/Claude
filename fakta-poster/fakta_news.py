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

import requests
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
MIN_COVERAGE = int(os.environ.get("NEWS_MIN_COVERAGE", "20"))

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


def _gather(category: str) -> list[dict]:
    seen, out = set(), []
    fresh = RECENCY.get(category, "m1")  # default: 1 bulan terakhir
    # cukup 2 query teratas (hemat kuota Custom Search yg cuma 100/hari)
    for q in CATEGORY_QUERIES.get(category, [f"berita {category} viral terbaru"])[:2]:
        try:
            _, items = _cse_web(q, num=8, date_restrict=fresh)
        except Exception as exc:
            print(f"      (cari '{q}' gagal: {exc})")
            continue
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
    return json.loads(raw)


def generate_news(category: str, avoid: list[str] | None = None) -> dict:
    """Return {category, hook, fact, detail, takeaway, caption, query} grounded ke berita asli.
    Raises RuntimeError kalau search kosong / API tak tersedia (caller boleh fallback)."""
    if not (os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID")):
        raise RuntimeError("GOOGLE_API_KEY/GOOGLE_CSE_ID belum di-set → tak bisa verifikasi berita")

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

    # VERIFIKASI RAMAI: cek topik terpilih muncul >= MIN_COVERAGE kali di search engine
    coverage = 0
    vq = str(data.get("verify_query", "")).strip()
    if vq:
        try:
            coverage, _ = _cse_web(vq, num=3)
        except Exception:
            coverage = 0
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
