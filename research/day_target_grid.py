"""Day target size: stop at +$T (T = 20..100) or at break-even after a red start. Chosen / +Both / Robust, quality
hours, true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.day_stop as DS
rows = {}
for v, X in DS.V.items():
    rows[v] = {f'+${t}': DS.run(X, tgt=t, be=True) for t in (20, 30, 40, 60, 80, 100)}
for v, R in rows.items():
    print(DS.Y, v); print(pd.DataFrame(R).T[['Profit', 'Green d', 'Worst d', 'Min bal']].to_string())
