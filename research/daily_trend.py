"""Big-trend handling. Daily trend from the M15 2-year file (finished days only):
- EMA20: previous daily close above / below the 20-day EMA of daily closes
- Breakout20: the direction of the latest 20-day breakout (new 20-day high = up, new 20-day low = down)
Rules for trades AGAINST the daily trend: (1) skip, (2) half lot, (3) skip zone trades only.
Chosen strategy (main + zone, RSI-50 filter, small-structure target), all hours, 2026, base 0.01 (half = 0.005, so
the half-lot rule needs a base of 0.02 or more in real trading)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
from castimofx import load_csv

m15 = load_csv('data/XAUUSDb_M15_2024-11_2026-11.csv')
d1 = m15.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
ema = d1.close.ewm(span=20, adjust=False).mean()
t_ema = np.sign(d1.close - ema)
hi20, lo20 = d1.high.rolling(20).max().shift(1), d1.low.rolling(20).min().shift(1)
brk = pd.Series(np.where(d1.high > hi20, 1, np.where(d1.low < lo20, -1, 0)), d1.index).replace(0, np.nan).ffill()
trend = {'EMA20': t_ema.shift(1), 'Breakout20': brk.shift(1)}          # known at the start of each day

T = pd.read_csv('research/consolidation_trades.csv', parse_dates=['time']).sort_values('time')
day = T.time.dt.normalize()
print(f'{"trend / rule":34}| Jan-Jun | Jul-Nov | YEAR')
print(f'{"current":34}| {R.st(list(zip(T.time, T.pnl)))}')
for name, tr in trend.items():
    with_tr = (tr.reindex(day).to_numpy() == T.d.to_numpy())
    against = ~with_tr
    a = T[against]; w = T[with_tr]
    print(f'{name}: with trend {len(w)} tr {100*(w.pnl>0).mean():.0f}% ${w.pnl.sum():.0f} | against {len(a)} tr {100*(a.pnl>0).mean():.0f}% ${a.pnl.sum():.0f}')
    rules = {'skip against': T[with_tr].pipe(lambda q: list(zip(q.time, q.pnl))),
             'half lot against': list(zip(T.time, np.where(against, T.pnl * 0.5, T.pnl))),
             'skip zone against': T[with_tr | (T.src == 'main')].pipe(lambda q: list(zip(q.time, q.pnl)))}
    for k, v in rules.items():
        print(f'  {k:32}| {R.st(sorted(v))}')
