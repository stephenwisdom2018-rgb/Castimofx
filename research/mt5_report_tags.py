"""Split an MT5 Strategy Tester report (copied as text into report.txt) by trade type (order comment), profit per 0.01 incl. costs.
Usage: python research/mt5_report_tags.py report.txt"""
import re, collections, sys
L=open(sys.argv[1] if len(sys.argv) > 1 else 'report.txt').read().split('\n')
oi=L.index('Orders'); di=L.index('Deals')
num=lambda s: float(s.replace(' ','').replace('\xa0','')) if s.strip() else 0.0
orders={}
for r in L[oi+2:di]:
    f=r.split('\t')
    if len(f)<11: continue
    orders[f[1]]=dict(sl=f[6].strip(),tp=f[7].strip(),cm=f[10].strip())
openp=[]; res=collections.defaultdict(lambda:[0,0,0.0,0.0,0.0])  # n, wins, pnl/0.01, cost/0.01, gross
unm=0
for r in L[di+2:]:
    f=r.split('\t')
    if len(f)<13 or f[2]!='XAUUSDb': continue
    vol=num(f[5]); com=num(f[8]); sw=num(f[9]); pr=num(f[10]); cm=f[12].strip(); typ=f[3]
    if f[4]=='in':
        o=orders.get(f[7],{}); tag=re.sub(r'\d+$','',o.get('cm',cm).replace('CFX ','')) or '?'
        openp.append(dict(d=typ,sl=o.get('sl'),tp=o.get('tp'),tag=tag,vol=vol,com=com,t=f[0]))
        continue
    want='buy' if typ=='sell' else 'sell'
    m=re.match(r'(sl|tp) ([\d.]+)',cm); k=None
    for i,p in enumerate(openp):
        if p['d']!=want: continue
        if m and p[m.group(1)].replace(' ','')!=m.group(2): continue
        k=i; break
    if k is None:
        k=next((i for i,p in enumerate(openp) if p['d']==want),None); unm+=1
    p=openp.pop(k); s=0.01/p['vol']
    R=res[p['tag']]; R[0]+=1; R[1]+=pr>0; R[2]+=(pr+sw+p['com']+com)*s; R[3]+=(sw+p['com']+com)*s; R[4]+=pr*s
    R2=res['ALL']; R2[0]+=1; R2[1]+=pr>0; R2[2]+=(pr+sw+p['com']+com)*s; R2[3]+=(sw+p['com']+com)*s; R2[4]+=pr*s
print('unmatched',unm,'left',len(openp))
for t,(n,w,p,c,g) in sorted(res.items(),key=lambda x:-x[1][2]):
    print(f'{t:6} {n:5} win {100*w/n:4.0f}%  net/0.01 ${p:7.0f}  costs ${c:5.0f}')
