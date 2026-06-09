"""Build TikTok-style karaoke captions (word-by-word highlight) as an ASS subtitle
file for a single clip, sized for 1080x1920 (9:16). ffmpeg's `subtitles` filter
burns it into the video.

The active word is highlighted GOLD; the rest of the on-screen phrase stays white.
Times are rebased so the clip starts at 0 (matches ffmpeg `-ss` accurate seek).
"""
from pathlib import Path

# ASS colours are &HAABBGGRR.
WHITE = r"&H00FFFFFF"
GOLD = r"&H0000C4FF"  # RGB (255,196,0)

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,Poppins,84,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,6,2,2,90,90,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text
"""


def _ass_time(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _esc(word: str) -> str:
    return word.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def build_ass(words: list[dict], clip_start: float, clip_end: float,
              out_path: Path, max_words: int = 3, uppercase: bool = True) -> Path:
    """words: full list of {start,end,word} (absolute seconds). Writes ASS to out_path."""
    dur = clip_end - clip_start
    ws = []
    for w in words:
        if w["end"] <= clip_start or w["start"] >= clip_end:
            continue
        tok = _esc(w["word"])
        if not tok:
            continue
        if uppercase:
            tok = tok.upper()
        ws.append({
            "start": max(0.0, w["start"] - clip_start),
            "end": min(dur, max(0.0, w["end"] - clip_start)),
            "word": tok,
        })

    events = []
    i = 0
    n = len(ws)
    while i < n:
        group = ws[i:i + max_words]
        for j, w in enumerate(group):
            start = w["start"]
            # keep the phrase on screen continuously: end this frame when the next word begins
            idx = i + j + 1
            nxt = ws[idx]["start"] if idx < n else min(dur, w["end"] + 0.35)
            end = max(start + 0.05, nxt)
            parts = []
            for k, gw in enumerate(group):
                if k == j:
                    parts.append(r"{\c" + GOLD + r"\b1}" + gw["word"] + r"{\c" + WHITE + r"}")
                else:
                    parts.append(gw["word"])
            events.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Pop,,0,0,0,{' '.join(parts)}"
            )
        i += len(group)

    out_path.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")
    return out_path
