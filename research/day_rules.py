"""Day rules on the TRUE 2026 data (one continuous file, real fills, 0.01), judged by days. Rules work on the trade
list in entry order (a skipped trade frees nothing else; approximation). Chosen and +Both.
CASTIMO_FILES=data/XAUUSDb_M1_2025-12_2026-11.csv CASTIMO_FILL=market python research/day_rules.py"""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_zone as Z, research.micro3_reentry as MR

df = R.prep[0][0]
c = df.close
FEAT = {}
for name, rule, n in (('H1', '1h', 50), ('H4', '4h', 50), ('D1', '1D', 20)):
    x = c.resample(rule).last().dropna(); e = x.ewm(span=n).mean()
    FEAT[name] = (x.shift(1).reindex(df.index, method='ffill'), e.shift(1).reindex(df.index, method='ffill'))
mom = {h: c - c.shift(h * 60) for h in (4, 24)}

def trades(tr, tag):
    out = [(pd.Timestamp(x[0]), pd.Timestamp(x[6]), x[1], x[3], tag) for x in tr]
    for x in tr:
        for t, p, ex in MR.reentries([x], 1, '2R', with_exit=True): out.append((pd.Timestamp(t), pd.Timestamp(ex), p, x[3], '3M'))
    return out

MZ = [(pd.Timestamp(x[0]), pd.Timestamp(x[6]), x[1], x[3], 'ZM') for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
BASE = trades(MR.EAZ, 'Z') + trades(MR.MAIN, 'M') + MZ
VERS = {'Chosen': BASE + trades(MR.FE, 'F'), '+Both': BASE + trades(MR.FE, 'F') + trades(MR.DB, 'DB')}
DAYS = pd.bdate_range('2026-01-02', '2026-11-25')

def apply(X, side_losses=None, day_cap=None, trend=None, dedupe=False, drop=(), mom_h=None):
    X = sorted(x for x in X if x[0].year == 2026 and x[4] not in drop); kept = []; seen = set(); day = {}
    for e, ex, p, d, tag in X:
        if dedupe and (e, d) in seen: continue
        if trend:
            px, em = FEAT[trend]
            if (px.at[e] - em.at[e]) * d < 0: continue
        if mom_h and mom[mom_h].at[e] * d < 0: continue
        k = day.setdefault(e.date(), [])
        closed = [q for q in k if q[1] <= e]
        if day_cap and sum(q[2] for q in closed) <= -day_cap: continue
        if side_losses and sum(1 for q in closed if q[2] < 0 and q[3] == d) >= side_losses: continue
        seen.add((e, d)); k.append((e, ex, p, d)); kept.append((e, ex, p, d))
    s = pd.Series([q[2] for q in kept], index=[q[1] for q in kept]).sort_index()
    dd = s.groupby(s.index.normalize()).sum().reindex(DAYS, fill_value=0)
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    m = dd.resample('ME').sum()
    return f'${s.sum():5.0f} green {100*(dd>0).mean():2.0f}% red {100*(dd<0).mean():2.0f}% avg ${dd.mean():3.0f} worst ${dd.min():4.0f} lose-mo {(m<0).sum()} min ${mb:4.0f}'

RULES = {'none': {}, 'dedupe': dict(dedupe=True), '2 loss/side': dict(side_losses=2), '3 loss/side': dict(side_losses=3),
         'cap $100': dict(day_cap=100), 'trend H1': dict(trend='H1'), 'trend H4': dict(trend='H4'), 'trend D1': dict(trend='D1'),
         'mom 4h': dict(mom_h=4), 'mom 24h': dict(mom_h=24), 'no ZM': dict(drop=('ZM',)), 'no F': dict(drop=('F',)),
         'H4+3loss': dict(trend='H4', side_losses=3), 'D1+3loss': dict(trend='D1', side_losses=3)}
if __name__ == '__main__':
    for v, X in VERS.items():
        print(v)
        for k, kw in RULES.items(): print(f'  {k:12} {apply(X, **kw)}', flush=True)
