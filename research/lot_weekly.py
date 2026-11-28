"""Robust + quality hours + day rule WITH the lot plan (EA LotUnits: 0.01 per $2,000 up to $10k, then per $4k / $8k;
half lot after 3 losses in a row; min 0.01). Day target +$20 per 0.01 of the day's lot. Start $1,000 (arg 2).
Weekly results + max drawdown INCLUDING open trades (hourly). True data, real fills. Arg: 2026 or 2025, start [, PER for a flat 0.01 per $PER plan]."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.float_dd as FD, research.day_stop as DS
START = float(sys.argv[2]) if len(sys.argv) > 2 else 1000.0
ARG3 = sys.argv[3] if len(sys.argv) > 3 else ''
FIX = float(ARG3[3:]) if ARG3.startswith('fix') else None   # 'fix40' = constant 0.40 lot (no half-lot rule)
PER = float(ARG3) if ARG3 and not FIX else None              # optional flat plan: 0.01 per $PER (e.g. 1000)

def units(bal):
    if FIX: return FIX
    if PER: return max(1.0, np.floor(bal / PER))
    u = np.floor(bal / 2000) if bal <= 10000 else (5 + np.floor((bal - 10000) / 4000) if bal <= 50000 else 15 + np.floor((bal - 50000) / 8000))
    return max(1.0, u)

X = FD.V['Robust']; taken = []; day = None
for e, ex, p, d, ent in X:
    closed = sorted((q for q in taken if q[1] <= e), key=lambda q: q[1])
    bal = START + sum(q[2] * q[5] for q in closed)
    if day != e.date():
        day = e.date(); dayu = units(bal); dstart = bal; neg = False
    dclosed = bal - dstart
    if dclosed < 0: neg = True
    if dclosed >= 20 * dayu or (neg and dclosed >= 0): continue
    u = units(bal); streak = 0
    for q in reversed(closed):
        if q[2] < 0: streak += 1
        else: break
    if streak >= 3 and not FIX: u = max(1.0, np.floor(u / 2))
    taken.append((e, ex, p, d, ent, u))

c, grid, gi = FD.c, FD.grid, FD.gi
eq = np.full(len(grid), START)
for e, ex, p, d, ent, u in taken:
    a = np.searchsorted(grid, e); b = np.searchsorted(grid, ex)
    if b > a: eq[a:b] += (c[gi[a:b]] - ent) * d * u
    eq[b:] += p * u
blown = np.nonzero(eq <= 0)[0]
if len(blown): print('ACCOUNT BLOWN (equity <= 0) on', grid[blown[0]])
peak = np.maximum.accumulate(eq); dd = peak - eq; k = dd.argmax()
s = pd.Series([q[2] * q[5] for q in taken], index=[q[1] for q in taken]).sort_index()
lots = pd.Series([q[5] for q in taken], index=[q[0] for q in taken])
w = s.resample('W-SUN').sum(); bal = START + s.cumsum().resample('W-SUN').last().ffill()
lw = lots.resample('W-SUN').max()
W = pd.DataFrame({'Lot': (lw * 0.01).round(2), 'Profit': w.round(0), 'Balance': bal.round(0)}).dropna()
W.index = (W.index - pd.Timedelta(days=6)).strftime('%d %b')
print(W.to_string())
print('TOTAL', round(s.sum()), 'end', round(START + s.sum()), 'green weeks', round(100 * (w > 0).mean()), '%',
      '| max drawdown with open trades $%.0f (%.0f%% of the peak %.0f) on %s' % (dd[k], 100 * dd[k] / peak[k], peak[k], grid[k].date()),
      '| lowest balance', round(eq.min()), '| worst week', round(w.min()))
