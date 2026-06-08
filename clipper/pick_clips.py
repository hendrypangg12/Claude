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

Aturan JUDUL/HOOK + KREDIT CREATOR (WAJIB):
- "title" = kalimat HOOK scroll-stopping yang DIMULAI dengan handle creator, lalu koma, lalu
  framing NARATIF-DRAMATIS yang ngerangkum momen + dampaknya yang bikin penasaran/serem/kaget.
  WAJIB sebut creator (kredit). FORMAT: "@creator , [framing naratif dramatis + dampak]".
  Gaya naratif kayak headline (boleh: "yang menemukan...", "kini bisa dipakai untuk...",
  "ngebongkar...", "bikin geger karena..."). Boleh tambah penekanan emosi (Serem banget, GILA, Parah).
  Contoh gaya (TIRU vibe-nya, sesuaikan isi video):
    "@realmrbert , konten kreator yang nemu 'kejahatan baru' lewat WiFi — kini bisa dipakai buat
     melacak aktivitas orang di dalam rumah / di balik dinding. Serem banget"
    "@realmrbert , bongkar kenapa justru orang desa yang paling kena dampak dolar naik"
  10-22 kata, naratif, scroll-stopping. WAJIB tetap sesuai isi transkrip (jangan ngarang fakta).
- Kalau handle creator gak dikasih/gak jelas, bikin hook biasa tanpa maksa nyebut handle.

Keluarkan STRICT JSON saja (tanpa markdown, tanpa komentar):
{"clips":[
  {
    "start_sec": 0.0,
    "end_sec": 0.0,
    "score": 85,                 // taksiran potensi viral 1-100
    "title": "...",              // HOOK naratif + sebut creator (lihat aturan di atas)
    "hook": "...",               // versi super pendek 3-7 kata
    "why": "...",                // 1 kalimat kenapa ini berpotensi viral
    "caption": "..."             // caption IG/TikTok lengkap utk @faktaviral.idn:
                                 //   baris 1 = hook (sebut creator), 1-2 kalimat isi,
                                 //   KREDIT creator ("Video: @creator"),
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
        clips.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "score": int(c.get("score", 0) or 0),
            "title": str(c.get("title", "")).strip(),
            "hook": str(c.get("hook", "")).strip(),
            "why": str(c.get("why", "")).strip(),
            "caption": str(c.get("caption", "")).strip(),
        })
    clips.sort(key=lambda x: x["score"], reverse=True)
    return clips[:num_clips]
