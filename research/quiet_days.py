"""Trades for quiet days. Live rule: an extra trade is allowed only if the bot has taken NO trade yet today
(max N extra per day). Extra pools: F-E zone trades (filtered), and trades the filters blocked (zone + main)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_profit3 as P, research.more_trades as M, research.bad_days as B
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
FE, BLOCKED = [], []
for fi, (df, sp, *_) in enumerate(R.prep):
    FE += [(x[0], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE, region='FE')[0] if M.keep(fi, x[0], x[4])]
    BLOCKED += [(x[0], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE)[0] if not M.keep(fi, x[0], x[4])]
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        BLOCKED += [(x.time, x.pnl) for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0)
                    if not M.keep(fi, x.time, x.signal.direction)]

def add_quiet(pool, n_max):
    first = {}
    for t, p in BASE: first[t.date()] = min(first.get(t.date(), t), t)
    out, cnt = [], {}
    for t, p in sorted(pool):
        dday = t.date()
        if dday in first and first[dday] <= t: continue                 # bot already traded today
        if cnt.get(dday, 0) >= n_max: continue
        cnt[dday] = cnt.get(dday, 0) + 1; out.append((t, p))
    return out

if __name__ == '__main__':
    print('BASE:', M.st(sorted(BASE)))
    for name, pool in (('F-E zone', FE), ('blocked trades', BLOCKED), ('both', FE + BLOCKED)):
        for n in (1, 2, 99):
            ex = add_quiet(pool, n)
            print(f'\n+ {name}, max {n} extra on quiet days: {len(ex)} extra trades, {100*np.mean([p>0 for t,p in ex]):.0f}% win, ${sum(p for t,p in ex):.0f}')
            print('  ', M.st(sorted(BASE + ex)))
            B.report('  days', BASE + ex)
