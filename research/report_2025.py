"""Full-report table for C, C+3m, C+3m+MZ, C+3m+MZ+FE on the files in CASTIMO_FILES, plus monthly profit."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F

MZ = Z.micro_zone(per=3, g_rsi=32)
V = {'C': [(x[0], x[1]) for x in MR.CH],
     'C+3m': [(x[0], x[1]) for x in MR.CH] + MR.reentries(MR.CH, 1, '2R')}
V['C+3m+MZ'] = V['C+3m'] + MZ
V['+FE'] = [(x[0], x[1]) for x in MR.CH + MR.FE] + MR.reentries(MR.CH + MR.FE, 1, '2R') + MZ
T = pd.DataFrame({k: F.report(v) for k, v in V.items()})
print(T.drop(['Jan-Jun', 'Jul-Nov']).to_string())
M = pd.DataFrame({k: pd.Series([p for t, p in v], index=[t for t, p in v]).sort_index().groupby(lambda t: t.strftime('%b')).sum() for k, v in V.items()})
M = M.reindex([m for m in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'] if m in M.index]).round(0)
print(M.to_string())
