"""Owner: do we lose more when trades are taken during consolidation? Each trade gets consolidation measures at
entry (known before entry): last 1h / 4h range vs its 5-day median, ADX(14) on M15, efficiency (net move / path)
of the last 60 M1 bars, Bollinger(20,2) width on M15 vs its median. Chosen strategy, all hours, 2026, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
import research.hold_time as H

def adx(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, h.index).ewm(alpha=1/n, adjust=False).mean() / atr
    ndi = 100 * pd.Series(ndm, h.index).ewm(alpha=1/n, adjust=False).mean() / atr
    return (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1/n, adjust=False).mean()

feats = []
for df, *_ in R.prep:
    c = df.close
    f = pd.DataFrame(index=df.index)
    for m in (60, 240):
        rng = df.high.rolling(m).max() - df.low.rolling(m).min()
        f[f'rng{m}'] = rng / rng.rolling(7200, min_periods=1440).median()
    f['eff'] = (c - c.shift(60)).abs() / c.diff().abs().rolling(60).sum()
    m15 = df.resample('15min').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    a = adx(m15.high, m15.low, m15.close)
    bw = 4 * m15.close.rolling(20).std() / m15.close.rolling(20).mean() * 1e4
    bw = bw / bw.rolling(480, min_periods=96).median()
    m = pd.DataFrame({'adx': a, 'bbw': bw}).shift(1)                     # last finished M15 bar
    f = f.join(m.reindex(df.index, method='ffill'))
    feats.append(f)
T = H.T.copy()
for k in ('rng60', 'rng240', 'eff', 'adx', 'bbw'):
    T[k] = [feats[x.fi].at[x.time, k] for x in T.itertuples()]
T['half'] = np.where(T.time < '2026-07-01', 'H1', 'H2')
B = {'rng60': ('last 1h range vs normal (low = tight)', [0, .6, .8, 1.2, 2, 99]),
     'rng240': ('last 4h range vs normal (low = tight)', [0, .6, .8, 1.2, 2, 99]),
     'adx': ('ADX M15 (low = no trend)', [0, 15, 20, 25, 35, 100]),
     'eff': ('last-hour efficiency (low = choppy)', [0, .1, .2, .35, .5, 1.01]),
     'bbw': ('Bollinger width M15 vs normal (low = squeeze)', [0, .6, .8, 1.2, 2, 99])}
for k, (name, bins) in B.items():
    print(f'\n{name}')
    T['b'] = pd.cut(T[k], bins)
    for b, g in T.groupby('b', observed=True):
        p = [f"{len(q):3} tr {100*(q.pnl>0).mean() if len(q) else 0:3.0f}% ${q.pnl.sum():5.0f}" for h in ('H1', 'H2') for q in [g[g.half == h]]]
        flag = '  <== loses in BOTH halves' if all(g[g.half == h].pnl.sum() < 0 for h in ('H1', 'H2')) else ''
        print(f'  {str(b):12} | {p[0]} | {p[1]}{flag}')
T.drop(columns='b').to_csv('research/consolidation_trades.csv', index=False)
