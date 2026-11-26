"""Where else is money lost? Rules tested on the chosen combination (main + E-A zone, up to 10 per structure).
A rule is kept only if it improves win rate, profit AND worst drop, in both halves of 2026. 0.01 lot.
Each rule only uses trades that had already closed before the new entry (no look-ahead)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from research.zone_multi import zone, FILES

data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
trades = []                               # (entry time, pnl, exit time, source, direction)
for df, sp in data:
    z, m = zone(df, sp, 10, 10)
    trades += [(x[0], x[1], x[2], 'zone', x[4]) for x in z] + [(x[0], x[1], x[2], 'main', x[4]) for x in m]
trades.sort(key=lambda x: x[0])

def apply(rule):
    kept = []
    for tr in trades:
        t, pnl, ex, src, d = tr
        closed_today = [k for k in kept if k[2] <= t and k[2].date() == t.date()]
        open_now = [k for k in kept if k[0] <= t < k[2]]
        if rule(t, d, src, closed_today, open_now): kept.append(tr)
    return kept

def st(tr):
    out = []
    for a, b in (('2026-01-01', '2026-07-01'), ('2026-07-01', '2027-01-01')):
        q = pd.Series([x[1] for x in tr if a <= str(x[0]) < b])
        eq = q.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
        out.append(f'{len(q):3} tr {100*(q>0).mean():3.0f}% ${q.sum():5.0f} drop ${(eq-pk).min():5.0f}')
    return ' | '.join(out)

loss = lambda c: sum(k[1] for k in c if k[1] < 0)
nloss = lambda c: sum(k[1] < 0 for k in c)
RULES = {
    'none (current)': lambda t, d, s, c, o: True,
    'stop for the day after 2 losses': lambda t, d, s, c, o: nloss(c) < 2,
    'stop for the day after 3 losses': lambda t, d, s, c, o: nloss(c) < 3,
    'stop for the day after -$40': lambda t, d, s, c, o: loss(c) > -40,
    'stop for the day after -$60': lambda t, d, s, c, o: loss(c) > -60,
    'no buy while a sell is open (and v.v.)': lambda t, d, s, c, o: all(k[4] == d for k in o),
    'max 3 trades open': lambda t, d, s, c, o: len(o) < 3,
    'max 5 trades open': lambda t, d, s, c, o: len(o) < 5,
    'max 2 open same direction': lambda t, d, s, c, o: sum(k[4] == d for k in o) < 2,
    'skip if last closed trade today lost': lambda t, d, s, c, o: not c or max(c, key=lambda k: k[2])[1] > 0,
}
if __name__ == '__main__':
    print(f'{"rule":40}| Jan-Jun                          | Jul-Nov')
    for name, rule in RULES.items():
        print(f'{name:40}| {st(apply(rule))}')
