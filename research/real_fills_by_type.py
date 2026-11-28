"""Backtest 2026 profit by trade type at 0.01 (compare with research/mt5_report_tags.py). CASTIMO_FILL=market for real fills."""
import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np
import research.micro3_zone as Z, research.micro3_reentry as MR, research.reentry_v2 as R
from research.zone_multi import zone
RE = dict(swings='3', target='2R', max=1)
import research.more_trades as M
rows={}
def add(tag,lst):
    lst=[x for x in lst if pd.Timestamp(x[0]).year==2026]
    rows[tag]=(len(lst), 100*np.mean([x[1]>0 for x in lst]) if lst else 0, sum(x[1] for x in lst))
for reg,tg in (('EA','Z'),('FE','F')):
    a,b=[],[]
    for fi,(df,sp,*_) in enumerate(R.prep):
        for x in zone(df,sp,40,20,main=False,reent=RE,region=reg)[0]:
            if M.keep(fi,x[0],x[4]): (b if x[6]==-1 else a).append(x)
    add(tg,a); add(tg+'R',b)
main=[x for x in MR.MAIN]
add('M+R',main)
add('ZM',Z.micro_zone(per=3,g_rsi=32))
add('3M',MR.reentries(MR.CH+MR.FE,1,'2R'))
for k,(n,w,p) in rows.items(): print(f'{k:4} {n:5} win {w:3.0f}% ${p:7.0f}')
