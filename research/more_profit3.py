"""More profit ideas on version B (stacking kept), 0.01, all filters on:
main re-entry target extra ($5/$15/$20 vs $10), main stop ($15/$25/$30 vs $20), zone 30 per structure / 30 days,
zone re-entry target 2.5x / 3x."""
import sys
sys.path.insert(0, '.')
import research.reentry_v2 as R, research.more_trades as M, research.more_trades2 as M2
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

def mains(sl=20, extra=10):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        sig = [s for s in M2.SIGS[fi] if s.with_boss]
        size = lambda s: abs(s.f - s.g)
        tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
        for tp in sorted({tp_of(s) for s in sig}):
            g = [s for s in sig if tp_of(s) == tp]
            out += [(x.time, x.pnl) for x in simulate_reentry(df, g, sl, tp, extra, 5, sp, pivot=0) if M.keep(fi, x.time, x.signal.direction)]
    return out

def zones(mp=20, mem=20, rr=2):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        out += [(x[0], x[1]) for x in zone(df, sp, mp, mem, main=False, reent=dict(swings='3', target='2R', max=1, rr=rr))[0] if M.keep(fi, x[0], x[4])]
    return out

if __name__ == '__main__':
    Z, Mn = zones(), mains()
    print(f'{"variant":34}| Jan-Jun | Jul-Nov | YEAR')
    print(f'{"version B":34}| {M.st(sorted(Z + Mn))}', flush=True)
    for e in (5, 15, 20):
        print(f'{f"main re-entry target +${e}":34}| {M.st(sorted(Z + mains(extra=e)))}', flush=True)
    for s in (15, 25, 30):
        print(f'{f"main stop ${s}":34}| {M.st(sorted(Z + mains(sl=s)))}', flush=True)
    for mp, mem in ((30, 20), (20, 30), (30, 30)):
        print(f'{f"zone {mp} per structure, {mem} days":34}| {M.st(sorted(zones(mp, mem) + Mn))}', flush=True)
    for rr in (2.5, 3):
        print(f'{f"zone re-entry target {rr}x":34}| {M.st(sorted(zones(rr=rr) + Mn))}', flush=True)
