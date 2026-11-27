"""How many times did price test the zone (separate visits below E for buys) before each zone trade?
Do later tests (a firmer level) win more? What happens to the trade count if we require 2+ or 3+ tests, or only the 1st?
Chosen version, all filters, stacking kept, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.client_report as C
from research.zone_multi import zone

RE = dict(swings='3', target='2R', max=1)
Z = []
for fi, (df, sp, *_) in enumerate(R.prep):
    Z += [(x[0], x[1], x[-1]) for x in zone(df, sp, 40, 20, main=False, reent=RE)[0] if M.keep(fi, x[0], x[4])]
T = pd.DataFrame(Z, columns=['time', 'pnl', 'tests']); T['half'] = np.where(T.time < '2026-07-01', 'H1', 'H2')
print('Zone trades by number of tests of the zone before entry:')
T['b'] = pd.cut(T.tests, [0, 1, 2, 3, 5, 1000], labels=['1st test', '2nd', '3rd', '4th-5th', '6th+'])
for b, g in T.groupby('b', observed=True):
    a, z = g[g.half == 'H1'], g[g.half == 'H2']
    print(f'  {b:9} | {len(a):3} tr {100*(a.pnl>0).mean():3.0f}% ${a.pnl.sum():5.0f} | {len(z):3} tr {100*(z.pnl>0).mean():3.0f}% ${z.pnl.sum():5.0f}')
Mn = P.mains(sl=30, extra=15)
print(f'\n{"rule":22}| Jan-Jun | Jul-Nov | YEAR | trades/day')
for name, keep in (('all (chosen)', T.tests >= 0), ('only 1st test', T.tests == 1), ('2+ tests', T.tests >= 2), ('3+ tests', T.tests >= 3)):
    tr = sorted(list(zip(T[keep].time, T[keep].pnl)) + Mn)
    print(f'{name:22}| {M.st(tr)} | {len(tr)/C.DAYS:.1f}')
