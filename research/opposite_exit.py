"""Owner: instead of a stop loss, close a trade when the bot opens a trade in the OTHER direction (or at the target).
Optional wide safety stop ($50 / $100). Main: first entries only. Chosen vs + both, 0.01. Floating losses marked daily."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.no_stop as N, research.strong_base as S, research.more_trades as M

def run(trades, hard=None):
    opp = {}
    for fi, i, d, e, tgt in trades: opp.setdefault((fi, d), []).append(i)
    for k in opp: opp[k] = np.array(sorted(opp[k]))
    res, marks = [], {}
    for fi, i, d, e, tgt in trades:
        h, l, c, idx, sp = N.D[fi]; n = len(h); T = e + d * tgt
        hit = np.nonzero(h[i+1:] >= T)[0] if d == 1 else np.nonzero(l[i+1:] + sp[i+1:] <= T)[0]
        jt = i + 1 + hit[0] if len(hit) else n
        o = opp.get((fi, -d), np.array([])); k = np.searchsorted(o, i, side='right'); jo = o[k] if k < len(o) else n
        js = n
        if hard:
            st = e - d * hard
            hs = np.nonzero(l[i+1:] <= st)[0] if d == 1 else np.nonzero(h[i+1:] + sp[i+1:] >= st)[0]
            js = i + 1 + hs[0] if len(hs) else n
        j = min(jt, jo, js, n - 1)
        if j == jt: pnl, why = tgt, 'target'
        elif j == js: pnl, why = -hard, 'safety stop'
        elif j == jo: pnl, why = (c[j] - e) * d - (sp[j] if d == -1 else 0), 'opposite'
        else: pnl, why = (c[j] - e) * d, 'data end'
        res.append((idx[i], pnl, why))
        days = pd.Series(c[i:j], index=idx[i:j]).groupby(idx[i:j].date).last()
        for dd, px in days.items(): marks[dd] = marks.get(dd, 0) + (px - e) * d
    R_ = pd.DataFrame(res, columns=['time', 'pnl', 'why'])
    return R_, pd.Series(marks)

if __name__ == '__main__':
    base = N.zone_trades() + N.main_trades()
    both = base + N.zone_trades('FE') + [(x[2], x[3], x[4], x[5], x[6]) for x in S.double_bottom(2, detail=True)]
    for name, tr in (('Chosen', base), ('+Both', both)):
        for hard in (None, 100, 50):
            R_, fl = run(tr, hard)
            d = R_.groupby(R_.time.dt.date).pnl.sum()
            print(f'{name}, opposite exit{"" if not hard else f" + ${hard} safety stop"}: {M.st(sorted(zip(R_.time, R_.pnl))).split("|")[-1].strip()}'
                  f' | worst day ${d.min():.0f} | worst open loss ${fl.min():.0f} | ' + ', '.join(f'{k} {v}' for k, v in R_.why.value_counts().items()), flush=True)
