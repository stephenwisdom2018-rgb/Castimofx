"""Run the chosen version (C+3m+MZ+FE) on any M1 files: CASTIMO_FILES=a.csv,b.csv python research/run_chosen.py
No settings are changed. Prints the full report, monthly results and the client view."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F, research.bad_days as B

MZ = Z.micro_zone(per=3, g_rsi=32)
versions = {'C+3m+MZ': MR.CH, 'C+3m+MZ+FE': MR.CH + MR.FE}
cols = {}
for name, tr in versions.items():
    T = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    cols[name] = F.report(T)
    if name == 'C+3m+MZ+FE':
        s = pd.Series([p for t, p in T], index=[t for t, p in T]).sort_index()
        print('Monthly (C+3m+MZ+FE):')
        for m, g in s.groupby(s.index.to_period('M')):
            d = g.groupby(g.index.date).sum()
            print(f'  {m}  ${g.sum():6.0f}  {len(g):4} tr  {100*(g>0).mean():.0f}% win  best ${d.max():.0f}  worst ${d.min():.0f}')
        B.report('client view', T)
print(pd.DataFrame(cols).to_string())
