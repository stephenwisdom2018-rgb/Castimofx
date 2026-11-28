"""Crash filters the bot can SEE LIVE (no dates, no future): judged on true 2026 data, real fills, 0.01.
 day N  : no buys when price is more than $N below today's open (sells: above)          [today so far]
 fast N : no buys when price fell more than $N in the last 60 minutes (sells: rose)     [last hour]
 wild k : no new trades when the last 60 min range > k x its normal size (24 h average) [last hour]
Crash day = gold moved more than $100 from open at some point in the day."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_rules as D

df = D.df; c = df.close
day_open = df.open.groupby(df.index.normalize()).transform('first')
from_open = (c - day_open).shift(1)                         # known at the next minute
move60 = (c - c.shift(60)).shift(1)
rng60 = (df.high.rolling(60).max() - df.low.rolling(60).min()).shift(1)
norm = rng60.rolling(1440).mean()
wild = rng60 / norm
dmax = (df.high.groupby(df.index.normalize()).max() - df.open.groupby(df.index.normalize()).first())
dmin = (df.open.groupby(df.index.normalize()).first() - df.low.groupby(df.index.normalize()).min())
crash = ((dmax > 100) | (dmin > 100)); crash = crash[crash.index.year == 2026]

def run(X, kind=None, v=None):
    X = sorted(x for x in X if x[0].year == 2026); kept = []; skip = 0
    for e, ex, p, d, tag in X:
        if kind == 'day' and from_open.at[e] * d < -v: skip += 1; continue
        if kind == 'fast' and move60.at[e] * d < -v: skip += 1; continue
        if kind == 'wild' and wild.at[e] > v: skip += 1; continue
        kept.append((e, ex, p))
    s = pd.Series([q[2] for q in kept], index=[q[1] for q in kept]).sort_index()
    dd = s.groupby(s.index.normalize()).sum().reindex(D.DAYS, fill_value=0); wk = dd.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return dict(profit=s.sum(), skipped=skip, green=100 * (dd > 0).mean(), gweek=100 * (wk > 0).mean(), worst_day=dd.min(), worst_week=wk.min(), minbal=mb)

if __name__ == '__main__':
    print(f'2026 crash days (moved > $100 from open): {crash.sum()} of {len(crash)}')
    tests = [('none', None, None)] + [('day', 'day', v) for v in (30, 50, 80)] + [('fast', 'fast', v) for v in (10, 15, 25)] + [('wild', 'wild', v) for v in (2, 2.5, 3)]
    for ver, X in D.VERS.items():
        rows = {f'{a} {v or ""}': run(X, k, v) for a, k, v in tests}
        print(ver); print(pd.DataFrame(rows).T.round(0).astype(int).to_string(), flush=True)
