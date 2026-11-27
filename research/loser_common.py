"""Common traits of losing trades in the chosen version (all known at entry). A bucket that loses money in BOTH
halves could be traded in REVERSE (a reversed trade wins when the original loses). Reverse value ~ -net - spread."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
rows = []
for fi, (df, sp, r, *_) in enumerate(R.prep):
    c = df.close; o = df.open
    day = df.index.normalize()
    d_open = o.groupby(day).transform('first')
    dd = df.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    prev = dd.shift(1).reindex(day).set_axis(df.index)
    lo_sofar = df.low.groupby(day).cummin(); hi_sofar = df.high.groupby(day).cummax()
    move4h = c - c.shift(240)
    f = M.FEAT[fi]
    def add(t, pnl, d, src):
        i = df.index.get_loc(t)
        rows.append(dict(time=t, pnl=pnl, d=d, src=src,
            day_dir=np.sign(c.iloc[i-1] - d_open.iloc[i]) * d if i else 0,
            prev_dir=np.sign(prev.close.iloc[i] - prev.open.iloc[i]) * d,
            from_open=(c.iloc[i-1] - d_open.iloc[i]) * d,
            swept_prev_low=bool(lo_sofar.iloc[i-1] < prev.low.iloc[i]) if d == 1 else bool(hi_sofar.iloc[i-1] > prev.high.iloc[i]),
            swept_prev_high=bool(hi_sofar.iloc[i-1] > prev.high.iloc[i]) if d == 1 else bool(lo_sofar.iloc[i-1] < prev.low.iloc[i]),
            move4h=move4h.iloc[i-1] * d, adx=f.adx.iloc[i], rsi=(r.iloc[i] if d == 1 else 100 - r.iloc[i]), hour=t.hour, wday=t.dayofweek))
    for x in zone(df, sp, 40, 20, main=False, reent=RE)[0]:
        if M.keep(fi, x[0], x[4]): add(x[0], x[1], x[4], 'zone re' if x[6] == -1 else ('zone 1st' if x[6] == 0 else 'zone later'))
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0):
            if M.keep(fi, x.time, x.signal.direction): add(x.time, x.pnl, x.signal.direction, 'main 1st' if 're-entry' not in x.reason else 'main re')
T = pd.DataFrame(rows).sort_values('time').reset_index(drop=True)
T['day'] = T.time.dt.date
T['n_today'] = T.groupby('day').cumcount()
T['half'] = np.where(T.time < '2026-07-01', 'H1', 'H2')
T.to_csv('research/loser_common_trades.csv', index=False)

def show(col, bins=None, labels=None):
    g0 = T.copy()
    if bins is not None: g0['b'] = pd.cut(g0[col], bins, labels=labels)
    else: g0['b'] = g0[col]
    print(f'\n{col}')
    for b, g in g0.groupby('b', observed=True):
        a, z = g[g.half == 'H1'], g[g.half == 'H2']
        both = a.pnl.sum() < 0 and z.pnl.sum() < 0
        print(f'  {str(b):18} | {len(a):3} tr {100*(a.pnl>0).mean() if len(a) else 0:3.0f}% ${a.pnl.sum():5.0f} | {len(z):3} tr {100*(z.pnl>0).mean() if len(z) else 0:3.0f}% ${z.pnl.sum():5.0f}'
              + (f'   <== loses BOTH halves; reversed ~ ${-g.pnl.sum() - 0.3*len(g):.0f}' if both else ''))

if __name__ == '__main__':
    print(f'{len(T)} trades, net ${T.pnl.sum():.0f}')
    show('src')
    show('day_dir', [-2, -0.5, 0.5, 2], ['against day', 'flat', 'with day'])
    show('prev_dir', [-2, -0.5, 0.5, 2], ['against prev day', 'flat', 'with prev day'])
    show('from_open', [-1e9, -20, -5, 5, 20, 1e9], ['<-20 against', '-20..-5', '-5..5', '5..20', '>20 with'])
    show('swept_prev_low'); show('swept_prev_high')
    show('move4h', [-1e9, -20, -5, 5, 20, 1e9], ['4h <-20 against', '-20..-5', '-5..5', '5..20', '>20 with'])
    show('n_today', [-1, 0, 1, 3, 100], ['1st today', '2nd', '3rd-4th', '5th+'])
    show('adx', [0, 15, 20, 25, 35, 50, 100]); show('rsi', [0, 50, 60, 68, 80, 100]); show('wday')
