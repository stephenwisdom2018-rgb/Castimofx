"""Full report (all parameters) for Chosen, Chosen+3micro, +Both, +Both+3micro, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.micro3_reentry as MR, research.bad_days as B

def report(tr):
    s = pd.Series([p for t, p in tr], index=[t for t, p in tr]).sort_index()
    d = s.groupby(s.index.date).sum(); wk = s.resample('W').sum(); wk = wk[wk != 0]
    mo = s.groupby(s.index.to_period('M')).sum().drop(pd.Period('2026-08'), errors='ignore')
    eq = s.cumsum().to_numpy(); dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    e1 = 1000 + eq; ddp = ((e1 - np.maximum.accumulate(np.r_[1000, e1])[1:]) / np.maximum.accumulate(np.r_[1000, e1])[1:]).min() * 100
    dl = B.daily(list(zip(s.index, s.values))); v = dl.fillna(0).to_numpy()
    bad = B.streaks(((dl < 0) | dl.isna()).tolist()); m20 = np.array([v[i:i+20].sum() for i in range(len(v) - 19)])
    return {'Profit': f'${s.sum():,.0f}', 'Jan-Jun': f'${s[s.index < "2026-07-01"].sum():,.0f}', 'Jul-Nov': f'${s[s.index >= "2026-07-01"].sum():,.0f}',
            'Win': f'{100*(s>0).mean():.0f}%', 'PF': f'{s[s>0].sum()/-s[s<0].sum():.2f}', 'Drop': f'{ddp:.0f}%',
            'Min bal': f'${dd:,.0f}', 'Safe bal': f'${1.5*dd:,.0f}', 'Trades/day': f'{len(s)/len(dl):.1f}',
            'Avg day': f'${s.sum()/len(dl):.0f}', 'Avg week': f'${wk.mean():.0f}', 'Avg month': f'${mo.mean():.0f}',
            'Best day': f'${d.max():.0f}', 'Worst day': f'${d.min():.0f}', 'Worst week': f'${wk.min():.0f}',
            'Worst month': f'${mo.min():.0f}', 'Losing months': f'{(mo<0).sum()}/{len(mo)}',
            'Win days': f'{100*(dl>0).mean():.0f}%', 'Lose days': f'{100*(dl<0).mean():.0f}%', 'Empty days': f'{100*dl.isna().mean():.0f}%',
            'Bad streak': f'{max(bad)}', 'Profit 20d': f'{100*(m20>0).mean():.0f}%'}

if __name__ == '__main__':
    cols = {}
    for ver, tr in (('Chosen', MR.CH), ('+Both', MR.CH + MR.EX)):
        base = [(x[0], x[1]) for x in tr]
        cols[ver] = report(base)
        cols[ver + '+3m'] = report(base + MR.reentries(tr, 1, '2R'))
    T = pd.DataFrame(cols)
    print(T.to_string())
    T.to_csv('research/full_report.csv')
