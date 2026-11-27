"""Evaluate any combination of parts and filters on 2025 (Jan-Jul) and 2026 (Jan-Nov) from research/both_*.pkl.
A rule is kept only if it helps BOTH years."""
import pickle, itertools
import numpy as np, pandas as pd
D = {y: pickle.load(open(f'research/both_{y}.pkl', 'rb')) for y in ('2025', '2026')}

def filt(df, rsi=True, hours=True, cons=True):
    k = np.ones(len(df), bool)
    if rsi: k &= df.rsi_ok.to_numpy()
    if hours: k &= ~df.hour.isin([15, 23]).to_numpy()
    if cons: k &= ~((df.rng60 < 0.6) | ((df.adx > 25) & (df.adx <= 35))).to_numpy()
    return df[k]

def run(parts, **f):
    res = {}
    for y, P in D.items():
        s = pd.concat([filt(P[p], **f) for p in parts]).sort_values('time')
        q = s.pnl.to_numpy(); eq = q.cumsum(); dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
        months = 7 if y == '2025' else 10
        res[y] = dict(profit=q.sum(), month=q.sum() / months, win=100 * (q > 0).mean(), pf=q[q > 0].sum() / -q[q < 0].sum(), minbal=dd, n=len(q))
    return res

def line(name, parts, **f):
    r = run(parts, **f)
    a, b = r['2025'], r['2026']
    print(f'{name:34}| 2025 ${a["profit"]:6.0f} PF {a["pf"]:.2f} mb ${a["minbal"]:5.0f} | 2026 ${b["profit"]:6.0f} PF {b["pf"]:.2f} mb ${b["minbal"]:5.0f}')
    return r

if __name__ == '__main__':
    FULL = ['main', 'ea40', 'fe', 'mz', 're3_main', 're3_ea40', 're3_fe']
    line('Full (chosen)', FULL)
    print('-- remove one part:')
    for p in FULL: line(f'  without {p}', [x for x in FULL if x != p])
    print('-- remove one filter:')
    for k in ('rsi', 'hours', 'cons'): line(f'  without {k} filter', FULL, **{k: False})
    print('-- single parts (with filters):')
    for p in ['main', 'main20', 'main_nosmall', 'ea40', 'ea20', 'ea10', 'fe', 'mz', 'db', 're3_main', 're3_ea40', 're3_fe', 're3_mz', 're3_db']:
        line(f'  {p}', [p])
    print('-- single parts WITHOUT filters:')
    for p in ['main', 'ea40', 'fe', 'mz', 'db']:
        line(f'  {p} no filters', [p], rsi=False, hours=False, cons=False)
