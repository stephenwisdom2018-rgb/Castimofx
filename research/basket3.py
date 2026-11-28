"""Owner idea v3: basket with STOP orders (add WITH the move): 1st order at the entry, buy-stops every $S above it
(sells mirror) up to the entry's target. Close everything when the whole basket is up by the entry's $ target,
or at the basket stop (the entry's own stop). True 2026 M1, real fills, 0.01 per order, $0.10 commission per order.
Worst case per candle: stop first, then the target with orders filled BEFORE this candle, then new fills."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.basket2 as B2

h, l, sp, idx, n, c = B2.h, B2.l, B2.sp, B2.idx, B2.n, B2.c
COMM = 0.10

def basket(t, d, e, tgt, risk, Sg, maxo=99):
    u = idx.get_loc(t); stop = e - d * risk
    levels = [e + d * k * Sg for k in range(1, maxo) if k * Sg < tgt]
    filled = [e]; nxt = 0
    for v in range(u + 1, n):
        bid_lo, bid_hi, ask_lo, ask_hi = l[v], h[v], l[v] + sp[v], h[v] + sp[v]
        if (bid_lo <= stop) if d == 1 else (ask_hi >= stop):
            return idx[v], sum((stop - p) * d for p in filled) - COMM * len(filled), len(filled)
        best = bid_hi if d == 1 else ask_lo
        if sum((best - p) * d for p in filled) >= tgt:
            return idx[v], tgt - COMM * len(filled), len(filled)
        while nxt < len(levels) and ((ask_hi >= levels[nxt]) if d == 1 else (bid_lo <= levels[nxt])):
            filled.append(levels[nxt] + (sp[v] if d == 1 else 0)); nxt += 1
    return idx[n - 1], sum((c[-1] - p) * d for p in filled), len(filled)

def run(E, Sg):
    E = sorted(x for x in E if x[0].year == 2026); T = [basket(*x, Sg) for x in E]
    s = pd.Series([q[1] for q in T], index=[q[0] for q in T]).sort_index()
    days = pd.bdate_range('2026-01-02', '2026-11-25')
    dd = s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0); wk = dd.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': f'${s.sum():,.0f}', 'Win': f'{100*(s>0).mean():.0f}%', 'Avg orders': f'{np.mean([q[2] for q in T]):.1f}',
            'Green days': f'{100*(dd>0).mean():.0f}%', 'Green wks': f'{100*(wk>0).mean():.0f}%', 'Worst day': f'${dd.min():.0f}',
            'Worst wk': f'${wk.min():.0f}', 'Min bal': f'${mb:,.0f}'}

if __name__ == '__main__':
    for v, E in B2.VERS.items():
        cols = {('1 order' if Sg == 999 else f'stops ${Sg}'): run(E, Sg) for Sg in (999, 2, 3, 5, 10)}
        print(v); print(pd.DataFrame(cols).to_string(), flush=True)
