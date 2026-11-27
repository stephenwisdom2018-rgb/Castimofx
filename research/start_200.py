"""$200 clients at 0.01: for every possible start day in 2026, how deep does the account go below its start before
recovering (closed trades)? Blown = balance reaches $0 (loss >= $200); 'danger' = loss >= $150."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.lot_final as L, research.micro3_reentry as MR, research.micro3_zone as Z

def versions():
    MZd = Z.micro_zone(per=3, g_rsi=32, detail=True)
    mz = [(x[0], x[6], x[1]) for x in MZd]
    def re(tr): return [(a, c, b) for a, b, c in MR.reentries(tr, 1, '2R', with_exit=True)]
    C = [(x[0], x[6], x[1]) for x in MR.CH]
    return {'C': C, 'C+3m+MZ': C + re(MR.CH) + mz, 'Chosen (+FE)': L.TR}

def risk(tr, start=200):
    s = pd.Series([p for t, e, p in tr], index=[e for t, e, p in tr]).sort_index()
    days = sorted({e.date() for e in s.index})
    res = []
    for d0 in days:
        seg = s[s.index.date >= d0].cumsum()
        res.append(seg.min())
    res = np.array(res)
    return dict(blown=100 * (res <= -start).mean(), danger=100 * (res <= -150).mean(), worst=res.min(), median=np.median(res))

if __name__ == '__main__':
    for name, tr in versions().items():
        r = risk(tr)
        print(f'{name:14} $200 start: blown {r["blown"]:4.1f}% of start days | lose $150+ {r["danger"]:4.1f}% | worst dip ${r["worst"]:.0f} | typical dip ${r["median"]:.0f}')
