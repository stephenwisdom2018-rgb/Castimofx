# Year-1 grid search for the CHoCH OTE filters. Usage: put the MT5 export at ./xau.csv, run python research/ote_grid.py
import sys, itertools, time, json
sys.path.insert(0,'.')
from multiprocessing import Pool
from castimofx import load_csv, OteConfig, run_ote_backtest
df=load_csv('xau.csv')
mid=df.index[len(df)//2]; A=df[df.index<mid]; B=df[df.index>=mid]
TPS={'4TP':((0.5,0.0,-0.27,-0.62),(0.25,)*4),'TP2only':((0.0,),(1.0,)),'TP3only':((-0.27,),(1.0,)),'50/50':((0.5,-0.27),(0.5,0.5))}
grid=list(itertools.product([3,5,8],[False,True],[False,True],[False,True],[0,25],[0,1.5],[0,16],[None,(9,21)],[0.62,0.705,0.79],list(TPS)))
def run(p):
    sw,bos,swp,ob,ps,dis,htf,ses,ent,tp=p
    lv,fr=TPS[tp]
    c=OteConfig(swing_length=sw,allow_bos=bos,require_sweep=swp,require_ob_overlap=ob,psych_step=ps,displacement_atr=dis,htf_factor=htf,session_hours=ses,ote_entry=ent,tp_levels=lv,tp_fractions=fr)
    s=run_ote_backtest(A,c,1000,1.0,0.10).stats()
    return p,s['trades'],s['avg_r'],s['profit_factor'],s['net_profit']
if __name__=='__main__':
    t=time.time()
    with Pool() as pool: res=pool.map(run,grid,chunksize=8)
    json.dump(res,open('grid_res.json','w'))
    print(len(grid),'combos',round(time.time()-t),'s')
