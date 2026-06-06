"""Use Claude to generate one surprising-but-true 'fakta unik' for the page."""
import json
import os

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Kamu bikin SATU 'fakta unik' yang mengejutkan TAPI BENAR, dalam Bahasa Indonesia, untuk halaman Instagram bertema rasa penasaran (curiosity page).

Keluarkan STRICT JSON saja (tanpa markdown, tanpa komentar):
{
  "category": salah satu dari: sains | sejarah | tubuh | hewan | luarangkasa | teknologi,
  "hook": "...",      // teaser cover — klaim mengejutkannya, 5-11 kata, bikin orang berhenti scroll. JANGAN pakai 'Tau gak sih' (sudah ada di template).
  "fact": "...",      // 1 kalimat inti fakta, jelas & spesifik (boleh pakai angka)
  "detail": "...",    // 1-2 kalimat kenapa/bagaimana, bahasa simpel
  "takeaway": "...",  // 1 kalimat penutup ringan/witty/relatable
  "caption": "...",   // caption IG lengkap (lihat aturan caption)
  "query": "..."      // 1-3 kata kunci BAHASA INGGRIS untuk cari foto/video stock yang relevan & visual (mis. "honey", "honeycomb jar", "galaxy stars"). Pilih yang gampang ada di stock + sesuai topik.
}

Aturan konten:
- WAJIB benar & bisa diverifikasi. DILARANG mitos, hoaks, atau 'fakta' palsu yang beredar di internet.
- Pilih yang benar-benar bikin 'wah', BUKAN yang umum diketahui (hindari hal yang semua orang sudah tahu).
- Bahasa Indonesia santai, gaya anak muda, jelas. Istilah teknis berat harus dijelaskan singkat.
- Kalau ada angka/nama/tahun spesifik, sebutkan — lebih kredibel.

Aturan caption:
- Baris 1 = hook. Lalu jelaskan faktanya 2-3 kalimat. Tutup dengan 1 pertanyaan yang ngajak komen.
- Baris terakhir = tepat 8 hashtag dalam 1 baris: campur #faktaunik #taugaksih #faktamenarik dengan tag spesifik topik.
- Maks ~700 karakter sebelum hashtag. Emoji maks 2."""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)


def generate_fakta(category: str | None = None, avoid: list[str] | None = None) -> dict:
    """Return {category, hook, fact, detail, takeaway, caption}."""
    cat_line = (
        f"Kategori: {category}."
        if category
        else "Kategori: bebas — pilih yang paling menarik & beragam."
    )
    avoid_line = ""
    if avoid:
        joined = "; ".join(a for a in avoid if a)[:1200]
        if joined:
            avoid_line = f"\n\nJANGAN ulangi atau mirip dengan fakta yang sudah pernah dibahas ini: {joined}"

    message = _client().messages.create(
        model=MODEL,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Buat satu fakta unik baru. {cat_line}{avoid_line}"}],
    )
    data = _parse_json(message.content[0].text)

    return {
        "category": str(data.get("category", "")).strip().lower() or "sains",
        "hook": str(data.get("hook", "")).strip(),
        "fact": str(data.get("fact", "")).strip(),
        "detail": str(data.get("detail", "")).strip(),
        "takeaway": str(data.get("takeaway", "")).strip(),
        "caption": str(data.get("caption", "")).strip(),
        "query": str(data.get("query", "")).strip(),
    }
