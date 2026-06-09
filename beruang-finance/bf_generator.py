"""Pakai Claude buat bikin 1 konten 'Beruang Finance' (tips / berita / lucu keuangan)."""
import json
import os
import re

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

# Poppins gak punya glyph emoji → bersihin dari teks yang DIGAMBAR (caption tetap boleh)
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⌀-⏿️]"
)


def _no_emoji(t: str) -> str:
    return re.sub(r"\s{2,}", " ", _EMOJI.sub("", t)).strip()

SYSTEM_PROMPT = """Kamu content creator untuk halaman Instagram keuangan Indonesia "Beruang Finance" (gaya santai, relatable, anak muda — tagline "Melek duit, pelan-pelan").

Keluarkan STRICT JSON saja (tanpa markdown, tanpa komentar):
{
  "type": "tips" | "berita" | "lucu",
  "kicker": "...",      // label kecil di atas hook, mis. "TIPS HARI INI" / "KAMU HARUS TAU" / "RELATABLE BANGET"
  "hook": "...",        // judul cover, 5-11 kata, bikin berhenti scroll. JANGAN pakai tanda kutip.
  "points": ["...","...","..."],  // 3 poin isi (tips=3 langkah; berita=3 fakta/dampak; lucu=3 momen relatable). Tiap poin PADAT & PENDEK: MAKS ~14 kata (idealnya <12), langsung ke intinya. JANGAN bertele-tele — biar muat & kebaca di slide.
  "takeaway": "...",    // 1 kalimat penutup witty/memotivasi
  "caption": "...",     // caption IG lengkap (lihat aturan)
  "query": "..."        // 1-2 kata BAHASA INGGRIS = subjek visual buat stock photo (mis. "saving money", "wallet", "rupiah cash", "piggy bank", "stock chart"). Konkret & umum ada di stock.
}

Aturan konten per type:
- "tips": tips keuangan PRAKTIS yang bisa langsung dipakai (nabung, atur gaji, hindari boros, dana darurat, investasi pemula). Harus actionable, bukan teori.
- "berita": isu/tren keuangan yang relevan, DIJELASKAN secara umum & evergreen (mis. "kenapa rupiah bisa melemah", "apa itu inflasi", "kenapa harga emas naik"). DILARANG angka real-time/hari ini (kurs/harga/skor) — kamu gak punya data live, nanti salah. Fokus ke konsep yang selalu benar.
- "lucu": konten relatable/lucu soal duit (tanggal tua, gaji numpang lewat, racun checkout, dompet kering) — bikin orang ngakak & tag temen. Tetap nyelipin 1 insight kecil.

Aturan umum:
- Bahasa Indonesia santai, gaya anak muda, jelas. Sapა "kamu".
- WAJIB akurat. DILARANG hoaks atau angka live yang gampang basi.
- Hook scroll-stopping, relatable, atau bikin penasaran.

Aturan caption:
- Baris 1 = hook. Lalu jelasin isinya 2-3 kalimat (boleh sebut poin-poinnya).
- Tutup dengan ajakan engagement (tag temen / komen / save).
- Baris terakhir = MAKSIMAL 5 hashtag 1 baris (JANGAN lebih dari 5): campur #keuangan #tipskeuangan #melekfinansial dengan tag spesifik.
- Maks ~700 karакter sebelum hashtag. Emoji maks 3."""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)


def generate_content(ctype: str | None = None, topic: str | None = None,
                     avoid: list[str] | None = None) -> dict:
    """Return {type, kicker, hook, points[], takeaway, caption, query}."""
    if topic:
        line = f"Buat konten SPESIFIK tentang: {topic}. Pilih sudut paling menarik, tetap akurat."
    elif ctype:
        line = f"Buat konten type: {ctype}."
    else:
        line = "Pilih type bebas (tips/berita/lucu) — yang paling menarik & beragam."
    avoid_line = ""
    if avoid:
        joined = "; ".join(a for a in avoid if a)[:1200]
        if joined:
            avoid_line = f"\n\nJANGAN ulangi/mirip konten yang sudah pernah dibahas: {joined}"

    msg = _client().messages.create(
        model=MODEL,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Buat satu konten baru. {line}{avoid_line}"}],
    )
    data = _parse_json(msg.content[0].text)
    pts = [_no_emoji(str(p)) for p in (data.get("points") or []) if str(p).strip()]
    return {
        "type": str(data.get("type", "tips")).strip().lower() or "tips",
        "kicker": _no_emoji(str(data.get("kicker", ""))) or "BERUANG FINANCE",
        "hook": _no_emoji(str(data.get("hook", ""))),
        "points": [p for p in pts if p][:3],
        "takeaway": _no_emoji(str(data.get("takeaway", ""))),
        "caption": str(data.get("caption", "")).strip(),  # caption boleh emoji
        "query": str(data.get("query", "")).strip() or "money",
    }
