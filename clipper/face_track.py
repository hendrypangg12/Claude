"""Track the speaker's face across a clip to drive a DYNAMIC 9:16 crop (auto-reframe
that keeps the face in frame, like Opus Clip), instead of a static center crop.

Uses OpenCV's bundled Haar cascade — no model download, no extra service. Returns a
smoothed horizontal track. Degrades gracefully (returns empty track) if OpenCV isn't
available or no face is found, so the caller just falls back to center crop.
"""
from pathlib import Path


def track_face(source: Path, start: float, end: float, sample_fps: float = 4.0) -> dict:
    """Sample the clip and follow the largest face.

    Returns {"src_w","src_h","track":[(t_rel, center_x_frac), ...]} where center_x_frac
    is 0..1 of the SOURCE width. Empty track => caller uses center crop.
    """
    try:
        import cv2
    except Exception:
        return {"src_w": 0, "src_h": 0, "track": []}

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        return {"src_w": 0, "src_h": 0, "track": []}

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    track, last_frac = [], 0.5
    step = 1.0 / max(1.0, sample_fps)
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(max(24, int(w * 0.06)), max(24, int(w * 0.06))))
        if len(faces):
            fx, _, fw, _ = max(faces, key=lambda f: f[2] * f[3])
            last_frac = (fx + fw / 2.0) / w
        track.append((round(t - start, 3), last_frac))
        t += step
    cap.release()

    return {"src_w": src_w, "src_h": src_h, "track": _smooth(track)}


def _smooth(track: list, win: int = 6, max_step: float = 0.035) -> list:
    """Moving-average + speed clamp so the crop pans smoothly, never jitters."""
    if not track:
        return track
    xs = [p[1] for p in track]
    sm = []
    for i in range(len(xs)):
        lo, hi = max(0, i - win), min(len(xs), i + win + 1)
        sm.append(sum(xs[lo:hi]) / (hi - lo))
    out = [sm[0]]
    for v in sm[1:]:
        prev = out[-1]
        out.append(max(prev - max_step, min(prev + max_step, v)))
    return [(track[i][0], out[i]) for i in range(len(track))]
