"""Trade only in lively markets: the average daily range of the last 20 days (as % of price) must be at least X.
Known before each trade. C and Full (C+3m+MZ+FE) on CASTIMO_FILES."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F

ADRP = []
for df, *_ in R.prep:
    d = df.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    p = ((d.high - d.low) / d.close * 100).rolling(20, min_periods=5).mean().shift(1)
    ADRP.append(p)
def adrp(t):
    for fi, (df, *_) in enumerate(R.prep):
        if df.index[0] <= t <= df.index[-1]:
            v = ADRP[fi].asof(t.normalize()); return 0 if pd.isna(v) else v
    return 0

if __name__ == '__main__':
    MZ = Z.micro_zone(per=3, g_rsi=32)
    C = [(x[0], x[1]) for x in MR.CH]
    tr = MR.CH + MR.FE
    FULL = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    cols = {}
    for name, v in (('C', C), ('Full', FULL)):
        cols[name] = F.report(v)
        for th in (1.5, 2.0):
            k = [x for x in v if adrp(x[0]) >= th]
            if k: cols[f'{name} ADR>={th}%'] = F.report(k)
    print(pd.DataFrame(cols).drop(['Jan-Jun', 'Jul-Nov']).iloc[:9].to_string())
