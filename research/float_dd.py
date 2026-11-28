"""Max drawdown INCLUDING open trades (marked every hour) for Chosen / +Both / Robust with quality hours + day rule
(+$20 or break-even after a red start), true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_stop as DS, research.micro3_reentry as MR, research.micro3_zone as Z, research.reentry_v2 as R

df, sp = R.prep[0][0], R.prep[0][1]; c = df.close.to_numpy(); idx = df.index
MZd = [(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
def lst(base, re_of):
    out = [(pd.Timestamp(x[0]), pd.Timestamp(x[6]), x[1], x[3], x[4]) for x in base]
    for x in re_of:
        for t, p, ex in MR.reentries([x], 1, '2R', with_exit=True):
            u = idx.get_loc(t); d = x[3]
            out.append((pd.Timestamp(t), pd.Timestamp(ex), p, d, c[u] + (sp[u] if d == 1 else 0)))
    return sorted(x for x in out if DS.S <= str(x[0]) < DS.E)
V = {'Chosen': lst(MR.CH + MR.FE + MZd, MR.CH + MR.FE), '+Both': lst(MR.CH + MR.FE + MR.DB + MZd, MR.CH + MR.FE + MR.DB),
     'Robust': lst(MR.MAIN + MR.EAZ + MZd + MR.DB, MZd + MR.DB)}

def kept(X):
    out = []; day = None
    for x in X:
        e, ex, p = x[:3]
        if day != e.date(): day, taken, neg = e.date(), [], False
        closed = sum(q[2] for q in taken if q[1] <= e)
        if closed < 0: neg = True
        if closed >= 20 or (neg and closed >= 0): continue
        taken.append(x); out.append(x)
    return out

grid = idx[(idx >= DS.S) & (idx < DS.E)]; grid = grid[grid.minute == 0]; gi = idx.get_indexer(grid)
cols = {}
for v, X in V.items():
    K = kept(X); eq = np.zeros(len(grid)); closed_only = []
    for e, ex, p, d, ent in K:
        a = np.searchsorted(grid, e); b = np.searchsorted(grid, ex)
        if b > a: eq[a:b] += (c[gi[a:b]] - ent) * d
        eq[b:] += p
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    s = pd.Series([q[2] for q in K], index=[q[1] for q in K]).sort_index().cumsum().to_numpy()
    ddc = -(s - np.maximum.accumulate(np.r_[0, s])[1:]).min()
    cols[v] = {'Closed-only drawdown': f'${ddc:,.0f}', 'With open trades': f'${dd:,.0f}', 'Safe (1.5x)': f'${1.5*dd:,.0f}'}
print(DS.Y); print(pd.DataFrame(cols).to_string())
