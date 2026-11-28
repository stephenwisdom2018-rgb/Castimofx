"""Owner's day plan: stop for the day at a profit target (+$20/40/60), or after getting back to break-even from a loss,
or after N trades; restart at midnight. The bot stops OPENING trades; open ones run to their own exit.
Chosen / +Both / Robust, quality hours (CASTIMO_SKIP_HOURS=8-13), true data, real fills, 0.01. Arg: 2026 or 2025."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR
Y = sys.argv[1]
S, E = ('2026-01-01', '2026-11-26') if Y == '2026' else ('2025-02-01', '2025-08-01')
MZd = [(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
def lst(base, re_of):
    out = [(pd.Timestamp(x[0]), pd.Timestamp(x[6]), x[1]) for x in base]
    for x in re_of: out += [(pd.Timestamp(t), pd.Timestamp(ex), p) for t, p, ex in MR.reentries([x], 1, '2R', with_exit=True)]
    return sorted(x for x in out if S <= str(x[0]) < E)
V = {'Chosen': lst(MR.CH + MR.FE + MZd, MR.CH + MR.FE), '+Both': lst(MR.CH + MR.FE + MR.DB + MZd, MR.CH + MR.FE + MR.DB),
     'Robust': lst(MR.MAIN + MR.EAZ + MZd + MR.DB, MZd + MR.DB)}
DAYS = pd.bdate_range(S, pd.Timestamp(E) - pd.Timedelta(days=1))

def run(X, tgt=None, be=False, maxn=None):
    kept = []; day = None
    for e, ex, p in X:
        if day != e.date(): day, taken, neg = e.date(), [], False
        closed = sum(q for e2, ex2, q in taken if ex2 <= e)
        if closed < 0: neg = True
        if tgt and closed >= tgt: continue
        if be and neg and closed >= 0: continue
        if maxn and len(taken) >= maxn: continue
        taken.append((e, ex, p)); kept.append((e, ex, p))
    s = pd.Series([q[2] for q in kept], index=[q[1] for q in kept]).sort_index()
    d = s.groupby(s.index.normalize()).sum().reindex(DAYS, fill_value=0)
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': round(s.sum()), 'Green d': round(100 * (d > 0).mean()), 'Red d': round(100 * (d < 0).mean()),
            'Worst d': round(d.min()), 'Tr/day': round(len(s) / len(DAYS), 1), 'Min bal': round(mb)}

RULES = {'none': {}, 'stop +$20': dict(tgt=20), 'stop +$40': dict(tgt=40), 'stop +$60': dict(tgt=60),
         'break-even': dict(be=True), 'max 4': dict(maxn=4), 'max 5': dict(maxn=5),
         '+$40 & BE': dict(tgt=40, be=True), '+$40 & BE & 5': dict(tgt=40, be=True, maxn=5), '+$20 & BE': dict(tgt=20, be=True)}
if __name__ == '__main__':
    for v, X in V.items():
        print(Y, v); print(pd.DataFrame({k: run(X, **kw) for k, kw in RULES.items()}).T.to_string(), flush=True)
