"""Pay the client a FIXED amount every weekday from the account, whatever the day's trading did. How much money must
the account start with so that it never runs out in 2026 (0.01)? True data, real fills. Buffer = worst point of
(trading result - payments so far)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_rules as D

def run(X, drop=()):
    X = [x for x in X if x[0].year == 2026 and x[4] not in drop]
    s = pd.Series([x[2] for x in X], index=[x[1] for x in X]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(D.DAYS, fill_value=0)
    out = {}
    for w in (5, 10, 15, 20, 25):
        bal = (d - w).cumsum()
        need = max(0.0, -bal.min()) + 0      # start money so the account never goes below 0 at a day's end
        out[f'${w}/day'] = f'start ${need:,.0f} -> end ${need + bal.iloc[-1]:,.0f}'
    return out

if __name__ == '__main__':
    cols = {'Chosen': run(D.VERS['Chosen']), '+Both': run(D.VERS['+Both']), '+Both no F': run(D.VERS['+Both'], ('F',))}
    print(pd.DataFrame(cols).to_string())
