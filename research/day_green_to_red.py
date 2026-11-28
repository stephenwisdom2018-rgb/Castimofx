"""With the current day rule (+$20 or break-even after a loss): how many days reached +$20 (closed) and still ended
RED because of trades that were already open? Quality hours, true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.day_stop as DS, research.day_stop_report as DR
cols = {}
for v, X in DS.V.items():
    k = sorted(DR.kept(X), key=lambda q: q[1])
    by = {}
    for e, ex, p in k: by.setdefault(e.date(), []).append((ex, p))
    hit = red = 0; lost = 0.0
    for dday, L in by.items():
        L.sort(); run = 0; reached = False
        for ex, p in L:
            run += p
            if run >= 20: reached = True
        if reached:
            hit += 1
            if run < 0: red += 1; lost += run
    cols[v] = {'Days that reached +$20': hit, '...and ended red': red, 'Money lost on those days': f'${lost:,.0f}'}
print(DS.Y); print(pd.DataFrame(cols).to_string())
