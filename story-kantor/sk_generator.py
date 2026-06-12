"""Generate konten 'Story Kantor' — relatable & sindiran halus dunia kerja (gaya Folkative)."""
import json
import os
import re

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Kamu content creator akun Instagram "Story Kantor" — relatable & sindiran HALUS dunia kerja kantoran Indonesia (gaya santai anak muda, jujur, kadang sarkas tapi gak kasar).

Tema yang boleh: cari muka ke atasan, lembur tanpa apresiasi, gaji numpang lewat, meeting gak penting, drama grup WA kantor, hari Senin, deadline mepet, rekan kerja toxic, butuh kopi, kerja vs hidup, kerja keras kurang dihargai, overthinking soal masa depan/karier, dll.

Keluarkan STRICT JSON saja (tanpa markdown):
{
  "topic": "...",          // tema singkat (mis. "cari muka", "lembur", "gaji")
  "hook": "...",           // STATEMENT UTAMA (slide 1) — relatable/sindiran, 1-3 kalimat, bikin orang "ini gue banget" & pengen tag temen kantor. JANGAN pakai tanda kutip ganda.
  "lines": ["...", "..."], // 2 statement TAMBAHAN senada (slide 2 & 3). Tiap satu berdiri sendiri, 1-2 kalimat, tetap relatable & nyambung temanya.
  "caption": "..."         // caption IG: 1-2 kalimat + ajakan tag temen/komen. Baris terakhir MAKS 5 hashtag (mis. #storykantor #anakkantoran #relatable #duniakerja). Emoji maks 3.
}

Aturan KERAS:
- Bahasa Indonesia santai & relatable. Boleh "gue/lo", "kamu/kita".
- Sindiran HALUS & lucu/jujur — BUKAN menjatuhkan. DILARANG kasar, SARA, ujaran kebencian.
- DILARANG nyebut nama orang asli, nama perusahaan asli, atau tokoh publik. Universal aja.
- Jangan menggurui. Bikin yang bener-bener relatable & shareable."""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip(), max_retries=6)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def generate_content(topic: str | None = None, avoid: list[str] | None = None) -> dict:
    """Return {topic, hook, lines[2], caption}."""
    if topic:
        line = f"Buat konten SPESIFIK tentang: {topic}. Ambil sudut paling relatable."
    else:
        line = "Pilih tema bebas yang lagi relatable banget buat anak kantoran."
    avoid_line = ""
    if avoid:
        joined = "; ".join(a for a in avoid if a)[:1200]
        if joined:
            avoid_line = f"\n\nJANGAN ulangi/mirip yang sudah pernah dibahas: {joined}"

    client = _client()
    user = f"Buat satu konten baru. {line}{avoid_line}"
    data = None
    last_exc: Exception | None = None
    for attempt in range(3):
        msg = client.messages.create(
            model=MODEL, max_tokens=800, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
        )
        try:
            data = _parse_json(msg.content[0].text)
            break
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            last_exc = exc
            print(f"      (JSON konten rusak, ulang {attempt + 1}/3: {exc})")
    if data is None:
        raise RuntimeError(f"gagal parse JSON konten setelah 3x coba → {last_exc}")

    lines = [str(x).strip() for x in (data.get("lines") or []) if str(x).strip()][:2]
    while len(lines) < 2:
        lines.append("")  # jaga-jaga biar selalu ada 3 slide
    return {
        "topic": str(data.get("topic", "")).strip() or "kerja",
        "hook": str(data.get("hook", "")).strip(),
        "lines": lines,
        "caption": str(data.get("caption", "")).strip(),
    }
