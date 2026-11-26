"""Reversal-confirmation indicators as filters on the best A-F zone entry (E-A zone, 3-candle H/I, stop $1 below G,
target 2R, 3-day memory). Jan-Jun vs Jul-Nov 2026, 0.01 lot. Sells mirror every rule."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from castimofx.sweep import find_signals, rsi, Swing

FILES = ['data/XAUUSDb_M1_2026-01_2026-04.csv', 'data/XAUUSDb_M1_2026-04_2026-08.csv', 'data/XAUUSDb_M1_2026-08_2026-11.csv']
KW = dict(tol=1.0, minor_e=5, structure='takeout', takeout_counts=True, cancel_on_g_sweep=True)

def indicators(df):
    o, h, l, c = (df[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
    s = pd.Series(c)
    r = rsi(c)
    lo14, hi14 = pd.Series(l).rolling(14).min(), pd.Series(h).rolling(14).max()
    k = (100 * (s - lo14) / (hi14 - lo14)).rolling(3).mean(); dd = k.rolling(3).mean()
    macd = s.ewm(span=12).mean() - s.ewm(span=26).mean(); hist = macd - macd.ewm(span=9).mean()
    mid = s.rolling(20).mean(); sd = s.rolling(20).std()
    vol = df['tickvol'].to_numpy(float) if 'tickvol' in df else np.ones(len(df))
    vavg = pd.Series(vol).rolling(60).mean().to_numpy()
    return dict(o=o, h=h, l=l, c=c, r=r, k=k.to_numpy(), d=dd.to_numpy(), hist=hist.to_numpy(),
                lb=(mid - 2 * sd).to_numpy(), ub=(mid + 2 * sd).to_numpy(), vol=vol, vavg=vavg)

def confirm(name, I, g, d, prev_g):
    """Is the reversal at G (bar g) confirmed by this indicator, within G and the next 5 bars?"""
    w = range(g, min(g + 6, len(I['c'])))
    if name == 'none': return True
    if name == 'RSI divergence':
        if prev_g is None: return False
        pi, pp = prev_g
        return ((I['l'][g] < pp and I['r'][g] > I['r'][pi]) if d == 1 else (I['h'][g] > pp and I['r'][g] < I['r'][pi]))
    if name == 'Stochastic cross':
        for t in w:
            if d == 1 and I['k'][t-1] < I['d'][t-1] and I['k'][t] > I['d'][t] and I['k'][t-1] < 20: return True
            if d == -1 and I['k'][t-1] > I['d'][t-1] and I['k'][t] < I['d'][t] and I['k'][t-1] > 80: return True
        return False
    if name == 'Engulfing / pin bar':
        for t in w:
            o, h, l, c = I['o'][t], I['h'][t], I['l'][t], I['c'][t]; rng = h - l + 1e-9
            if d == 1 and ((c > o and c > I['o'][t-1] and o < I['c'][t-1] and I['c'][t-1] < I['o'][t-1]) or (min(o, c) - l) / rng > 0.6): return True
            if d == -1 and ((c < o and c < I['o'][t-1] and o > I['c'][t-1] and I['c'][t-1] > I['o'][t-1]) or (h - max(o, c)) / rng > 0.6): return True
        return False
    if name == 'MACD turning':
        return any((I['hist'][t] > I['hist'][t-1] > I['hist'][t-2]) if d == 1 else (I['hist'][t] < I['hist'][t-1] < I['hist'][t-2]) for t in w)
    if name == 'Bollinger re-entry':
        poke = (I['l'][g] < I['lb'][g]) if d == 1 else (I['h'][g] > I['ub'][g])
        back = any((I['c'][t] > I['lb'][t]) if d == 1 else (I['c'][t] < I['ub'][t]) for t in w)
        return poke and back
    if name == 'Volume spike':
        return any(I['vol'][t] > 2 * I['vavg'][t] for t in range(max(g - 2, 0), min(g + 3, len(I['c']))))

NAMES = ['none', 'RSI divergence', 'Stochastic cross', 'Engulfing / pin bar', 'MACD turning', 'Bollinger re-entry', 'Volume spike']

def run():
    rows = {n: [] for n in NAMES}
    for f in FILES:
        df = load_csv(f); raw = pd.read_csv(f, sep='\t'); sp = raw['<SPREAD>'].to_numpy(float) / 100
        df['tickvol'] = raw['<TICKVOL>'].to_numpy(float)[:len(df)] if len(raw) == len(df) else 1.0
        I = indicators(df); h, l = I['h'], I['l']; n = len(df)
        lv = []; find_signals(df, **KW, a_levels=lv)
        sw = []
        for i in range(3, n - 3):
            if h[i] == h[i-3:i+4].max(): sw.append(Swing('H', h[i], i, i + 3))
            if l[i] == l[i-3:i+4].min(): sw.append(Swing('L', l[i], i, i + 3))
        sw.sort(key=lambda x: x.confirmed); conf = np.array([x.confirmed for x in sw])
        for d, A, t0, E, *_ in lv:
            if A is None or E is None or (E - A) * d <= 0: continue
            depth = (E - A) * d; ok = lambda p: 0 < (E - p) * d < depth
            lo = 'L' if d == 1 else 'H'
            j = int(np.searchsorted(conf, t0, side='right')); end = t0 + 3 * 1440
            G = H = None; gi = None; prev = None; I_ok = False; trade = None
            last_lo = None
            while j < len(sw) and sw[j].confirmed < end:
                x = sw[j]; j += 1
                if x.kind == lo and G is None:
                    if ok(x.price): G, gi, prev = x.price, x.index, last_lo
                    else: last_lo = (x.index, x.price)
                    continue
                if G is None: continue
                if x.kind == lo:
                    if (x.price < G) if d == 1 else (x.price > G):
                        if ok(x.price): prev = (gi, G); G, gi, H, I_ok = x.price, x.index, None, False
                        else: break
                    elif H is not None: I_ok = True
                else: H, I_ok = x.price, False
                if H is not None and I_ok:
                    u = x.confirmed + 1; nxt = sw[j].confirmed if j < len(sw) else n
                    while u < min(nxt, n):
                        if (l[u] < G) if d == 1 else (h[u] > G): break
                        if (h[u] > H) if d == 1 else (l[u] < H): trade = (u, H); break
                        u += 1
                    if trade: break
            if not trade: continue
            u, lvl = trade
            entry = lvl + (sp[u] if d == 1 else 0); risk = max(abs(entry - G) + 1, 5)
            stop, target = entry - d * risk, entry + d * 2 * risk
            pnl = None
            for v in range(u, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): pnl = -risk; break
                if v > u and ((h[v] >= target) if d == 1 else (l[v] + sp[v] <= target)): pnl = 2 * risk; break
            if pnl is None: continue
            for nm in NAMES:
                if confirm(nm, I, gi, d, prev): rows[nm].append((df.index[u], pnl))
    return rows

if __name__ == '__main__':
    rows = run(); cut = pd.Timestamp('2026-07-01')
    print('indicator             | Jan-Jun: trades win net drop | Jul-Nov: trades win net drop')
    for nm, tr in rows.items():
        out = []
        for part in ([x for x in tr if x[0] < cut], [x for x in tr if x[0] >= cut]):
            p = np.array([v for _, v in part]) if part else np.zeros(1)
            eq = np.cumsum(p); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
            out.append(f'{len(part):3} {100*(p>0).mean():4.0f}% ${p.sum():6.0f} ${(eq-pk).min():5.0f}')
        print(f'{nm:21} | ' + ' | '.join(out))
