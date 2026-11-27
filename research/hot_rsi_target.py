"""Bigger target for trades where RSI is already 68+ at entry (32- for sells), chosen version, all filters, 0.01.
Zone: target hot_rr x risk (vs 2x). Main first entry: target $X (vs $20, small structures keep their own target)."""
import sys
sys.path.insert(0, '.')
import numpy as np
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
def zones(hot):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        out += [(x[0], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE, hot_rr=hot)[0] if M.keep(fi, x[0], x[4])]
    return out
def mains(hot_tp):
    out = []
    for fi, (df, sp, r, *_) in enumerate(R.prep):
        r = np.asarray(r); sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
        def tp_of(s):
            if size(s) < 20: return max(5, int(size(s)))
            hot = (r[s.bar] >= 68) if s.direction == 1 else (r[s.bar] <= 32)
            return hot_tp if (hot_tp and hot) else 20
        for tp in sorted({tp_of(s) for s in sig}):
            out += [(x.time, x.pnl) for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0) if M.keep(fi, x.time, x.signal.direction)]
    return out

if __name__ == '__main__':
    Z0, M0 = zones(None), mains(None)
    print(f'{"variant":32}| Jan-Jun | Jul-Nov | YEAR')
    print(f'{"chosen":32}| {M.st(sorted(Z0 + M0))}', flush=True)
    for h in (2.5, 3, 4):
        print(f'{f"zone hot target {h}x":32}| {M.st(sorted(zones(h) + M0))}', flush=True)
    for t in (30, 40):
        print(f'{f"main hot target ${t}":32}| {M.st(sorted(Z0 + mains(t)))}', flush=True)
