"""Plan a 'tighten' edit for a clip: drop long silences between words and obvious
filler interjections, so the clip is punchy (higher retention). Works off the
Whisper word timestamps. Returns a select expression for ffmpeg + a remap()
that maps original (clip-relative) seconds → compressed seconds, so captions,
zoom emphasis and durations can be re-timed to the cut timeline.
"""

# very conservative: only standalone non-word interjections
FILLERS = {"eh", "ee", "eee", "eeh", "em", "emm", "ehm", "hmm", "hm",
           "mmm", "mm", "uh", "uhm", "uhh", "anu"}


def _norm(tok: str) -> str:
    return "".join(ch for ch in tok.lower() if ch.isalpha())


def _is_filler(tok: str) -> bool:
    return _norm(tok) in FILLERS


def plan_edit(words: list[dict], dur: float, max_gap: float = 0.45,
              pad: float = 0.08, drop_filler: bool = True) -> dict | None:
    """words: clip-relative {start,end,word}. Returns None if nothing worth cutting."""
    ws = [w for w in words if w["end"] > w["start"]
          and not (drop_filler and _is_filler(w["word"]))]
    if not ws:
        return None

    iv = sorted([max(0.0, w["start"] - pad), min(dur, w["end"] + pad)] for w in ws)
    merged = [iv[0][:]]
    for a, b in iv[1:]:
        if a - merged[-1][1] <= max_gap:           # small gap → keep (merge)
            merged[-1][1] = max(merged[-1][1], b)
        else:                                       # long pause → cut it out
            merged.append([a, b])

    total = sum(b - a for a, b in merged)
    if total >= dur - 0.25:                         # < 0.25s saved → not worth it
        return None

    def remap(ts: float) -> float:
        acc = 0.0
        for a, b in merged:
            if ts < a:
                return round(acc, 3)
            if ts <= b:
                return round(acc + (ts - a), 3)
            acc += b - a
        return round(acc, 3)

    select = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in merged)
    return {"intervals": merged, "new_dur": round(total, 3),
            "remap": remap, "select": select}
