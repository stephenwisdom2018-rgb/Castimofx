"""More options on top of version B (lot size left for last), 0.01, all filters on:
1. main: also take against-boss signals
2. main: bigger target ($30 / $40) when F - G is $50 or more
3. zone: also trade G sweeps between F and E (shallow pullback)"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.reentry_v2 as R
import research.more_trades as M
from research.zone_multi import zone, KW
from castimofx.sweep import find_signals, simulate_reentry

RE1 = dict(swings='3', target='2R', max=1)
SIGS = []
for df, sp, *_ in R.prep:
    sig, _ = find_signals(df, **KW); SIGS.append([s for s in sig if s.bar >= 600])

def main_trades(boss_only=True, big=None):
    out = []
    for fi, (df, sp, *_ ) in enumerate(R.prep):
        sig = [s for s in SIGS[fi] if s.with_boss or not boss_only]
        size = lambda s: abs(s.f - s.g)
        def tp_of(s):
            if size(s) < 20: return max(5, int(size(s)))
            return big if (big and size(s) >= 50) else 20
        for tp in sorted({tp_of(s) for s in sig}):
            g = [s for s in sig if tp_of(s) == tp]
            out += [(x.time, x.pnl) for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0) if M.keep(fi, x.time, x.signal.direction)]
    return out

def zone_trades(region='EA'):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        out += [(x[0], x[1]) for x in zone(df, sp, 20, 20, main=False, reent=RE1, region=region)[0] if M.keep(fi, x[0], x[4])]
    return out

if __name__ == '__main__':
    Z, Mn = zone_trades(), main_trades()
    print(f'{"variant":40}| Jan-Jun | Jul-Nov | YEAR')
    print(f'{"version B (current)":40}| {M.st(sorted(Z + Mn))}', flush=True)
    print(f'{"+ main against-boss signals":40}| {M.st(sorted(Z + main_trades(boss_only=False)))}', flush=True)
    for b in (30, 40):
        print(f'{f"main target ${b} when F-G >= $50":40}| {M.st(sorted(Z + main_trades(big=b)))}', flush=True)
    FE = zone_trades('FE')
    print(f'{"+ zone between F and E":40}| {M.st(sorted(Z + Mn + FE))}', flush=True)
    print(f'{"   F-E zone alone":40}| {M.st(sorted(FE))}', flush=True)
