"""$200 account, $200 mode (C+3m+MZ, 1 trade at a time, stops <= $15), 2026 at 0.01, with and without flips
(after a stopped main/zone trade: opposite trade, stop 0.5x its risk, target 1.5x). True stop sizes (main = $30)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.micro3_reentry as MR, research.micro3_zone as Z

def build():
    main_ids = {id(x) for x in MR.MAIN}
    out = []   # (t, exit, pnl, risk, kind, fi, d, entry)
    for x in MR.EAZ + MR.MAIN:
        t, p, fi, d, e, T, ex = x
        risk = 30.0 if id(x) in main_ids else abs(T - e) / 2
        out.append((t, ex, p, risk, 'base', fi, d, e))
    for a, b, c in MR.reentries(MR.CH, 1, '2R', with_exit=True):
        out.append((a, c, b, -b if b < 0 else b / 2, 'm3', None, None, None))
    for x in Z.micro_zone(per=3, g_rsi=32, detail=True):
        out.append((x[0], x[6], x[1], abs(x[5] - x[4]) / 2, 'mz', None, None, None))
    return sorted(out, key=lambda x: x[0])

def flip_of(x):
    t, ex, p, risk, kind, fi, d, e = x
    df, sp = R.prep[fi][0], R.prep[fi][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
    j = df.index.get_loc(ex); fd = -d; px = e - d * risk
    ent = px + (sp[j] if fd == 1 else 0); rk = 0.5 * risk; stop, tgt = ent - fd * rk, ent + fd * 1.5 * rk
    for v in range(j + 1, n):
        if (l[v] <= stop) if fd == 1 else (h[v] + sp[v] >= stop): return (ex, df.index[v], -rk, rk)
        if (h[v] >= tgt) if fd == 1 else (l[v] + sp[v] <= tgt): return (ex, df.index[v], 1.5 * rk, rk)
    return None

def run(start, use_flip, cap=15, maxopen=1, frm=None, to=None):
    tr = [x for x in build() if (frm is None or x[0] >= pd.Timestamp(frm)) and (to is None or x[0] < pd.Timestamp(to))]
    bal = start; low = start; open_until = []; trades = []; pend_flips = []
    events = sorted(tr, key=lambda x: x[0])
    i = 0
    queue = [(x[0], 'trade', x) for x in events]
    queue.sort(key=lambda q: q[0])
    while queue:
        t, typ, x = queue.pop(0)
        open_until = [e for e in open_until if e > t]
        if typ == 'trade':
            tt, ex, p, risk, kind = x[:5]
            if risk > cap or len(open_until) >= maxopen: continue
            open_until.append(ex); trades.append((tt, ex, p, kind))
            if use_flip and kind == 'base' and p < 0:
                f = flip_of(x)
                if f: queue.append((f[0], 'flip', f)); queue.sort(key=lambda q: q[0])
        else:
            ft, fex, fp, frk = x
            if frk > cap or len(open_until) >= maxopen: continue
            open_until.append(fex); trades.append((ft, fex, fp, 'flip'))
    s = pd.Series([p for t, e, p, k in trades], index=[e for t, e, p, k in trades]).sort_index()
    eq = start + s.cumsum()
    kinds = pd.Series([k for t, e, p, k in trades]).value_counts().to_dict()
    return dict(end=eq.iloc[-1] if len(eq) else start, low=min(start, eq.min()) if len(eq) else start, trades=len(trades),
                flips=kinds.get('flip', 0), win=100 * (s > 0).mean() if len(s) else 0, kinds=kinds)

if __name__ == '__main__':
    for label, frm, to in (('January 2026', '2026-01-01', '2026-02-01'), ('All 2026', None, None)):
        for f in (False, True):
            r = run(200, f, frm=frm, to=to)
            print(f'{label:12} $200 mode {"WITH flips" if f else "no flips  "}: $200 -> ${r["end"]:.0f}, lowest ${r["low"]:.0f}, {r["trades"]} trades ({r["flips"]} flips), win {r["win"]:.0f}%  {r["kinds"]}')
