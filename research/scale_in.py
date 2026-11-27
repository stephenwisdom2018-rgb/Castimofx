"""Owner: stack more trades at DIFFERENT prices, each with its OWN target. When a trade moves against us by a x risk
(before it closes), add one more trade there: same stop level as the first trade (so a smaller risk), own target =
rr x its own risk. Up to 1 or 2 adds (at a and 2a). Stop bar counts (worst case). Chosen and +Both, 2026, 0.01."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F

def adds(tr, main_ids, a, rr, nmax):
    out = []
    for x in tr:
        t, p, fi, d, e, T, ex = x
        risk = 30.0 if id(x) in main_ids else abs(T - e) / 2
        df, sp = R.prep[fi][0], R.prep[fi][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
        i0, i1 = df.index.get_loc(t), df.index.get_loc(ex)
        S = e - d * risk
        for k in range(1, nmax + 1):
            A = e - d * k * a * risk
            if k * a >= 1: break
            j = next((v for v in range(i0, i1 + 1) if ((l[v] <= A) if d == 1 else (h[v] >= A))), None)
            if j is None: break
            ent = A + (sp[j] if d == 1 else 0); rk = abs(ent - S); tgt = ent + d * rr * rk
            for v in range(j, n):
                if (l[v] <= S) if d == 1 else (h[v] + sp[v] >= S): out.append((df.index[j], -rk)); break
                if v > j and ((h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt)): out.append((df.index[j], rr * rk)); break
    return out

if __name__ == '__main__':
    MZ = Z.micro_zone(per=3, g_rsi=32); main_ids = {id(x) for x in MR.MAIN}
    for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB)):
        base = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
        cols = {name: F.report(base)}; info = []
        for a, rr, nmax in ((0.5, 1, 1), (0.5, 2, 1), (0.33, 1, 2), (0.33, 2, 2)):
            ad = adds(tr, main_ids, a, rr, nmax)
            k = f'add {a}R tgt {rr}x x{nmax}'
            cols[k] = F.report(base + ad)
            info.append(f'{k}: {len(ad)} adds, {100*np.mean([p>0 for t,p in ad]):.0f}% win, ${sum(p for t,p in ad):,.0f}')
        print('\n'.join(info))
        print(pd.DataFrame(cols).loc[['Profit', 'Jan-Jun', 'Jul-Nov', 'Win', 'PF', 'Min bal', 'Worst day', 'Worst month', 'Losing months']].to_string(), flush=True)
