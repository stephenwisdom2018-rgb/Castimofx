"""Test: an H left behind when its first G was swept. Put a stop order at H and see what happens
when price comes back to it (any time later)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals

CSV = 'data/XAUUSDb_M1_2026-08_2026-11.csv'
df = load_csv(CSV)
h, l = df.high.to_numpy(), df.low.to_numpy()
start = df.index.searchsorted(pd.Timestamp('2026-10-01'))
left = []
find_signals(df, tol=1.0, left_h=left)
left = [x for x in left if x[2] >= start]

def trade(d, level, t0, sl, tp, max_wait=10**9):
    """Stop order at `level` placed at bar t0. Returns 'TP', 'SL', 'open' or 'never'."""
    n = len(df)
    # price must first be on the other side of the level (it is: H was not broken), wait for the touch
    t = t0
    while t < n and t - t0 < max_wait:
        if (h[t] >= level) if d == 1 else (l[t] <= level):
            break
        t += 1
    else:
        return 'never', None
    if t >= n:
        return 'never', None
    entry = level + (0.05 if d == 1 else 0)
    stop, target = entry - d * sl, entry + d * tp
    for k in range(t, n):
        hit_sl = (l[k] <= stop) if d == 1 else (h[k] + 0.05 >= stop)
        hit_tp = (h[k] >= target) if d == 1 else (l[k] + 0.05 <= target)
        if hit_sl:
            return 'SL', t
        if hit_tp and k > t:
            return 'TP', t
    return 'open', t

rng = np.random.default_rng(1)
for sl, tp in [(30, 20), (30, 15), (20, 20), (10, 10)]:
    res = [trade(d, lv, t, sl, tp)[0] for d, lv, t in left]
    c = pd.Series(res).value_counts().to_dict()
    done = c.get('TP', 0) + c.get('SL', 0)
    # control: random stop orders $3 away from price at random times, same direction mix
    ctrl = []
    for _ in range(400):
        t = int(rng.integers(start, len(df) - 2000)); d = int(rng.choice([1, -1]))
        ctrl.append(trade(d, (h[t] + 3) if d == 1 else (l[t] - 3), t, sl, tp)[0])
    cc = pd.Series(ctrl).value_counts().to_dict(); cd = cc.get('TP', 0) + cc.get('SL', 0)
    print(f'SL ${sl} TP ${tp}: left-behind H levels {len(left)} -> {c}; TP rate {100*c.get("TP",0)/max(done,1):.1f}% '
          f'| random control TP rate {100*cc.get("TP",0)/max(cd,1):.1f}% (break-even {100*sl/(sl+tp):.0f}%)')
