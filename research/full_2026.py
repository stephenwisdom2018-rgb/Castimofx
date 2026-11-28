"""All of 2026 on ONE continuous M1 file (Dec 2025 warm-up + Jan-Nov 2026 incl. 3-31 Aug, no file restarts), real fills, 0.01.
CASTIMO_FILES=data/XAUUSDb_M1_2025-12_2026-11.csv CASTIMO_FILL=market python research/full_2026.py"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F
from research.daily_green import daily

MZ = Z.micro_zone(per=3, g_rsi=32)
cols, monthly = {}, {}
for name, tr in (('F-E off', MR.CH), ('Chosen', MR.CH + MR.FE), ('F-E off+DB', MR.CH + MR.DB), ('+Both', MR.CH + MR.FE + MR.DB)):
    T = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    T = [x for x in T if pd.Timestamp(x[0]).year == 2026 and pd.Timestamp(x[0]) < pd.Timestamp('2026-11-28')]
    r = F.report(T); dly = daily(T)
    cols[name] = {'Profit': r['Profit'], 'PF': r['PF'], 'Green days': dly['Green days'], 'Avg day': dly['Avg day'],
                  'Worst day': dly['Worst day'], 'Min bal': r['Min bal'], 'Safe bal': r['Safe bal'], 'Trades/day': r['Trades/day']}
    s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T]))
    monthly[name] = s.groupby(s.index.to_period('M')).sum().round(0)
print(pd.DataFrame(cols).to_string()); print(pd.DataFrame(monthly).to_string())
