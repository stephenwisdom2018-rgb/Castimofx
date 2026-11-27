"""Owner's line = SMA 10 on close (M1), confirmed: 4272.969 at 2026.03.23 13:03. 'Inside' for buys = candles above
the line (side A), for sells below. Rule: the last N finished candles all closed on the trade's side (N = 1, 3).
Tested on Chosen and +Both, 0.01, normal stops. Min balance = biggest $ drop of closed trades (x1.5 = safe)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.strong_base as S
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
CH, EX = [], []                                   # (time, pnl, file, d)
for fi, (df, sp, *_) in enumerate(R.prep):
    CH += [(x[0], x[1], fi, x[4]) for x in zone(df, sp, 40, 20, main=False, reent=RE)[0] if M.keep(fi, x[0], x[4])]
    EX += [(x[0], x[1], fi, x[4]) for x in zone(df, sp, 40, 20, main=False, reent=RE, region='FE')[0] if M.keep(fi, x[0], x[4])]
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        CH += [(x.time, x.pnl, fi, x.signal.direction) for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0)
               if M.keep(fi, x.time, x.signal.direction)]
seen = set()
for x in sorted(S.double_bottom(2, detail=True)):
    if x[0] not in seen: seen.add(x[0]); EX.append((x[0], x[1], x[2], x[4]))
SIDE = []
for df, *_ in R.prep:
    c = df.close; ma = c.rolling(10).mean()
    SIDE.append({n: ((c > ma).astype(int).rolling(n).sum().shift(1).to_numpy() == n, (c < ma).astype(int).rolling(n).sum().shift(1).to_numpy() == n) for n in (1, 3)})
def ok(t, fi, d, n):
    i = R.prep[fi][0].index.get_loc(t); a, b = SIDE[fi][n]; return a[i] if d == 1 else b[i]

def stats(tr):
    s = pd.Series([x[1] for x in tr], index=[x[0] for x in tr]).sort_index(); eq = s.cumsum().to_numpy()
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    h1, h2 = s[s.index < '2026-07-01'].sum(), s[s.index >= '2026-07-01'].sum()
    return dict(profit=s.sum(), h1=h1, h2=h2, win=100 * (s > 0).mean(), pf=s[s > 0].sum() / -s[s < 0].sum(), minbal=dd, tpd=len(s) / 218)

if __name__ == '__main__':
    rows = {}
    for ver, tr in (('Chosen', CH), ('+Both', CH + EX)):
        rows[f'{ver}'] = stats(tr)
        for n in (1, 3):
            rows[f'{ver} SMA10 x{n}'] = stats([x for x in tr if ok(x[0], x[2], x[3], n)])
    T = pd.DataFrame(rows).T
    print(T.round(1).to_string())
