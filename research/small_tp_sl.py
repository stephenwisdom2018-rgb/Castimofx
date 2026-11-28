"""Owner idea: many trades go our way first. Take SMALL profits with SMALL stops (high win rate), then grow with lot.
Same entries as the versions (Chosen = E-A zone + main + MZ + F-E zone + 3-micro; +Both adds double bottom),
new exits: fixed take-profit $TP and stop $SL from the real entry price. True 2026 M1 data, real fills, 0.01,
commission $0.10 per trade. If TP and SL are both inside one M1 candle we count a LOSS (worst case).
CASTIMO_FILES=data/XAUUSDb_M1_2025-12_2026-11.csv CASTIMO_FILL=market python research/small_tp_sl.py"""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_zone as Z, research.micro3_reentry as MR, research.more_trades as M

df, sp = R.prep[0][0], R.prep[0][1]
o, h, l, c = (df[k].to_numpy(float) for k in ('open', 'high', 'low', 'close')); idx = df.index; n = len(c)
COMM = 0.10

def entries_3m(tr):
    """3-micro re-entries after each losing trade (original rule), returned as (time, d, entry)."""
    out = []
    o_, h_, l_, c_, sp_, ix, up, dn = MR.ARR[0]
    for t, p, fi, d, e, T, ex in tr:
        if p >= 0: continue
        j = ix.get_loc(ex); sig = up if d == 1 else dn
        u = next((v for v in range(j + 1, min(n, j + 1440)) if sig[v]), None)
        if u is None or not M.keep(0, ix[u], d): continue
        out.append((ix[u], d, c_[u] + (sp_[u] if d == 1 else 0)))
    return out

def base(tr): return [(pd.Timestamp(x[0]), x[3], x[4]) for x in tr]
MZd = [(pd.Timestamp(x[0]), x[3], x[4]) for x in Z.micro_zone(per=3, g_rsi=32, detail=True)]
CH = MR.EAZ + MR.MAIN + MR.FE
VERS = {'Chosen': base(CH) + MZd + entries_3m(CH), '+Both': base(CH + MR.DB) + MZd + entries_3m(CH + MR.DB)}

def first_moves(E, ups=(2, 3, 5, 10), downs=(2, 3, 5, 10)):
    """share of trades that reach +$up before -$down (both in one candle = against)."""
    res = {}
    for t, d, e in E:
        u0 = idx.get_loc(t) + 1
        fav = (h[u0:u0 + 2880] - e) if d == 1 else (e - (l[u0:u0 + 2880] + sp[u0:u0 + 2880]))
        adv = (e - l[u0:u0 + 2880]) if d == 1 else ((h[u0:u0 + 2880] + sp[u0:u0 + 2880]) - e)
        for U in ups:
            for D_ in downs:
                a = np.argmax(fav >= U) if (fav >= U).any() else 10**9
                b = np.argmax(adv >= D_) if (adv >= D_).any() else 10**9
                res.setdefault((U, D_), []).append(a < b)
    return res

def run(E, tp, sl):
    out = []
    for t, d, e in E:
        if t.year != 2026: continue
        u0 = idx.get_loc(t) + 1; res = None
        for s0 in range(u0, n, 2880):
            hh, ll, ss = h[s0:s0 + 2880], l[s0:s0 + 2880], sp[s0:s0 + 2880]
            hit_tp = (hh >= e + tp) if d == 1 else (ll + ss <= e - tp)
            hit_sl = (ll <= e - sl) if d == 1 else (hh + ss >= e + sl)
            a = np.argmax(hit_tp) if hit_tp.any() else 10**9; b = np.argmax(hit_sl) if hit_sl.any() else 10**9
            if a < 10**9 or b < 10**9:
                res = (tp if a < b else -sl) - COMM; ex = idx[s0 + min(a, b)]; break
        if res is not None: out.append((t, ex, res, d))
    return out

def stats(T):
    s = pd.Series([x[2] for x in T], index=[x[1] for x in T]).sort_index()
    days = pd.bdate_range('2026-01-02', '2026-11-25')
    dd = s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0)
    eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return {'Profit': f'${s.sum():,.0f}', 'Win': f'{100*(s>0).mean():.0f}%', 'Green days': f'{100*(dd>0).mean():.0f}%',
            'Avg day': f'${dd.mean():.0f}', 'Worst day': f'${dd.min():.0f}', 'Min bal': f'${mb:,.0f}'}

if __name__ == '__main__':
    E26 = [x for x in VERS['Chosen'] if x[0].year == 2026]
    fm = first_moves(E26)
    print(f'Chosen 2026: {len(E26)} entries. Share that go +$X BEFORE -$Y:')
    tab = pd.DataFrame({f'-${D_}': {f'+${U}': f'{100*np.mean(fm[(U, D_)]):.0f}%' for U in (2, 3, 5, 10)} for D_ in (2, 3, 5, 10)})
    print(tab.to_string(), flush=True)
    for v, E in VERS.items():
        cols = {}
        for tp, sl in ((2, 2), (3, 3), (2, 5), (3, 5), (5, 5), (3, 10), (5, 10), (10, 10), (5, 20)):
            cols[f'TP{tp}/SL{sl}'] = stats(run(E, tp, sl))
        print(v); print(pd.DataFrame(cols).to_string(), flush=True)
