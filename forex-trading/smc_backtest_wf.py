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
                 fixed_sl=None, fixed_tp=None):
    """Walk-forward: recompute SMC pakai data sampai bar t saja. 1 posisi pada satu waktu.
    fixed_sl/fixed_tp (dalam $): kalau diisi, pakai SL/TP TETAP, bukan dari Order Block."""
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
                entry = min(top, close[t])
                if fixed_sl: sl = entry - fixed_sl; risk = fixed_sl; tp = entry + fixed_tp
                else: sl = bot - sl_buf; risk = entry - sl; tp = entry + rr * risk
                if risk > 0:
                    pos = {"dir": 1, "entry": entry, "sl": sl, "tp": tp, "risk": risk}; entered = True
                break
            if struct == -1 and high[t] >= bot and close[t] <= top:  # masuk zona bearish OB
                entry = max(bot, close[t])
                if fixed_sl: sl = entry + fixed_sl; risk = fixed_sl; tp = entry - fixed_tp
                else: sl = top + sl_buf; risk = sl - entry; tp = entry - rr * risk
                if risk > 0:
                    pos = {"dir": -1, "entry": entry, "sl": sl, "tp": tp, "risk": risk}; entered = True
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
    print(f"Data emas: {len(df)} bar ({interval}, {rng})  harga akhir {df['close'].iloc[-1]:.1f}", flush=True)
    # SL TETAP 50 pips ($5), TP TETAP 100 pips ($10) -> R:R 1:2
    SL, TP, LOT, KURS, COMM = 5.0, 10.0, 0.03, 16200, 4890
    tr = walk_forward(df, swing=20, rr=TP/SL, recompute_every=every, fixed_sl=SL, fixed_tp=TP)
    n = len(tr); wins = int((tr["R"] > 0).sum()); losses = n - wins
    # dollar di lot 0.03: menang +$10, kalah -$5 (tetap)
    usd = wins * TP - losses * SL
    idr_gross = usd * LOT * 100 * KURS
    idr_net = idr_gross - n * COMM
    print(f"\n===== SL 50pip ($5) / TP 100pip ($10) | lot {LOT} | 6 bulan =====")
    print(f"  Total sinyal : {n} trade")
    print(f"  KENA TP (menang): {wins}   |  KENA SL (kalah): {losses}")
    print(f"  Win rate : {100*wins/n:.1f}%" if n else "  no trade")
    print(f"  Hasil harga : {usd:+.0f}$  ({wins}x+$10  {losses}x-$5)")
    print(f"  Kotor (lot {LOT}) : Rp{idr_gross:,.0f}")
    print(f"  Komisi ({n}x)    : -Rp{n*COMM:,.0f}")
    print(f"  NET 6 bulan     : Rp{idr_net:,.0f}")
    be = 100*SL/(SL+TP)
    print(f"  (Break-even win rate yang dibutuhin: {be:.0f}% — di atas itu = cuan)")
