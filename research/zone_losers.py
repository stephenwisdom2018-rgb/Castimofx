"""Zone trades of the chosen strategy (RSI-50 filter on): what do the losers have in common?
Traits: stop size, where G sits in the E-A zone (0 = at E, 1 = at A), hours since the structure formed, nth trade
in the structure, E-A size, H-G size, previous zone trade in the same structure won or lost, buy/sell, hour.
A bucket worth cutting must lose money in BOTH halves."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
from research.zone_multi import zone

rows = []
for df, sp, r, _, _ in R.prep:
    prev = {}
    for x in zone(df, sp, 10, 10, main=False)[0]:
        t, pnl, ex, _, d, risk, k, depth, fe, frac, age, hg, u = x
        key = (d, depth, fe)
        last = prev.get(key); prev[key] = pnl
        if not R.ok(d, r[t]): continue
        rows.append(dict(time=t, pnl=pnl, side='buy' if d == 1 else 'sell', risk=risk, frac=frac, age=age, nth=k + 1,
                         depth=depth, hg=hg, hg_risk=hg / risk, prev=('first' if last is None else 'prev won' if last > 0 else 'prev lost'),
                         hour=t.hour))
T = pd.DataFrame(rows); T['half'] = np.where(T.time < '2026-07-01', 'Jan-Jun', 'Jul-Nov')
B = {'risk': ('stop size $', [0, 7, 10, 15, 20, 30, 1e9]), 'frac': ('G position in zone (0=E,1=A)', [-1, .25, .5, .75, 1.01]),
     'age': ('hours since structure', [-1, 6, 24, 72, 1e9]), 'nth': ('nth trade in structure', [0, 1, 2, 4, 100]),
     'depth': ('E-A size $', [0, 20, 40, 80, 1e9]), 'hg_risk': ('H-G size / stop', [0, .5, .8, 1.01, 1e9]),
     'hour': ('server hour', [-1, 2, 8, 14, 19, 24])}
print(f'{len(T)} zone trades, {100*(T.pnl>0).mean():.0f}% win, ${T.pnl.sum():.0f}')
for col, (name, bins) in B.items():
    T['b'] = pd.cut(T[col], bins); print(f'\n{name}')
    for b, g in T.groupby('b', observed=True):
        p = [f"{len(q):3} tr {100*(q.pnl>0).mean() if len(q) else 0:3.0f}% ${q.pnl.sum():5.0f}" for h in ('Jan-Jun', 'Jul-Nov') for q in [g[g.half == h]]]
        flag = '  <== loses in BOTH halves' if all(g[g.half == h].pnl.sum() < 0 for h in ('Jan-Jun', 'Jul-Nov')) else ''
        print(f'  {str(b):16} | {p[0]} | {p[1]}{flag}')
for col in ('prev', 'side'):
    print(f'\n{col}')
    for b, g in T.groupby(col):
        p = [f"{len(q):3} tr {100*(q.pnl>0).mean() if len(q) else 0:3.0f}% ${q.pnl.sum():5.0f}" for h in ('Jan-Jun', 'Jul-Nov') for q in [g[g.half == h]]]
        flag = '  <== loses in BOTH halves' if all(g[g.half == h].pnl.sum() < 0 for h in ('Jan-Jun', 'Jul-Nov')) else ''
        print(f'  {b:16} | {p[0]} | {p[1]}{flag}')
T.drop(columns='b').to_csv('research/zone_losers_trades.csv', index=False)
