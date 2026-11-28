"""Exact backtest of a quality filter (no new trades in some server hours) on 2026 and 2025, Chosen / +Both and the
same without the F-E zone. Real fills, 0.01. Run once per year/hours:
CASTIMO_SKIP_HOURS=8-13 CASTIMO_FILES=data/XAUUSDb_M1_2025-12_2026-11.csv CASTIMO_FILL=market python research/quality_run.py 2026"""
import sys, os
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F
from research.daily_green import daily
Y = sys.argv[1]
S, E = ('2026-01-01', '2026-11-26') if Y == '2026' else ('2025-02-01', '2025-08-01')
MZ = Z.micro_zone(per=3, g_rsi=32); cols = {}
for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB), ('no F-E', MR.CH), ('+Both no F-E', MR.CH + MR.DB)):
    T = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    T = [x for x in T if S <= str(x[0]) < E]
    r = F.report(T); dl = daily(T, start=pd.bdate_range(S, E)[0].strftime('%Y-%m-%d'), end=pd.bdate_range(S, E)[-2].strftime('%Y-%m-%d'))
    s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T])); w = s.resample('W').sum()
    cols[name] = {'Profit': r['Profit'], 'Trades/day': r['Trades/day'], 'Green days': dl['Green days'], 'Green wks': f'{100*(w>0).mean():.0f}%',
                  'Worst wk': f'${w.min():.0f}', 'Min bal': r['Min bal'], 'Safe bal': r['Safe bal']}
print(Y, 'skip hours', os.environ.get('CASTIMO_SKIP_HOURS', 'none')); print(pd.DataFrame(cols).to_string())
