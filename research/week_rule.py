"""Owner: on top of the day rule (+$20 or break-even after a red start), a WEEK rule: stop opening trades for the rest
of the week at +$W, or at -$L, or at break-even after a red week start. Restart Monday. Chosen / +Both / Robust,
quality hours, true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_stop as DS

def kept(X, W=None, L=None, wbe=False):
    out = []; day = wk = None
    for e, ex, p in X:
        k = e.isocalendar()[:2]
        if wk != k: wk, wtaken, wneg = k, [], False
        if day != e.date(): day, taken, neg = e.date(), [], False
        closed = sum(q for e2, ex2, q in taken if ex2 <= e); wclosed = sum(q for e2, ex2, q in wtaken if ex2 <= e)
        if closed < 0: neg = True
        if wclosed < 0: wneg = True
        if closed >= 20 or (neg and closed >= 0): continue
        if (W and wclosed >= W) or (L and wclosed <= -L) or (wbe and wneg and wclosed >= 0): continue
        taken.append((e, ex, p)); wtaken.append((e, ex, p)); out.append((e, ex, p))
    return out

def stats(k):
    s = pd.Series([q[2] for q in k], index=[q[1] for q in k]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(DS.DAYS, fill_value=0); w = d.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': round(s.sum()), 'Green wk %': round(100 * (w > 0).mean()), 'Red wk %': round(100 * (w < 0).mean()),
            'Worst wk': round(w.min()), 'Green d %': round(100 * (d > 0).mean()), 'Min bal': round(mb)}

RULES = {'day rule only': {}, 'week +$60': dict(W=60), 'week +$100': dict(W=100), 'week -$60': dict(L=60), 'week -$100': dict(L=100),
         'week BE': dict(wbe=True), 'week +$100 & BE': dict(W=100, wbe=True), 'week +$100 & -$100': dict(W=100, L=100)}
if __name__ == '__main__':
    for v, X in DS.V.items():
        print(DS.Y, v); print(pd.DataFrame({k: stats(kept(X, **kw)) for k, kw in RULES.items()}).T.to_string(), flush=True)
