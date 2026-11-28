"""Owner's $20,000 push (lot size left for last). New trades from the same structures, all at 0.01, with every
adopted filter on (RSI-50 side, no new trades at 15:00 / 23:00, consolidation: last 1h range < 0.6x or ADX M15 25-35):
1. zone re-entries after a zone stop (RSI or 3-candle swings; first target or 2x risk; up to 3)
2. more zone trades per structure / longer zone memory
3. bigger target (3x) for zone trades with stops over $20
Main strategy (small-structure target) unchanged."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
from research.zone_multi import zone
from research.indicators import adx
from castimofx.sweep import simulate_reentry

FEAT = []
for df, sp, r, _, groups in R.prep:
    f = pd.DataFrame({'rsi': r}, index=df.index)
    rng = df.high.rolling(60).max() - df.low.rolling(60).min()
    f['rng60'] = rng / rng.rolling(7200, min_periods=1440).median()
    m15 = df.resample('15min').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    f['adx'] = adx(m15.high, m15.low, m15.close).shift(1).reindex(df.index, method='ffill')
    FEAT.append(f)

import os
# optional quality filter: no new trades in these server hours, e.g. CASTIMO_SKIP_HOURS=8-13 (London morning)
_SK = os.environ.get('CASTIMO_SKIP_HOURS', '')
SKIP_HOURS = set(range(int(_SK.split('-')[0]), int(_SK.split('-')[1]) + 1)) if _SK else set()

def keep(fi, t, d):
    f = FEAT[fi].loc[t]
    if not ((f.rsi >= 50) if d == 1 else (f.rsi <= 50)): return False
    if t.hour in (15, 23) or t.hour in SKIP_HOURS: return False
    if f.rng60 < 0.6 or 25 < f.adx <= 35: return False
    return True

MAIN = []
for fi, (df, sp, r, _, groups) in enumerate(R.prep):
    for g, tp in groups:
        MAIN += [(x.time, x.pnl) for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0) if keep(fi, x.time, x.signal.direction)]

def run(**kw):
    tr = list(MAIN); zt = 0
    for fi, (df, sp, *_) in enumerate(R.prep):
        for x in zone(df, sp, kw.pop('max_per', 10) if False else kw.get('max_per', 10), kw.get('mem', 10), main=False,
                      big_rr=kw.get('big_rr'), reent=kw.get('reent'))[0]:
            if keep(fi, x[0], x[4]): tr.append((x[0], x[1])); zt += 1
    return sorted(tr)

def st(tr):
    o = []
    for a, b in (('2026-01-01', '2026-07-01'), ('2026-07-01', '2027-01-01'), ('2026-01-01', '2027-01-01')):
        q = pd.Series([p for t, p in tr if a <= str(t) < b]); eq = 1000 + q.cumsum().to_numpy()
        pk = np.maximum.accumulate(np.r_[1000, eq])[1:]; dd = ((eq - pk) / pk).min() * 100
        pf = q[q > 0].sum() / -q[q < 0].sum()
        o.append(f'{len(q):3} tr {100*(q>0).mean():3.0f}% ${q.sum():5.0f} {dd:5.1f}% PF {pf:.2f}')
    return ' | '.join(o)

if __name__ == '__main__':
    print(f'{"variant":42}| Jan-Jun | Jul-Nov | YEAR')
    V = {'current (10 per structure, 10 days)': {}}
    for sw_, tg, mx in itertools.product(['rsi', '3'], ['orig', '2R'], [1, 3]):
        V[f'zone re-entry {sw_} swings, {tg}, up to {mx}'] = dict(reent=dict(swings=sw_, target=tg, max=mx))
    for mp, mem in ((20, 10), (10, 20), (20, 20), (99, 30)):
        V[f'zone up to {mp} per structure, {mem} days'] = dict(max_per=mp, mem=mem)
    for b in (2.5, 3, 4):
        V[f'zone target {b}x when stop > $20'] = dict(big_rr=b)
    for k, kw in V.items():
        print(f'{k:42}| {st(run(**kw))}', flush=True)
