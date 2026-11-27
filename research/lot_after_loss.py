"""Chosen version: smaller lot after a loss. Lot for a new trade depends on the trades already CLOSED before it
(live rule): normal after a win, smaller after a loss (or after 2 losses in a row). Base lot = 0.02, reduced = 0.01,
so results are shown in $ at a 0.02 base. Also: does the chosen version show the same streak pattern?"""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
TR = []
for fi, (df, sp, *_) in enumerate(R.prep):
    TR += [(x[0], x[2], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE)[0] if M.keep(fi, x[0], x[4])]
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        TR += [(x.time, x.exit_time, x.pnl) for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0)
               if M.keep(fi, x.time, x.signal.direction)]
TR.sort()
w = np.array([p > 0 for _, _, p in TR])
print(f'chosen: {len(TR)} trades; after a loss next wins {100*np.mean([w[i] for i in range(1,len(w)) if not w[i-1]]):.0f}%, after a win {100*np.mean([w[i] for i in range(1,len(w)) if w[i-1]]):.0f}%')

def run(rule):
    closed, out = [], []
    for t, ex, p in TR:
        done = [c for c in closed if c[0] <= t]; done.sort()
        k = 0
        for c in reversed(done):
            if c[1] < 0: k += 1
            else: break
        mult = rule(k)
        out.append((t, p * mult)); closed.append((ex, p))
    return out

def st2(tr):
    s = pd.Series([p for t, p in tr], index=[t for t, p in tr]).sort_index(); eq = s.cumsum().to_numpy()
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(); d = s.groupby(s.index.date).sum()
    h1 = s[s.index < '2026-07-01'].sum(); h2 = s[s.index >= '2026-07-01'].sum()
    return f'profit ${s.sum():6,.0f} (H1 ${h1:,.0f} H2 ${h2:,.0f}) | biggest $ drop ${dd:,.0f} | worst day ${d.min():,.0f} | profit/drop {s.sum()/dd:.1f}'

if __name__ == '__main__':
    print('All at a 0.02 base (0.01 = half):')
    for name, rule in (('always 0.02', lambda k: 2), ('always 0.01', lambda k: 1),
                       ('0.01 after a loss, else 0.02', lambda k: 1 if k >= 1 else 2),
                       ('0.01 after 2 losses, else 0.02', lambda k: 1 if k >= 2 else 2),
                       ('0.01 after 3 losses, else 0.02', lambda k: 1 if k >= 3 else 2)):
        print(f'  {name:32}| {st2(run(rule))}')
