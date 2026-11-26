"""Owner's idea: take no NEW trades at 15:00 and 23:00 (server). When the hour ends, a skipped trade that has not hit
its stop or target yet is joined, but only if price is at its entry or better (at or below the entry for a buy).
It keeps the original stop and target. Chosen strategy (main + zone, RSI-50 filter, small-structure target), 2026, 0.01."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

SKIP = {15, 23}
rows = []
for df, sp, r, _, groups in R.prep:
    o = df.open.to_numpy(); hrs = df.index.hour.to_numpy()
    def join_price(t, d):
        """first bar after the skipped hour: its open (buys pay the spread)"""
        i = df.index.get_loc(t)
        while i < len(df) and hrs[i] in SKIP: i += 1
        return (df.index[i], o[i] + (sp[i] if d == 1 else 0)) if i < len(df) else (None, None)
    for x in zone(df, sp, 10, 10, main=False)[0]:
        if not R.ok(x[4], r[x[0]]): continue
        d, entry = x[4], x[13]
        rows.append((x[0], x[1], d, entry, entry + d * x[1], x[2], 'zone', 0) + join_price(x[0], d))
    for g, tp in groups:
        for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0):
            d = x.signal.direction
            if not R.ok(d, r[x.time]): continue
            m = re.search(r're-entry (\d+)', x.reason); k = int(m.group(1)) if m else 0
            rows.append((x.time, x.pnl, d, x.entry, x.exit, x.exit_time, 'main', k) + join_price(x.time, d))
T = pd.DataFrame(rows, columns=['time', 'pnl', 'd', 'entry', 'exit_px', 'exit_time', 'src', 'k', 'jt', 'jpx']).sort_values('time')

def build(join):
    out, joined = [], []
    for x in T.itertuples():
        if x.time.hour not in SKIP: out.append((x.time, x.pnl)); continue
        if not join(x) or x.jt is None or x.exit_time <= x.jt: continue          # already closed before the hour ended
        if (x.entry - x.jpx) * x.d < 0: continue                                     # price is past the entry: don't chase
        p = (x.exit_px - x.jpx) * x.d; out.append((x.jt, p)); joined.append(p)
    return sorted(out), joined

print(f'{"rule":40}| Jan-Jun | Jul-Nov | YEAR')
print(f'{"current (trade all hours)":40}| {R.st(sorted(zip(T.time, T.pnl)))}')
for name, j in (('skip 15 & 23, no join', lambda x: False), ('skip 15 & 23, join any skipped trade', lambda x: True),
                ('skip 15 & 23, join main re-entries only', lambda x: x.src == 'main' and x.k >= 1)):
    tr, jn = build(j)
    print(f'{name:40}| {R.st(tr)}')
    if jn: print(f'{"":40}  joined {len(jn)} trades: {sum(p > 0 for p in jn)} won, {sum(p < 0 for p in jn)} lost, ${sum(jn):.0f}')
