"""Owner's hedge idea: when a trade reaches its stop, keep it open and open an opposite HEDGE (same lot) at the stop
level. Hedge target = k x risk; hedge closes at a small loss if price returns to the original entry. When the hedge is
closed and price comes back to the stop level, hedge again. The original closes at its target or at a hard stop m x
risk away (the hedge, if open, closes there too). Bars checked with the worst-case order (bad events first).
Only trades that reached their stop change; winners are unchanged. Chosen and +Both, 2026, 0.01."""
import sys, itertools
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F

def hedge_result(fi, d, e, T, risk, k, m):
    df, sp = R.prep[fi][0], R.prep[fi][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
    i0 = df.index.get_loc(e[1]); e = e[0]
    S = e - d * risk; HS = e - d * m * risk; HT = S - d * k * risk
    # find when the stop level is first reached (from entry bar)
    j = next((v for v in range(i0, n) if ((l[v] <= S) if d == 1 else (h[v] >= S))), None)
    if j is None: return None
    pnl = 0.0; hedge = True; armed = False; v = j
    while v < n:
        lo, hi = l[v], h[v]
        adverse = (lo <= HS) if d == 1 else (hi >= HS)
        if adverse:                                              # hard stop: original -m R, hedge (if open) wins S->HS
            pnl += -m * risk + ((m - 1) * risk if hedge else 0); return pnl, df.index[v]
        tgt = ((hi >= T) if d == 1 else (lo <= T)) and v > j
        if hedge:
            back = ((hi >= e) if d == 1 else (lo <= e)) and v > j   # price back to the entry: hedge closes at -1R
            ht = (lo <= HT) if d == 1 else (hi >= HT)
            if back: pnl -= risk; hedge = False; armed = True
            elif ht: pnl += k * risk; hedge = False; armed = False
        else:
            if (hi > S) if d == 1 else (lo < S): armed = True        # price came back above the stop level
            elif armed and ((lo <= S) if d == 1 else (hi >= S)): hedge = True; armed = False   # crosses it again: hedge at S
        if tgt:
            return pnl + abs(T - e) - ((abs(T - e) + risk) if hedge else 0), df.index[v]
        v += 1
    return pnl, df.index[n - 1]

if __name__ == '__main__':
    MZ = Z.micro_zone(per=3, g_rsi=32); main_ids = {id(x) for x in MR.MAIN}
    for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB)):
        others = MR.reentries(tr, 1, '2R') + MZ
        base = [(x[0], x[1]) for x in tr] + others
        cols = {name: F.report(base)}
        for k, m in itertools.product((0.5, 1.0), (2, 3)):
            out = []
            for x in tr:
                t, p, fi, d, e, T, ex = x
                if p >= 0: out.append((t, p)); continue
                risk = 30.0 if id(x) in main_ids else abs(T - e) / 2
                r = hedge_result(fi, d, (e, t), T, risk, k, m)
                out.append((t, p if r is None else r[0]))
            cols[f'hedge k{k} m{m}'] = F.report(out + others)
        print(pd.DataFrame(cols).loc[['Profit', 'Jan-Jun', 'Jul-Nov', 'Win', 'PF', 'Min bal', 'Worst day', 'Worst month', 'Losing months']].to_string(), flush=True)
