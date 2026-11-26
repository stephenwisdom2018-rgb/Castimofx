"""Search for the most accurate entry on the owner's A-F structures (zone below E).
Entries are chosen on Jan-Jun 2026 and checked on Jul-Nov 2026. 0.01 lot."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from multiprocessing import Pool
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi, rsi_swings, Swing

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)
DATA = None

def load():
    global DATA
    DATA = []
    for f in FILES:
        df = load_csv(f); sp = pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100
        lv = []; find_signals(df, **KW, a_levels=lv)
        h, l, c = (df[k].to_numpy(float) for k in ('high', 'low', 'close'))
        sw = {'rsi': rsi_swings(h, l, rsi(c), 68, 32, True)}
        for k in (2, 3, 5, 8):
            out = []
            for i in range(k, len(h) - k):
                if h[i] == h[i - k:i + k + 1].max(): out.append(Swing('H', h[i], i, i + k))
                if l[i] == l[i - k:i + k + 1].min(): out.append(Swing('L', l[i], i, i + k))
            sw[k] = sorted(out, key=lambda x: x.confirmed)
        DATA.append((df, sp, lv, h, l, sw))

def trades(params):
    zone, swk, mem_days, stop_mode, tp = params
    res = []
    for df, sp, lv, h, l, swd in DATA:
        sw = swd[swk]; conf = np.array([x.confirmed for x in sw]); n = len(df)
        for d, A, t0, E, *_ in lv:
            if A is None or E is None: continue
            lo, hi = ('L', 'H') if d == 1 else ('H', 'L')
            depth = (E - A) * d
            if depth <= 0: continue
            if zone == 'E to A': ok = lambda p: 0 < (E - p) * d < depth
            elif zone == 'top half E-A': ok = lambda p: 0 < (E - p) * d < depth / 2
            elif zone == 'bottom half E-A': ok = lambda p: depth / 2 <= (E - p) * d < depth
            elif zone == 'E to A + $10': ok = lambda p: 0 < (E - p) * d < depth + 10
            end = t0 + mem_days * 1440
            j = int(np.searchsorted(conf, t0, side='right'))
            G = H = None; I_ok = False; trade = None
            while j < len(sw) and sw[j].confirmed < end:
                x = sw[j]; j += 1
                if G is None:
                    if x.kind == lo and ok(x.price): G = x.price
                    continue
                if x.kind == lo:
                    if (x.price < G) if d == 1 else (x.price > G):
                        if ok(x.price): G, H, I_ok = x.price, None, False
                        else: break
                    elif H is not None: I_ok = True
                else:
                    H, I_ok = x.price, False
                if H is not None and I_ok:
                    u = x.confirmed + 1; nxt = sw[j].confirmed if j < len(sw) else n
                    while u < min(nxt, n):
                        if (l[u] < G) if d == 1 else (h[u] > G): break
                        if (h[u] > H) if d == 1 else (l[u] < H): trade = (u, H, G); break
                        u += 1
                    if trade: break
            if not trade: continue
            u, lvl, g = trade
            entry = lvl + (sp[u] if d == 1 else 0)
            risk = 20 if stop_mode == '$20' else max(abs(entry - g) + 1, 5)
            stop, target = entry - d * risk, entry + d * (tp if stop_mode == '$20' else tp / 20 * risk)
            for v in range(u, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop):
                    res.append((df.index[u], -risk / 20)); break
                if v > u and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)):
                    res.append((df.index[u], (abs(target - entry)) / 20)); break
    return params, res

def score(res, a, b):
    p = np.array([r for t, r in res if a <= t < b])
    if len(p) == 0: return 0, 0, 0, 0
    eq = np.cumsum(p) * 20; pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    return len(p), 100 * (p > 0).mean(), p.sum() * 20, (eq - pk).min()

if __name__ == '__main__':
    grid = list(itertools.product(['E to A', 'top half E-A', 'bottom half E-A', 'E to A + $10'], ['rsi', 2, 3, 5, 8],
                                  [3, 30], ['$20', 'below G'], [20, 40]))
    with Pool(4, initializer=load) as pool:
        out = pool.map(trades, grid)
    A, B, C = pd.Timestamp('2026-01-01'), pd.Timestamp('2026-07-01'), pd.Timestamp('2026-12-01')
    rows = []
    for params, res in out:
        n1, w1, net1, dd1 = score(res, A, B); n2, w2, net2, dd2 = score(res, B, C)
        rows.append((params, n1, w1, net1, dd1, n2, w2, net2, dd2))
    rows.sort(key=lambda r: -r[3])
    print('params (zone, swings, memory days, stop, target) | Jan-Jun: trades win net drop | Jul-Nov: trades win net drop')
    for r in rows[:15]:
        print(f'{str(r[0]):52} | {r[1]:3} {r[2]:4.0f}% ${r[3]:6.0f} ${r[4]:5.0f} | {r[5]:3} {r[6]:4.0f}% ${r[7]:6.0f} ${r[8]:5.0f}')
