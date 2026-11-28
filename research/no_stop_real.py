"""Owner: no stop loss, every trade must reach its take-profit, the bot keeps taking every signal. TRUE data, real
fills, quality hours (CASTIMO_SKIP_HOURS=8-13), 0.01. Drawdown = worst drop of (closed profit + open losses) at each
day's end. Arg: 2026 or 2025. Chosen = main + E-A zone; +Both adds F-E zone + double bottom."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.no_stop as N, research.strong_base as S
Y = sys.argv[1]
S0, E0 = ('2026-01-01', '2026-11-26') if Y == '2026' else ('2025-02-01', '2025-08-01')
base = N.zone_trades() + N.main_trades()
both = base + N.zone_trades('FE') + [(x[2], x[3], x[4], x[5], x[6]) for x in S.double_bottom(2, detail=True)]
cols = {}
for name, tr in (('Chosen', base), ('+Both', both)):
    h, l, c, idx, sp = N.D[0]; n = len(c)
    tr = [x for x in tr if S0 <= str(idx[x[1]]) < E0]
    days = pd.bdate_range(S0, pd.Timestamp(E0) - pd.Timedelta(days=1)); de = {d: i for i, d in enumerate(days)}
    closed = np.zeros(len(days)); open_ = np.zeros(len(days)); stuck = 0; maxopen = 0
    ends = [min(n - 1, idx.searchsorted(d + pd.Timedelta(hours=23, minutes=59))) for d in days]
    for fi, i, d, e, tgt in tr:
        T = e + d * tgt
        hit = np.nonzero(h[i+1:] >= T)[0] if d == 1 else np.nonzero(l[i+1:] + sp[i+1:] <= T)[0]
        j = i + 1 + hit[0] if len(hit) else n - 1
        if not len(hit) or idx[j] >= pd.Timestamp(E0): stuck += 1
        for k, b in enumerate(ends):
            if i <= b < j: open_[k] += (c[b] - e) * d
        dj = idx[j].normalize()
        if len(hit) and dj in de: closed[de[dj]] += tgt
    eq = np.cumsum(closed) + open_
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    cols[name] = {'Trades': len(tr), 'Took profit': f'{100*(1-stuck/len(tr)):.0f}%', 'Still open at end': stuck,
                  'Closed profit': f'${closed.sum():,.0f}', 'Open loss at end': f'${open_[-1]:,.0f}', 'Worst open loss': f'${open_.min():,.0f}',
                  'Drawdown (min bal)': f'${dd:,.0f}', 'Safe bal': f'${1.5*dd:,.0f}'}
print(Y); print(pd.DataFrame(cols).to_string())
