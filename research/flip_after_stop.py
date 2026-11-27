"""Owner's idea: when a trade hits its stop, immediately trade the OTHER way (stop-and-reverse).
Flip trade: entered at the stop price, stop = the same distance as the losing trade's risk, target 1x or 2x that risk.
Checked from the next bar. With / without the usual filters on the flip. Chosen (C+3m+MZ+FE) and +Both, 2026, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F

def losers(tr, main_ids):
    out = []
    for x in tr:
        t, p, fi, d, e, T, ex = x
        if p >= 0: continue
        risk = 30.0 if id(x) in main_ids else abs(T - e) / 2
        out.append((fi, d, e - d * risk, risk, ex))
    return out

def flips(L, rr, filt, sm=1.0):
    out = []
    for fi, d, px, risk, ex in L:
        df, sp = R.prep[fi][0], R.prep[fi][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
        j = df.index.get_loc(ex); fd = -d
        if filt and not M.keep(fi, ex, fd): continue
        ent = px + (sp[j] if fd == 1 else 0); rk = risk * sm; stop, tgt = ent - fd * rk, ent + fd * rr * rk
        for v in range(j + 1, n):
            if (l[v] <= stop) if fd == 1 else (h[v] + sp[v] >= stop): out.append((ex, -rk)); break
            if (h[v] >= tgt) if fd == 1 else (l[v] + sp[v] <= tgt): out.append((ex, rr * rk)); break
    return out

if __name__ == '__main__':
    MZ = Z.micro_zone(per=3, g_rsi=32)
    main_ids = {id(x) for x in MR.MAIN}
    V = {'Chosen': MR.CH + MR.FE, '+Both': MR.CH + MR.FE + MR.DB}
    for name, tr in V.items():
        base = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
        L = losers(tr, main_ids)
        cols = {name: F.report(base)}
        for rr in (1, 2):
            for filt in (False, True):
                fl = flips(L, rr, filt)
                k = f'flip {rr}R{" filt" if filt else ""}'
                cols[k] = F.report(base + fl)
                print(f'{name} {k}: {len(fl)} flips, {100*np.mean([p>0 for t,p in fl]):.0f}% win, ${sum(p for t,p in fl):,.0f}', flush=True)
        T = pd.DataFrame(cols)
        print(T.loc[['Profit', 'Win', 'PF', 'Drop', 'Min bal', 'Worst day', 'Worst month', 'Losing months']].to_string())
