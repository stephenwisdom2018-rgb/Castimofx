"""Owner's reversal entry, v3: after a buy structure's G sweep, the buy level is ALWAYS the most recent low that price
has just taken out (E, G1, G2 ... G7). Buy when price comes back into that zone with RSI 68+. It stays active until an
opposite trend forms (a sell G sweep or a sell signal). Lows = RSI swing lows or 3-candle lows. Stop $20, target $20.
Sells mirror. Full 2026, 0.01 lot."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def run(df, sp, lows='rsi', zone=3.0, hi=68, sl=20, tp=20, k=3, need32=False):
    h, l, c = (df[x].to_numpy(float) for x in ('high', 'low', 'close')); r = rsi(c); n = len(df)
    ev = []; sig, swings = find_signals(df, g_events=ev, **KW)
    # regime changes: (bar, direction, swept level)
    starts = sorted([(tc, d, lvl) for d, lvl, G, gi, tc in ev] + [(s.bar, s.direction, None) for s in sig])
    # known lows/highs: (bar known, price)
    if lows == 'rsi':
        known = {1: sorted((s.confirmed, s.price) for s in swings if s.kind == 'L'),
                 -1: sorted((s.confirmed, s.price) for s in swings if s.kind == 'H')}
    else:
        known = {1: [], -1: []}
        for i in range(k, n - k):
            if l[i] == l[i-k:i+k+1].min(): known[1].append((i + k, l[i]))
            if h[i] == h[i-k:i+k+1].max(): known[-1].append((i + k, h[i]))
    out = []
    for d in (1, -1):
        bounds = []
        cur = None
        for b, dd, lvl in starts:                                          # buy regime: from a buy G sweep to the next sell event
            if dd == d and lvl is not None and cur is None: cur = (b, lvl)
            elif dd == -d and cur is not None: bounds.append((cur[0], b, cur[1])); cur = None
        if cur: bounds.append((cur[0], n, cur[1]))
        kn = known[d]; j = 0
        for a, b, lvl in bounds:
            if a < 600: continue
            while j < len(kn) and kn[j][0] < a: j += 1
            open_lows = [p for bk, p in kn[max(0, j - 20):j]]               # recent lows known at the start
            L, t, armed = lvl, a, True; jj = j; got32 = not need32
            while t < b:
                while jj < len(kn) and kn[jj][0] <= t: open_lows.append(kn[jj][1]); jj += 1
                broken = [p for p in open_lows if ((l[t] < p) if d == 1 else (h[t] > p))]
                if broken:
                    L = min(broken) if d == 1 else max(broken)               # the low it has just taken out
                    open_lows = [p for p in open_lows if p not in broken]
                    got32 = not need32
                if (r[t] <= 100 - hi) if d == 1 else (r[t] >= hi): got32 = True     # the sweep reached RSI 32
                near = abs(c[t] - L) <= zone
                if not near: armed = True
                if armed and near and got32 and ((r[t] >= hi) if d == 1 else (r[t] <= 100 - hi)):
                    entry = c[t] + (sp[t] if d == 1 else 0)
                    stop, target, res = entry - d * sl, entry + d * tp, None
                    for v in range(t + 1, n):
                        if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res, ex = -sl, v; break
                        if (h[v] >= target) if d == 1 else (l[v] + sp[v] <= target): res, ex = tp, v; break
                    if res is None: break
                    out.append((df.index[t], res)); armed = False
                    for v in range(t + 1, ex + 1):                          # lows taken during the trade still count
                        while jj < len(kn) and kn[jj][0] <= v: open_lows.append(kn[jj][1]); jj += 1
                        br = [p for p in open_lows if ((l[v] < p) if d == 1 else (h[v] > p))]
                        if br: L = min(br) if d == 1 else max(br); open_lows = [p for p in open_lows if p not in br]; got32 = not need32
                        if (r[v] <= 100 - hi) if d == 1 else (r[v] >= hi): got32 = True
                    t = ex + 1; continue
                t += 1
    return sorted(out)

def stats(tr):
    if not tr: return '  0 trades'
    p = np.array([v for _, v in tr]); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    days = len({x[0].date() for x in tr})
    return f'{len(p):4} tr ({len(p)/max(days,1):.1f}/day)  win {100*(p>0).mean():3.0f}%  net ${p.sum():6.0f}  drop ${(eq-pk).min():5.0f}'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    cut = pd.Timestamp('2026-07-01')
    print('lows   zone RSI 32-must | Jan-Jun                                         | Jul-Nov (unseen)')
    for lows, zone, hi, n32 in itertools.product(['rsi', '3-candle'], [2, 5], [68], [False, True]):
        tr = []
        for df, sp in data: tr += run(df, sp, lows, zone, hi, need32=n32)
        tr.sort()
        print(f'{lows:8} ${zone}  {hi} {str(n32):5} | {stats([x for x in tr if x[0] < cut])} | {stats([x for x in tr if x[0] >= cut])}')
