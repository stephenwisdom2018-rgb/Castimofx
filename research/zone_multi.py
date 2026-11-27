"""More trades from the same A-F structures: allow several zone trades per structure (E-A zone, 3-candle H/I,
stop $1 below G, target 2x risk), and combine with the main strategy. Full 2026, 0.01 lot."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, simulate_reentry, Swing

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def zone(df, sp, max_per, mem_days, fresh=None, rr=2.0, be=None, g_rsi=None, main=True, big_rr=None, reent=None, region='EA', hot_rr=None):
    c = df.close.to_numpy()
    from castimofx.sweep import rsi as _rsi
    r = _rsi(c)
    rsi_ok = lambda x, d: g_rsi is None or ((r[max(0, x.index - 3):x.index + 4].min() <= g_rsi) if d == 1 else (r[max(0, x.index - 3):x.index + 4].max() >= 100 - g_rsi))
    h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(df)
    lv = []; sig, _ = find_signals(df, **KW, a_levels=lv)
    sw = []
    for i in range(3, n - 3):
        if h[i] == h[i-3:i+4].max(): sw.append(Swing('H', h[i], i, i + 3))
        if l[i] == l[i-3:i+4].min(): sw.append(Swing('L', l[i], i, i + 3))
    sw.sort(key=lambda x: x.confirmed); conf = np.array([x.confirmed for x in sw])
    rsw = None
    def _reenter(v0, d, tgt0, stop_bar, cfg, info):
        """after a zone stop: wait for a high then a low, re-enter on the break of that high (buys; sells mirror).
        stop $1 beyond the lowest point since the stop (min $5); target = the first target, or 2x risk."""
        nonlocal rsw
        if cfg['swings'] == 'rsi':
            if rsw is None:
                from castimofx.sweep import rsi_swings
                rsw = sorted(rsi_swings(h, l, r, 68, 32, True), key=lambda x: x.confirmed)
            S = rsw
        else:
            S = sw
        cf = np.array([x.confirmed for x in S]); res = []; t, k = v0, 0
        while k < cfg['max'] and t < stop_bar:
            j = int(np.searchsorted(cf, t, side='right')); lvl = None; seen = False; ent = None
            while j < len(S) and S[j].confirmed < stop_bar:
                x = S[j]; j += 1
                if x.kind == ('H' if d == 1 else 'L'): lvl, seen = x.price, False
                elif lvl is not None: seen = True
                if lvl is not None and seen:
                    u = x.confirmed + 1; nxt = S[j].confirmed if j < len(S) else n
                    while u < min(nxt, stop_bar):
                        if (h[u] > lvl) if d == 1 else (l[u] < lvl): ent = u; break
                        u += 1
                    if ent: break
            if ent is None: break
            entry = lvl + (sp[ent] if d == 1 else 0)
            ext = l[v0:ent + 1].min() if d == 1 else h[v0:ent + 1].max()
            risk = max(abs(entry - ext) + 1, 5); stop = entry - d * risk
            target = tgt0 if cfg['target'] == 'orig' else entry + d * cfg.get('rr', 2) * risk
            if (target - entry) * d <= 0: break
            ex = None
            for v in range(ent, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res.append((df.index[ent], d * (stop - entry), df.index[v]) + info[:3] + (-1,) + info[4:10] + (entry,)); ex = v; break
                if v > ent and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)): res.append((df.index[ent], abs(target - entry), df.index[v]) + info[:3] + (-1,) + info[4:10] + (entry,)); ex = v; break
            if ex is None or res[-1][1] > 0: break
            k += 1; t = ex; v0 = ex
        return res
    out = []
    for d, A, t0, E, F in lv:
        if A is None or E is None or (E - A) * d <= 0: continue
        depth = (E - A) * d; ok = lambda p: 0 < (E - p) * d < depth; lo = 'L' if d == 1 else 'H'
        if region == 'FE':                                                # shallow pullback: G between F and E
            if (F - E) * d <= 0: continue
            ok = lambda p: 0 < (F - p) * d < (F - E) * d
        start, end, taken = t0, t0 + mem_days * 1440, 0
        if fresh:                                                        # first touch only: trade the first visit to the zone
            tt = t0
            while tt < min(end, n) and not ((l[tt] < E) if d == 1 else (h[tt] > E)): tt += 1
            v = tt + 1
            while v < min(end, n):
                if fresh == 'close above E' and ((c[v] > E) if d == 1 else (c[v] < E)): break
                if fresh == 'one zone-height above E' and ((h[v] > E + depth) if d == 1 else (l[v] < E - depth)): break
                v += 1
            end = min(end, v)
        while taken < max_per:
            j = int(np.searchsorted(conf, start, side='right'))
            G = H = None; I_ok = False; trade = None
            while j < len(sw) and sw[j].confirmed < end:
                x = sw[j]; j += 1
                if G is None:
                    if x.kind == lo and ok(x.price) and rsi_ok(x, d): G = x.price
                    continue
                if x.kind == lo:
                    if (x.price < G) if d == 1 else (x.price > G):
                        if ok(x.price) and rsi_ok(x, d): G, H, I_ok = x.price, None, False
                        else: break
                    elif H is not None: I_ok = True
                else: H, I_ok = x.price, False
                if H is not None and I_ok:
                    u = x.confirmed + 1; nxt = sw[j].confirmed if j < len(sw) else n
                    while u < min(nxt, n):
                        if (l[u] < G) if d == 1 else (h[u] > G): break
                        if u >= end: break
                        if (h[u] > H) if d == 1 else (l[u] < H): trade = (u, H, G); break
                        u += 1
                    if trade: break
            if not trade: break
            u, lvl, g = trade
            entry = lvl + (sp[u] if d == 1 else 0); risk = max(abs(entry - g) + 1, 5)
            trr = big_rr if (big_rr and risk > 20) else rr                 # bigger target for big-stop trades
            if hot_rr and ((r[u] >= 68) if d == 1 else (r[u] <= 32)): trr = hot_rr   # RSI already hot at entry
            stop, target = entry - d * risk, entry + d * trr * risk
            exit_t = None; info = ('zone', d, risk, taken, depth, abs(F - E), (E - g) * d / depth, (u - t0) / 60, abs(lvl - g), u, entry)
            for v in range(u, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop):
                    out.append((df.index[u], d * (stop - entry), df.index[v]) + info); exit_t = v; break
                if v > u and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)):
                    out.append((df.index[u], trr * risk, df.index[v]) + info); exit_t = v; break
                if be is not None and ((h[v] >= entry + be * risk) if d == 1 else (l[v] + sp[v] <= entry - be * risk)):
                    stop = entry if d == 1 else entry          # move the stop to breakeven
            if exit_t is None: break
            if reent and out[-1][1] < 0:
                out += _reenter(exit_t, d, target, min(n - 1, max(end, exit_t + 4320)), reent, info)
            taken += 1; start = exit_t
    if not main: return out, []
    main = simulate_reentry(df, [s for s in sig if s.bar >= 600 and s.with_boss], 20, 20, 10, 5, sp, pivot=0)
    return out, [(x.time, x.pnl, x.exit_time, id(x.signal), x.signal.direction) for x in main]

def stats(tr):
    s = pd.Series([x[1] for x in tr], index=[x[0] for x in tr]).sort_index()
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
