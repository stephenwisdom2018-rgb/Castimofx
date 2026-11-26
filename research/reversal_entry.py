"""Owner's reversal entry: clean A-F staircase, then G sweeps the most recent low (E or the last small low).
Price comes back up to the level it swept. Buy immediately when it has just entered that level AND RSI is 68+
(hooked in). Stop $20, target $20. If stopped out below G, the next entry is only when price comes back to G with
RSI 68+. Sells mirror (RSI 32 and below). Full 2026, 0.01 lot. Jan-Jun vs Jul-Nov."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def run(df, sp, zone=3.0, hook=1, max_per=1, max_wait=1440, hi=68, sl=20, tp=20):
    h, l, c = (df[x].to_numpy(float) for x in ('high', 'low', 'close')); r = rsi(c); n = len(df)
    ev = []; find_signals(df, g_events=ev, **KW)
    out = []
    for d, lvl, G, gi, tc in ev:
        if tc < 600: continue
        L, t, taken, end, armed = lvl, tc, 0, min(n, tc + max_wait), True
        while taken < max_per and t < end:
            strong = all((r[t-j] >= hi) if d == 1 else (r[t-j] <= 100 - hi) for j in range(hook))
            near = abs(c[t] - L) <= zone and ((h[t] >= L - zone) if d == 1 else (l[t] <= L + zone))
            if not near: armed = True                                     # must enter the level fresh
            if armed and near and strong:
                entry = c[t] + (sp[t] if d == 1 else 0)
                stop, target, res = entry - d * sl, entry + d * tp, None
                for v in range(t + 1, n):
                    if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res, ex = -sl, v; break
                    if (h[v] >= target) if d == 1 else (l[v] + sp[v] <= target): res, ex = tp, v; break
                if res is None: break
                out.append((df.index[t], res)); taken += 1; armed = False
                if res < 0 and ((stop < G) if d == 1 else (stop > G)): L = G   # stopped below G: next entry at G
                t = ex + 1; continue
            t += 1
    return out

def stats(tr):
    if not tr: return '  0 trades'
    p = np.array([v for _, v in tr]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    return f'{len(p):4} tr  win {100*(p>0).mean():3.0f}%  net ${p.sum():6.0f}  drop ${(eq-pk).min():5.0f}'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    cut = pd.Timestamp('2026-07-01')
    print('zone hook RSI per | Jan-Jun                               | Jul-Nov (unseen)')
    for zone, hook, hi, per in itertools.product([2, 5], [1, 3], [68, 70], [1, 3]):
        tr = []
        for df, sp in data: tr += run(df, sp, zone, hook, per, hi=hi)
        tr.sort()
        print(f'${zone}   {hook}    {hi}  {per}  | {stats([x for x in tr if x[0] < cut])} | {stats([x for x in tr if x[0] >= cut])}')
