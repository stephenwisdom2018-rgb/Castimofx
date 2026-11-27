"""Lot sizing for the chosen version C+3m+MZ+FE on 2026. Each trade's lot is set from the balance of CLOSED trades at
its entry (live rule). Results in $ (0.01 lot = $1 per $1 move). Closed trades only: floating losses are not counted,
and stacked copies each get the lot, so real risk is a bit higher."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR

tr = MR.CH + MR.FE
TR = [(x[0], x[6], x[1]) for x in tr] + [(a, c, b) for a, b, c in MR.reentries(tr, 1, '2R', with_exit=True)] + \
     [(x[0], x[6], x[1]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
TR.sort()

def sim(start, lot_rule, loss_rule=False):
    bal, peak, worst, low = start, start, 0.0, start
    pending, day_pnl, streak, curve = [], {}, 0, []
    for t, ex, p in TR:
        done = [x for x in pending if x[0] <= t]; pending = [x for x in pending if x[0] > t]
        for e, v, raw in sorted(done):
            bal += v; peak = max(peak, bal); worst = min(worst, (bal - peak) / peak); low = min(low, bal)
            streak = streak + 1 if raw < 0 else 0
        if bal <= 0: return dict(end=bal, worst=-100, low=bal)
        lots = lot_rule(bal, start)
        if loss_rule and streak >= 3: lots = max(1, lots // 2)
        pending.append((ex, p * lots, p)); day_pnl[t.date()] = day_pnl.get(t.date(), 0) + p * lots
    for e, v, raw in sorted(pending):
        bal += v; peak = max(peak, bal); worst = min(worst, (bal - peak) / peak); low = min(low, bal)
    return dict(end=bal, worst=100 * worst, low=low)

if __name__ == '__main__':
    rules = {'fixed 0.01': lambda b, s: 1,
             '0.01 per $2,000': lambda b, s: max(1, int(b // 2000)),
             '0.01 per $1,500': lambda b, s: max(1, int(b // 1500)),
             '0.01 per $1,000': lambda b, s: max(1, int(b // 1000)),
             '0.01 per $500': lambda b, s: max(1, int(b // 500)),
             'old rule (cushion / $500)': lambda b, s: max(2 if b >= s + 100 else 1, int(b // 500))}
    for start in (1000, 2000):
        print(f'\nStart ${start:,} (2026, Jan-Nov):')
        for name, rule in rules.items():
            for lr in (False, True):
                r = sim(start, rule, lr)
                print(f'  {name:26}{" +half after 3 losses" if lr else "":21} end ${r["end"]:>12,.0f}  worst drop {r["worst"]:5.0f}%  lowest ${r["low"]:>8,.0f}')
    print('\nProp $100,000 (fixed lots; limits: 4% day = $4,000, 10% total = $10,000):')
    days = {}
    for t, ex, p in TR: days[t.date()] = days.get(t.date(), 0) + p
    dmin = min(days.values())
    for lots in (5, 7, 9, 12):
        r = sim(100000, lambda b, s, L=lots: L)
        print(f'  0.{lots:02d} lot: profit ${r["end"]-100000:>9,.0f}  worst drop ${100000*-r["worst"]/100:>7,.0f} ({-r["worst"]:.1f}%)  worst day ~${dmin*lots:,.0f}')
