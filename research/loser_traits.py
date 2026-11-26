"""What do the losing trades have in common? Chosen combination (main + E-A zone, up to 10 per structure), 2026.
Each trade gets traits at entry. For each trait bucket: trades, win %, net, in Jan-Jun and Jul-Nov.
A bucket worth skipping must lose money in BOTH halves."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import rsi
from research.zone_multi import zone, FILES

rows = []
for f in FILES:
    df = load_csv(f); sp = pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100
    c = df.close; r = rsi(c.to_numpy(float))
    tr = (df.high - df.low).rolling(14).mean()
    atr_rel = tr / tr.rolling(1440).median()
    h1 = c.resample('1h').last().dropna(); h1e = h1.ewm(span=50, adjust=False).mean()
    h1_up = (h1 > h1e).reindex(df.index, method='ffill').shift(60)               # last finished hour
    m15 = c.resample('15min').last().dropna(); m15e = m15.ewm(span=50, adjust=False).mean()
    m15_up = (m15 > m15e).reindex(df.index, method='ffill').shift(15)
    move60 = c - c.shift(60)
    day_rng = (df.high.rolling(1440).max() - df.low.rolling(1440).min())
    z, m = zone(df, sp, 10, 10)
    seen = {}
    for x in z + m:
        t, pnl, d = x[0], x[1], x[4]
        i = df.index.get_loc(t)
        if x[3] == 'zone': src, k, risk = 'zone', x[6] + 1, x[5]
        else: src, k, risk = 'main', seen.get(x[3], 0) + 1, 20; seen[x[3]] = k
        rows.append(dict(time=t, pnl=pnl, src=src, side='buy' if d == 1 else 'sell', nth=k, risk=risk,
                         hour=t.hour, wday=t.day_name()[:3], atr=atr_rel.iloc[i], rsi=r[i],
                         h1=('with' if bool(h1_up.iloc[i]) == (d == 1) else 'against'),
                         m15=('with' if bool(m15_up.iloc[i]) == (d == 1) else 'against'),
                         move60=d * move60.iloc[i], spread=sp[i], dayrange=day_rng.iloc[i]))
T = pd.DataFrame(rows).sort_values('time')
T['half'] = np.where(T.time < '2026-07-01', 'Jan-Jun', 'Jul-Nov')
T['risk_b'] = pd.cut(T.risk, [0, 7, 10, 15, 20, 1e9], labels=['<$7', '$7-10', '$10-15', '$15-20', '>$20'])
T['atr_b'] = pd.cut(T.atr, [0, 0.8, 1.2, 1.8, 3, 1e9], labels=['quiet <0.8x', 'normal', '1.2-1.8x', 'fast 1.8-3x', 'very fast >3x'])
T['rsi_b'] = pd.cut(T.rsi.where(T.side == 'buy', 100 - T.rsi), [0, 32, 50, 68, 100], labels=['<32', '32-50', '50-68', '68+'])
T['move_b'] = pd.cut(T.move60, [-1e9, -10, 0, 10, 1e9], labels=['against >$10', 'against <$10', 'with <$10', 'with >$10'])
T['dayrng_b'] = pd.cut(T.dayrange, [0, 40, 60, 90, 1e9], labels=['<$40', '$40-60', '$60-90', '>$90'])
T['hour_b'] = pd.cut(T.hour, [-1, 2, 8, 14, 19, 24], labels=['00-02', '03-08 Asia', '09-14 London', '15-19 NY', '20-23 late'])
T['nth_b'] = pd.cut(T.nth, [0, 1, 2, 4, 100], labels=['1st', '2nd', '3rd-4th', '5th+'])
T.to_csv('research/loser_traits_trades.csv', index=False)

def show(col):
    print(f'\n{col}')
    for (src), G in [('all', T)]:
        for b, g in G.groupby(col, observed=True):
            parts = []
            for h in ('Jan-Jun', 'Jul-Nov'):
                q = g[g.half == h]
                parts.append(f'{len(q):3} tr {100*(q.pnl>0).mean() if len(q) else 0:3.0f}% ${q.pnl.sum():6.0f}')
            both_lose = all(g[g.half == h].pnl.sum() < 0 for h in ('Jan-Jun', 'Jul-Nov'))
            print(f'  {str(b):16} | {parts[0]} | {parts[1]}' + ('   <== loses in BOTH halves' if both_lose else ''))

print(f'{len(T)} trades, {100*(T.pnl>0).mean():.0f}% win, net ${T.pnl.sum():.0f}')
for col in ('src', 'side', 'nth_b', 'risk_b', 'hour_b', 'wday', 'atr_b', 'rsi_b', 'h1', 'm15', 'move_b', 'dayrng_b'):
    show(col)
