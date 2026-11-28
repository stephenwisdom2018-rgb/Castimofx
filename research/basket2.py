"""Owner idea v2: BASKET PER ENTRY. Each entry keeps its own $ target (main $20, zone/MZ/3m/DB 2x risk) and gets one
basket stop. 1st order at the entry, pendings every $S against us down to the stop. When the WHOLE basket is up by the
entry's $ target (all orders together, 0.01 each), close everything; if price hits the basket stop, close everything.
Stop = the entry's own stop (x1) or x2. True 2026 M1, real fills, commission $0.10 per order.
Worst case per candle: stop checked first, then the target with the orders filled BEFORE this candle, then new fills.
'one at a time' = a new entry only when no basket is open."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.small_tp_sl as S, research.micro3_reentry as MR, research.micro3_zone as Z, research.more_trades as M

h, l, sp, idx, n, c = S.h, S.l, S.sp, S.idx, S.n, S.c
COMM = 0.10

def lists(tr):
    E = [(pd.Timestamp(x[0]), x[3], x[4], abs(x[5] - x[4]), abs(x[5] - x[4]) / 2 if abs(x[5] - x[4]) else 5) for x in tr]
    return E

def main_list():
    return [(pd.Timestamp(x[0]), x[3], x[4], abs(x[5] - x[4]), 30.0) for x in MR.MAIN]

def m3_list(tr):
    o_, h_, l_, c_, sp_, ix, up, dn = MR.ARR[0]; out = []
    for t, p, fi, d, e, T, ex in tr:
        if p >= 0: continue
        j = ix.get_loc(ex); sig = up if d == 1 else dn
        u = next((v for v in range(j + 1, min(n, j + 1440)) if sig[v]), None)
        if u is None or not M.keep(0, ix[u], d): continue
        ent = c_[u] + (sp_[u] if d == 1 else 0)
        ext = l_[j:u + 1].min() if d == 1 else h_[j:u + 1].max(); risk = max(abs(ent - ext) + 1, 5)
        out.append((ix[u], d, ent, 2 * risk, risk))
    return out

MZd = [(pd.Timestamp(x[0]), x[3], x[4], abs(x[5] - x[4]), abs(x[5] - x[4]) / 2) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
CHt = MR.EAZ + MR.FE
ZONES = [(pd.Timestamp(x[0]), x[3], x[4], abs(x[5] - x[4]), abs(x[5] - x[4]) / 2) for x in MR.EAZ + MR.FE]
DBl = [(pd.Timestamp(x[0]), x[3], x[4], abs(x[5] - x[4]), abs(x[5] - x[4]) / 2) for x in MR.DB]
VERS = {'Chosen': ZONES + main_list() + MZd + m3_list(MR.CH + MR.FE),
        '+Both': ZONES + main_list() + MZd + DBl + m3_list(MR.CH + MR.FE + MR.DB)}

def basket(t, d, e, tgt, risk, Sg, mult, maxo=99):
    u = idx.get_loc(t); B = risk * mult; stop = e - d * B
    levels = [e - d * k * Sg for k in range(1, maxo) if k * Sg < B]
    filled = [e]; nxt = 0
    for v in range(u + 1, n):
        bid_lo, bid_hi, ask_lo, ask_hi = l[v], h[v], l[v] + sp[v], h[v] + sp[v]
        if (bid_lo <= stop) if d == 1 else (ask_hi >= stop):
            return idx[v], sum(-abs(p - stop) for p in filled) - COMM * len(filled), len(filled)
        best = bid_hi if d == 1 else ask_lo
        if sum((best - p) * d for p in filled) >= tgt:
            return idx[v], tgt - COMM * len(filled), len(filled)
        while nxt < len(levels) and ((ask_lo <= levels[nxt]) if d == 1 else (bid_hi >= levels[nxt])):
            filled.append(levels[nxt]); nxt += 1
    return idx[n - 1], sum((c[-1] - p) * d for p in filled), len(filled)

def run(E, Sg, mult, one=False):
    E = sorted(x for x in E if x[0].year == 2026); T = []; busy = None
    for x in E:
        if one and busy is not None and x[0] < busy: continue
        ex, p, k = basket(*x, Sg, mult); T.append((ex, p, k)); busy = ex
    s = pd.Series([q[1] for q in T], index=[q[0] for q in T]).sort_index()
    days = pd.bdate_range('2026-01-02', '2026-11-25')
    dd = s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0); wk = dd.resample('W').sum()
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': f'${s.sum():,.0f}', 'Baskets': len(s), 'Win': f'{100*(s>0).mean():.0f}%', 'Avg orders': f'{np.mean([q[2] for q in T]):.1f}',
            'Green days': f'{100*(dd>0).mean():.0f}%', 'Green wks': f'{100*(wk>0).mean():.0f}%', 'Worst day': f'${dd.min():.0f}',
            'Worst wk': f'${wk.min():.0f}', 'Min bal': f'${mb:,.0f}'}

if __name__ == '__main__':
    for v, E in VERS.items():
        cols = {'normal 1 order': None}
        cols = {}
        for Sg, mult, one in ((99, 1, False), (5, 1, False), (3, 1, False), (5, 2, False), (3, 2, False), (5, 1, True), (5, 2, True)):
            cols[('1 order' if Sg == 99 else f'S{Sg} stop x{mult}') + (' one' if one else '')] = run(E, Sg, mult, one)
        print(v); print(pd.DataFrame(cols).to_string(), flush=True)
