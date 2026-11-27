"""Skip trades with a very big stop ONLY when the market is wild: last 4 h range vs its 5-day median (known at entry).
Stop size: zone / F-E / double bottom = half the target distance (2x risk targets); main stop is $30.
Chosen and +Both, 0.01, normal stops. Min balance = biggest $ drop of closed trades."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_reentry as MR

VOL = []
for df, *_ in R.prep:
    rng = df.high.rolling(240).max() - df.low.rolling(240).min()
    VOL.append((rng / rng.rolling(7200, min_periods=1440).median()).shift(1))
def tag(tr):
    return [(t, p, abs(T - e) / 2, VOL[fi].iloc[R.prep[fi][0].index.get_loc(t)]) for t, p, fi, d, e, T, ex in tr]
VERS = {'Chosen': tag(MR.CH), '+Both': tag(MR.CH + MR.EX)}

def stats(tr):
    s = pd.Series([x[1] for x in tr], index=[x[0] for x in tr]).sort_index(); eq = s.cumsum().to_numpy()
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(); d = s.groupby(s.index.date).sum()
    return dict(profit=s.sum(), H1=s[s.index < '2026-07-01'].sum(), H2=s[s.index >= '2026-07-01'].sum(),
                win=100 * (s > 0).mean(), pf=s[s > 0].sum() / -s[s < 0].sum(), minbal=dd, worstday=d.min(), tpd=len(s) / 218)

if __name__ == '__main__':
    rows = {}
    for ver, tr in VERS.items():
        rows[ver] = stats(tr)
        for cap, v in itertools.product((30, 40, 60), (1.5, 2, 3)):
            rows[f'{ver} skip stop>${cap} if wild>{v}x'] = stats([x for x in tr if not (x[2] > cap and x[3] > v)])
    T = pd.DataFrame(rows).T
    print(T.round(1).to_string())
