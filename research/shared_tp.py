"""Owner: when several trades are open in the same direction, should they SHARE one take profit?
Rules: 'own' (today), 'first' (a new trade takes the TP of the oldest open same-side trade), 'newest' (all open
same-side trades move to the newest trade's TP). Each trade keeps its own stop. Main, E-A and F-E zone trades
(3 micro and MZ unchanged). Bar by bar, stop checked before target. Chosen and +Both, 2026, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F

def run(tr, main_ids, rule):
    out = []
    by_file = {}
    for x in tr: by_file.setdefault(x[2], []).append(x)
    for fi, lst in by_file.items():
        df, sp = R.prep[fi][0], R.prep[fi][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
        idx = df.index
        lst = sorted(lst, key=lambda x: x[0])
        starts = {}
        for x in lst: starts.setdefault(idx.get_loc(x[0]), []).append(x)
        open_ = []   # dicts
        first_bar = min(starts); last = n
        for v in range(first_bar, n):
            for x in starts.get(v, []):
                t, p, fi_, d, e, T, ex = x
                risk = 30.0 if id(x) in main_ids else abs(T - e) / 2
                tr_ = dict(t=t, d=d, e=e, stop=e - d * risk, tp=T, v0=v)
                same = [o for o in open_ if o['d'] == d]
                if same and rule == 'first':
                    tr_['tp'] = min(same, key=lambda o: o['v0'])['tp']
                    if (tr_['tp'] - e) * d <= 0: tr_['tp'] = T
                if same and rule == 'newest':
                    for o in same:
                        if (T - o['e']) * d > 0: o['tp'] = T
                open_.append(tr_)
            keep = []
            for o in open_:
                d = o['d']
                if (l[v] <= o['stop']) if d == 1 else (h[v] + sp[v] >= o['stop']): out.append((o['t'], (o['stop'] - o['e']) * d)); continue
                if v > o['v0'] and ((h[v] >= o['tp']) if d == 1 else (l[v] + sp[v] <= o['tp'])): out.append((o['t'], (o['tp'] - o['e']) * d)); continue
                keep.append(o)
            open_ = keep
            if not open_ and v > max(starts): break
    return out

if __name__ == '__main__':
    MZ = Z.micro_zone(per=3, g_rsi=32); main_ids = {id(x) for x in MR.MAIN}
    for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB)):
        others = MR.reentries(tr, 1, '2R') + MZ
        cols = {}
        for rule in ('own', 'first', 'newest'):
            cols[f'{name} {rule} TP'] = F.report(run(tr, main_ids, rule) + others)
        print(pd.DataFrame(cols).loc[['Profit', 'Jan-Jun', 'Jul-Nov', 'Win', 'PF', 'Min bal', 'Worst day', 'Worst month', 'Losing months']].to_string(), flush=True)
