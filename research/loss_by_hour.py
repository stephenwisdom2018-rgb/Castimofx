"""Chosen strategy (main + zone, RSI-50 filter, small-structure target), 2026, 0.01: trades by server hour.
Server = HF Markets (UTC+2 winter, UTC+3 summer). Uganda (UTC+3) = server +1h in winter, same in summer."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
from castimofx.sweep import simulate_reentry

rows = []
for df, sp, r, z, groups in R.prep:
    rows += [(t, p, 'zone') for t, p, d, rv in z if R.ok(d, rv)]
    for g, tp in groups:
        rows += [(x.time, x.pnl, 'main') for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0) if R.ok(x.signal.direction, r[x.time])]
T = pd.DataFrame(rows, columns=['time', 'pnl', 'src']); T['hour'] = T.time.dt.hour
T['half'] = np.where(T.time < '2026-07-01', 'H1', 'H2')
print('hour | all: trades losers win%  lost    net | Jan-Jun net | Jul-Nov net')
for h, g in T.groupby('hour'):
    a, b = g[g.half == 'H1'].pnl.sum(), g[g.half == 'H2'].pnl.sum()
    flag = '  <== loses in BOTH halves' if a < 0 and b < 0 else ('  < loses in one half' if a < 0 or b < 0 else '')
    print(f'{h:02d}   |      {len(g):3}   {(g.pnl<0).sum():3}   {100*(g.pnl>0).mean():3.0f}% ${g.pnl[g.pnl<0].sum():6.0f} ${g.pnl.sum():5.0f} |   ${a:5.0f}   |   ${b:5.0f}{flag}')
T.to_csv('research/loss_by_hour_trades.csv', index=False)
