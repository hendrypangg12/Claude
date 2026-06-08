"""Use Claude to generate one surprising-but-true 'fakta unik' for the page."""
import json
import os

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Kamu bikin SATU 'fakta unik' yang mengejutkan TAPI BENAR, dalam Bahasa Indonesia, untuk halaman Instagram bertema rasa penasaran (curiosity page).

Keluarkan STRICT JSON saja (tanpa markdown, tanpa komentar):
{
  "category": pilih SATU yang paling pas (huruf kecil, tanpa spasi): sains | sejarah | tubuh | otak | psikologi | hewan | laut | serangga | dinosaurus | tumbuhan | luarangkasa | teknologi | internet | geografi | negara | alam | cuaca | makanan | kuliner | kesehatan | olahraga | hiburan | musik | budaya | bahasa | ekonomi | uang | rekor | misteri | transportasi | bangunan | militer,
  "hook": "...",      // teaser cover — klaim mengejutkannya, 5-11 kata, bikin orang berhenti scroll. JANGAN pakai 'Tau gak sih' (sudah ada di template).
  "fact": "...",      // 1 kalimat inti fakta, jelas & spesifik (boleh pakai angka)
  "detail": "...",    // 1-2 kalimat kenapa/bagaimana, bahasa simpel
  "takeaway": "...",  // 1 kalimat penutup ringan/witty/relatable
  "caption": "...",   // caption IG lengkap (lihat aturan caption)
  "query": "..."      // 1-2 kata BAHASA INGGRIS = SUBJEK VISUAL UTAMA fakta, yang umum ada di stock (mis. "octopus", "honey", "human brain", "volcano"). HINDARI frase panjang/abstrak — makin simpel & konkret, makin pas videonya.
}

Aturan konten:
- VIRAL DULUAN: pilih fakta dengan potensi viral TINGGI — yang bikin orang langsung "HAH, SERIUS?!", pengen tag temen, share, atau save. DILARANG fakta kering/textbook yang ngebosenin.
- Yang paling nampol (prioritaskan): counterintuitive (kebalik dari yang orang kira) · relatable ke kebiasaan sehari-hari ("hal yang lo lakuin tiap hari ternyata...") · bikin merinding/ngakak/kagum · angka yang gak masuk akal · mitos populer yang ternyata SALAH.
- BEBAS dari SEGALA bidang: sains, sejarah, tubuh manusia, hewan, luar angkasa, teknologi, geografi, makanan, ekonomi/uang, rekor dunia, budaya, alam — apa aja yang bikin "wah".
- WAJIB benar & bisa diverifikasi. DILARANG mitos, hoaks, atau 'fakta' palsu yang beredar di internet. (Viral TAPI tetap akurat — jangan korbankan kebenaran demi sensasi.)
- WAJIB EVERGREEN (tetap benar kapan pun). DILARANG fakta yang butuh angka real-time / berubah-ubah — mis. kurs/harga "hari ini", "saat ini", rekor "terbaru", skor terkini. Kamu TIDAK punya data live, jadi angka begitu bisa salah/kadaluarsa. (Boleh: fakta sejarah/permanen, mis. "mata uang dengan inflasi tertinggi dalam sejarah", "kota terpadat di dunia".)
- Pilih yang benar-benar bikin 'wah', BUKAN yang umum diketahui (hindari hal yang semua orang sudah tahu).
- Bahasa Indonesia santai, gaya anak muda, jelas. Istilah teknis berat harus dijelaskan singkat.
- Kalau ada angka/nama/tahun spesifik (yang sifatnya tetap), sebutkan — lebih kredibel.

Aturan caption:
- Baris 1 = hook yang scroll-stopping (bikin penasaran/kaget). Lalu jelaskan faktanya 2-3 kalimat.
- Tutup dengan ajakan ENGAGEMENT: tag temen / komen / save — pilih yang paling pas (mis. "Tag temen yang belum tau ini 👇", "Save dulu, ntar lupa", "Percaya gak?").
- Baris terakhir = MAKSIMAL 5 hashtag dalam 1 baris (JANGAN lebih dari 5): campur #faktaunik #taugaksih #faktamenarik dengan tag spesifik topik.
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


def generate_fakta(category: str | None = None, avoid: list[str] | None = None,
                   topic: str | None = None, avoid_categories: list[str] | None = None) -> dict:
    """Return {category, hook, fact, detail, takeaway, caption, query}."""
    if topic:
        cat_line = (
            f"Buat fakta unik SPESIFIK tentang: {topic}. "
            f"Cari sudut yang paling mengejutkan/viral dari topik itu, tetap 100% benar."
        )
    elif category:
        cat_line = f"Kategori: {category}."
    else:
        cat_line = "Kategori: bebas — pilih yang paling menarik & beragam."
        recent = [c for c in (avoid_categories or []) if c]
        if recent:
            cat_line += (f" WAJIB VARIASI: JANGAN pilih kategori yang baru dipakai "
                         f"({', '.join(recent)}). Pilih bidang yang BEDA dari itu.")
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
