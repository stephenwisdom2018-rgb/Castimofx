"""3-micro as a NEW zone entry: after a 3-candle low (G) inside the E-A zone, enter on the first '3 micro inside
SMA 10' (3 rising candles closing above SMA 10; sells mirror) before price breaks below G, within 4 h. Stop $1 below G
(min $5), target 2x risk. One trade per G, one per minute and side. Filters on. Added to C+3m and B+3m. 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.micro3_reentry as MR
from research.zone_multi import KW
from castimofx.sweep import find_signals

def micro_zone(region='EA', wait=240, rr=2.0, per=99, g_rsi=None):
    out, seen = [], set()
    for fi, (df, sp, *_) in enumerate(R.prep):
        o, h, l, c, sp_, idx, up, dn = MR.ARR[fi]; n = len(c)
        lv = []; find_signals(df, **KW, a_levels=lv)
        piv_l = np.array([i for i in range(3, n - 3) if l[i] == l[i-3:i+4].min()])
        piv_h = np.array([i for i in range(3, n - 3) if h[i] == h[i-3:i+4].max()])
        for d, A, t0, E, F in lv:
            if A is None or E is None or (E - A) * d <= 0: continue
            depth = (E - A) * d
            piv = piv_l if d == 1 else piv_h; px = l if d == 1 else h
            cand = piv[(piv + 3 > t0) & (piv + 3 < t0 + 20 * 1440)]; taken = 0
            r = R.prep[fi][2].to_numpy() if hasattr(R.prep[fi][2], 'to_numpy') else np.asarray(R.prep[fi][2])
            for g in cand:
                if taken >= per: break
                if g_rsi and not ((r[max(0, g-3):g+4].min() <= g_rsi) if d == 1 else (r[max(0, g-3):g+4].max() >= 100 - g_rsi)): continue
                G = px[g]
                if region == 'EA' and not (0 < (E - G) * d < depth): continue
                if region == 'FE' and not (F is not None and 0 < (F - G) * d < (F - E) * d): continue
                sig = up if d == 1 else dn
                for u in range(g + 3, min(n, g + 3 + wait)):
                    if (l[u] < G) if d == 1 else (h[u] > G): break
                    if sig[u]:
                        if (idx[u], d) in seen or not M.keep(fi, idx[u], d): break
                        seen.add((idx[u], d)); taken += 1
                        ent = c[u] + (sp_[u] if d == 1 else 0); risk = max(abs(ent - G) + 1, 5)
                        stop, tgt = ent - d * risk, ent + d * rr * risk
                        for v in range(u + 1, n):
                            if (l[v] <= stop) if d == 1 else (h[v] + sp_[v] >= stop): out.append((idx[u], -risk)); break
                            if (h[v] >= tgt) if d == 1 else (l[v] + sp_[v] <= tgt): out.append((idx[u], rr * risk)); break
                        break
    return out

if __name__ == '__main__':
    MZ = micro_zone()
    print(f'3-micro zone entries: {len(MZ)} tr, {100*np.mean([p>0 for t,p in MZ]):.0f}% win, ${sum(p for t,p in MZ):.0f}')
    for ver, tr in (('C+3m', MR.CH), ('B+3m', MR.CH + MR.EX)):
        base = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R')
        print(f'{ver:6}              | {M.st(sorted(base))}')
        print(f'{ver:6} + micro zone | {M.st(sorted(base + MZ))}', flush=True)
