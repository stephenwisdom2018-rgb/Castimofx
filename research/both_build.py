"""Build every part of the bot WITHOUT filters on CASTIMO_FILES and save tagged trades to research/both_<tag>.pkl.
Parts: main (stop 30 / extra 15, small-structure target), main20 (stop 20 / extra 10), E-A zone 40/20 and 20/20,
F-E zone, MZ, double bottom, 3-micro re-entries after each part's stops. Tags at entry: rsi side ok, hour, rng60, adx."""
import sys, os, pickle
sys.path.insert(0, '.')
import research.more_trades as M
M_keep_real = M.keep
M.keep = lambda fi, t, d: True                       # build without filters
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_profit3 as P, research.micro3_reentry as MR, research.micro3_zone as Z, research.strong_base as S
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
def mains(sl, extra, small=True):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
        tp_of = (lambda s: max(5, int(size(s))) if size(s) < 20 else 20) if small else (lambda s: 20)
        for tp in sorted({tp_of(s) for s in sig}):
            for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], sl, tp, extra, 5, sp, pivot=0):
                d = x.signal.direction; T = x.signal.entry + d * (tp + (extra if 're-entry' in x.reason else 0))
                out.append((x.time, x.pnl, fi, d, x.entry, T, x.exit_time))
    return out
def zones(per, mem, region='EA'):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        for x in zone(df, sp, per, mem, main=False, reent=RE, region=region)[0]:
            dist = x[1] if x[1] > 0 else -2 * x[1]
            out.append((x[0], x[1], fi, x[4], x[13], x[13] + x[4] * dist, x[2]))
    return out
parts = {'main': mains(30, 15), 'main20': mains(20, 10), 'main_nosmall': mains(30, 15, False),
         'ea40': zones(40, 20), 'ea20': zones(20, 20), 'ea10': zones(10, 10), 'fe': zones(40, 20, 'FE')}
parts['mz'] = [(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
seen = set(); db = []
for x in sorted(S.double_bottom(2, detail=True)):
    if x[0] not in seen: seen.add(x[0]); db.append((x[0], x[1], x[2], x[4], x[5], x[5] + x[4] * x[6], x[7]))
parts['db'] = db
for k in ('main', 'ea40', 'fe', 'mz', 'db'):
    parts['re3_' + k] = [(t, p, None, None, None, None, None) for t, p in MR.reentries(parts[k], 1, '2R')]
# re-entry trades need file/direction for tags: recompute with a small wrapper
def re_tagged(lst):
    out = []
    for t, p, fi, d, e, T, ex in lst:
        if p >= 0: continue
        r = MR.reentries([(t, p, fi, d, e, T, ex)], 1, '2R')
        out += [(tt, pp, fi, d, None, None, None) for tt, pp in r]
    return out
for k in ('main', 'ea40', 'fe', 'mz', 'db'):
    parts['re3_' + k] = re_tagged(parts[k])
# tags
FEAT = M.FEAT
def tag(lst):
    rows = []
    for t, p, fi, d, *_ in lst:
        f = FEAT[fi].loc[t]
        rows.append(dict(time=t, pnl=p, d=d, rsi_ok=bool((f.rsi >= 50) if d == 1 else (f.rsi <= 50)), hour=t.hour,
                         rng60=f.rng60, adx=f.adx))
    return pd.DataFrame(rows)
out = {k: tag(v) for k, v in parts.items()}
tagname = os.environ.get('BOTH_TAG', 'x')
pickle.dump(out, open(f'research/both_{tagname}.pkl', 'wb'))
print({k: len(v) for k, v in out.items()})
