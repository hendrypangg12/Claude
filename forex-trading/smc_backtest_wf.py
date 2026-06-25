"""
SMC walk-forward backtest — JUJUR (tanpa lookahead).
Tiap bar, SMC dihitung ulang HANYA pakai data yang tersedia saat itu (df[:t+1]),
jadi tidak ngintip masa depan. Entry di Order Block searah struktur, SL di luar OB,
exit kronologis (SL/TP mana duluan). Ini hasil yang bisa dipercaya.
"""
import os, sys
import pandas as pd
import requests
from smartmoneyconcepts import smc

CA = "/root/.ccr/ca-bundle.crt"
os.environ.setdefault("REQUESTS_CA_BUNDLE", CA)


def get_gold(interval="60m", rng="730d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range={rng}&interval={interval}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=40,
                     verify=CA if os.path.exists(CA) else True)
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"],
        "volume": q.get("volume") or [0] * len(q["open"]),
    }, index=pd.to_datetime(res["timestamp"], unit="s")).dropna().reset_index(drop=True)
    return df


def walk_forward(df, swing=20, rr=2.0, sl_buf=0.10, recompute_every=3, warmup=120):
    """Walk-forward: recompute SMC pakai data sampai bar t saja. 1 posisi pada satu waktu."""
    n = len(df)
    high = df["high"].values; low = df["low"].values; close = df["close"].values
    trades = []
    pos = None  # dict: dir, entry, sl, tp
    cache = None; cache_t = -1

    for t in range(warmup, n):
        # --- kelola posisi terbuka (cek SL/TP di bar ini) ---
        if pos is not None:
            if pos["dir"] == 1:
                if low[t] <= pos["sl"]:
                    trades.append({**pos, "R": -1}); pos = None
                elif high[t] >= pos["tp"]:
                    trades.append({**pos, "R": rr}); pos = None
            else:
                if high[t] >= pos["sl"]:
                    trades.append({**pos, "R": -1}); pos = None
                elif low[t] <= pos["tp"]:
                    trades.append({**pos, "R": rr}); pos = None
            if pos is not None:
                continue  # masih ada posisi, tunggu

        # --- cari sinyal baru (recompute SMC sampai t, no future) ---
        if t - cache_t >= recompute_every or cache is None:
            sub = df.iloc[: t + 1]
            shl = smc.swing_highs_lows(sub, swing_length=swing)
            bos = smc.bos_choch(sub, shl, close_break=True)
            obs = smc.ob(sub, shl, close_mitigation=False)
            cache = (bos, obs); cache_t = t
        bos, obs = cache

        # struktur terakhir (ambil sinyal BOS/CHOCH terakhir, no loop penuh)
        bv = pd.Series(bos["BOS"].values).fillna(0)
        cv = pd.Series(bos["CHOCH"].values).fillna(0)
        sig = bv.where(bv != 0).combine_first(cv.where(cv != 0))
        last = sig.dropna()
        struct = int(last.iloc[-1]) if len(last) else 0
        if struct == 0:
            continue

        # OB aktif terakhir searah struktur, yang zona-nya kena harga bar t
        odir = obs["OB"].values; otop = obs["Top"].values; obot = obs["Bottom"].values
        idxs = [i for i in range(len(odir)) if not pd.isna(odir[i]) and odir[i] == struct and i < t]
        entered = False
        for i in reversed(idxs[-5:]):  # cek beberapa OB terbaru
            top, bot = otop[i], obot[i]
            if struct == 1 and low[t] <= top and close[t] >= bot:   # masuk zona bullish OB
                entry = min(top, close[t]); sl = bot - sl_buf; risk = entry - sl
                if risk > 0:
                    pos = {"dir": 1, "entry": entry, "sl": sl, "tp": entry + rr * risk}; entered = True
                break
            if struct == -1 and high[t] >= bot and close[t] <= top:  # masuk zona bearish OB
                entry = max(bot, close[t]); sl = top + sl_buf; risk = sl - entry
                if risk > 0:
                    pos = {"dir": -1, "entry": entry, "sl": sl, "tp": entry - rr * risk}; entered = True
                break
    return pd.DataFrame(trades)


def report(tr, label):
    print(f"\n===== {label} =====")
    if len(tr) == 0:
        print("  Tidak ada trade."); return
    wins = (tr["R"] > 0).sum(); losses = (tr["R"] < 0).sum()
    total_R = tr["R"].sum(); wr = 100 * wins / len(tr)
    gp = tr.loc[tr["R"] > 0, "R"].sum(); gl = -tr.loc[tr["R"] < 0, "R"].sum()
    pf = (gp / gl) if gl > 0 else float("inf")
    print(f"  Total trade : {len(tr)}  (BUY {int((tr['dir']==1).sum())} / SELL {int((tr['dir']==-1).sum())})")
    print(f"  Menang/Kalah: {wins} / {losses}   Win rate: {wr:.1f}%")
    print(f"  Total hasil : {total_R:+.1f} R")
    print(f"  Profit Factor: {pf:.2f}  ({'CUAN' if pf>1 else 'RUGI'})")
    print(f"  Kalau risiko Rp100rb/trade -> net ~Rp{total_R*100000:,.0f}")


if __name__ == "__main__":
    interval = sys.argv[1] if len(sys.argv) > 1 else "60m"
    rng = sys.argv[2] if len(sys.argv) > 2 else "180d"
    every = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    df = get_gold(interval=interval, rng=rng)
    print(f"Data emas: {len(df)} bar ({interval}, {rng})  harga akhir {df['close'].iloc[-1]:.1f}", flush=True)
    for rr in [2.0]:
        tr = walk_forward(df, swing=20, rr=rr, recompute_every=every)
        report(tr, f"WALK-FORWARD (jujur) | TP={rr}R | recompute/{every}bar")
