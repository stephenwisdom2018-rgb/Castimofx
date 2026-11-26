"""Lot sizing on the chosen combination (main strategy + E-A zone, up to 10 per structure), full 2026 M1.
The balance grows as trades close. Lot rules:
- fixed 0.01
- 0.01 per $500 of balance
- owner's rule: base = max(cushion: 0.01 until +$100 above start then 0.02, scaling 0.01 per $500);
  main-strategy re-entries alternate L, 2L, L, 2L...
Profit is $ per 0.01 lot (1 oz), so a lot of 0.03 makes 3x. Closed trades only (open losses not counted)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from research.zone_multi import zone, FILES

def simulate(trades, start, rule, per=500):
    ev = sorted(trades, key=lambda x: x[0])
    bal, open_, closed, peak, worst, low, first = start, [], [], start, 0.0, start, {}
    for tr in ev:
        t = tr[0]
        for o in sorted([o for o in open_ if o[0] <= t]):                  # close trades that finished before this entry
            bal += o[1]; peak = max(peak, bal); worst = min(worst, (bal - peak) / peak); low = min(low, bal)
        open_ = [o for o in open_ if o[0] > t]
        if bal <= 0: return bal, worst, low, True
        scale = max(1, int(bal // per))
        if rule == 'fixed 0.01': base = 1
        elif rule.startswith('0.01 per'): base = scale
        else: base = max(scale, 2 if bal >= start + 100 else 1)
        lot = base
        if rule.startswith('owner') and tr[3] != 'zone':                         # main trade: re-entries alternate L, 2L
            k = first.get(tr[3], 0); lot = base * (2 if k % 2 == 1 else 1); first[tr[3]] = k + 1
        open_.append((tr[2], tr[1] * lot))
    for o in sorted(open_):
        bal += o[1]; peak = max(peak, bal); worst = min(worst, (bal - peak) / peak); low = min(low, bal)
    return bal, worst, low, bal <= 0

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    allt = []
    for df, sp in data:
        z, m = zone(df, sp, 10, 10); allt += z + m
    print(f'{len(allt)} trades, 1 Jan - 25 Nov 2026 (1-25 Aug missing)')
    print('start   rule                         | end balance   worst drop   lowest balance')
    for start in (100, 200, 500, 1000):
        for rule in ('fixed 0.01', '0.01 per $500', '0.01 per $1000', "owner's rule"):
            per = 1000 if '1000' in rule else 500
            bal, worst, low, dead = simulate(allt, start, rule, per)
            print(f'${start:<5}  {rule:28} | ${bal:10,.0f}   {100*worst:5.0f}%     ${low:8,.0f}' + ('  WIPED OUT' if dead else ''))
