"""Full-2026 test of rule variants over all M1 files (Jan 1 - Nov 25, Aug 1-25 missing)."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry, simulate

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
n_of = lambda x: int(m.group(1)) if (m := re.search(r're-entry (\d)', x.reason)) else 0
DATA = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]

def run(find_kw, with_boss_only, sim):
    vals, months = [], {}
    for df, sp in DATA:
        sig, _ = find_signals(df, tol=1.0, minor_e=5, **find_kw)
        sig = [s for s in sig if s.bar >= 600 and (s.with_boss or not with_boss_only)]
        for x, v in sim(df, sig, sp):
            vals.append(v); k = x.time.strftime('%m'); months[k] = months.get(k, 0) + v
    p = np.array(vals); eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    return p.sum(), (eq - pk).min(), len(p), sum(v < 0 for v in months.values()), months

SIMS = {
    'no re-entry': lambda df, s, sp: [(x, x.pnl) for x in simulate(df, s, 'fixed', 20, 20, sp)],
    'RSI re-entry, 0.01': lambda df, s, sp: [(x, x.pnl) for x in simulate_reentry(df, s, 20, 20, 10, 5, sp, pivot=0)],
    'mixed re-entry, alternating': lambda df, s, sp: [(x, x.pnl * (2 if n_of(x) % 2 == 1 else 1))
                                                     for x in simulate_reentry(df, s, 20, 20, 10, 5, sp, pivot=3, later_pivot=0)],
}
if __name__ == '__main__':
    for rule, fk, wb in [('OLD rules (boss filter, H may be first F)', {}, True),
                         ('FIX 1: H after G', {'h_after_g': True}, True),
                         ('FIX 2: both sides (no boss filter)', {}, False),
                         ('FIX 1 + 2', {'h_after_g': True}, False)]:
        print(f'== {rule}')
        for name, sim in SIMS.items():
            net, dd, n, lm, months = run(fk, wb, sim)
            print(f'   {name:28} net ${net:8.0f}  worst drop ${dd:7.0f}  trades {n}  losing months {lm}/{len(months)}')
