"""Owner: pullbacks that do NOT come back to the E-A zone, but stop above E and build a strong base, then continue.
(1) RSI base: zone logic in the F-E area (G above E) and G must reach RSI 32 (68 for sells).
(2) Double bottom: two 3-candle lows above E within $tol of each other (the 2nd not lower by more than tol and not
    breaking E), then buy the break of the highest high between them; stop $1 below the lower low (min $5); 2x risk.
Structures from find_signals a_levels; memory 20 days; one trade per base. All filters, 0.01, stacking as usual."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P
from research.zone_multi import zone, KW
from castimofx.sweep import find_signals

RE = dict(swings='3', target='2R', max=1)

def rsi_base(g):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        out += [(x[0], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE, region='FE', g_rsi=g)[0] if M.keep(fi, x[0], x[4])]
    return out

def double_bottom(tol, mem=20, detail=False):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(df); idx = df.index
        lv = []; find_signals(df, **KW, a_levels=lv)
        piv_l = [i for i in range(3, n - 3) if l[i] == l[i-3:i+4].min()]
        piv_h = [i for i in range(3, n - 3) if h[i] == h[i-3:i+4].max()]
        for d, A, t0, E, F in lv:
            if A is None or E is None or F is None or (F - E) * d <= 0: continue
            lows = piv_l if d == 1 else piv_h; px = l if d == 1 else h
            cand = [i for i in lows if t0 < i + 3 < t0 + mem * 1440 and 0 < (px[i] - E) * d < (F - E) * d]
            used = set()
            for a, b in zip(cand, cand[1:]):
                if abs(px[a] - px[b]) > tol or b - a < 10: continue
                seg_ext = (l[a:b+1].min() < min(px[a], px[b]) - tol) if d == 1 else (h[a:b+1].max() > max(px[a], px[b]) + tol)
                if seg_ext: continue
                top = h[a:b+1].max() if d == 1 else l[a:b+1].min(); base = min(px[a], px[b]) if d == 1 else max(px[a], px[b])
                for i in range(b + 3, min(n, b + 3 + 1440)):
                    if (l[i] < base) if d == 1 else (h[i] > base): break
                    if (h[i] > top) if d == 1 else (l[i] < top):
                        if i in used or not M.keep(fi, idx[i], d): break
                        used.add(i)
                        entry = top + (sp[i] if d == 1 else 0); risk = max(abs(entry - base) + 1, 5)
                        stop, tgt = entry - d * risk, entry + d * 2 * risk
                        for v in range(i, n):
                            if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): out.append((idx[i], -risk) + ((fi, i, d, entry, 2 * risk) if detail else ())); break
                            if v > i and ((h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt)): out.append((idx[i], 2 * risk) + ((fi, i, d, entry, 2 * risk) if detail else ())); break
                        break
    return out

if __name__ == '__main__':
    BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
    print('BASE                      |', M.st(sorted(BASE)))
    for name, ex in (('RSI base 32', rsi_base(32)), ('RSI base 30', rsi_base(30)),
                     ('double bottom $1', double_bottom(1)), ('double bottom $2', double_bottom(2)), ('double bottom $3', double_bottom(3))):
        print(f'{name}: {len(ex)} tr, {100*np.mean([p>0 for t,p in ex]) if ex else 0:.0f}% win, ${sum(p for t,p in ex):.0f}')
        print('  + BASE                  |', M.st(sorted(BASE + ex)), flush=True)
