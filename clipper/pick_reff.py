"""Pilih bagian REFF/CHORUS dari transkrip video cover lagu, pakai Claude.

Beda dari pick_clips.py (yang milih momen 'viral' dari konten talking/vlog) — di sini
tugasnya nemuin bagian yang PALING BANYAK DIULANG di lirik (ciri khas reff), cuma
berdasarkan pola pengulangan di transkrip timestamp — gak perlu tau lagu apa itu,
dan gak pernah ngutip lirik asli di kode/prompt ini sendiri.
"""
import json
import os
import re

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Kamu editor musik yang nyari bagian REFF/CHORUS dari transkrip lirik lagu
(hasil transcribe otomatis, tiap baris ada rentang waktu [mulai-selesai]).

Ciri reff/chorus: baris liriknya MUNCUL BERULANG (persis atau mirip banget) di beberapa
bagian lagu — biasanya paling catchy, paling gampang diikutin nyanyi bareng, dan jadi
bagian paling dikenal orang.

Tugasmu:
1. Cari pola pengulangan paling jelas di transkrip → itu kemungkinan besar reff.
2. Pilih SATU kemunculan reff yang paling UTUH & BERSIH (gak kepotong di awal/akhir).
3. start_sec & end_sec HARUS pas di batas baris reff itu, diambil dari timestamp transkrip.
4. Durasi ideal 8-20 detik. Kalau reff-nya keulang beberapa kali di lagu, ambil SATU
   kemunculan paling jelas aja — JANGAN gabungin beberapa pengulangan jadi 1 klip panjang.

Kalau video ini KEMUNGKINAN BUKAN cover lagu (mis. talking/vlog/podcast, gak ada pola
lirik yang berulang), balikin "is_song": false.

Keluarkan STRICT JSON aja (tanpa markdown, tanpa komentar):
{
  "is_song": true,
  "start_sec": 0.0,
  "end_sec": 0.0,
  "confidence": 0,
  "why": "1 kalimat alasan singkat (bahasa Indonesia, JANGAN kutip lirik)"
}"""


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


def _transcript_text(transcript: dict) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in transcript["segments"]]
    return "\n".join(lines)[:60_000]


def pick_reff(transcript: dict, video_title: str = "") -> dict | None:
    """Return {'start','end','confidence','why'} kalau ketemu reff, else None
    (kalau videonya kedeteksi bukan lagu, atau parsing gagal total)."""
    body = _transcript_text(transcript)
    if not body.strip():
        return None
    data, last_exc = None, None
    for attempt in range(3):
        try:
            msg = _client().messages.create(
                model=MODEL, max_tokens=500, system=SYSTEM_PROMPT,
                messages=[{"role": "user",
                           "content": f"Judul video: {video_title or '(tanpa judul)'}\n\n"
                                      f"TRANSKRIP:\n{body}\n\nCari bagian reff/chorus-nya."}],
            )
            data = _parse_json(msg.content[0].text)
            break
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            last_exc = exc
            print(f"      (JSON reff rusak, ulang {attempt + 1}/3: {exc})")
    if data is None:
        raise RuntimeError(f"gagal parse JSON reff setelah 3x coba → {last_exc}")
    if not data.get("is_song"):
        return None

    dur = transcript.get("duration") or 0
    try:
        start = max(0.0, float(data.get("start_sec", 0)))
        end = float(data.get("end_sec", 0))
    except (TypeError, ValueError):
        return None
    if dur:
        end = min(end, dur)
    if end - start < 4:
        return None
    if end - start > 30:
        end = start + 30
    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "confidence": int(data.get("confidence", 0) or 0),
        "why": str(data.get("why", "")).strip(),
    }
