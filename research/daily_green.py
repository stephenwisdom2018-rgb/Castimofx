"""Owner: clients need money TODAY. Test higher win-rate versions (smaller target = rr x risk for zone, MZ and
3-micro trades; main unchanged) and judge by DAYS: green days %, average day, worst day. Real fills
(CASTIMO_FILL=market), F-E zone off (C+3m+MZ), 2026 at 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.micro3_reentry as MR, research.micro3_zone as Z
from research.zone_multi import zone

def build(rr, with_db=False):
    RE = dict(swings='3', target='2R', max=1, rr=rr)
    EAZ = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        for x in zone(df, sp, 40, 20, rr=rr, main=False, reent=RE, region='EA')[0]:
            if M.keep(fi, x[0], x[4]):
                dist = x[1] if x[1] > 0 else -rr * x[1]
                EAZ.append((x[0], x[1], fi, x[4], x[13], x[13] + x[4] * dist, x[2]))
    tr = EAZ + MR.MAIN + (MR.DB if with_db else [])
    return [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, str(rr)) + Z.micro_zone(per=3, g_rsi=32, rr=rr)

def daily(T, side_stop=None, start='2026-01-02', end='2026-11-27'):
    s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T])).sort_index()
    s = s[(s.index >= start) & (s.index <= pd.Timestamp(end) + pd.Timedelta(days=1))]
    days = pd.bdate_range(start, end)
    have = pd.Index(s.index.normalize().unique())
    if start.startswith('2026'):
        days = days[days.isin(have) | (days < '2026-08-01') | (days >= '2026-08-26')]   # old split files: data hole
    d = s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0)
    eq = s.cumsum().to_numpy(); dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': f'${s.sum():,.0f}', 'Trade win': f'{100*(s>0).mean():.0f}%', 'Green days': f'{100*(d>0).mean():.0f}%',
            'Red days': f'{100*(d<0).mean():.0f}%', 'Avg day': f'${d.mean():.0f}', 'Worst day': f'${d.min():.0f}',
            'Worst/avg': f'{-d.min()/max(d.mean(),0.01):.0f}', 'Min bal': f'${dd:,.0f}'}

if __name__ == '__main__':
    cols = {}
    for rr in (2.0, 1.5, 1.0, 0.7, 0.5):
        cols[f'C {rr}R'] = daily(build(rr))
        cols[f'+DB {rr}R'] = daily(build(rr, True))
        print(pd.DataFrame(cols).to_string(), flush=True)
