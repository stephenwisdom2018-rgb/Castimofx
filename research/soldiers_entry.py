"""Owner's breakout-retest entry, version 2: H breaks (no entry). Price comes back to H or below and RSI hooks at
30/32. Then buy when 3 white soldiers (3 bullish candles, each closing higher) form INSIDE a moving average
(not outside). Buy again every time price comes back to H, as many as possible until an opposite trend forms
(opposite signal) or price goes below G. Stop $20, target $20. Sells mirror. Full 2026, 0.01 lot."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def ma(c, kind, n):
    s = pd.Series(c)
    return (s.ewm(span=n, adjust=False).mean() if kind == 'EMA' else s.rolling(n).mean()).to_numpy()

def run(df, sp, lo_level, kind, period, inside, max_wait=4320):
    o, h, l, c = (df[x].to_numpy(float) for x in ('open', 'high', 'low', 'close'))
    r = rsi(c); m = ma(c, kind, period); n = len(df)
    sig, _ = find_signals(df, **KW)
    starts = sorted((s.bar, s.direction) for s in sig)
    out = []
    for s in sig:
        if s.bar < 600: continue
        d, H, G = s.direction, s.entry, s.g
        opp = [b for b, dd in starts if b > s.bar and dd == -d]          # opposite trend ends the setup
        end = min(n, s.bar + max_wait, opp[0] if opp else n)
        t, hooked = s.bar + 1, False
        while t < end:
            if (l[t] < G) if d == 1 else (h[t] > G): break             # below G: invalid
            if ((l[t] <= H) if d == 1 else (h[t] >= H)) and ((r[t] <= lo_level) if d == 1 else (r[t] >= 100 - lo_level)):
                hooked = True
            if hooked and t >= 3:
                k = range(t - 2, t + 1)
                soldiers = all(d * (c[i] - o[i]) > 0 for i in k) and d * (c[t-1] - c[t-2]) > 0 and d * (c[t] - c[t-1]) > 0
                if inside == 'MA touches all 3':  ok = all(l[i] <= m[i] <= h[i] for i in k)
                elif inside == 'MA touches 1+':   ok = any(l[i] <= m[i] <= h[i] for i in k)
                elif inside == 'below MA':        ok = all(d * (c[i] - m[i]) <= 0 for i in k)
                else:                             ok = True
                if soldiers and ok:
                    entry = c[t] + (sp[t] if d == 1 else 0)
                    stop, target, res = entry - d * 20, entry + d * 20, None
                    for v in range(t + 1, n):
                        if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res, ex = -20, v; break
                        if (h[v] >= target) if d == 1 else (l[v] + sp[v] <= target): res, ex = 20, v; break
                    if res is None: break
                    out.append((df.index[t], res)); hooked = False; t = ex + 1; continue
            t += 1
    return out

def stats(tr):
    if not tr: return '  0 trades'
    p = np.array([v for _, v in tr]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    return f'{len(p):4} tr  win {100*(p>0).mean():3.0f}%  net ${p.sum():6.0f}  drop ${(eq-pk).min():5.0f}'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    cut = pd.Timestamp('2026-07-01')
    print('RSI  MA      inside           | Jan-Jun                              | Jul-Nov (unseen)')
    for lo, (kind, per), inside in itertools.product([30, 32], [('EMA', 20), ('EMA', 50), ('SMA', 20)],
                                                     ['MA touches all 3', 'MA touches 1+', 'below MA', 'no MA']):
        if inside == 'no MA' and (kind, per) != ('EMA', 20): continue
        tr = []
        for df, sp in data: tr += run(df, sp, lo, kind, per, inside)
        tr.sort()
        print(f'{lo}   {kind}{per:<3} {inside:16} | {stats([x for x in tr if x[0] < cut])} | {stats([x for x in tr if x[0] >= cut])}')
