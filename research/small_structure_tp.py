"""Main strategy: the target is $20, but some structures are smaller than $20. Split main trades by structure size
and test: skip small structures, or use a target equal to the structure size. Size = F - G (the sweep leg) or
H - G. Full 2026, 0.01 lot, RSI re-entries as in the chosen combination."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry
from research.zone_multi import zone, FILES, KW

def st(tr):
    s = pd.Series([x[1] for x in tr], index=[x[0] for x in tr]).sort_index()
    eq = s.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    h1, h2 = s[s.index < '2026-07-01'].sum(), s[s.index >= '2026-07-01'].sum()
    return f'{len(s):3} tr {100*(s>0).mean():3.0f}% win  Jan-Jun ${h1:5.0f}  Jul-Nov ${h2:5.0f}  year ${s.sum():5.0f}  drop ${(eq-pk).min():5.0f}'

data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
zt, rows = [], []
for df, sp in data:
    zt += zone(df, sp, 10, 10)[0]
    sig, _ = find_signals(df, **KW)
    sig = [s for s in sig if s.bar >= 600 and s.with_boss]
    rows.append((df, sp, sig))

for name, size in (('F - G', lambda s: abs(s.f - s.g)), ('H - G', lambda s: abs(s.entry - s.g))):
    print(f'\nsize = {name}')
    by = {}
    for df, sp, sig in rows:
        for x in simulate_reentry(df, sig, 20, 20, 10, 5, sp, pivot=0):
            by.setdefault(size(x.signal) < 20, []).append((x.time, x.pnl))
    print(f'  main, structure under $20: {st(by.get(True, []))}')
    print(f'  main, structure $20+     : {st(by.get(False, []))}')
    for rule in ('target $20 (current)', 'skip under $20', 'target = size (min $5)'):
        tr = []
        for df, sp, sig in rows:
            big = [s for s in sig if size(s) >= 20]; small = [s for s in sig if size(s) < 20]
            tr += [(x.time, x.pnl) for x in simulate_reentry(df, big, 20, 20, 10, 5, sp, pivot=0)]
            if rule == 'target $20 (current)':
                tr += [(x.time, x.pnl) for x in simulate_reentry(df, small, 20, 20, 10, 5, sp, pivot=0)]
            elif rule.startswith('target = size'):
                for tp in range(5, 20):
                    grp = [s for s in small if max(5, int(size(s))) == tp]
                    if grp: tr += [(x.time, x.pnl) for x in simulate_reentry(df, grp, 20, tp, 10, 5, sp, pivot=0)]
        print(f'  {rule:24} main alone: {st(tr)}')
        print(f'  {"":24} + zone    : {st(tr + [(x[0], x[1]) for x in zt])}')
