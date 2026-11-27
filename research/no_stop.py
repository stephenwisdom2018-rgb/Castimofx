"""Owner: what if trades have NO stop loss? Each trade stays open until its target is hit (or the data ends, then it is
closed at the last price). Main: first entries only (no stop = no re-entries). Floating losses are measured at each
day's end (sum of open trades). Chosen vs chosen + both on-hold ideas, 0.01."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.strong_base as S
from research.zone_multi import zone

RE = dict(swings='3', target='2R', max=1)
D = [(df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy(), df.index, sp) for df, sp, *_ in R.prep]

def zone_trades(region='EA'):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        for x in zone(df, sp, 40, 20, main=False, reent=RE, region=region)[0]:
            if M.keep(fi, x[0], x[4]):
                tgt = x[1] if x[1] > 0 else 2 * -x[1]
                out.append((fi, df.index.get_loc(x[0]), x[4], x[13], tgt))
    return out

def main_trades():
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        o = df.open.to_numpy()
        for s in P.M2.SIGS[fi]:
            if not s.with_boss: continue
            size = abs(s.f - s.g); tp = max(5, int(size)) if size < 20 else 20
            t = s.bar; d = s.direction
            if not M.keep(fi, df.index[t], d): continue
            e = (max(o[t], s.entry) + sp[t]) if d == 1 else min(o[t], s.entry)
            out.append((fi, t, d, e, tp))
    return out

def run(trades):
    res, marks = [], {}
    for fi, i, d, e, tgt in trades:
        h, l, c, idx, sp = D[fi]; T = e + d * tgt
        hit = np.nonzero(h[i+1:] >= T)[0] if d == 1 else np.nonzero(l[i+1:] + sp[i+1:] <= T)[0]
        j = i + 1 + hit[0] if len(hit) else len(h) - 1
        pnl = tgt if len(hit) else (c[j] - e) * d
        mae = (e - l[i:j+1].min()) if d == 1 else (h[i:j+1].max() - e)
        res.append((idx[i], pnl, bool(len(hit)), mae, (idx[j] - idx[i]).total_seconds() / 86400))
        days = pd.Series(c[i:j], index=idx[i:j]).groupby(idx[i:j].date).last()       # open at each day's end
        for dd, px in days.items(): marks[dd] = marks.get(dd, 0) + (px - e) * d
    R_ = pd.DataFrame(res, columns=['time', 'pnl', 'hit', 'mae', 'days'])
    closed = R_.groupby(R_.time.dt.date).pnl.sum()          # booked at entry day for simplicity
    float_ = pd.Series(marks).sort_index()
    real = R_[R_.hit]; dates = sorted(set(float_.index) | set(closed.index))
    eq = np.cumsum([0])
    return R_, float_

if __name__ == '__main__':
    base = zone_trades() + main_trades()
    both = base + zone_trades('FE') + [(x[2], x[3], x[4], x[5], x[6]) for x in S.double_bottom(2, detail=True)]
    for name, tr in (('Chosen, no stop', base), ('+Both, no stop', both)):
        R_, fl = run(tr)
        stuck = R_[~R_.hit]
        print(f'\n{name}: {len(R_)} trades | hit target {R_.hit.mean()*100:.0f}% | still open at data end {len(stuck)} (closed there: ${stuck.pnl.sum():.0f})')
        print(f'  total ${R_.pnl.sum():.0f} | worst single trade went ${R_.mae.max():.0f} against | trades that went $50+ against: {(R_.mae>=50).sum()}, $100+: {(R_.mae>=100).sum()}')
        print(f'  avg hold {R_.days.mean():.1f} days, longest {R_.days.max():.0f} days | worst floating loss of open trades at a day end: ${fl.min():.0f}')
