"""Small-account modes recomputed with the TRUE stop size known at entry (fix: the old mode test estimated the stop
from the result, which is exact for 2x-risk trades but wrong for main trades, whose stop is always $30).
Main trades (stop $30) are therefore excluded by any stop cap below $30."""
import sys, itertools
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_reentry as MR, research.micro3_zone as Z, research.start_200 as S

def tagged():
    def re(tr): return [(a, c, b, (-b if b < 0 else b / 2)) for a, b, c in MR.reentries(tr, 1, '2R', with_exit=True)]
    zone = lambda L: [(x[0], x[6], x[1], abs(x[5] - x[4]) / 2) for x in L]
    main = [(x[0], x[6], x[1], 30.0) for x in MR.MAIN]
    mz = [(x[0], x[6], x[1], abs(x[5] - x[4]) / 2) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
    C = zone(MR.EAZ) + main
    return {'C': C, 'C+3m+MZ': C + re(MR.CH) + mz, 'Chosen': C + zone(MR.FE) + re(MR.CH + MR.FE) + mz}

def mode(tr, maxopen=99, cap=1e9, dedupe=False):
    kept, seen, op = [], set(), []
    for t, e, p, risk in sorted(tr):
        if risk > cap: continue
        if dedupe and t in seen: continue
        op = [x for x in op if x > t]
        if len(op) >= maxopen: continue
        kept.append((t, e, p)); seen.add(t); op.append(e)
    return kept

if __name__ == '__main__':
    V = tagged(); rows = []
    for (vn, tr), dd, mo, cap in itertools.product(V.items(), (False, True), (99, 3, 2, 1), (1e9, 30, 20, 15, 10)):
        m = mode(tr, mo, cap, dd)
        r1, r2, r4 = S.risk(m, 100), S.risk(m, 200), S.risk(m, 400)
        rows.append(dict(version=vn, no_copies=dd, max_open=mo, stop_cap=None if cap > 1e8 else cap, profit=round(sum(p for _, _, p in m)),
                         blown100=round(r1['blown'], 1), blown200=round(r2['blown'], 1), blown400=round(r4['blown'], 1), worst_dip=round(r1['worst'])))
    T = pd.DataFrame(rows); T.to_csv('research/modes_fixed.csv', index=False)
    pd.set_option('display.width', 220)
    for col, lim, name in (('blown100', 70, '$100'), ('blown200', 130, '$200'), ('blown400', 260, '$400')):
        q = T[(T[col] == 0) & (T.worst_dip >= -lim)].sort_values('profit', ascending=False).head(4)
        print(f'\n{name} mode candidates (never blown, worst dip >= -${lim}):'); print(q.to_string(index=False))
    old = [('$100 old', 'C+3m+MZ', False, 1, 15), ('$200 old', 'C+3m+MZ', False, 2, 15), ('$400 old', 'C', True, 99, None)]
    print('\nOld mode settings recomputed correctly:')
    for name, v, dd, mo, cap in old:
        q = T[(T.version == v) & (T.no_copies == dd) & (T.max_open == mo) & ((T.stop_cap == cap) if cap else T.stop_cap.isna())]
        print(name, q[['profit', 'blown100', 'blown200', 'blown400', 'worst_dip']].to_dict('records'))
