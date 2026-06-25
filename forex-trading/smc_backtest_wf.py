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


def walk_forward(df, swing=20, rr=2.0, sl_buf=0.10, recompute_every=3, warmup=120,
                 fixed_sl=None, fixed_tp=None, lookback=300):
    """Walk-forward: SMC dihitung pada ROLLING window (lookback bar terakhir) -> cepat & no-lookahead.
    fixed_sl/fixed_tp (dalam $): kalau diisi, pakai SL/TP TETAP, bukan dari Order Block."""
    n = len(df)
    high = df["high"].values; low = df["low"].values; close = df["close"].values
    trades = []
    pos = None
    cache = None; cache_t = -1

    for t in range(warmup, n):
        if pos is not None:
            if pos["dir"] == 1:
                if low[t] <= pos["sl"]: trades.append({**pos, "R": -1, "t": t}); pos = None
                elif high[t] >= pos["tp"]: trades.append({**pos, "R": rr, "t": t}); pos = None
            else:
                if high[t] >= pos["sl"]: trades.append({**pos, "R": -1, "t": t}); pos = None
                elif low[t] <= pos["tp"]: trades.append({**pos, "R": rr, "t": t}); pos = None
            if pos is not None:
                continue

        if t - cache_t >= recompute_every or cache is None:
            sub = df.iloc[max(0, t + 1 - lookback): t + 1]
            shl = smc.swing_highs_lows(sub, swing_length=swing)
            bos = smc.bos_choch(sub, shl, close_break=True)
            obs = smc.ob(sub, shl, close_mitigation=False)
            cache = (bos, obs); cache_t = t
        bos, obs = cache

        bv = pd.Series(bos["BOS"].values).fillna(0)
        cv = pd.Series(bos["CHOCH"].values).fillna(0)
        sig = bv.where(bv != 0).combine_first(cv.where(cv != 0)).dropna()
        struct = int(sig.iloc[-1]) if len(sig) else 0
        if struct == 0:
            continue

        odir = obs["OB"].values; otop = obs["Top"].values; obot = obs["Bottom"].values
        idxs = [i for i in range(len(odir) - 1) if not pd.isna(odir[i]) and odir[i] == struct]
        for i in reversed(idxs[-5:]):
            top, bot = otop[i], obot[i]
            if struct == 1 and low[t] <= top and close[t] >= bot:
                entry = min(top, close[t])
                if fixed_sl: sl = entry - fixed_sl; risk = fixed_sl; tp = entry + fixed_tp
                else: sl = bot - sl_buf; risk = entry - sl; tp = entry + rr * risk
                if risk > 0:
                    pos = {"dir": 1, "entry": entry, "sl": sl, "tp": tp, "risk": risk}
                break
            if struct == -1 and high[t] >= bot and close[t] <= top:
                entry = max(bot, close[t])
                if fixed_sl: sl = entry + fixed_sl; risk = fixed_sl; tp = entry - fixed_tp
                else: sl = top + sl_buf; risk = sl - entry; tp = entry - rr * risk
                if risk > 0:
                    pos = {"dir": -1, "entry": entry, "sl": sl, "tp": tp, "risk": risk}
                break
    return pd.DataFrame(trades)


def report(tr, label, cost_usd=0.0):
    print(f"\n===== {label}  (biaya ${cost_usd}/trade) =====")
    if len(tr) == 0:
        print("  Tidak ada trade."); return
    # net R per trade SETELAH biaya: biaya dalam $ dibagi risk$ -> dalam satuan R
    cost_R = cost_usd / tr["risk"].clip(lower=0.01)
    gross = tr["R"]
    net = gross - cost_R                       # potong biaya tiap trade
    wins = (net > 0).sum(); losses = (net <= 0).sum()
    total_R = net.sum(); wr = 100 * wins / len(tr)
    gp = net[net > 0].sum(); gl = -net[net <= 0].sum()
    pf = (gp / gl) if gl > 0 else float("inf")
    print(f"  Total trade : {len(tr)}  | Win rate: {wr:.1f}%  | Total: {total_R:+.1f} R")
    print(f"  Profit Factor: {pf:.2f}  ({'CUAN' if pf>1 else 'RUGI'})  | risiko Rp100rb/trade -> ~Rp{total_R*100000:,.0f}")


if __name__ == "__main__":
    interval = sys.argv[1] if len(sys.argv) > 1 else "60m"
    rng = sys.argv[2] if len(sys.argv) > 2 else "180d"
    every = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    df = get_gold(interval=interval, rng=rng)
    print(f"Data emas: {len(df)} bar ({interval}, {rng})  {df.index[0] if hasattr(df.index,'__getitem__') else ''}", flush=True)
    SL, TP, LOT, KURS, COMM = 5.0, 10.0, 0.03, 16200, 4890
    tr = walk_forward(df, swing=20, rr=TP/SL, recompute_every=every, fixed_sl=SL, fixed_tp=TP)
    print(f"Total {len(tr)} trade di seluruh {rng}.", flush=True)

    def stats(sub, label):
        n = len(sub)
        if n == 0:
            print(f"  {label:16s}: tidak ada trade"); return
        w = int((sub["R"] > 0).sum()); l = n - w
        usd = w * TP - l * SL
        idr_net = usd * LOT * 100 * KURS - n * COMM
        pf = (w * TP) / (l * SL) if l else float("inf")
        print(f"  {label:16s}: {n:3d} trade | win {100*w/n:4.1f}% | PF {pf:.2f} | net(0.03) Rp{idr_net:>12,.0f}")

    # bagi jadi 4 periode berdasarkan urutan trade (tiap ~1/4 rentang waktu)
    print(f"\n===== ROBUSTNESS: SL$5/TP$10, lot 0.03, dibagi 4 periode =====")
    tr = tr.reset_index(drop=True)
    q = len(tr) // 4
    for k in range(4):
        seg = tr.iloc[k*q:(k+1)*q] if k < 3 else tr.iloc[k*q:]
        stats(seg, f"Periode {k+1}")
    print("  " + "-"*60)
    stats(tr, "SEMUA (2 thn)")
    be = 100*SL/(SL+TP)
    print(f"\n  Break-even win rate: {be:.0f}%. Konsisten kalau tiap periode win >{be:.0f}% & PF>1.")
