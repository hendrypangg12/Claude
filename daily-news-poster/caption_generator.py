"""Generate an Instagram caption using Claude."""
import os
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = """You write engaging Instagram captions in Bahasa Indonesia for a daily news account.

Rules:
- 2-4 short paragraphs, max ~600 characters total before hashtags
- Hook in the first line (a question, surprising fact, or strong statement)
- Neutral, factual tone — no clickbait, no political bias
- End with exactly 5 relevant hashtags on one line (mix of #beritaterkini #infoterbaru with topic-specific tags)
- Do NOT include the article URL
- Do NOT use emoji unless it genuinely fits the topic (max 2)"""


def generate_caption(title: str, description: str, source: str) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_prompt = (
        f"Buat caption Instagram untuk berita berikut.\n\n"
        f"Judul: {title}\n"
        f"Ringkasan: {description}\n"
        f"Sumber: {source}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()
