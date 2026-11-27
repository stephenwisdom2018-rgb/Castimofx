"""Profit of each part of the chosen version, by month, on the selected files (CASTIMO_FILES)."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.more_profit3 as P

MZ = Z.micro_zone(per=3, g_rsi=32)
EA = [(x[0], x[1]) for x in P.zones(40, 20)]
MAIN = P.mains(sl=30, extra=15)
FE = [(x[0], x[1]) for x in MR.FE]
RE3 = MR.reentries(MR.CH + MR.FE, 1, '2R')
parts = {'main': MAIN, 'EA zone': EA, 'F-E zone': FE, 'MZ': MZ, '3m re-entry': RE3}
rows = {}
for k, tr in parts.items():
    s = pd.Series([p for t, p in tr], index=[t for t, p in tr]).sort_index()
    g = s.groupby(s.index.strftime('%Y-%m')).sum(); g['TOTAL'] = s.sum(); rows[k] = g
    rows[k + ' win%'] = pd.Series({'TOTAL': 100 * (s > 0).mean()})
T = pd.DataFrame({k: v for k, v in rows.items() if 'win' not in k}).round(0)
print(T.to_string())
print({k: round(v['TOTAL']) for k, v in rows.items() if 'win' in k})
