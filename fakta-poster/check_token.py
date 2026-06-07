"""Cek kesehatan token IG TANPA ngepost apa-apa.

Manggil Graph API `debug_token` + `/me/accounts` buat mastiin:
  - token VALID atau enggak
  - expired KAPAN (long-lived ~60 hari, atau short-lived 1 jam?)
  - SCOPE lengkap buat content publish atau kurang
  - IG_USER_ID nyambung ke akun yang bener

Dipakai sama workflow "Test Token IG (cek doang)". Aman: read-only, gak posting.

Env:
  IG_ACCESS_TOKEN   token yang mau dicek (wajib)
  IG_USER_ID        opsional — kalau diisi, dicek bisa diakses pakai token ini
  IG_ACCOUNTS       opsional — JSON array; kalau ada, tiap akun dicek satu-satu
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v25.0"

# scope minimal yang dibutuhin buat auto-post carousel + reel
NEEDED_SCOPES = {
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
}


def _get(path: str, params: dict) -> dict:
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fmt_ts(ts: int) -> str:
    if not ts:
        return "tidak pernah (never)"
    return time.strftime("%d %b %Y, %H:%M UTC", time.gmtime(ts))


def check_one(name: str, token: str, ig_user_id: str = "") -> bool:
    """Return True kalau token sehat & siap auto-post."""
    print(f"\n=== Cek akun: {name} ===")
    healthy = True

    # 1) debug_token: validitas, expiry, scope
    try:
        data = _get("debug_token", {"input_token": token, "access_token": token}).get("data", {})
    except Exception as exc:
        print(f"  ❌ GAGAL manggil debug_token: {exc}")
        print("     → token kemungkinan ngawur/salah-tempel. Cek lagi nilai secret-nya.")
        return False

    is_valid = data.get("is_valid", False)
    expires = int(data.get("expires_at", 0) or 0)
    now = int(time.time())
    scopes = set(data.get("scopes", []))

    print(f"  Valid        : {'✅ YA' if is_valid else '❌ TIDAK'}")
    if not is_valid:
        err = data.get("error", {}).get("message", "")
        print(f"  Alasan       : {err or '(token expired / dicabut / salah app)'}")
        healthy = False

    if expires == 0:
        print("  Expired      : ♾️  TIDAK PERNAH (System User token / permanen) — mantap!")
    else:
        days_left = (expires - now) / 86400
        print(f"  Expired      : {_fmt_ts(expires)}  (~{days_left:.1f} hari lagi)")
        if days_left < 0:
            print("     → ❌ token SUDAH EXPIRED. Perlu generate ulang.")
            healthy = False
        elif days_left < 2:
            print("     → ⚠️  ini masih token PENDEK (1 jam-an), BUKAN 60 hari.")
            print("        Tukar dulu jadi long-lived (fb_exchange_token) sebelum dipakai.")
            healthy = False
        elif days_left < 50:
            print("     → ⚠️  bukan token fresh 60 hari (mungkin sisa). Masih jalan, tapi siap2 refresh.")
        else:
            print("     → ✅ token panjang (long-lived ~60 hari). Pas!")

    # 2) scope cukup nggak
    missing = NEEDED_SCOPES - scopes
    if missing:
        print(f"  Scope        : ❌ KURANG → {', '.join(sorted(missing))}")
        print(f"     (ada: {', '.join(sorted(scopes)) or '(kosong)'})")
        healthy = False
    else:
        print(f"  Scope        : ✅ lengkap ({', '.join(sorted(scopes & NEEDED_SCOPES))})")

    # 3) IG user id nyambung & bisa diakses pakai token ini
    if ig_user_id:
        try:
            me = _get(ig_user_id, {"fields": "username,name", "access_token": token})
            uname = me.get("username") or me.get("name") or "(tanpa username)"
            print(f"  IG account   : ✅ @{uname}  (id {ig_user_id})")
        except Exception as exc:
            print(f"  IG account   : ❌ gak bisa akses id {ig_user_id} pakai token ini → {exc}")
            print("     → cek IG_USER_ID bener nggak, & token ini punya akun yang sama.")
            healthy = False

    print(f"  HASIL        : {'✅ SIAP AUTO-POST' if healthy else '❌ BELUM beres — lihat catatan di atas'}")
    return healthy


def main() -> int:
    accounts = []
    raw = os.environ.get("IG_ACCOUNTS", "").strip()
    if raw:
        try:
            for i, a in enumerate(json.loads(raw)):
                tok = str(a.get("token", "")).strip()
                if tok:
                    accounts.append((a.get("name") or f"akun-{i+1}", tok, str(a.get("ig_user_id", "")).strip()))
        except json.JSONDecodeError as exc:
            print(f"IG_ACCOUNTS bukan JSON valid → {exc}")

    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if tok:
        accounts.append(("default", tok, os.environ.get("IG_USER_ID", "").strip()))

    if not accounts:
        print("Gak ada token (IG_ACCESS_TOKEN / IG_ACCOUNTS kosong). Set dulu di GH Secrets.")
        return 1

    results = [check_one(n, t, u) for n, t, u in accounts]
    ok = sum(results)
    print(f"\n========== RINGKASAN: {ok}/{len(results)} akun siap auto-post ==========")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
