"""Money management on top of the day rule (+$20 or break-even after a red start): (1) max copies of the same setup
(same entry minute, same result = stacked copy), (2) max trades open at once. Chosen / +Both / Robust, quality hours,
true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_stop as DS

def kept(X, copies=None, maxopen=None):
    out = []; day = None; cnt = {}
    for e, ex, p in X:
        if day != e.date(): day, taken, neg = e.date(), [], False
        closed = sum(q for e2, ex2, q in taken if ex2 <= e)
        if closed < 0: neg = True
        if closed >= 20 or (neg and closed >= 0): continue
        key = (e, ex, round(p, 2))
        if copies and cnt.get(key, 0) >= copies: continue
        if maxopen and sum(1 for e2, ex2, q in out if ex2 > e) >= maxopen: continue
        cnt[key] = cnt.get(key, 0) + 1; taken.append((e, ex, p)); out.append((e, ex, p))
    return out

def stats(k):
    s = pd.Series([q[2] for q in k], index=[q[1] for q in k]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(DS.DAYS, fill_value=0); w = d.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': round(s.sum()), 'Green d %': round(100 * (d > 0).mean()), 'Green wk %': round(100 * (w > 0).mean()),
            'Worst d': round(d.min()), 'Worst wk': round(w.min()), 'Min bal': round(mb)}

RULES = {'day rule only': {}, 'copies 1': dict(copies=1), 'copies 2': dict(copies=2), 'copies 3': dict(copies=3),
         'max open 3': dict(maxopen=3), 'max open 5': dict(maxopen=5), 'max open 8': dict(maxopen=8), 'copies 2 + open 5': dict(copies=2, maxopen=5)}
if __name__ == '__main__':
    for v, X in DS.V.items():
        print(DS.Y, v); print(pd.DataFrame({k: stats(kept(X, **kw)) for k, kw in RULES.items()}).T.to_string(), flush=True)
