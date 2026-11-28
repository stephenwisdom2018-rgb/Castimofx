"""Daily view of the quality version (CASTIMO_SKIP_HOURS=8-13) for clients: chance of a green day, average green /
red day, worst day, and days losing more than 10% / 20% of the safe balance; does an account started at the safe
balance ever blow (go to 0)? 0.01, real fills. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR
Y = sys.argv[1]
S, E = ('2026-01-02', '2026-11-25') if Y == '2026' else ('2025-02-03', '2025-07-31')
MZ = Z.micro_zone(per=3, g_rsi=32); cols = {}
for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB)):
    T = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T])).sort_index()
    s = s[(s.index >= S) & (s.index < pd.Timestamp(E) + pd.Timedelta(days=1))]
    d = s.groupby(s.index.normalize()).sum().reindex(pd.bdate_range(S, E), fill_value=0)
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(); safe = 1.5 * mb
    bal = safe + s.cumsum()
    cols[name] = {'Green days': f'{100*(d>0).mean():.0f}%', 'Red days': f'{100*(d<0).mean():.0f}%', 'No trade': f'{100*(d==0).mean():.0f}%',
                  'Avg green day': f'${d[d>0].mean():.0f}', 'Avg red day': f'${d[d<0].mean():.0f}', 'Avg day': f'${d.mean():.0f}',
                  'Worst day': f'${d.min():.0f}', 'Days < -10% safe': f'{100*(d < -0.1*safe).mean():.1f}%',
                  'Days < -20% safe': f'{100*(d < -0.2*safe).mean():.1f}%', 'Safe bal': f'${safe:,.0f}',
                  'Lowest balance': f'${bal.min():,.0f}', 'Blown?': 'no' if bal.min() > 0 else 'YES'}
print(Y); print(pd.DataFrame(cols).to_string())
