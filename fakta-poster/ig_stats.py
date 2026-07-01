"""Ambil statistik IG (foto profil, jumlah post/follower/following) → docs/ig-stats.json.

Dijalanin GitHub Actions (token IG aman di Secrets, gak ke-expose ke halaman).
Monitor (docs/monitor.html) baca JSON ini buat nampilin profil tiap akun.
"""
import datetime
import json
import os
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v23.0"
FIELDS = "username,profile_picture_url,followers_count,follows_count,media_count"

# key : (ig_user_id env, token env)
ACCTS = [
    ("faktaviral", "IG_USER_ID", "IG_ACCESS_TOKEN"),
    ("beruang", "IG_USER_ID_BF", "IG_ACCESS_TOKEN_BF"),
    ("storykantor", "IG_USER_ID_SK", "IG_ACCESS_TOKEN"),
]


def main() -> int:
    out = {}
    for key, id_env, tok_env in ACCTS:
        uid = os.environ.get(id_env, "").strip()
        tok = os.environ.get(tok_env, "").strip() or os.environ.get("IG_ACCESS_TOKEN", "").strip()
        if not (uid and tok):
            print(f"{key}: skip (id/token kosong)")
            continue
        try:
            r = requests.get(f"{GRAPH}/{uid}", params={"fields": FIELDS, "access_token": tok}, timeout=20)
            d = r.json()
            if "error" in d:
                print(f"{key}: error → {d['error'].get('message')}")
                continue
            out[key] = {
                "username": d.get("username", ""),
                "pic": d.get("profile_picture_url", ""),
                "followers": d.get("followers_count"),
                "follows": d.get("follows_count"),
                "media": d.get("media_count"),
            }
            print(f"{key}: ✅ {out[key]['followers']} followers, {out[key]['media']} post")
        except Exception as exc:
            print(f"{key}: gagal → {exc}")

    out["_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    docs = Path(__file__).resolve().parent.parent / "docs"
    (docs / "ig-stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # RIWAYAT harian (buat pertambahan follower) → 1 entri per hari (WIB), simpan 60 hari
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    hpath = docs / "ig-history.json"
    try:
        hist = json.loads(hpath.read_text(encoding="utf-8"))
    except Exception:
        hist = {}
    for key, v in out.items():
        if key == "_updated" or v.get("followers") is None:
            continue
        lst = hist.setdefault(key, [])
        entry = {"d": today, "f": v["followers"], "m": v.get("media")}
        if lst and lst[-1].get("d") == today:
            lst[-1] = entry          # update snapshot hari ini
        else:
            lst.append(entry)
        hist[key] = lst[-60:]
    hpath.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"tersimpan → ig-stats.json + ig-history.json ({len(out) - 1} akun)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
