"""Owner: clients expect 2% of the deposit paid every weekday and the deposit back at year end. 2026, 0.01, true data, real fills."""
import sys; sys.path.insert(0,'.')
import pandas as pd, research.day_rules as D
for name,drop in (('Chosen',()),('+Both no F',('F',))):
    X=[x for x in D.VERS['Chosen' if name=='Chosen' else '+Both'] if x[0].year==2026 and x[4] not in drop]
    s=pd.Series([x[2] for x in X],index=[x[1] for x in X]).sort_index()
    d=s.groupby(s.index.normalize()).sum().reindex(D.DAYS,fill_value=0)
    for dep in (1000,1500,2000):
        bal=dep+(d-0.02*dep).cumsum()
        m=bal.resample('ME').last().round(0)
        print(name,dep,'pay/day',0.02*dep,'lowest',round(bal.min()),'end',round(bal.iloc[-1]),'after returning deposit',round(bal.iloc[-1]-dep),'| month ends',list(m.astype(int)))
