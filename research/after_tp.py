"""After a winning trade hits its target: does price continue, go sideways or reverse?
Then trade it: (1) pullback continuation: after the target, wait for a 3-candle low (buy; mirror for sells), enter on
the break of the next 3-candle high, stop $1 beyond that low (min $5), target 2x risk. (2) reversal: after the target,
wait for a 3-candle high, enter the OTHER way on the break of the next 3-candle low, stop $1 beyond that high, 2x risk.
Search window 4 hours. Chosen version, all filters on the new trades, 0.01."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_profit3 as P, research.more_trades as M
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
WIN = []                                         # (file, exit bar, direction, exit price)
for fi, (df, sp, *_) in enumerate(R.prep):
    idx = df.index
    for x in zone(df, sp, 40, 20, main=False, reent=RE)[0]:
        if M.keep(fi, x[0], x[4]) and x[1] > 0:
            WIN.append((fi, idx.get_loc(x[2]), x[4], x[13] + x[4] * x[1]))
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0):
            if M.keep(fi, x.time, x.signal.direction) and x.pnl > 0:
                WIN.append((fi, idx.get_loc(x.exit_time), x.signal.direction, x.exit))
WIN = sorted(set(WIN))
H = [(df.high.to_numpy(), df.low.to_numpy(), df.index, sp) for df, sp, *_ in R.prep]

# 1) what happens after the target (next 4 hours)
cont, rev = [], []
for fi, b, d, px in WIN:
    h, l, idx, sp = H[fi]; e = min(len(h), b + 240)
    up = (h[b+1:e].max() - px) if d == 1 else (px - l[b+1:e].min())
    dn = (px - l[b+1:e].min()) if d == 1 else (h[b+1:e].max() - px)
    cont.append(up); rev.append(dn)
cont, rev = np.array(cont), np.array(rev)
print(f'{len(WIN)} winning targets. In the next 4 hours:')
for k in (5, 10, 20):
    print(f'  price went ${k}+ further our way: {100*(cont>=k).mean():3.0f}%   |   ${k}+ back against: {100*(rev>=k).mean():3.0f}%')
print(f'  median further: ${np.median(cont):.1f}, median back: ${np.median(rev):.1f}')

def piv(h, l, i, k=3):
    return (h[i] == h[i-k:i+k+1].max(), l[i] == l[i-k:i+k+1].min())

def trade(mode):
    out = []
    for fi, b, d, px in WIN:
        h, l, idx, sp = H[fi]; n = len(h); e = min(n - 4, b + 240)
        td = d if mode == 'cont' else -d                       # trade direction
        ext = lvl = None
        for i in range(b + 4, e):                              # pivot at i-3 is known at bar i
            ph, pl = piv(h, l, i - 3)
            first, second = (pl, ph) if td == 1 else (ph, pl)  # cont buy: a low then a high
            if first: ext, lvl = (l[i-3] if td == 1 else h[i-3]), None
            elif second and ext is not None: lvl = h[i-3] if td == 1 else l[i-3]
            if lvl is not None and ((h[i] > lvl) if td == 1 else (l[i] < lvl)):
                if not M.keep(fi, idx[i], td): break
                entry = lvl + (sp[i] if td == 1 else 0); risk = max(abs(entry - ext) + 1, 5)
                stop, tgt = entry - td * risk, entry + td * 2 * risk
                for v in range(i, n):
                    if (l[v] <= stop) if td == 1 else (h[v] + sp[v] >= stop): out.append((idx[i], -risk)); break
                    if v > i and ((h[v] >= tgt) if td == 1 else (l[v] + sp[v] <= tgt)): out.append((idx[i], 2 * risk)); break
                break
    return out

if __name__ == '__main__':
    BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
    print('\nBASE                   |', M.st(sorted(BASE)))
    for mode in ('cont', 'rev'):
        ex = trade(mode)
        name = 'pullback continuation' if mode == 'cont' else 'reversal'
        print(f'{name}: {len(ex)} trades, {100*np.mean([p>0 for t,p in ex]):.0f}% win, ${sum(p for t,p in ex):.0f}')
        print(f'  + BASE               |', M.st(sorted(BASE + ex)))
