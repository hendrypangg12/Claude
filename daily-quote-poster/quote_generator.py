"""Generate a Folkative-style relatable quote in Bahasa Indonesia."""
import json
import os
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

THEMES = {
    "pagi": [
        "alarm pagi",
        "ngantuk tapi harus kerja",
        "kopi pagi",
        "macet pagi",
        "berangkat kerja",
        "rapat pagi",
        "tagihan dewasa",
        "tidur larut karena overthinking",
        "weekend yang cepat banget",
        "harapan hari Senin vs realita",
    ],
    "siang": [
        "lunch break sebentar banget",
        "lapar tapi gajian masih lama",
        "rapat zoom yang harusnya email",
        "scroll TikTok diem-diem di kantor",
        "ngantuk siang setelah makan",
        "AC kantor terlalu dingin",
        "deadline yang nempel terus",
        "balas chat WA kerjaan",
        "antrian makan siang",
        "bos minta laporan dadakan",
    ],
    "sore": [
        "pulang kerja macet",
        "lihat sunset sambil bengong",
        "rencana gym vs realita rebahan",
        "ngumpul sama temen tapi lewat hp",
        "kuliner kaki lima",
        "nostalgia masa sekolah",
        "lihat bocah main di taman",
        "kangen rumah",
        "drakor binge-watch",
        "weekend plan yang gajadi",
    ],
    "malam": [
        "scroll medsos sampai larut",
        "overthinking sebelum tidur",
        "ngantuk tapi gabisa tidur",
        "kangen seseorang",
        "refleksi hari ini",
        "rencana besok yang ga jelas",
        "lagu sad random masuk playlist",
        "lihat foto lama",
        "doa malam",
        "kasih ucapan terima kasih ke orang baik",
    ],
}

SYSTEM_PROMPT = """You write viral Instagram quote posts in Bahasa Indonesia in the exact style of @folkative.

STYLE RULES (wajib diikuti):
- 1 sampai 3 kalimat pendek. Total max 220 karakter (target 80-180).
- Casual lo-gue ATAU aku-kamu (pilih yang lebih natural untuk topiknya).
- Boleh pakai abbreviation Indonesian populer: bs, kpd, dlm, tp, sm, smga, dr, krn, jg.
- Topik: relatable struggle hidup modern Indonesia. Jangan motivational cliche, jangan religious preaching, jangan politik.
- Hook di kalimat pertama. Bisa: ironi, observasi tajam, atau plot twist.
- Tone: melankolis dengan humor halus, atau jujur-pahit-tapi-relate.

FORMAT OUTPUT — strict JSON only, no markdown, no extra text:
{"text": "kontennya di sini"}

CONTOH STYLE (jangan disalin, cuma referensi):
- "Dewasa itu ketika lo nyalain alarm jam 5:00 tapi lo buat lagi di jam 5:10. Soalnya 10 menit berharga buat merem bentar."
- "Kangen bs nonton drakor 16 episode semalem, skarang nonton 1 episode aja udah ngantuk."
- "Tanggal muda kelaparan, tanggal tua kepenuhan."
- "Mau berterimakasih kpd orang2 yang gak sedarah tp kebaikannya melebihi apapun."

Sekarang tulis SATU quote sesuai theme yang dikasih."""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


def generate_quote(theme: str) -> str:
    """Return a single Folkative-style quote text for `theme`."""
    message = _client().messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Theme: {theme}"}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        data = json.loads(raw)
        text = str(data.get("text", "")).strip()
        if text:
            return text
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    return raw[:220]


CAPTION_SYSTEM_PROMPT = """Beri caption Instagram singkat untuk quote berikut. Aturan:
- Max 1 kalimat pembuka emosional (boleh berupa emoji repeat seperti 😭😭😭 atau 🥲).
- Diikuti 5 hashtag relevan satu baris (mix #quotesindonesia #relatable + topik specifik).
- Hindari spam tag yang tidak relate.
Format output: plain text, no JSON, no markdown.
"""


def generate_caption(quote_text: str, theme: str) -> str:
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=200,
        system=CAPTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Quote:\n{quote_text}\n\nTheme: {theme}"}],
    )
    return msg.content[0].text.strip()
