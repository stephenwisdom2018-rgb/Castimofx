"""How long were losing trades held compared with winners? And a time exit: if a trade is still open after N minutes,
close it at market (optionally only if it is losing). Chosen strategy (main + zone, RSI-50 filter, small-structure
target), all hours, 2026, 0.01."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

rows = []
for fi, (df, sp, r, _, groups) in enumerate(R.prep):
    for x in zone(df, sp, 10, 10, main=False)[0]:
        if R.ok(x[4], r[x[0]]): rows.append((x[0], x[1], x[4], x[13], x[2], 'zone', fi))
    for g, tp in groups:
        for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0):
            if R.ok(x.signal.direction, r[x.time]): rows.append((x.time, x.pnl, x.signal.direction, x.entry, x.exit_time, 'main', fi))
T = pd.DataFrame(rows, columns=['time', 'pnl', 'd', 'entry', 'exit_time', 'src', 'fi']).sort_values('time')
T['mins'] = (T.exit_time - T.time).dt.total_seconds() / 60
T['res'] = np.where(T.pnl > 0, 'win', 'loss')
print('Minutes held (median / 75% / 90%):')
for (src, res), g in T.groupby(['src', 'res']):
    print(f'  {src:4} {res:4}: {len(g):3} trades  median {g.mins.median():5.0f}  75% {g.mins.quantile(.75):5.0f}  90% {g.mins.quantile(.9):6.0f}')
bins = [0, 15, 30, 60, 120, 240, 480, 1440, 1e9]
T['b'] = pd.cut(T.mins, bins, labels=['<15m', '15-30m', '30-60m', '1-2h', '2-4h', '4-8h', '8-24h', '>1 day'])
print('\nHeld for | trades | win% | net')
for b, g in T.groupby('b', observed=True):
    print(f'  {b:8} | {len(g):4} | {100*(g.pnl>0).mean():3.0f}% | ${g.pnl.sum():6.0f}')

# time exit: close at market after N minutes if still open
closes = [(df.index, df.close.to_numpy(), sp) for df, sp, *_ in R.prep]
def time_exit(N, only_losing):
    out = []
    for x in T.itertuples():
        if x.mins <= N: out.append((x.time, x.pnl)); continue
        idx, c, sp = closes[x.fi]; i = idx.get_loc(x.time) + N
        while idx[i] - x.time > pd.Timedelta(minutes=N) and i > 0: i -= 1        # weekend gaps
        px = c[i] + (sp[i] if x.d == -1 else 0); p = (px - x.entry) * x.d
        if only_losing and p >= 0: out.append((x.time, x.pnl)); continue
        out.append((x.time, p))
    return sorted(out)
print(f'\n{"time exit":34}| Jan-Jun | Jul-Nov | YEAR')
print(f'{"none (current)":34}| {R.st(sorted(zip(T.time, T.pnl)))}')
for N in (60, 120, 240, 480, 1440):
    for ol in (False, True):
        print(f'{f"close after {N} min" + (" if losing" if ol else ""):34}| {R.st(time_exit(N, ol))}')
