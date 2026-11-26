"""Owner: how many trades go into a loss first? Could we enter $X better (buy limit $X below the signal entry, sell
limit $X above), keeping the SAME stop and target levels? Losers always reach the stop, so they always fill (with a
smaller loss). Winners fill only if price first came back $X; otherwise they are missed.
Chosen strategy (main + zone, RSI-50 filter, small-structure target), all hours, 2026, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
import research.hold_time as H                     # builds the trade table T (entry, exit time, file)

T = H.T.copy()
P = [(df.index, df.high.to_numpy(), df.low.to_numpy(), sp) for df, sp, *_ in R.prep]
mae = []
for x in T.itertuples():
    idx, h, l, sp = P[x.fi]; a, b = idx.get_loc(x.time), idx.get_loc(x.exit_time)
    if x.d == 1: mae.append(x.entry - l[a:b + 1].min() if b > a else 0.0)
    else: mae.append(h[a:b + 1].max() + sp[a:b + 1].max() - x.entry if b > a else 0.0)
T['mae'] = np.maximum(mae, 0)
W = T[T.pnl > 0]
print(f'{len(T)} trades, {len(W)} winners. How far winners went AGAINST us before reaching target:')
for X in (1, 2, 3, 5, 7, 10, 15, 20):
    print(f'  ${X:>2}+ against first: {100*(W.mae >= X).mean():3.0f}% of winners')

def limit(X, frac=None):
    out = []
    for x in T.itertuples():
        risk = 20 if x.src == 'main' else abs(x.pnl) if x.pnl < 0 else x.pnl / 2
        off = X if frac is None else frac * risk
        if off >= risk: out.append((x.time, x.pnl)); continue                 # limit would sit at/below the stop: normal entry
        if x.pnl < 0: out.append((x.time, x.pnl + off))                       # loser: fills on the way to the stop
        elif x.mae >= off: out.append((x.time, x.pnl + off))                  # winner that came back: bigger win
    return sorted(out)
print(f'\n{"entry":30}| Jan-Jun | Jul-Nov | YEAR')
print(f'{"at signal (current)":30}| {R.st(sorted(zip(T.time, T.pnl)))}')
for X in (1, 2, 3, 5, 10):
    print(f'{f"${X} better":30}| {R.st(limit(X))}')
for f in (0.1, 0.25, 0.5):
    print(f'{f"{int(f*100)}% of the stop better":30}| {R.st(limit(0, f))}')
