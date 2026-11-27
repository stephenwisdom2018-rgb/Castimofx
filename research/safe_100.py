"""'$100 mode' for the chosen version at 0.01: the biggest $ drop must stay under about $65 (safe = 1.5x on $100).
Levers: skip trades with a stop over $cap, only 1 trade open at a time (no stacking), daily loss limit, smaller main
stop. Drop = biggest peak-to-low $ drop of closed trades; with 1 open trade the open loss is at most one stop."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
ZT = []
for fi, (df, sp, *_) in enumerate(R.prep):
    for x in zone(df, sp, 40, 20, main=False, reent=RE)[0]:
        if M.keep(fi, x[0], x[4]): ZT.append((x[0], x[2], x[1], -x[1] if x[1] < 0 else x[1] / 2))
def mains(sl):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
        tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
        for tp in sorted({tp_of(s) for s in sig}):
            out += [(x.time, x.exit_time, x.pnl, sl) for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], sl, tp, 15, 5, sp, pivot=0)
                    if M.keep(fi, x.time, x.signal.direction)]
    return out
MAINS = {s: mains(s) for s in (10, 15, 20, 30)}

def run(cap, one_open, day_cap, msl, use_main=True):
    tr = sorted([x for x in ZT if x[3] <= cap] + ([x for x in MAINS[msl] if x[3] <= cap] if use_main else []))
    taken, busy_until, day_loss = [], None, {}
    for t, ex, p, risk in tr:
        if one_open and busy_until is not None and t < busy_until: continue
        dl = sum(q for (tt, ee, q) in taken if ee <= t and ee.date() == t.date() and q < 0)
        if day_cap and dl <= -day_cap: continue
        taken.append((t, ex, p)); busy_until = ex
    s = pd.Series([p for t, e, p in taken], index=[e for t, e, p in taken]).sort_index()
    eq = s.cumsum().to_numpy(); dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(eq) else 0
    return s.sum(), dd, len(s), (s > 0).mean() * 100 if len(s) else 0, s[s.index < '2026-07-01'].sum(), s[s.index >= '2026-07-01'].sum()

if __name__ == '__main__':
    rows = []
    for cap, one, dc, msl, um in itertools.product([10, 15, 20, 1e9], [True, False], [0, 20, 30], [10, 15, 20, 30], [True, False]):
        if not um and msl != 30: continue
        p, dd, n, w, h1, h2 = run(cap, one, dc, msl, um)
        rows.append((cap, one, dc, msl if um else '-', p, dd, n, w, h1, h2))
    T = pd.DataFrame(rows, columns=['stop cap', '1 open', 'day cap', 'main stop', 'profit', 'drop', 'trades', 'win', 'H1', 'H2'])
    T['safe balance'] = 1.5 * T['drop']
    print('Best profit with safe balance <= $100:')
    print(T[T['safe balance'] <= 100].sort_values('profit', ascending=False).head(8).round(0).to_string(index=False))
    print('\nBest profit with safe balance <= $200:')
    print(T[T['safe balance'] <= 200].sort_values('profit', ascending=False).head(5).round(0).to_string(index=False))
    T.to_csv('research/safe_100_grid.csv', index=False)
