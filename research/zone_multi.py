"""More trades from the same A-F structures: allow several zone trades per structure (E-A zone, 3-candle H/I,
stop $1 below G, target 2x risk), and combine with the main strategy. Full 2026, 0.01 lot."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry, Swing

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def zone(df, sp, max_per, mem_days):
    h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(df)
    lv = []; sig, _ = find_signals(df, **KW, a_levels=lv)
    sw = []
    for i in range(3, n - 3):
        if h[i] == h[i-3:i+4].max(): sw.append(Swing('H', h[i], i, i + 3))
        if l[i] == l[i-3:i+4].min(): sw.append(Swing('L', l[i], i, i + 3))
    sw.sort(key=lambda x: x.confirmed); conf = np.array([x.confirmed for x in sw])
    out = []
    for d, A, t0, E in lv:
        if A is None or E is None or (E - A) * d <= 0: continue
        depth = (E - A) * d; ok = lambda p: 0 < (E - p) * d < depth; lo = 'L' if d == 1 else 'H'
        start, end, taken = t0, t0 + mem_days * 1440, 0
        while taken < max_per:
            j = int(np.searchsorted(conf, start, side='right'))
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
                else: H, I_ok = x.price, False
                if H is not None and I_ok:
                    u = x.confirmed + 1; nxt = sw[j].confirmed if j < len(sw) else n
                    while u < min(nxt, n):
                        if (l[u] < G) if d == 1 else (h[u] > G): break
                        if (h[u] > H) if d == 1 else (l[u] < H): trade = (u, H, G); break
                        u += 1
                    if trade: break
            if not trade: break
            u, lvl, g = trade
            entry = lvl + (sp[u] if d == 1 else 0); risk = max(abs(entry - g) + 1, 5)
            stop, target = entry - d * risk, entry + d * 2 * risk
            exit_t = None
            for v in range(u, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): out.append((df.index[u], -risk)); exit_t = v; break
                if v > u and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)): out.append((df.index[u], 2 * risk)); exit_t = v; break
            if exit_t is None: break
            taken += 1; start = exit_t
    main = simulate_reentry(df, [s for s in sig if s.bar >= 600 and s.with_boss], 20, 20, 10, 5, sp, pivot=0)
    return out, [(x.time, x.pnl) for x in main]

def stats(tr):
    s = pd.Series([v for _, v in tr], index=[t for t, _ in tr]).sort_index()
    eq = s.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
    m = s.groupby(s.index.strftime('%m')).sum()
    return f'trades {len(s):3} ({len(s)/215:.1f}/day)  win {100*(s>0).mean():.0f}%  net ${s.sum():6.0f}  worst drop ${(eq-pk).min():5.0f}  losing months {(m<0).sum()}/{len(m)}'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    for max_per, mem in ((1, 3), (3, 3), (5, 5), (10, 10), (99, 30)):
        z, m = [], []
        for df, sp in data:
            a, b = zone(df, sp, max_per, mem); z += a; m += b
        print(f'zone, up to {max_per:2} trades per structure, memory {mem:2} days: {stats(z)}')
        print(f'   + main strategy together:                       {stats(z + m)}')
