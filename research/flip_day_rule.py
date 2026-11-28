"""Flip re-test with the new rules: after a main or zone trade hits its stop, trade the other way at the stop price:
stop = half the stopped trade's risk, target = 1.5x that stop (as EA FLIP), filters on (incl. quality hours).
Flips obey the day rule like any trade. Chosen / +Both / Robust, true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_stop as DS, research.day_stop_report as DR, research.micro3_reentry as MR, research.reentry_v2 as R, research.more_trades as M

df, sp = R.prep[0][0], R.prep[0][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
MAIN_IDS = {id(x) for x in MR.MAIN}
def flips(tr):
    out = []
    for x in tr:
        t, p, fi, d, e, T, ex = x
        if p >= 0: continue
        risk = 30.0 if id(x) in MAIN_IDS else abs(T - e) / 2
        j = df.index.get_loc(ex); fd = -d
        if not M.keep(0, ex, fd): continue
        px = e - d * risk; ent = px + (sp[j] if fd == 1 else 0); rk = risk * 0.5; stop, tgt = ent - fd * rk, ent + fd * 1.5 * rk
        for v in range(j + 1, n):
            if (l[v] <= stop) if fd == 1 else (h[v] + sp[v] >= stop): out.append((pd.Timestamp(ex), df.index[v], -rk)); break
            if (h[v] >= tgt) if fd == 1 else (l[v] + sp[v] <= tgt): out.append((pd.Timestamp(ex), df.index[v], 1.5 * rk)); break
    return [x for x in out if DS.S <= str(x[0]) < DS.E]

FL = {'Chosen': flips(MR.CH + MR.FE), '+Both': flips(MR.CH + MR.FE), 'Robust': flips(MR.MAIN + MR.EAZ)}
def stats(k):
    s = pd.Series([q[2] for q in k], index=[q[1] for q in k]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(DS.DAYS, fill_value=0); w = d.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': round(s.sum()), 'Green d %': round(100 * (d > 0).mean()), 'Green wk %': round(100 * (w > 0).mean()),
            'Worst d': round(d.min()), 'Min bal': round(mb)}
rows = {}
for v, X in DS.V.items():
    rows[f'{v}'] = stats(DR.kept(X))
    rows[f'{v} + flip'] = stats(DR.kept(sorted(X + FL[v])))
    f = FL[v]; print(DS.Y, v, f'flips: {len(f)}, win {100*np.mean([q[2]>0 for q in f]):.0f}%, alone ${sum(q[2] for q in f):,.0f}')
print(DS.Y); print(pd.DataFrame(rows).T.to_string())
