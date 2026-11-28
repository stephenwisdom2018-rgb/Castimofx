"""Exact backtest of Robust or Max (true data, real fills, 0.01). Max needs CASTIMO_NO_CONS=1.
CASTIMO_SKIP_HOURS=8-13 [CASTIMO_NO_CONS=1] CASTIMO_FILES=... CASTIMO_FILL=market python research/onhold_exact.py <Robust|Max> <2026|2025>"""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F
from research.daily_green import daily
V, Y = sys.argv[1], sys.argv[2]
S, E = ('2026-01-01', '2026-11-26') if Y == '2026' else ('2025-02-01', '2025-08-01')
MZd = [(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
if V == 'Robust':
    base = MR.MAIN + MR.EAZ + MZd + MR.DB; re_of = MZd + MR.DB
else:
    base = MR.MAIN + MR.EAZ + MR.FE + MZd + MR.DB; re_of = MZd + MR.FE + MR.DB + MR.MAIN
T = [(x[0], x[1]) for x in base] + MR.reentries(re_of, 1, '2R')
T = [x for x in T if S <= str(x[0]) < E]
r = F.report(T); b0 = pd.bdate_range(S, E); dl = daily(T, start=b0[0].strftime('%Y-%m-%d'), end=b0[-2].strftime('%Y-%m-%d'))
s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T])); w = s.resample('W').sum()
print(V, Y, {'Profit': r['Profit'], 'Trades/day': r['Trades/day'], 'Green days': dl['Green days'], 'Green wks': f'{100*(w>0).mean():.0f}%',
             'Worst day': dl['Worst day'], 'Worst wk': f'${w.min():.0f}', 'Min bal': r['Min bal'], 'Safe bal': r['Safe bal']})
