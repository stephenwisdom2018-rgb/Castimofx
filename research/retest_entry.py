"""Owner's breakout-retest entry: price breaks H (no entry). Wait for it to come back to H or below AND for RSI to
hook at 32 or below. Then buy on the break of the last 3-candle high. Invalid if price goes below G (a new G-H-I
breakout gives a new chance). Sells mirror it. Full 2026, 0.01 lot. Jan-Jun vs Jul-Nov."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def run(df, sp, stop_mode, max_per, boss_only, lo_level=32, max_wait=1440, k=3):
    h, l, c = (df[x].to_numpy(float) for x in ('high', 'low', 'close')); r = rsi(c); n = len(df)
    sig, _ = find_signals(df, **KW)
    out = []
    for s in sig:
        if s.bar < 600 or (boss_only and not s.with_boss): continue
        d, H, G = s.direction, s.entry, s.g
        t, taken, end = s.bar + 1, 0, min(n, s.bar + max_wait)
        while taken < max_per and t < end:
            hooked = False; last_hi = None; entry_t = None
            while t < end:
                if (l[t] < G) if d == 1 else (h[t] > G): t = end; break          # below G: invalid
                back = (l[t] <= H) if d == 1 else (h[t] >= H)
                if back and ((r[t] <= lo_level) if d == 1 else (r[t] >= 100 - lo_level)): hooked = True
                i = t - k
                if hooked and i > 0 and ((h[i] == h[i-k:i+k+1].max()) if d == 1 else (l[i] == l[i-k:i+k+1].min())):
                    last_hi = h[i] if d == 1 else l[i]
                if hooked and last_hi is not None and ((h[t] > last_hi) if d == 1 else (l[t] < last_hi)):
                    entry_t = t; break
                t += 1
            if entry_t is None: break
            entry = last_hi + (sp[entry_t] if d == 1 else 0)
            risk = 20 if stop_mode == '$20/$20' else max(abs(entry - G) + 1, 5)
            tgt = 20 if stop_mode == '$20/$20' else 2 * risk
            stop, target = entry - d * risk, entry + d * tgt
            res = None
            for v in range(entry_t, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res, ex = -risk, v; break
                if v > entry_t and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)): res, ex = tgt, v; break
            if res is None: break
            out.append((df.index[entry_t], res)); taken += 1; t = ex + 1
    return out

def stats(tr):
    if not tr: return '  0 trades'
    p = np.array([v for _, v in tr]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    return f'{len(p):3} tr  win {100*(p>0).mean():3.0f}%  net ${p.sum():6.0f}  drop ${(eq-pk).min():5.0f}'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    cut = pd.Timestamp('2026-07-01')
    print('stop/target       per-H  boss-only | Jan-Jun                              | Jul-Nov (unseen)')
    for stop_mode, max_per, boss in itertools.product(['$20/$20', 'below G, 2x'], [1, 3], [True, False]):
        tr = []
        for df, sp in data: tr += run(df, sp, stop_mode, max_per, boss)
        tr.sort()
        print(f'{stop_mode:14} {max_per:5}  {str(boss):9} | {stats([x for x in tr if x[0] < cut])} | {stats([x for x in tr if x[0] >= cut])}')
