"""Run the saved final plan on any XAUUSDb M1 export, month by month.
Usage: python research/final_plan_test.py data/XAUUSDb_M1_2026-01_2026-04.csv"""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry

csv = sys.argv[1]
df = load_csv(csv)
spread = pd.read_csv(csv, sep='\t')['<SPREAD>'].to_numpy(float) / 100
sig, _ = find_signals(df, tol=1.0, minor_e=5)
sig = [s for s in sig if s.with_boss and s.bar >= 600]  # skip the first 10 hours (warm-up)
tr = simulate_reentry(df, sig, 20, 20, 10, 5, spread, pivot=3, later_pivot=0)
n_of = lambda x: int(m.group(1)) if (m := re.search(r're-entry (\d)', x.reason)) else 0
p = np.array([x.pnl * (2 if n_of(x) % 2 == 1 else 1) for x in tr])  # alternating lots, base 0.01
t = pd.Series(p, index=[x.time for x in tr])
print(f'{csv}: {df.index[0]} -> {df.index[-1]}')
for m, g in t.groupby(t.index.to_period('M')):
    eq = g.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    days = df.loc[str(m)].index.normalize().nunique()
    print(f'  {m}: trades {len(g):3} ({len(g)/max(days,1):.1f}/day)  net ${g.sum():8.2f}  worst drop ${(eq-pk).min():8.2f}  win {100*(g>0).mean():.0f}%')
eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
print(f'  TOTAL: trades {len(p)}  net ${p.sum():.2f}  worst drop ${(eq-pk).min():.2f}  (base 0.01, re-entries alternate 0.02/0.01)')
w = t.resample('W').sum(); print(f'  losing weeks {(w<0).sum()}/{len(w)}')
