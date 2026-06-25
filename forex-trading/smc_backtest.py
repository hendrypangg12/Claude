"""
SMC (Smart Money Concept) backtest — emas (XAUUSD).
Strategi: entry di Order Block searah struktur (BOS), SL di luar OB, TP = R-multiple.
Data ditarik dari Yahoo (GC=F). Murni evaluasi: cuan apa nggak SEBELUM dipakai live.
"""
import os, sys, io
import pandas as pd
import requests
from smartmoneyconcepts import smc

CA = "/root/.ccr/ca-bundle.crt"
os.environ.setdefault("REQUESTS_CA_BUNDLE", CA)


def get_gold(interval="60m", rng="60d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range={rng}&interval={interval}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30,
                     verify=CA if os.path.exists(CA) else True)
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"],
        "volume": q.get("volume") or [0] * len(q["open"]),
    }, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    return df


def backtest(df, swing=20, rr=2.0, sl_buf=0.10, trend_filter=True, max_wait=48):
    """Entry saat harga retrace ke Order Block searah struktur. TP=rr*risk."""
    shl = smc.swing_highs_lows(df, swing_length=swing)
    bos = smc.bos_choch(df, shl, close_break=True)
    obs = smc.ob(df, shl, close_mitigation=False)

    n = len(df)
    high = df["high"].values; low = df["low"].values; close = df["close"].values
    ob_dir = obs["OB"].values; ob_top = obs["Top"].values; ob_bot = obs["Bottom"].values
    bos_v = bos["BOS"].values; choch_v = bos["CHOCH"].values

    # arah struktur terakhir di tiap bar (1=bull, -1=bear)
    struct = [0] * n
    cur = 0
    for i in range(n):
        if not pd.isna(bos_v[i]) and bos_v[i] != 0: cur = int(bos_v[i])
        if not pd.isna(choch_v[i]) and choch_v[i] != 0: cur = int(choch_v[i])
        struct[i] = cur

    trades = []
    for i in range(n):
        d = ob_dir[i]
        if pd.isna(d) or d == 0:
            continue
        if trend_filter and struct[i] != d:
            continue  # cuma OB searah struktur
        top, bot = ob_top[i], ob_bot[i]
        # tunggu harga retrace masuk OB
        entry_idx = None
        for j in range(i + 1, min(i + 1 + max_wait, n)):
            if d == 1 and low[j] <= top:          # bullish OB: harga turun masuk zona
                entry_idx = j; break
            if d == -1 and high[j] >= bot:         # bearish OB: harga naik masuk zona
                entry_idx = j; break
        if entry_idx is None:
            continue
        if d == 1:
            entry = top; sl = bot - sl_buf; risk = entry - sl
            tp = entry + rr * risk
        else:
            entry = bot; sl = top + sl_buf; risk = sl - entry
            tp = entry - rr * risk
        if risk <= 0:
            continue
        # walk-forward cek TP/SL duluan mana
        result = None
        for k in range(entry_idx + 1, n):
            if d == 1:
                if low[k] <= sl: result = -1; break
                if high[k] >= tp: result = rr; break
            else:
                if high[k] >= sl: result = -1; break
                if low[k] <= tp: result = rr; break
        if result is not None:
            trades.append({"dir": "BUY" if d == 1 else "SELL", "entry": entry,
                           "sl": sl, "tp": tp, "R": result})
    return pd.DataFrame(trades)


def report(tr, label):
    print(f"\n===== {label} =====")
    if len(tr) == 0:
        print("  Tidak ada trade.")
        return
    wins = (tr["R"] > 0).sum(); losses = (tr["R"] < 0).sum()
    total_R = tr["R"].sum()
    wr = 100 * wins / len(tr)
    gp = tr.loc[tr["R"] > 0, "R"].sum(); gl = -tr.loc[tr["R"] < 0, "R"].sum()
    pf = (gp / gl) if gl > 0 else float("inf")
    print(f"  Total trade : {len(tr)}  (BUY {sum(tr['dir']=='BUY')} / SELL {sum(tr['dir']=='SELL')})")
    print(f"  Menang/Kalah: {wins} / {losses}   Win rate: {wr:.1f}%")
    print(f"  Total hasil : {total_R:+.1f} R  (1R = jarak SL)")
    print(f"  Profit Factor: {pf:.2f}   ({'CUAN' if pf>1 else 'RUGI'})")
    # estimasi rupiah kalau 1R = risiko Rp100rb (lot disesuaikan)
    print(f"  Kalau tiap trade risiko Rp100rb -> net ~Rp{total_R*100000:,.0f}")


if __name__ == "__main__":
    interval = sys.argv[1] if len(sys.argv) > 1 else "60m"
    df = get_gold(interval=interval, rng="60d")
    print(f"Data emas: {len(df)} bar ({interval}), {df.index[0]} -> {df.index[-1]}")
    print(f"Harga terakhir: {df['close'].iloc[-1]:.1f}")

    for tf_filter in [True, False]:
        for rr in [1.5, 2.0, 3.0]:
            tr = backtest(df, swing=20, rr=rr, trend_filter=tf_filter)
            report(tr, f"{'SEARAH STRUKTUR' if tf_filter else 'SEMUA OB'} | TP={rr}R")
