"""Owner's re-entry ideas on the chosen strategy (main + E-A zone + RSI-50 filter + small-structure target).
After a stop: re-enter on the break of the most recent high (RSI swing or 3-candle swing).
Lots: 1st entry 1x, 1st re-entry 2x, then 1x, 2x ... (zone trades 1x).
Re-entry target: 'orig+extra' = first target + $10 (current) | 'above' = $20 from the re-entry if it is above the first
entry, else first target + $10 | 'own+extra' = $20 from the re-entry if above, else $30 from the re-entry.
Full 2026, base 0.01 lot."""
import sys, re, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry, rsi
from research.zone_multi import zone, FILES, KW

data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
prep = []
for df, sp in data:
    r = pd.Series(rsi(df.close.to_numpy(float)), index=df.index)
    z, _ = zone(df, sp, 10, 10, main=False)
    sig, _ = find_signals(df, **KW); sig = [s for s in sig if s.bar >= 600 and s.with_boss]
    size = lambda s: abs(s.f - s.g)
    groups = [([s for s in sig if size(s) >= 20], 20)] + [([s for s in sig if size(s) < 20 and max(5, int(size(s))) == tp], tp) for tp in range(5, 20)]
    prep.append((df, sp, r, [(x[0], x[1], x[4], r[x[0]]) for x in z], [g for g in groups if g[0]]))
ok = lambda d, rv: rv >= 50 if d == 1 else rv <= 50

def run(pivot, rtp, alt):
    tr = []
    for df, sp, r, z, groups in prep:
        tr += [(t, p) for t, p, d, rv in z if ok(d, rv)]
        for g, tp in groups:
            for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=pivot, reentry_tp=rtp):
                if not ok(x.signal.direction, r[x.time]): continue
                m = re.search(r're-entry (\d+)', x.reason); k = int(m.group(1)) if m else 0
                tr.append((x.time, x.pnl * (2 if alt and k % 2 == 1 else 1)))
    return sorted(tr)

def st(tr):
    o = []
    for a, b in (('2026-01-01', '2026-07-01'), ('2026-07-01', '2027-01-01'), ('2026-01-01', '2027-01-01')):
        q = pd.Series([p for t, p in tr if a <= str(t) < b]); eq = q.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
        dd = -(eq - pk).min(); pf = q[q > 0].sum() / -q[q < 0].sum()
        o.append(f'{100*(q>0).mean():3.0f}% ${q.sum():5.0f} -${dd:3.0f} PF {pf:.2f} R {q.sum()/dd:4.1f}')
    return ' | '.join(o)

if __name__ == '__main__':
    print(f'{"high / target / lots":34}| Jan-Jun                          | Jul-Nov                          | YEAR')
    for pivot, rtp, alt in itertools.product([0, 3], ['orig+extra', 'above', 'own+extra'], [False, True]):
        name = f'{"RSI" if pivot == 0 else "3-candle"} / {rtp} / {"1-2-1-2" if alt else "flat"}'
        print(f'{name:34}| {st(run(pivot, rtp, alt))}')
