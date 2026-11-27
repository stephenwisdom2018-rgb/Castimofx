"""Search a '$200 mode': which trades to take so a $200 account at 0.01 never (or almost never) blows, whatever the
start day. Levers: version (C / C+3m+MZ / Chosen), no copies, max open trades (1/2), stop cap ($15/$20/$30).
Stop size estimate: loser = its loss; winner = target/2 (2x-risk trades), main stop $30."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.start_200 as S

V = S.versions()
def risk_of(p): return -p if p < 0 else p / 2
rows = []
for (vname, tr), dedupe, maxopen, cap in itertools.product(V.items(), (False, True), (99, 2, 1), (1e9, 30, 20, 15)):
    tr2 = sorted(tr); kept = []; seen = set(); open_ = []
    for t, e, p in tr2:
        if risk_of(p) > cap: continue
        if dedupe and t in seen: continue
        open_ = [x for x in open_ if x > t]
        if len(open_) >= maxopen: continue
        kept.append((t, e, p)); seen.add(t); open_.append(e)
    r = S.risk(kept); prof = sum(p for _, _, p in kept)
    rows.append(dict(version=vname, no_copies=dedupe, max_open=maxopen, stop_cap=cap if cap < 1e8 else None, profit=prof,
                     blown=r['blown'], lose150=r['danger'], worst_dip=r['worst'], trades=len(kept)))
T = pd.DataFrame(rows); T.to_csv('research/mode_200.csv', index=False)
pd.set_option('display.width', 200)
print('Never blown at $200 (best profit):')
print(T[T.blown == 0].sort_values('profit', ascending=False).head(8).round(1).to_string(index=False))
print('\nBlown <= 2% of start days:')
print(T[T.blown <= 2].sort_values('profit', ascending=False).head(5).round(1).to_string(index=False))
