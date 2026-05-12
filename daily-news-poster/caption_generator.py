"""Use Claude to pick the best candidate and generate an Instagram caption."""
import json
import os
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

CAPTION_SYSTEM_PROMPT = """You write engaging Instagram captions in Bahasa Indonesia for a daily news account.

Rules:
- 2-4 short paragraphs, max ~600 characters total before hashtags
- Hook in the first line (a question, surprising fact, or strong statement)
- Neutral, factual tone — no clickbait, no political bias
- If the source article is in English, translate the substance to Bahasa Indonesia naturally
- End with exactly 5 relevant hashtags on one line (mix of #beritaterkini #infoterbaru with topic-specific tags)
- Do NOT include the article URL
- Do NOT use emoji unless it genuinely fits the topic (max 2)"""

PICK_SYSTEM_PROMPT_BASE = """You are an editor for the Indonesian Instagram account @berstock.id, focused on bisnis, saham, ekonomi, dan investasi. Given several candidate articles (each shown with how recently it was published), pick the ONE most likely to perform well on Instagram for this slot.

General criteria:
1. FRESHNESS WAJIB: prioritaskan berita yang baru terbit (semakin sedikit menit/jam lalu, semakin baik). Hindari berita lebih dari beberapa jam kecuali memang masih sangat relevan.
2. Relevan untuk audiens Indonesia
3. Visually concrete (bisa di-illustrasikan dengan foto nyata)
4. Avoid: hoaks, gore, politik partisan, berita lokal sangat sempit, teaser tanpa substansi
5. Prefer angka konkret, nama emiten/tokoh, momentum hari ini

Respond with ONLY a JSON object: {"index": <integer 0-based>, "reason": "<short why, in Bahasa Indonesia. Sebutkan umur berita dan kenapa Anda pilih.>"}"""

NICHE_PICK_HINTS = {
    "pagi": (
        "Slot khusus: BERITA PEMERINTAHAN INDONESIA YANG LAGI RAMAI (06:30 WIB).\n"
        "Tugas Anda: cari satu berita PEMERINTAHAN INDONESIA yang paling viral / dibicarakan "
        "pagi ini. Audiens kita pelaku pasar, jadi prioritaskan yang punya implikasi ekonomi/bisnis, "
        "tapi tidak wajib — yang penting topiknya lagi rame.\n\n"
        "PRIORITAS TOPIK (urut):\n"
        "1. Presiden & Istana (kebijakan presiden, pidato, perpres, pengumuman penting)\n"
        "2. Kabinet & Menteri (terutama Kemenkeu/Sri Mulyani, ESDM, BUMN, Perdagangan, Investasi)\n"
        "3. DPR / RUU yang baru saja diproses, terutama yang affect ekonomi atau publik luas\n"
        "4. Bank Indonesia / OJK (BI rate, kebijakan moneter, aturan baru)\n"
        "5. Pemerintah daerah besar (Gubernur DKI, Jabar, dll.) kalau berita lagi viral nasional\n"
        "6. Lembaga negara (KPK, Polri, MK, MA) — kalau lagi rame & substansial\n\n"
        "SINYAL 'LAGI RAMAI':\n"
        "• Muncul di BEBERAPA outlet sekaligus (Detik + Antara + CNN) → kuat\n"
        "• Topik segar (< 6 jam) dengan banyak referensi pejabat/lembaga\n"
        "• Ada angka konkret atau peristiwa baru (bukan analisis lama)\n\n"
        "HINDARI:\n"
        "• Berita pejabat soal kunjungan rutin tanpa substansi\n"
        "• Politik partisan / kampanye / debat pilkada\n"
        "• Berita lokal tanpa dampak nasional\n"
        "• Berita lebih dari 6 jam lalu kalau ada yang lebih segar\n\n"
        "FALLBACK: kalau memang tidak ada berita pemerintahan yang lagi rame pagi ini, "
        "pilih berita ekonomi/bisnis Indonesia paling viral di pool sebagai cadangan.\n\n"
        "Di 'reason' SEBUTKAN: kenapa berita ini lagi ramai (mis. 'muncul di 3 outlet', "
        "'pidato presiden semalam'), umur berita, dan kalau bukan pemerintahan jelaskan kenapa fallback."
    ),
    "saham": "Slot khusus: SAHAM IDX. Pilih berita yang SPESIFIK tentang saham di Bursa Efek Indonesia — emiten BEI, IPO baru, dividend, RUPS, rights issue, stock split, aksi korporasi, kinerja keuangan emiten. Hindari berita ekonomi makro umum tanpa kaitan saham. Prioritaskan freshness (<3 jam).",
    "market": "Slot khusus: MARKET UPDATE SORE. Pilih berita pergerakan pasar hari ini — penutupan IHSG, kurs rupiah, harga emas, BBM, komoditas, atau crypto. Fokus angka konkret, sentimen pasar global yang mempengaruhi Indonesia, dan top gainers/losers. Prioritaskan freshness (<3 jam).",
    "startup": "Slot khusus: STARTUP & BISNIS VIRAL. Pilih berita yang inspiratif/menarik tentang startup Indonesia, founder story, fundraise/investasi, unicorn, UMKM sukses, atau e-commerce. Hindari berita politik atau makro ekonomi yang membosankan.",
    "ai": "Slot khusus: AI & TEKNOLOGI MODEL. Pilih berita tentang artificial intelligence, large language models, atau penerapan AI yang lagi viral. PRIORITAS: rilis/update model besar (OpenAI/ChatGPT, Anthropic/Claude, Google/Gemini, Meta/Llama, DeepSeek), tools AI baru, akuisisi/funding perusahaan AI, AI di perusahaan Indonesia (BUMN, bank, startup lokal pakai AI), regulasi AI di Indonesia, dampak AI ke pekerjaan/profesi, atau drama/kontroversi AI yang lagi rame. Hindari berita gadget biasa, smartphone launch tanpa elemen AI, atau opini tanpa peristiwa konkret. Prioritaskan freshness (<6 jam) dan angka konkret (jumlah user, valuasi, benchmark)."
}


def _pick_prompt(niche: str | None = None) -> str:
    if niche and niche.lower() in NICHE_PICK_HINTS:
        return PICK_SYSTEM_PROMPT_BASE + "\n\n" + NICHE_PICK_HINTS[niche.lower()]
    return PICK_SYSTEM_PROMPT_BASE


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


def pick_best_article(candidates: list[dict]) -> tuple[dict, str]:
    """Ask Claude to choose the most engaging candidate. Returns (article, reason)."""
    if not candidates:
        raise ValueError("No candidates to pick from")
    if len(candidates) == 1:
        return candidates[0], "satu-satunya kandidat"

    niche = os.environ.get("NICHE", "").strip().lower() or None

    def _fmt(i, c):
        age = c.get("age_minutes")
        if age is None:
            age_str = "umur tidak diketahui"
        elif age < 60:
            age_str = f"{age} menit lalu"
        else:
            age_str = f"{age // 60} jam {age % 60} menit lalu"
        return (
            f"[{i}] Sumber: {c['source']} ({age_str})\n"
            f"Judul: {c['title']}\n"
            f"Ringkasan: {c['description'][:300]}"
        )

    listing = "\n\n".join(_fmt(i, c) for i, c in enumerate(candidates))
    message = _client().messages.create(
        model=MODEL,
        max_tokens=300,
        system=_pick_prompt(niche),
        messages=[{"role": "user", "content": f"Kandidat hari ini:\n\n{listing}"}],
    )
    raw = message.content[0].text.strip()
    # Strip code fences if Claude added any.
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        decision = json.loads(raw)
        idx = int(decision["index"])
        reason = decision.get("reason", "")
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Fall back to the first candidate if Claude's response is unparseable.
        return candidates[0], "fallback (parse error)"
    if not (0 <= idx < len(candidates)):
        return candidates[0], "fallback (index out of range)"
    return candidates[idx], reason


def generate_caption(title: str, description: str, source: str) -> str:
    user_prompt = (
        f"Buat caption Instagram untuk berita berikut.\n\n"
        f"Judul: {title}\n"
        f"Ringkasan: {description}\n"
        f"Sumber: {source}"
    )
    message = _client().messages.create(
        model=MODEL,
        max_tokens=600,
        system=CAPTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()


HEADLINE_SYSTEM_PROMPT = """You translate news headlines to Bahasa Indonesia for an Instagram news post overlay.

Rules:
- Output ONLY the translated headline, no quotes, no extra commentary
- Maximum 14 words, ideally 8-12
- Punchy and readable on a square image
- Keep proper nouns (names, places, organizations) as-is
- If the headline is already in good Bahasa Indonesia, lightly tighten it but don't translate"""


def generate_headline_id(title: str) -> str:
    """Return a short Indonesian headline suitable for the image overlay."""
    message = _client().messages.create(
        model=MODEL,
        max_tokens=80,
        system=HEADLINE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": title}],
    )
    return message.content[0].text.strip().strip('"').strip("'")


CAROUSEL_SYSTEM_PROMPT = """You produce text for an Indonesian news Instagram carousel post (3 slides).

Output STRICT JSON with this exact shape:
{
  "points": ["...", "...", "..."],
  "takeaway": "..."
}

Rules:
- "points": exactly 3 short bullets in Bahasa Indonesia, each 8-16 words, factual, no fluff
- Each bullet should stand alone (assume reader didn't see the others)
- "takeaway": 1 sentence summary / why-it-matters in Bahasa Indonesia, 10-20 words
- Tone: neutral, informative, slightly punchy (not sensational)
- No emoji, no hashtags, no quotes around values"""


def generate_carousel_content(title: str, description: str, source: str) -> dict:
    """Return {'points': [3 bullets], 'takeaway': str} for slides 2 and 3."""
    user_prompt = (
        f"Berita:\nJudul: {title}\nRingkasan: {description}\nSumber: {source}"
    )
    message = _client().messages.create(
        model=MODEL,
        max_tokens=400,
        system=CAROUSEL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        data = json.loads(raw)
        points = [str(p).strip() for p in data.get("points", []) if str(p).strip()][:3]
        takeaway = str(data.get("takeaway", "")).strip()
    except (json.JSONDecodeError, KeyError, TypeError):
        points, takeaway = [], ""
    while len(points) < 3:
        points.append("")
    return {"points": points, "takeaway": takeaway or "Simak berita lengkapnya di feed kami."}
