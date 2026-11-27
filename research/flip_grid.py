"""Flip after a stop: grid of stop size (x the losing trade's risk) and target (x flip stop), on Chosen and +Both.
Shows both halves of 2026 and losing months, so only balanced settings are kept."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.flip_after_stop as FS, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F

MZ = Z.micro_zone(per=3, g_rsi=32); ids = {id(x) for x in MR.MAIN}
rows = []
for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB)):
    base = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    L = FS.losers(tr, ids)
    combos = [(None, None)] + list(itertools.product((0.5, 1.0, 1.5), (0.5, 0.75, 1.0, 1.5, 2.0)))
    for sm, rr in combos:
        fl = [] if sm is None else FS.flips(L, rr, False, sm)
        r = F.report(base + fl)
        s = pd.Series([p for t, p in base + fl], index=[t for t, p in base + fl])
        mo = s.groupby(s.index.to_period('M')).sum().drop(pd.Period('2026-08'), errors='ignore')
        rows.append(dict(version=name, flip_stop='none' if sm is None else f'{sm}x', target='-' if rr is None else f'{rr}x',
                         flips=len(fl), flip_win=round(100 * np.mean([p > 0 for t, p in fl])) if fl else None,
                         profit=r['Profit'], H1=r['Jan-Jun'], H2=r['Jul-Nov'], win=r['Win'], PF=r['PF'], minbal=r['Min bal'],
                         worst_day=r['Worst day'], worst_month=r['Worst month'], losing=r['Losing months'],
                         months_better=None))
        rows[-1]['_mo'] = mo
    base_mo = rows[-len(combos)]['_mo']
    for r in rows[-len(combos):]: r['months_better'] = int((r['_mo'] > base_mo).sum())
T = pd.DataFrame(rows).drop(columns='_mo')
T.to_csv('research/flip_grid.csv', index=False)
pd.set_option('display.width', 250)
print(T.to_string(index=False))
