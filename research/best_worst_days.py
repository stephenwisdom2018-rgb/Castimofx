"""Best and worst days of Chosen, +Both and Robust (quality hours on: CASTIMO_SKIP_HOURS=8-13), true data, real
fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR
Y = sys.argv[1]
S, E = ('2026-01-01', '2026-11-26') if Y == '2026' else ('2025-02-01', '2025-08-01')
MZd = [(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
MZ = [(x[0], x[1]) for x in MZd]
V = {'Chosen': [(x[0], x[1]) for x in MR.CH + MR.FE] + MR.reentries(MR.CH + MR.FE, 1, '2R') + MZ,
     '+Both': [(x[0], x[1]) for x in MR.CH + MR.FE + MR.DB] + MR.reentries(MR.CH + MR.FE + MR.DB, 1, '2R') + MZ,
     'Robust': [(x[0], x[1]) for x in MR.MAIN + MR.EAZ + MZd + MR.DB] + MR.reentries(MZd + MR.DB, 1, '2R')}
out = {}
for k, T in V.items():
    s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T]))
    s = s[(s.index >= S) & (s.index < E)]
    out[k] = s.groupby(s.index.normalize()).sum()
for k, d in out.items():
    print(k, Y, 'WORST:', ', '.join(f'{t:%d %b} {v:.0f}' for t, v in d.nsmallest(10).items()))
    print(k, Y, 'BEST: ', ', '.join(f'{t:%d %b} {v:.0f}' for t, v in d.nlargest(10).items()))
    print(k, Y, 'days below -$100:', (d < -100).sum(), ' below -$200:', (d < -200).sum(), ' above +$200:', (d > 200).sum(), ' above +$400:', (d > 400).sum(), ' trading days:', len(d))
