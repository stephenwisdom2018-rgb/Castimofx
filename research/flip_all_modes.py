"""Flips (after a stopped main/zone trade: opposite trade, stop 0.5x its risk, target 1.5x) in EVERY account mode,
2026 at 0.01, true stop sizes. Every start day checked for a blown account."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.mode200_flip as MF, research.start_200 as S, research.micro3_reentry as MR, research.micro3_zone as Z

ALL = MF.build()
def run(kinds, cap, maxopen, dedupe, use_flip, extra=None):
    tr = [x for x in ALL if x[4] in kinds] + (extra or [])
    queue = sorted([(x[0], 0, 'trade', x) for x in tr], key=lambda q: (q[0], q[1]))
    open_until, trades, seen = [], [], set()
    while queue:
        t, _, typ, x = queue.pop(0)
        open_until = [e for e in open_until if e > t]
        if typ == 'trade':
            tt, ex, p, risk, kind = x[:5]
            if risk > cap or len(open_until) >= maxopen: continue
            if dedupe and (tt, x[6]) in seen: continue
            seen.add((tt, x[6])); open_until.append(ex); trades.append((tt, ex, p, kind))
            if use_flip and kind == 'base' and p < 0:
                f = MF.flip_of(x)
                if f:
                    queue.append((f[0], 1, 'flip', f)); queue.sort(key=lambda q: (q[0], q[1]))
        else:
            ft, fex, fp, frk = x
            if frk > cap or len(open_until) >= maxopen: continue
            open_until.append(fex); trades.append((ft, fex, fp, 'flip'))
    return [(t, e, p) for t, e, p, k in trades], sum(k == 'flip' for *_, k in trades)

FE = [(x[0], x[6], x[1], abs(x[5] - x[4]) / 2, 'base', x[2], x[3], x[4]) for x in MR.FE]
FE_RE = [(a, c, b, -b if b < 0 else b / 2, 'm3', None, None, None) for a, b, c in MR.reentries(MR.FE, 1, '2R', with_exit=True)]
MODES = {'$100 mode': (dict(kinds=('base', 'm3', 'mz'), cap=10, maxopen=1, dedupe=False), 100),
         '$200 mode': (dict(kinds=('base', 'm3', 'mz'), cap=15, maxopen=1, dedupe=False), 200),
         '$400 mode': (dict(kinds=('base',), cap=1e9, maxopen=999, dedupe=True), 400),
         'Full': (dict(kinds=('base', 'm3', 'mz'), cap=1e9, maxopen=999, dedupe=False, extra=FE + FE_RE), 1000)}
if __name__ == '__main__':
    print(f'{"mode":10} {"flips":6}| profit  | win | flips | start-day blown | worst dip | Jan')
    for name, (kw, start) in MODES.items():
        for f in (False, True):
            tr, nf = run(use_flip=f, **kw)
            s = pd.Series([p for t, e, p in tr], index=[e for t, e, p in tr]).sort_index()
            r = S.risk(tr, start)
            jan = s[(s.index >= '2026-01-01') & (s.index < '2026-02-01')].sum()
            print(f'{name:10} {"on" if f else "off":6}| ${s.sum():6,.0f} | {100*(s>0).mean():3.0f}% | {nf:4} | {r["blown"]:5.1f}% at ${start} | ${r["worst"]:5.0f} | ${jan:4.0f}', flush=True)
