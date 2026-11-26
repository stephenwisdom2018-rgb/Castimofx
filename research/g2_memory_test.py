"""Owner's idea: remember G2 of each cancelled setup; after price has made at least one high above it (buy), the
first time price returns to G2, buy once there ($20 stop, $20 target). Sells mirror it. Full 2026, 0.01 lot."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi, rsi_swings

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def g2_trades(df, sp, max_days, sl=20, tp=20):
    lv = []
    find_signals(df, **KW, g2_levels=lv)
    h, l, c = (df[k].to_numpy(float) for k in ('high', 'low', 'close'))
    sw = rsi_swings(h, l, rsi(c), 68, 32, True)
    out = []
    for d, price, idx, conf in lv:
        # wait for a confirmed swing high (buy) above the level after it formed
        later = [x for x in sw if x.confirmed > conf and x.kind == ('H' if d == 1 else 'L')]
        if not later:
            continue
        t0 = later[0].confirmed + 1
        end = min(len(df), t0 + max_days * 1440)
        hit = None
        for t in range(t0, end):
            if (l[t] <= price) if d == 1 else (h[t] + sp[t] >= price):
                hit = t; break
        if hit is None:
            continue
        entry = price + (sp[hit] if d == 1 else 0)
        stop, target = entry - d * sl, entry + d * tp
        res = None
        for t in range(hit, len(df)):
            if (l[t] <= stop) if d == 1 else (h[t] + sp[t] >= stop):
                res = -sl - (0 if t > hit else 0); break
            if t > hit and ((h[t] >= target) if d == 1 else (l[t] + sp[t] <= target)):
                res = tp; break
        if res is not None:
            out.append((df.index[hit], d, res))
    return out

if __name__ == '__main__':
    for days in (1, 3, 10, 60):
        allt = []
        for f in FILES:
            df = load_csv(f); sp = pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100
            allt += g2_trades(df, sp, days)
        p = np.array([x[2] for x in allt]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
        print(f'G2 memory valid {days:2} days: trades {len(p)}  win {100*(p>0).mean():.0f}%  net ${p.sum():.0f}  worst drop ${(eq-pk).min():.0f}')
