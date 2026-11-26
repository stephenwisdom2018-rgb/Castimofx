"""Owner's idea: remember A of every structure. When price returns to A, A acts as G: price must stay above A
(buy; tolerance $2), a small H forms, then a small I above A, and a wick break of H is a buy ($20/$20, once per
level). Sells mirror it. Small swings = 3-candle pivots. Full 2026, 0.01 lot."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def a_trades(df, sp, max_days=30, zone_tol=2.0, k=3, sl=20, tp=20):
    lv = []
    find_signals(df, **KW, a_levels=lv)
    h, l = df.high.to_numpy(), df.low.to_numpy()
    n = len(df); out = []
    for d, A, t0, *_ in lv:
        end = min(n, t0 + max_days * 1440)
        # first return to A
        t = t0 + 1
        while t < end and not ((l[t] <= A + zone_tol) if d == 1 else (h[t] >= A - zone_tol)):
            t += 1
        if t >= end:
            continue
        H = None; I_ok = False; entry_t = None
        for u in range(t, min(end, t + 1440)):
            if (l[u] < A - zone_tol) if d == 1 else (h[u] > A + zone_tol):
                break  # left the zone: invalid
            i = u - k
            if i > t:
                if d == 1 and h[i] == h[i - k:i + k + 1].max():
                    H, I_ok = h[i], False
                if d == -1 and l[i] == l[i - k:i + k + 1].min():
                    H, I_ok = l[i], False
                if H is not None and ((d == 1 and l[i] == l[i - k:i + k + 1].min() and i > 0) or
                                      (d == -1 and h[i] == h[i - k:i + k + 1].max())):
                    I_ok = True
            if H is not None and I_ok and ((h[u] > H) if d == 1 else (l[u] < H)):
                entry_t = u; break
        if entry_t is None:
            continue
        entry = H + (sp[entry_t] if d == 1 else 0)
        stop, target = entry - d * sl, entry + d * tp
        res = None
        for u in range(entry_t, n):
            if (l[u] <= stop) if d == 1 else (h[u] + sp[u] >= stop):
                res = -sl; break
            if u > entry_t and ((h[u] >= target) if d == 1 else (l[u] + sp[u] <= target)):
                res = tp; break
        if res is not None:
            out.append((df.index[entry_t], d, res))
    return out

if __name__ == '__main__':
    for days in (3, 30, 120):
        allt = []
        for f in FILES:
            df = load_csv(f); sp = pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100
            allt += a_trades(df, sp, days)
        allt.sort()
        p = np.array([x[2] for x in allt]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
        print(f'A levels valid {days:3} days: trades {len(p)}  win {100*(p>0).mean():.0f}%  net ${p.sum():.0f}  worst drop ${(eq-pk).min():.0f}')
