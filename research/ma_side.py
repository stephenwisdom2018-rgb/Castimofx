"""Owner's 'inside the moving average' rule: a buy only when the last 3 finished M1 candles closed ABOVE the line
(side A), a sell only when they closed BELOW it. MA settings unknown yet, so EMA/SMA 20/50 are tested.
Applied to every trade (main, zone, F-E, double bottom) of Chosen and +Both. 0.01, normal stops."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.loss_streaks as L, research.more_trades as M, research.min_balance as MB, research.no_stop as N, research.strong_base as S

LINES = {}
for fi, (df, *_ ) in enumerate(R.prep):
    c = df.close
    for k, n in (('EMA', 20), ('EMA', 50), ('SMA', 20), ('SMA', 50)):
        ma = c.ewm(span=n, adjust=False).mean() if k == 'EMA' else c.rolling(n).mean()
        above = (c > ma).astype(int); below = (c < ma).astype(int)
        LINES[(fi, k, n)] = (above.rolling(3).sum().shift(1).to_numpy() == 3, below.rolling(3).sum().shift(1).to_numpy() == 3)

CHOSEN_KEYS = None
def side_ok(fi, t, d, k, n):
    a, b = LINES[(fi, k, n)]; i = R.prep[fi][0].index.get_loc(t)
    return a[i] if d == 1 else b[i]

# trade lists with file and direction: (entry time, exit time, pnl, file, d, source)
ALL = [(x[0], x[1], x[2], x[3], x[5], 'main' if x[6] is None else 'other') for x in L.TR]
import research.lot_after_loss as LA
CH = set((t, p) for t, ex, p in LA.TR)

def stats(tr):
    s = pd.Series([p for t, p in tr], index=[t for t, p in tr]).sort_index(); eq = s.cumsum().to_numpy()
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return s.sum(), 100 * (s > 0).mean(), s[s > 0].sum() / -s[s < 0].sum(), dd, len(s)

if __name__ == '__main__':
    print('version  line   | profit   win   PF    drop$  trades')
    for ver in ('Chosen', '+Both'):
        base = [x for x in ALL if ver == '+Both' or (x[0], x[2]) in CH]
        p, w, pf, dd, n = stats([(x[0], x[2]) for x in base])
        print(f'{ver:7}  none   | ${p:6,.0f} {w:3.0f}% {pf:.2f}  ${dd:4.0f}  {n}')
        for k, nn in (('EMA', 20), ('EMA', 50), ('SMA', 20), ('SMA', 50)):
            kept = [(x[0], x[2]) for x in base if side_ok(x[3], x[0], x[4], k, nn)]
            p, w, pf, dd, n = stats(kept)
            print(f'{ver:7}  {k}{nn} | ${p:6,.0f} {w:3.0f}% {pf:.2f}  ${dd:4.0f}  {n}', flush=True)
