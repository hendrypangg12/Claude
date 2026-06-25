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
    print(f"Data emas: {len(df)} bar ({interval}, {rng})", flush=True)
    LOT, KURS, COMM = 0.03, 16200, 4890

    def summarize(tr, label):
        n = len(tr)
        if n == 0:
            print(f"  {label}: tidak ada trade"); return
        w = int((tr["R"] > 0).sum()); l = n - w
        # P/L harga per trade = R x risk; dollar = x lot x 100
        price_pl = (tr["R"] * tr["risk"])
        idr = price_pl * LOT * 100 * KURS - COMM
        gp = price_pl[price_pl > 0].sum(); gl = -price_pl[price_pl <= 0].sum()
        pf = gp / gl if gl else float("inf")
        max_loss = (tr["risk"][tr["R"] <= 0] * LOT * 100 * KURS).max() if l else 0
        print(f"\n  === {label} ===")
        print(f"    Trade: {n} | Win: {100*w/n:.1f}% ({w}W/{l}L) | PF: {pf:.2f}")
        print(f"    Rata2 jarak SL: ${tr['risk'].mean():.1f}  (risiko/trade lot 0.03 ~Rp{tr['risk'].mean()*LOT*100*KURS:,.0f})")
        print(f"    RUGI TERBESAR 1 trade (lot 0.03): -Rp{max_loss:,.0f}")
        print(f"    NET total (lot 0.03): Rp{idr.sum():,.0f}")

    print("\n========== BANDINGIN 2 METODE (data 2 thn, sinyal SMC sama) ==========")
    trA = walk_forward(df, swing=20, rr=2.0, recompute_every=every, fixed_sl=5.0, fixed_tp=10.0)
    summarize(trA, "METODE A: SL/TP TETAP ($5/$10)")
    trB = walk_forward(df, swing=20, rr=2.0, recompute_every=every)  # OB-based
    summarize(trB, "METODE B: SMC PENUH (SL/TP dari Order Block)")
