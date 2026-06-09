"""Use Claude to pick the most viral-worthy moments from a transcript.

Input: the transcript dict from transcribe.py (segments with timestamps).
Output: a list of clips, each with precise start/end seconds + a ready caption.
"""
import json
import os

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Kamu editor konten viral short-form (TikTok / Reels / YouTube Shorts), kayak Opus Clip,
untuk akun @faktaviral.idn (momen & konten viral harian).
Dikasih TRANSKRIP video panjang dalam format baris: "[mulai-selesai] teks" (mulai & selesai = detik).
Tugasmu: pilih {N} POTONGAN paling berpotensi VIRAL dari video itu.

Kriteria viral (prioritaskan tinggi):
- Hook 3 detik pertama langsung nampar (pertanyaan, klaim berani, angka kaget, plot-twist).
- Ada emosi: lucu, marah, haru, kaget, atau insight yang bikin "oh iya juga ya".
- Quotable / relatable / ada cerita mini yang UTUH.
- HINDARI: basa-basi pembuka, sponsor, ngalor-ngidul, bagian yang butuh konteks panjang.

Aturan potongan (WAJIB):
- Tiap potongan harus berdiri sendiri — paham tanpa nonton bagian lain.
- Mulai PAS di awal kalimat, selesai PAS di akhir kalimat. JANGAN motong di tengah kalimat.
- Durasi 15-60 detik (paling enak 20-45). Boleh gabung beberapa baris berurutan.
- start_sec & end_sec WAJIB ngambil dari rentang timestamp di transkrip. end_sec > start_sec.
- Antar potongan JANGAN tumpang-tindih. Urutkan dari yang paling viral.

Aturan JUDUL HOOK (yang DI-BURN ke video — WAJIB):
- "title" = HOOK PENDEK & PUNCHY gaya CapCut/TikTok yang bikin orang langsung berhenti scroll.
  5-11 kata aja (SINGKAT — ini tampil di kotak putih di video, bukan paragraf).
  Boleh huruf kapital buat penekanan + tanda seru. TANPA EMOJI (emoji taruh di caption aja).
  TANPA nama creator di title (creator udah dikredit di caption + watermark video).
  Contoh gaya (TIRU vibe-nya, sesuaikan isi video):
    "Gilaa!! WIFI bisa dipakai buat CCTV ngintip tetangga"
    "RAHASIA!!! WIFI ternyata bisa tembus tembok"
    "Software ini bisa lacak kamu lewat sinyal WiFi"
  Harus sesuai isi transkrip (jangan ngarang fakta).

Keluarkan STRICT JSON saja (tanpa markdown, tanpa komentar):
{"clips":[
  {
    "start_sec": 0.0,
    "end_sec": 0.0,
    "score": 85,                 // taksiran potensi viral 1-100
    "title": "...",              // HOOK PENDEK punchy 5-11 kata (di-burn ke video, tanpa emoji)
    "hook": "...",               // versi super pendek 3-5 kata
    "why": "...",                // 1 kalimat kenapa ini berpotensi viral
    "emphasis": [0.0],           // 1-4 DETIK (absolut, dari timestamp transkrip) di momen
                                 //   PENEGASAN/PENTING (punchline, angka kaget, kalimat kunci).
                                 //   Kamera bakal ZOOM ke wajah di momen ini. Boleh [] kalau gak ada.
    "caption": "..."             // caption IG/TikTok lengkap utk @faktaviral.idn:
                                 //   baris 1 = hook naratif (boleh sebut @creator + emoji),
                                 //   1-2 kalimat isi, KREDIT creator ("Video: @creator"),
                                 //   ajakan "Follow @faktaviral.idn buat momen viral tiap hari",
                                 //   baris terakhir MAKS 5 hashtag dalam 1 baris.
  }
],"language":"id"}

Pilih TEPAT {N} potongan terbaik (atau lebih sedikit kalau videonya pendek). Bahasa Indonesia santai."""

MAX_TRANSCRIPT_CHARS = 120_000  # ~30k token, cukup buat video ~1.5 jam


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)


def _transcript_text(transcript: dict) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in transcript["segments"]]
    body = "\n".join(lines)
    if len(body) > MAX_TRANSCRIPT_CHARS:
        body = body[:MAX_TRANSCRIPT_CHARS] + "\n...[transkrip dipotong karena terlalu panjang]"
    return body


def pick_clips(transcript: dict, num_clips: int = 4, video_title: str = "",
               creator: str = "") -> list[dict]:
    body = _transcript_text(transcript)
    if not body.strip():
        return []
    sys = SYSTEM_PROMPT.replace("{N}", str(num_clips))
    cred = creator.lstrip("@") if creator else ""
    cred_line = (f"Creator video ini: @{cred} (SEBUT di judul/hook + kredit di caption). "
                 if cred else "Nama creator gak diketahui. ")
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=2500,
        system=sys,
        messages=[{
            "role": "user",
            "content": f"Judul video: {video_title or '(tanpa judul)'}\n{cred_line}\n\n"
                       f"TRANSKRIP:\n{body}\n\nPilih {num_clips} potongan paling viral.",
        }],
    )
    data = _parse_json(msg.content[0].text)
    dur = transcript.get("duration") or 0
    clips = []
    for c in data.get("clips", []):
        try:
            start = max(0.0, float(c["start_sec"]))
            end = float(c["end_sec"])
        except (KeyError, TypeError, ValueError):
            continue
        if dur:
            end = min(end, dur)
        length = end - start
        if length < 6:           # kependekan, skip
            continue
        if length > 90:          # cap 90 detik biar tetap short-form
            end = start + 90
        emph = []
        for e in (c.get("emphasis") or [])[:4]:
            try:
                ev = float(e)
            except (TypeError, ValueError):
                continue
            if start <= ev <= end:        # keep only marks inside this clip
                emph.append(round(ev, 2))
        clips.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "score": int(c.get("score", 0) or 0),
            "title": str(c.get("title", "")).strip(),
            "hook": str(c.get("hook", "")).strip(),
            "why": str(c.get("why", "")).strip(),
            "emphasis": emph,
            "caption": str(c.get("caption", "")).strip(),
        })
    clips.sort(key=lambda x: x["score"], reverse=True)
    return clips[:num_clips]
