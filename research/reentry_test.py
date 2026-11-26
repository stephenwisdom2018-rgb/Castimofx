"""Owner's stop-loss / re-entry rule on XAUUSDb M1, 1 Oct - 25 Nov 2026."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate, simulate_reentry

CSV = 'data/XAUUSDb_M1_2026-08_2026-11.csv'
df = load_csv(CSV)
spread = pd.read_csv(CSV, sep='\t')['<SPREAD>'].to_numpy(float) / 100
start = df.index.searchsorted(pd.Timestamp('2026-10-01'))
sig, _ = find_signals(df, tol=1.0)
sig = [s for s in sig if s.bar >= start]

def show(name, tr):
    p = np.array([x.pnl for x in tr])
    eq = np.cumsum(p); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    first = [x for x in tr if 're-entry' not in x.reason]
    re = [x for x in tr if 're-entry' in x.reason]
    rs = pd.Series([x.reason.split(' ')[0] for x in tr]).value_counts().to_dict()
    weeks = pd.Series(p, index=[x.time for x in tr]).resample('W').sum()
    print(f'{name:42} trades {len(p):3} (re-entries {len(re):2})  {rs}  net ${p.sum():8.2f}  worst drop ${dd:8.2f}  '
          f'losing weeks {(weeks < 0).sum()}/{len(weeks)}')

if __name__ == '__main__':
    show('no re-entry, SL $20 TP $20', simulate(df, sig, 'fixed', 20, 20, spread))
    show('no re-entry, SL $30 TP $20 (last test)', simulate(df, sig, 'fixed', 30, 20, spread))
    for tp in (20, 30, 40):
        for extra in (0, 10, 20):
            for mx in (1, 2, 5):
                show(f'SL $20 TP ${tp}, re-entry TP +${extra}, max {mx} re-entries',
                     simulate_reentry(df, sig, 20, tp, extra, mx, spread))
