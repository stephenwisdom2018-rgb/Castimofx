"""Owner's personal test: stack N positions every $spacing against each trade, one $20 stop for all,
all close at the trade's target. Oct-Nov 2026, 0.01 lot each, $1,000 account."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from research.reentry_test import df, spread
from castimofx.sweep import find_signals, simulate_reentry

h, l = df.high.to_numpy(), df.low.to_numpy()
idx = {t: i for i, t in enumerate(df.index)}
sig, _ = find_signals(df, tol=1.0, minor_e=5)
a = df.index.searchsorted(pd.Timestamp('2026-10-01')); b = df.index.searchsorted(pd.Timestamp('2026-11-26'))
sig = [s for s in sig if s.with_boss and a <= s.bar < b]
trades = simulate_reentry(df, sig, 20, 20, 10, 5, spread)

def run(n, spacing, sp=0.05):
    bal, peak, worst_dd, low_eq = 1000.0, 1000.0, 0.0, 1000.0
    rows = []
    for x in trades:
        d = x.signal.direction
        i, j = idx[x.time], idx[x.exit_time]
        levels = [x.entry - d * k * spacing for k in range(n)]
        seg_lo, seg_hi = l[i:j + 1].min(), h[i:j + 1].max()
        filled = [lv for lv in levels if (seg_lo <= lv if d == 1 else seg_hi >= lv)]
        worst_px = max(seg_lo, x.entry - 20) if d == 1 else min(seg_hi, x.entry + 20)
        floating = sum((worst_px - lv) * d - sp for lv in filled)
        low_eq = min(low_eq, bal + floating)
        worst_dd = min(worst_dd, (bal + floating - peak) / peak)
        pnl = sum((x.exit - lv) * d - sp for lv in filled)
        bal += pnl; peak = max(peak, bal)
        rows.append((x.time, len(filled), pnl, x.reason))
    p = np.array([r[2] for r in rows])
    w = pd.Series(p, index=[r[0] for r in rows]).resample('W').sum()
    return bal - 1000, 100 * worst_dd, low_eq, (w < 0).sum(), len(w), p.min(), np.mean([r[1] for r in rows])

if __name__ == '__main__':
    print(f'{len(trades)} trades (incl. re-entries), Oct 1 - Nov 25 2026')
    for n, spc in ((1, 0), (10, 2), (10, 1), (20, 1)):
        net, dd, low, lw, nw, worst, avgf = run(n, spc)
        print(f'{n:2} positions every ${spc}: net ${net:8.2f}  max drawdown (incl. open) {dd:6.1f}%  lowest equity ${low:7.2f}  '
              f'worst single trade ${worst:7.2f}  avg positions filled {avgf:4.1f}  losing weeks {lw}/{nw}')
