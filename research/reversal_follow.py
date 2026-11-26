"""Owner's reversal entry, v2: the buy level always follows the newest swept low. After G sweeps the most recent low,
buy when price comes back to the swept level with RSI 68+. If price later takes out G1 and forms G2, the level becomes
G1. If it stops on the way and sweeps another low, the level becomes that swept low. Buy only inside the zone (no
entries outside it). Stop $20, target $20. Sells mirror. Full 2026, 0.01 lot."""
import sys, itertools, bisect
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def run(df, sp, zone=3.0, hook=1, max_per=10, max_wait=1440, hi=68, sl=20, tp=20):
    h, l, c = (df[x].to_numpy(float) for x in ('high', 'low', 'close')); r = rsi(c); n = len(df)
    ev = []; _, swings = find_signals(df, g_events=ev, **KW)
    sw = {1: [(s.confirmed, s.price) for s in swings if s.kind == 'L'], -1: [(s.confirmed, s.price) for s in swings if s.kind == 'H']}
    conf = {d: [x[0] for x in sw[d]] for d in (1, -1)}
    out, busy_until = [], {1: -1, -1: -1}
    for d, lvl, G, gi, tc in ev:
        if tc < 600: continue
        end = min(n, tc + max_wait)
        later = sw[d][bisect.bisect_right(conf[d], tc):]               # swing lows confirmed after G (buys)
        k, L, t, taken, armed = 0, lvl, max(tc, busy_until[d] + 1), 0, True
        while taken < max_per and t < end:
            while k < len(later) and later[k][0] <= t:                   # a new low swept the current G
                if (later[k][1] < G) if d == 1 else (later[k][1] > G): L = G
                G = later[k][1] if ((later[k][1] < G) if d == 1 else (later[k][1] > G)) else G
                k += 1
            strong = all((r[t-j] >= hi) if d == 1 else (r[t-j] <= 100 - hi) for j in range(hook))
            near = abs(c[t] - L) <= zone and ((h[t] >= L - zone) if d == 1 else (l[t] <= L + zone))
            if not near: armed = True
            if armed and near and strong:
                entry = c[t] + (sp[t] if d == 1 else 0)
                stop, target, res = entry - d * sl, entry + d * tp, None
                for v in range(t + 1, n):
                    if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res, ex = -sl, v; break
                    if (h[v] >= target) if d == 1 else (l[v] + sp[v] <= target): res, ex = tp, v; break
                if res is None: break
                out.append((df.index[t], res)); taken += 1; armed = False; busy_until[d] = ex
                t = ex + 1; continue
            t += 1
    return out

def stats(tr):
    if not tr: return '  0 trades'
    p = np.array([v for _, v in tr]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    days = len({x[0].date() for x in tr}) or 1
    return f'{len(p):4} tr  win {100*(p>0).mean():3.0f}%  net ${p.sum():6.0f}  drop ${(eq-pk).min():5.0f}'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    cut = pd.Timestamp('2026-07-01')
    print('zone hook RSI wait | Jan-Jun                               | Jul-Nov (unseen)')
    for zone, hook, hi, wait in itertools.product([2, 5], [1, 3], [68, 70], [1440, 4320]):
        tr = []
        for df, sp in data: tr += run(df, sp, zone, hook, hi=hi, max_wait=wait)
        tr.sort()
        print(f'${zone}   {hook}    {hi}  {wait:4} | {stats([x for x in tr if x[0] < cut])} | {stats([x for x in tr if x[0] >= cut])}')
