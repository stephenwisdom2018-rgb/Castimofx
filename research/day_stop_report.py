"""Best/worst day, week, month and worst drawdown for Chosen / +Both / Robust with the owner's day rule
(stop at +$20, or at break-even after a loss). Quality hours on, true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_stop as DS

def kept(X, tgt=20, be=True):
    out = []; day = None
    for e, ex, p in X:
        if day != e.date(): day, taken, neg = e.date(), [], False
        closed = sum(q for e2, ex2, q in taken if ex2 <= e)
        if closed < 0: neg = True
        if (tgt and closed >= tgt) or (be and neg and closed >= 0): continue
        taken.append((e, ex, p)); out.append((e, ex, p))
    return out

cols = {}
for v, X in DS.V.items():
    k = kept(X)
    s = pd.Series([q[2] for q in k], index=[q[1] for q in k]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(DS.DAYS, fill_value=0)
    w = d.resample('W').sum(); m = d.resample('ME').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    cols[v] = {'Profit': f'${s.sum():,.0f}', 'Best day': f'${d.max():,.0f}', 'Worst day': f'${d.min():,.0f}', 'Best week': f'${w.max():,.0f}',
               'Worst week': f'${w.min():,.0f}', 'Best month': f'${m.max():,.0f}', 'Worst month': f'${m.min():,.0f}',
               'Worst drawdown': f'${mb:,.0f}', 'Safe bal': f'${1.5*mb:,.0f}'}
print(DS.Y); print(pd.DataFrame(cols).to_string())
