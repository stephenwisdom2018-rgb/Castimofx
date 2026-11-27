"""Owner: after the target is hit, give price room to run $X more our way (exhaustion), THEN look for a reversal:
a 3-candle high (for a buy that hit target; mirror for sells), trade the other way on the break of the next 3-candle low.
Stop $1 beyond the top of the run (min $5), target 2x risk. Optional: RSI must have reached 68+ (32- for sells)
during the run. Window 8 hours after the target. Chosen version + all filters, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.after_tp as A, research.more_trades as M, research.more_profit3 as P, research.reentry_v2 as R

RSI = [np.asarray(r) for _, _, r, *_ in R.prep]
def run(ext_need, need_rsi):
    out = []
    for fi, b, d, px in A.WIN:
        h, l, idx, sp = A.H[fi]; r = RSI[fi]; n = len(h); e = min(n - 4, b + 480)
        td = -d; reached = False; top = None; lvl = None; hot = False
        for i in range(b + 1, e):
            if not reached:
                if (h[i] - px if d == 1 else px - l[i]) >= ext_need: reached = True
                else: continue
            top = max(top or h[i], h[i]) if d == 1 else min(top or l[i], l[i])
            if (r[i] >= 68) if d == 1 else (r[i] <= 32): hot = True
            if i < b + 4: continue
            ph, pl = A.piv(h, l, i - 3)
            if (ph if d == 1 else pl): lvl = None; swing_hi = True                     # a high formed: wait for a low
            if (pl if d == 1 else ph) and top is not None: lvl = l[i-3] if d == 1 else h[i-3]
            if lvl is not None and ((l[i] < lvl) if td == -1 else (h[i] > lvl)):
                if (need_rsi and not hot) or not M.keep(fi, idx[i], td): break
                entry = lvl + (sp[i] if td == 1 else 0)
                risk = max(abs(top - entry) + 1, 5); stop, tgt = entry - td * risk, entry + td * 2 * risk
                for v in range(i, n):
                    if (l[v] <= stop) if td == 1 else (h[v] + sp[v] >= stop): out.append((idx[i], -risk)); break
                    if v > i and ((h[v] >= tgt) if td == 1 else (l[v] + sp[v] <= tgt)): out.append((idx[i], 2 * risk)); break
                break
    return out

if __name__ == '__main__':
    BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
    print('BASE                         |', M.st(sorted(BASE)))
    for ext in (10, 20, 30):
        for nr in (False, True):
            ex = run(ext, nr)
            if not ex: print(f'run ${ext}, RSI {nr}: no trades'); continue
            print(f'run ${ext}{", RSI 68/32" if nr else ""}: {len(ex)} tr, {100*np.mean([p>0 for t,p in ex]):.0f}% win, ${sum(p for t,p in ex):.0f}')
            print('  + BASE                     |', M.st(sorted(BASE + ex)))

def run_cont(ext_need):
    """after the $X run: wait for a 3-candle low (buy), then buy the break of the next 3-candle high; stop $1 below
    that low (min $5), target 2x risk."""
    out = []
    for fi, b, d, px in A.WIN:
        h, l, idx, sp = A.H[fi]; n = len(h); e = min(n - 4, b + 480)
        reached = False; ext = lvl = None
        for i in range(b + 1, e):
            if not reached:
                if (h[i] - px if d == 1 else px - l[i]) >= ext_need: reached = True
                continue
            if i < b + 4: continue
            ph, pl = A.piv(h, l, i - 3)
            if (pl if d == 1 else ph): ext, lvl = (l[i-3] if d == 1 else h[i-3]), None
            elif (ph if d == 1 else pl) and ext is not None: lvl = h[i-3] if d == 1 else l[i-3]
            if lvl is not None and ((h[i] > lvl) if d == 1 else (l[i] < lvl)):
                if not M.keep(fi, idx[i], d): break
                entry = lvl + (sp[i] if d == 1 else 0); risk = max(abs(entry - ext) + 1, 5)
                stop, tgt = entry - d * risk, entry + d * 2 * risk
                for v in range(i, n):
                    if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): out.append((idx[i], -risk)); break
                    if v > i and ((h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt)): out.append((idx[i], 2 * risk)); break
                break
    return out
