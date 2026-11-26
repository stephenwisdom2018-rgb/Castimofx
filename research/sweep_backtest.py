"""Backtest of the Castimofx sweep strategy on XAUUSDb M1 (run: python research/sweep_backtest.py)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate

CSV = 'data/XAUUSDb_M1_2026-08_2026-11.csv'
df = load_csv(CSV)
spread = pd.read_csv(CSV, sep='\t')['<SPREAD>'].to_numpy(float) / 100
start = df.index.searchsorted(pd.Timestamp('2026-10-01'))
days = df.index[start:].normalize().unique()

def per_day(sig):
    s = pd.Series(1, index=[df.index[x.bar].normalize() for x in sig]).groupby(level=0).sum()
    return s.reindex(days, fill_value=0)

def summary(tr):
    p = np.array([x.pnl for x in tr])
    eq = np.cumsum(p); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(p) else 0
    return dict(trades=len(p), tp=sum(x.reason == 'TP' for x in tr), sl=sum(x.reason == 'SL' for x in tr),
                other=sum(x.reason not in ('TP', 'SL') for x in tr), win=round(100 * (p > 0).mean(), 1) if len(p) else 0,
                net=round(p.sum(), 2), worst_dd=round(dd, 2))

if __name__ == '__main__':
    results = {}
    for name, kw in [('v1 strict (RSI 70/30, no continuation)', dict(hi_level=70, lo_level=30, continuation=False)),
                     ('v2 RSI 68/32, tol $0', dict(tol=0.0)),
                     ('v2 RSI 68/32, tol $0.50', dict(tol=0.5)),
                     ('v2 RSI 68/32, tol $1', dict(tol=1.0))]:
        sig, _ = find_signals(df, **kw)
        sig = [s for s in sig if s.bar >= start]
        pdy = per_day(sig)
        print(f'\n=== {name}: {len(sig)} signals, {pdy.mean():.2f}/day, days with 0: {(pdy==0).sum()}/{len(pdy)}, max/day {pdy.max()}')
        rows = []
        for sl, tp in [(10, 10), (15, 15), (20, 15), (20, 20), (25, 15), (30, 15), (30, 20), (30, 30)]:
            rows.append({'SL$': sl, 'TP$': tp, **summary(simulate(df, sig, 'fixed', sl, tp, spread))})
        for buf, rr in [(0.5, 1), (0.5, 2)]:
            rows.append({'SL$': f'G+{buf}', 'TP$': f'{rr}R', **summary(simulate(df, sig, 'g', buf, rr, spread))})
        print(pd.DataFrame(rows).to_string(index=False))
        results[name] = sig
