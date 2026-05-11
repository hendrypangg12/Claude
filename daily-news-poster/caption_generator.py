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

PICK_SYSTEM_PROMPT = """You are an editor for an Indonesian news Instagram account. Given several candidate articles, pick the ONE most likely to perform well on Instagram today.

Selection criteria, in priority order:
1. Genuinely interesting/surprising/important to a general Indonesian audience
2. Visually concrete (something that can be illustrated with a real image)
3. Avoid: pure politics-bait, gore, deeply local news outside Indonesia, paywalled-feeling teasers
4. Prefer: human interest, tech, science, sports, entertainment, business with clear impact

Respond with ONLY a JSON object: {"index": <integer 0-based>, "reason": "<short why, in Bahasa Indonesia>"}"""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


def pick_best_article(candidates: list[dict]) -> tuple[dict, str]:
    """Ask Claude to choose the most engaging candidate. Returns (article, reason)."""
    if not candidates:
        raise ValueError("No candidates to pick from")
    if len(candidates) == 1:
        return candidates[0], "satu-satunya kandidat"

    listing = "\n\n".join(
        f"[{i}] Sumber: {c['source']}\nJudul: {c['title']}\nRingkasan: {c['description'][:300]}"
        for i, c in enumerate(candidates)
    )
    message = _client().messages.create(
        model=MODEL,
        max_tokens=300,
        system=PICK_SYSTEM_PROMPT,
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
