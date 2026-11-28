"""Owner's next day plan: (1) PROTECT PROFIT: once the day is in profit, stop for the day when it falls $G from the
day's best closed level; (2) COMING FROM A LOSS: if the day was red, stop as soon as it is back to $R (0 or +20).
No fixed target. Compared with the current rule (+$20 target or break-even after a loss).
Quality hours on, true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_stop as DS

def kept(X, G=None, R=0, tgt=None, minpeak=0):
    out = []; day = None
    for e, ex, p in X:
        if day != e.date(): day, taken, neg, peak = e.date(), [], False, 0.0
        closed = sum(q for e2, ex2, q in taken if ex2 <= e)
        if closed < 0: neg = True
        peak = max(peak, closed)
        if tgt and closed >= tgt: continue
        if neg and closed >= R: continue
        if G and peak > minpeak and closed <= peak - G: continue
        taken.append((e, ex, p)); out.append((e, ex, p))
    return out

def stats(k):
    s = pd.Series([q[2] for q in k], index=[q[1] for q in k]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(DS.DAYS, fill_value=0); w = d.resample('W').sum(); m = d.resample('ME').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': round(s.sum()), 'Green d %': round(100 * (d > 0).mean()), 'Worst d': round(d.min()), 'Worst wk': round(w.min()),
            'Worst mo': round(m.min()), 'Drawdown': round(mb)}

RULES = {'now: +20 / BE': dict(tgt=20, R=0), 'give back 20 / BE': dict(G=20, R=0), 'give back 40 / BE': dict(G=40, R=0),
         'give back 60 / BE': dict(G=60, R=0), 'give back 40 / +20': dict(G=40, R=20), 'give back 60 / +20': dict(G=60, R=20),
         'give back 40 (peak>40) / BE': dict(G=40, R=0, minpeak=40)}
if __name__ == '__main__':
    for v, X in DS.V.items():
        print(DS.Y, v); print(pd.DataFrame({k: stats(kept(X, **kw)) for k, kw in RULES.items()}).T.to_string(), flush=True)
