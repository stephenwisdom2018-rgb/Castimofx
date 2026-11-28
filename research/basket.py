"""Owner idea: BASKET. At each signal: 1st trade at market; pending orders every $S further against us down to a
basket stop $B from the 1st entry; every order has its own $10 take-profit; if price reaches the basket stop all
open orders close and unfilled ones cancel. Unfilled pendings also cancel when the 1st trade takes profit.
Same entries as Chosen / +Both. True 2026 M1, real fills, 0.01 per order, commission $0.10 per order.
Worst case inside a candle: fill and stop in one candle = loss; take-profit only from the candle after the fill.
CASTIMO_FILES=data/XAUUSDb_M1_2025-12_2026-11.csv CASTIMO_FILL=market python research/basket.py"""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.small_tp_sl as S

h, l, sp, idx, n = S.h, S.l, S.sp, S.idx, S.n
TP, COMM, W = 10.0, 0.10, 4 * 1440
BIG = 10**9

def first(mask, start=0):
    k = np.argmax(mask[start:]) if mask[start:].any() else -1
    return BIG if k < 0 else start + k

def mae_before_tp(E):
    out = []
    for t, d, e in E:
        u0 = idx.get_loc(t) + 1; hh, ll, ss = h[u0:u0 + W], l[u0:u0 + W], sp[u0:u0 + W]
        fav = (hh - e) if d == 1 else (e - (ll + ss)); adv = (e - ll) if d == 1 else (hh + ss - e)
        a = first(fav >= TP)
        if a < BIG: out.append(adv[:a + 1].max())
    return np.array(out)

def basket(t, d, e, B, Sg):
    u0 = idx.get_loc(t); hh, ll, ss = h[u0:u0 + W], l[u0:u0 + W], sp[u0:u0 + W]
    bid_lo, bid_hi, ask_lo, ask_hi = ll, hh, ll + ss, hh + ss
    stop = e - d * B
    s = first((bid_lo <= stop) if d == 1 else (ask_hi >= stop), 1)
    res = []; t0 = None
    for k in range(int(np.ceil(B / Sg))):
        p = e - d * k * Sg
        if k * Sg >= B: break
        if k == 0: f = 0
        else:
            f = first((ask_lo <= p) if d == 1 else (bid_hi >= p), 1)
            if f >= BIG or f > s or (t0 is not None and f > t0): continue
        tp = first((bid_hi >= p + TP) if d == 1 else (ask_lo <= p - TP), f + 1)
        if k == 0: t0 = tp
        if tp < s and tp < BIG: res.append((idx[u0 + tp], TP - COMM))
        elif s < BIG: res.append((idx[u0 + s], -abs(p - stop) - COMM))
        else: res.append((idx[min(n - 1, u0 + W - 1)], ((hh[-1] - p) if d == 1 else (p - ask_lo[-1])) - COMM))
    return res

def stats(T):
    s = pd.Series([x[1] for x in T], index=[x[0] for x in T]).sort_index()
    days = pd.bdate_range('2026-01-02', '2026-11-25')
    dd = s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0); wk = dd.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': f'${s.sum():,.0f}', 'Orders': len(s), 'Win': f'{100*(s>0).mean():.0f}%', 'Green days': f'{100*(dd>0).mean():.0f}%',
            'Green wks': f'{100*(wk>0).mean():.0f}%', 'Worst day': f'${dd.min():.0f}', 'Worst wk': f'${wk.min():.0f}', 'Min bal': f'${mb:,.0f}'}

if __name__ == '__main__':
    E = [x for x in S.VERS['Chosen'] if x[0].year == 2026]
    m = mae_before_tp(E)
    print(f'{len(E)} entries, {len(m)} reach +$10 within 4 days. How far they went AGAINST us first:')
    print('  ' + '  '.join(f'{q}%: ${np.percentile(m, q):.0f}' for q in (50, 70, 80, 90, 95)), flush=True)
    for v, Ev in S.VERS.items():
        Ev = [x for x in Ev if x[0].year == 2026]; cols = {}
        for B, Sg in ((10, 5), (20, 5), (20, 10), (30, 5), (30, 10), (50, 10), (50, 5)):
            T = [r for x in Ev for r in basket(*x, B, Sg)]
            cols[f'B{B}/S{Sg}'] = stats(T)
        print(v); print(pd.DataFrame(cols).to_string(), flush=True)
