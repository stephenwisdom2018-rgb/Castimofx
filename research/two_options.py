"""Two more profit options on the chosen version (all filters, stacking kept, 0.01):
1. zone below A: G past A (up to one E-A depth beyond), same zone trade rules, added to the E-A zone trades
2. faster zone entry: break of the first H after G, without waiting for I (replaces the E-A zone trades)"""
import sys
sys.path.insert(0, '.')
import numpy as np
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone

RE = dict(swings='3', target='2R', max=1)
def zones(**kw):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        out += [(x[0], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE, **kw)[0] if M.keep(fi, x[0], x[4])]
    return out

if __name__ == '__main__':
    Z, Mn = zones(), P.mains(sl=30, extra=15)
    print(f'{"variant":34}| Jan-Jun | Jul-Nov | YEAR')
    print(f'{"chosen":34}| {M.st(sorted(Z + Mn))}', flush=True)
    BA = zones(region='BA')
    print(f'below-A zone alone: {len(BA)} tr, {100*np.mean([p>0 for t,p in BA]):.0f}% win, ${sum(p for t,p in BA):.0f}')
    print(f'{"+ zone below A":34}| {M.st(sorted(Z + Mn + BA))}', flush=True)
    F = zones(need_i=False)
    print(f'{"faster zone entry (no I)":34}| {M.st(sorted(F + Mn))}', flush=True)
    print(f'{"faster entry + zone below A":34}| {M.st(sorted(F + Mn + zones(region="BA", need_i=False)))}', flush=True)
