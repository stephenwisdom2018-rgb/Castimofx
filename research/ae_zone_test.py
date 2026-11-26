"""Owner's idea: every completed structure A-F is remembered. When price comes back, a low that sweeps into the
zone is G (below E / between A and E / below A), then H, then I (not below G), and a break of H is a buy
($20 stop, $20 target, once per structure). Sells mirror it. Full 2026, 0.01 lot."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi, rsi_swings, Swing

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def pivots(h, l, k):
    out = []
    for i in range(k, len(h) - k):
        if h[i] == h[i - k:i + k + 1].max(): out.append(Swing('H', h[i], i, i + k))
        if l[i] == l[i - k:i + k + 1].min(): out.append(Swing('L', l[i], i, i + k))
    return sorted(out, key=lambda x: x.confirmed)

def zone_trades(df, sp, zone, swings_kind, max_days=30, max_below=30, sl=20, tp=20):
    lv = []
    find_signals(df, **KW, a_levels=lv)
    h, l, c = (df[k].to_numpy(float) for k in ('high', 'low', 'close'))
    sw = rsi_swings(h, l, rsi(c), 68, 32, True) if swings_kind == 'rsi' else pivots(h, l, 3)
    conf = np.array([x.confirmed for x in sw])
    out = []
    for d, A, t0, E, *_ in lv:
        if A is None or E is None:
            continue
        lo_kind, hi_kind = ('L', 'H') if d == 1 else ('H', 'L')
        if zone == 'below E':
            ok = lambda p: (p < E and p > E - max_below) if d == 1 else (p > E and p < E + max_below)
        elif zone == 'between A and E':
            ok = lambda p: (A < p < E) if d == 1 else (E < p < A)
        else:  # below A
            ok = lambda p: (p < A and p > A - max_below) if d == 1 else (p > A and p < A + max_below)
        end = t0 + max_days * 1440
        j = int(np.searchsorted(conf, t0, side='right'))
        G = H = None; Ht = -1; I_ok = False; trade = None
        while j < len(sw) and sw[j].confirmed < end:
            x = sw[j]; j += 1
            if G is None:
                if x.kind == lo_kind and ok(x.price): G = x.price
                continue
            if x.kind == lo_kind:
                if (x.price < G) if d == 1 else (x.price > G):
                    if ok(x.price): G, H, I_ok = x.price, None, False  # deeper G inside the zone
                    else: break  # left the zone
                elif H is not None:
                    I_ok = True
            elif x.kind == hi_kind:
                H, Ht, I_ok = x.price, x.confirmed, False
            if H is not None and I_ok:
                # wait for the break of H from the next bar
                u = x.confirmed + 1
                nxt = sw[j].confirmed if j < len(sw) else len(df)
                while u < min(nxt, len(df)):
                    if (l[u] < G) if d == 1 else (h[u] > G): break
                    if (h[u] > H) if d == 1 else (l[u] < H):
                        trade = (u, H); break
                    u += 1
                if trade: break
        if not trade: continue
        u, lvl = trade
        entry = lvl + (sp[u] if d == 1 else 0); stop, target = entry - d * sl, entry + d * tp
        for v in range(u, len(df)):
            if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop):
                out.append((df.index[u], d, -sl)); break
            if v > u and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)):
                out.append((df.index[u], d, tp)); break
    return out

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    for swk in ('rsi', 'small'):
        for zone in ('below E', 'between A and E', 'below A'):
            allt = []
            for df, sp in data: allt += zone_trades(df, sp, zone, swk)
            allt.sort(); p = np.array([x[2] for x in allt]) if allt else np.zeros(1)
            eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
            print(f'{swk:5} swings, G {zone:16}: trades {len(allt):3}  win {100*(p>0).mean():.0f}%  net ${p.sum():.0f}  worst drop ${(eq-pk).min():.0f}')
