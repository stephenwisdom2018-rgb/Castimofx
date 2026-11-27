"""Minimum account balance at 0.01: the largest peak-to-low $ drop of the account, counting closed trades AND the
floating losses of open trades (marked at every hour's end). Minimum balance = that drop (the account would hit 0),
safe balance = 1.5x."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.no_stop as N

def equity_drop(trades, hard=None, opposite=True, stop_of=None):
    """trades: (file, bar, d, entry, target_distance[, stop_distance]). Returns max $ drop with floating, and closed-only."""
    opp = {}
    for x in trades: opp.setdefault((x[0], x[2]), []).append(x[1])
    for k in opp: opp[k] = np.array(sorted(opp[k]))
    events = []                       # (time, $ change) on an hourly grid
    closed = []
    for x in trades:
        fi, i, d, e, tgt = x[:5]; sl = x[5] if len(x) > 5 else hard
        h, l, c, idx, sp = N.D[fi]; n = len(h); T = e + d * tgt
        hit = np.nonzero(h[i+1:] >= T)[0] if d == 1 else np.nonzero(l[i+1:] + sp[i+1:] <= T)[0]
        jt = i + 1 + hit[0] if len(hit) else n
        jo = n
        if opposite:
            o = opp.get((fi, -d), np.array([])); k = np.searchsorted(o, i, side='right'); jo = o[k] if k < len(o) else n
        js = n
        if sl:
            st = e - d * sl
            hs = np.nonzero(l[i+1:] <= st)[0] if d == 1 else np.nonzero(h[i+1:] + sp[i+1:] >= st)[0]
            js = i + 1 + hs[0] if len(hs) else n
        j = min(jt, jo, js, n - 1)
        exit_px = T if j == jt else (e - d * sl if j == js else c[j])
        # floating value at each hour end while open, then the final value
        hrs = np.arange(i, j, 60)
        vals = (c[hrs] - e) * d
        prev = 0.0
        for b, v in zip(hrs, vals): events.append((idx[b], v - prev)); prev = v
        final = (exit_px - e) * d
        events.append((idx[j], final - prev)); closed.append((idx[j], final))
    ev = pd.Series([v for t, v in events], index=[t for t, v in events]).sort_index()
    eq = ev.groupby(level=0).sum().cumsum().to_numpy()
    dd_float = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    cs = pd.Series([v for t, v in closed], index=[t for t, v in closed]).sort_index().cumsum().to_numpy()
    dd_closed = -(cs - np.maximum.accumulate(np.r_[0, cs])[1:]).min()
    return dd_float, dd_closed, sum(v for t, v in closed)
