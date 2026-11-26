"""Owner's measure: profit per $1 of worst drop (profit / drop). Even if profit stays the same, a smaller drop lets the
lot size grow. Chosen combination (main + E-A zone, up to 10 per structure), full 2026, 0.01 lot.
Rules: RSI side filter (skip buys with RSI < 50, sells with RSI > 50) and target = structure size when F - G < $20."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry, rsi
from research.zone_multi import zone, FILES, KW

data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
def build(small_tp):
    out = []
    for df, sp in data:
        r = pd.Series(rsi(df.close.to_numpy(float)), index=df.index)
        z, _ = zone(df, sp, 10, 10, main=False)
        out += [(x[0], x[1], x[4], r[x[0]], 'zone') for x in z]
        sig, _ = find_signals(df, **KW); sig = [s for s in sig if s.bar >= 600 and s.with_boss]
        if not small_tp:
            groups = [(sig, 20)]
        else:
            size = lambda s: abs(s.f - s.g)
            groups = [([s for s in sig if size(s) >= 20], 20)] + [([s for s in sig if size(s) < 20 and max(5, int(size(s))) == tp], tp) for tp in range(5, 20)]
        for g, tp in groups:
            if g: out += [(x.time, x.pnl, x.signal.direction, r[x.time], 'main') for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0)]
    return sorted(out, key=lambda x: x[0])

def st(tr):
    res = []
    for a, b in (('2026-01-01', '2026-07-01'), ('2026-07-01', '2027-01-01'), ('2026-01-01', '2027-01-01')):
        q = pd.Series([x[1] for x in tr if a <= str(x[0]) < b]); eq = q.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
        dd = -(eq - pk).min(); res.append((len(q), 100 * (q > 0).mean(), q.sum(), dd, q.sum() / dd))
    return res

if __name__ == '__main__':
    base, small = build(False), build(True)
    rsi_ok = lambda x: (x[3] >= 50) if x[2] == 1 else (x[3] <= 50)
    cases = {'current': base, 'RSI side filter': [x for x in base if rsi_ok(x)],
             'small-structure target': small, 'both': [x for x in small if rsi_ok(x)]}
    print(f'{"rule":24}| Jan-Jun: win profit drop ratio | Jul-Nov: win profit drop ratio | YEAR: win profit drop ratio')
    for k, tr in cases.items():
        print(f'{k:24}| ' + ' | '.join(f'{w:3.0f}% ${p:5.0f} -${d:3.0f} {p/d:4.1f}' for n, w, p, d, _ in st(tr)))
