"""Owner's version of the 3-micro entry: AFTER H has broken, price comes back BELOW H (G not broken), then '3 micro
inside SMA 10' -> enter. Up to N per H, within 24 h of the break. Stop $1 beyond G or beyond the lowest point since the
break (min $5); target 2x risk. H breaks from main signals and zone trades (EA; F-E too for +Both). 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.micro3_reentry as MR, research.more_profit3 as P
from research.zone_multi import zone

RE = dict(swings='3', target='2R', max=1)
HB = {'EA': [], 'FE': [], 'main': []}                 # (file, break bar, d, H, G)
for fi, (df, sp, *_) in enumerate(R.prep):
    for region in ('EA', 'FE'):
        for x in zone(df, sp, 40, 20, main=False, reent=RE, region=region)[0]:
            if x[6] == -1: continue                      # zone re-entries are not H breaks
            d, u, H = x[4], x[12], x[13] - (sp[x[12]] if x[4] == 1 else 0)
            HB[region].append((fi, u, d, H, H - d * x[11]))
    for s in P.M2.SIGS[fi]:
        if s.with_boss: HB['main'].append((fi, s.bar, s.direction, s.entry, s.g))
for k in HB: HB[k] = sorted(set(HB[k]))

def run(sources, per=1, stop_mode='G', hours=24):
    out, seen = [], set()
    for src in sources:
        for fi, b, d, H, G in HB[src]:
            o, h, l, c, sp, idx, up, dn = MR.ARR[fi]; n = len(c); sig = up if d == 1 else dn
            below = False; taken = 0; u = b + 1
            while u < min(n, b + hours * 60) and taken < per:
                if (l[u] < G) if d == 1 else (h[u] > G): break
                if (c[u] < H) if d == 1 else (c[u] > H): below = True
                if below and sig[u]:
                    key = (idx[u], d)
                    if key not in seen and M.keep(fi, idx[u], d):
                        seen.add(key); taken += 1
                        ent = c[u] + (sp[u] if d == 1 else 0)
                        ext = G if stop_mode == 'G' else (l[b:u+1].min() if d == 1 else h[b:u+1].max())
                        risk = max(abs(ent - ext) + 1, 5); stop, tgt = ent - d * risk, ent + d * 2 * risk
                        res = None
                        for v in range(u + 1, n):
                            if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res = -risk; break
                            if (h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt): res = 2 * risk; break
                        if res is None: break
                        out.append((idx[u], res)); below = False; u = v + 1; continue
                u += 1
    return out

if __name__ == '__main__':
    bases = {'C+3m': ([(x[0], x[1]) for x in MR.CH] + MR.reentries(MR.CH, 1, '2R'), ('main', 'EA')),
             'B+3m': ([(x[0], x[1]) for x in MR.CH + MR.EX] + MR.reentries(MR.CH + MR.EX, 1, '2R'), ('main', 'EA', 'FE'))}
    for v, (b, srcs) in bases.items():
        print(f'{v:5}                     | {M.st(sorted(b)).split("|")[-1].strip()}')
        for per in (1, 3):
            for sm in ('G', 'low'):
                ex = run(srcs, per, sm)
                print(f'{v:5} +afterH {per}/H stop {sm:3} | {M.st(sorted(b + ex)).split("|")[-1].strip()} | extra {len(ex)} tr {100*np.mean([p>0 for t,p in ex]):.0f}% ${sum(p for t,p in ex):.0f}', flush=True)
