"""Owner: after a winning target, price pulls back INTO the entry-target band but never back to the entry, builds a
base (a quiet range for some hours) and continues. Entry: break of the base high, or break of the high made after
the target. Stop $1 below the base low (min $5), target 2x risk. Search 24 h after the target. All filters, 0.01."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
WIN = []                                              # (file, exit bar, d, entry, target)
for fi, (df, sp, *_) in enumerate(R.prep):
    idx = df.index
    for x in zone(df, sp, 40, 20, main=False, reent=RE)[0]:
        if M.keep(fi, x[0], x[4]) and x[1] > 0: WIN.append((fi, idx.get_loc(x[2]), x[4], x[13], x[13] + x[4] * x[1]))
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0):
            if M.keep(fi, x.time, x.signal.direction) and x.pnl > 0:
                WIN.append((fi, idx.get_loc(x.exit_time), x.signal.direction, x.entry, x.exit))
WIN = sorted(set(WIN))
DATA = [(df.high.to_numpy(), df.low.to_numpy(), df.index, sp) for df, sp, *_ in R.prep]

def run(base_min, trigger, max_range=None):
    out, used = [], set()
    for fi, b, d, entry0, tp0 in WIN:
        h, l, idx, sp = DATA[fi]; n = len(h); e = min(n, b + 1440)
        top = None; in_band = False; start = None
        for i in range(b + 1, e):
            if (l[i] <= entry0) if d == 1 else (h[i] >= entry0): break                 # back to the entry: cancel
            prev_top = top
            top = (max(top, h[i]) if d == 1 else min(top, l[i])) if top is not None else (h[i] if d == 1 else l[i])
            if not in_band and ((l[i] < tp0) if d == 1 else (h[i] > tp0)): in_band, start = True, i
            if not in_band or i - start < base_min: continue
            seg_h, seg_l = h[i - base_min:i].max(), l[i - base_min:i].min()
            if max_range and seg_h - seg_l > max_range: continue
            lvl = (seg_h if d == 1 else seg_l) if trigger == 'base high' else prev_top
            if (h[i] > lvl) if d == 1 else (l[i] < lvl):
                key = (fi, i, d)
                if key in used or not M.keep(fi, idx[i], d): break
                used.add(key)
                base = seg_l if d == 1 else seg_h
                ent = lvl + (sp[i] if d == 1 else 0); risk = max(abs(ent - base) + 1, 5)
                stop, tgt = ent - d * risk, ent + d * 2 * risk
                for v in range(i, n):
                    if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): out.append((idx[i], -risk)); break
                    if v > i and ((h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt)): out.append((idx[i], 2 * risk)); break
                break
    return out

if __name__ == '__main__':
    BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
    print('BASE                                  |', M.st(sorted(BASE)))
    for trig in ('base high', 'post-target high'):
        for bm in (60, 120, 240):
            for mr in (None, 10):
                ex = run(bm, trig, mr)
                if not ex: print(f'{trig}, base {bm}m, range<={mr}: no trades'); continue
                print(f'{trig}, base {bm}m, range {"any" if mr is None else "<=$"+str(mr)}: {len(ex)} tr, {100*np.mean([p>0 for t,p in ex]):.0f}% win, ${sum(p for t,p in ex):.0f}')
                print('  + BASE                              |', M.st(sorted(BASE + ex)), flush=True)
