"""Weekly profit 2026 at 0.01, true data, real fills: Chosen and +Both (by trade close time, week = Mon-Fri)."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.day_rules as D
cols = {}
for v, X in D.VERS.items():
    X = [x for x in X if x[0].year == 2026]
    s = pd.Series([x[2] for x in X], index=[x[1] for x in X]).sort_index()
    cols[v] = s.groupby(s.index.to_period('W-SUN').start_time).sum()
W = pd.DataFrame(cols).fillna(0).round(0).astype(int)
W.index = W.index.strftime('%d %b')
print(W.to_string()); print('sum', W.sum().to_dict(), 'green weeks', (W > 0).mean().round(2).to_dict())
