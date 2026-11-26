import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate, excursions
df=load_csv('./data/XAUUSDb_M1_2026-08_2026-11.csv')
raw=pd.read_csv('./data/XAUUSDb_M1_2026-08_2026-11.csv',sep='\t')
spread=raw['<SPREAD>'].to_numpy(float)/100
sig,sw=find_signals(df)
start=df.index.searchsorted(pd.Timestamp('2026-10-01'))
sig=[s for s in sig if s.bar>=start]
days=df.index[start:].normalize().nunique()
print('swings',len(sw),'signals Oct1-Nov25:',len(sig),'per day',round(len(sig)/days,2), 'buys',sum(s.direction==1 for s in sig),'sells',sum(s.direction==-1 for s in sig),'second-G',sum(s.second_g for s in sig))
ex=excursions(df,sig,240)
for b in (60,240):
    e=excursions(df,sig,b)
    print(f'within {b} bars: median best move ${e.mfe.median():.2f}, median worst ${e.mae.median():.2f}; best>=10 {100*(e.mfe>=10).mean():.0f}%  best>=20 {100*(e.mfe>=20).mean():.0f}%')
def rep(name,tr):
    p=np.array([x.pnl for x in tr]); 
    if not len(p): print(name,'no trades'); return
    w=(p>0).mean()*100; eq=np.cumsum(p); dd=(eq-np.maximum.accumulate(np.r_[0,eq])[1:]).min()
    print(f'{name:28} trades {len(p):3}  win {w:5.1f}%  net ${p.sum():8.2f}  avg ${p.mean():6.2f}  worst DD ${dd:8.2f}  (per 0.01 lot)')
for sl,tp in [(5,5),(5,10),(10,10),(10,20),(15,30),(20,20),(20,40)]:
    rep(f'fixed SL ${sl} TP ${tp}', simulate(df,[s for s in sig],'fixed',sl,tp,spread))
for buf,rr in [(0.5,1),(0.5,2),(0.5,3),(2,2)]:
    rep(f'SL beyond G+${buf}, TP {rr}R', simulate(df,sig,'g',buf,rr,spread))
print()
tr=simulate(df,sig,'g',0.5,2,spread)
for x in tr:
    s=x.signal
    print(f"{x.time:%b %d %H:%M}  {'BUY ' if s.direction==1 else 'SELL'}  F {s.f:.2f}  G {s.g:.2f}  entry(H) {s.entry:.2f}  {'2nd G' if s.second_g else '1st G'}  -> {x.reason:8} ${x.pnl:+.2f}")
# how many staircases formed
