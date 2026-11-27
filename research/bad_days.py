"""Client view of the chosen version: winning / losing / no-trade days, streaks of consecutive bad days
(losing OR no trade), and what a client who connects on any day sees after 1, 3, 5, 10, 20 trading days."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_profit3 as P

def daily(tr):
    days = sorted({d for df, *_ in R.prep for d in set(df.index.date)})
    tdays = {t.date() for t, p in tr}
    if not tdays & set(days):                                            # trades from other data: use weekdays
        days = [d.date() for d in pd.bdate_range(min(tdays), max(tdays))]
    s = pd.Series([p for t, p in tr], index=[t.date() for t, p in tr]).groupby(level=0).sum()
    return pd.Series([s.get(d, np.nan) for d in days], index=days)       # NaN = no trade

def streaks(mask):
    out, n = [], 0
    for m in mask:
        if m: n += 1
        elif n: out.append(n); n = 0
    if n: out.append(n)
    return out

def report(name, tr):
    d = daily(tr); win = (d > 0).sum(); lose = (d < 0).sum(); none = d.isna().sum()
    bad = streaks(((d < 0) | d.isna()).tolist()); lose_only = streaks((d < 0).tolist())
    print(f'{name}: {len(d)} days | winning {win} ({100*win/len(d):.0f}%) | losing {lose} ({100*lose/len(d):.0f}%) | no trade {none} ({100*none/len(d):.0f}%)')
    print(f'  bad-day streaks (losing or no trade): longest {max(bad)}, '
          + ', '.join(f'{k}+ days: {sum(b >= k for b in bad)}x' for k in (2, 3, 4, 5, 7)))
    print(f'  losing-day streaks only: longest {max(lose_only)}, ' + ', '.join(f'{k}+: {sum(b >= k for b in lose_only)}x' for k in (2, 3, 4)))
    v = d.fillna(0).to_numpy()
    for k in (1, 3, 5, 10, 20):
        sums = np.array([v[i:i + k].sum() for i in range(len(v) - k + 1)])
        print(f'  client connects any day, after {k:2} days: in profit {100*(sums>0).mean():3.0f}%, flat {100*(sums==0).mean():3.0f}%, in loss {100*(sums<0).mean():3.0f}% (worst ${sums.min():.0f})')
    worst = max(range(len(bad)), key=lambda i: bad[i])
    return d

if __name__ == '__main__':
    d = report('Chosen version', P.zones(40, 20) + P.mains(sl=30, extra=15))
    m = ((d < 0) | d.isna()).tolist(); n = best = 0; end = None
    for i, x in enumerate(m):
        n = n + 1 if x else 0
        if n > best: best, end = n, i
    print(f'  longest bad stretch: {d.index[end - best + 1]} to {d.index[end]}')
