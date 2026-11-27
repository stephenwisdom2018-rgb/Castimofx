"""Owner's '3 micro inside SMA 10' re-entry after a stop. After a losing trade closes, within 24 h: 3 rising candles in
a row (each bullish and closing higher, all closes above SMA 10; mirror for sells). Enter at the 3rd candle's close.
Stop $1 beyond the extreme since the stop (min $5). Target = the losing trade's target (or 2x risk). If the re-entry
is stopped too, repeat (up to max). Filters apply at entry. Chosen and +Both, 0.01."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.strong_base as S
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
CH, EX, FE, DB, EAZ, MAIN = [], [], [], [], [], []   # (entry time, pnl, file, d, entry, target price, exit time)
for fi, (df, sp, *_) in enumerate(R.prep):
    for region, lst in (('EA', EAZ), ('FE', FE)):
        for x in zone(df, sp, 40, 20, main=False, reent=RE, region=region)[0]:
            if M.keep(fi, x[0], x[4]):
                dist = x[1] if x[1] > 0 else -2 * x[1]
                lst.append((x[0], x[1], fi, x[4], x[13], x[13] + x[4] * dist, x[2]))
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0):
            d = x.signal.direction
            if not M.keep(fi, x.time, d): continue
            T = x.signal.entry + d * (tp + (15 if 're-entry' in x.reason else 0))
            MAIN.append((x.time, x.pnl, fi, d, x.entry, T, x.exit_time))
seen = set()
for x in sorted(S.double_bottom(2, detail=True)):
    if x[0] not in seen: seen.add(x[0]); DB.append((x[0], x[1], x[2], x[4], x[5], x[5] + x[4] * x[6], x[7]))
EX = FE + DB
CH = EAZ + MAIN

ARR = []
for df, sp, *_ in R.prep:
    o, h, l, c = (df[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
    ma = df.close.rolling(10).mean().to_numpy()
    up = np.zeros(len(c), bool); dn = np.zeros(len(c), bool)
    for k in range(3, len(c)):
        a, b, e = k - 2, k - 1, k
        up[k] = c[a] > o[a] and c[b] > o[b] and c[e] > o[e] and c[b] > c[a] and c[e] > c[b] and min(c[a], c[b], c[e]) > max(ma[a], ma[b], ma[e])
        dn[k] = c[a] < o[a] and c[b] < o[b] and c[e] < o[e] and c[b] < c[a] and c[e] < c[b] and max(c[a], c[b], c[e]) < min(ma[a], ma[b], ma[e])
    ARR.append((o, h, l, c, sp, df.index, up, dn))

def reentries(trades, max_n, tgt_mode, hours=24):
    out = []
    for t, p, fi, d, e, T, ex in trades:
        if p >= 0: continue
        o, h, l, c, sp, idx, up, dn = ARR[fi]; n = len(c)
        j = idx.get_loc(ex); k = 0
        while k < max_n:
            sig = up if d == 1 else dn
            u = next((v for v in range(j + 1, min(n, j + hours * 60)) if sig[v]), None)
            if u is None or not M.keep(fi, idx[u], d): break
            ent = c[u] + (sp[u] if d == 1 else 0)
            ext = l[j:u + 1].min() if d == 1 else h[j:u + 1].max()
            risk = max(abs(ent - ext) + 1, 5); stop = ent - d * risk
            tgt = T if tgt_mode == 'orig' else ent + d * (2 if tgt_mode == '2R' else float(tgt_mode)) * risk
            if (tgt - ent) * d <= 0: break
            res = None
            for v in range(u + 1, n):
                if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): res = -risk; break
                if (h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt): res = abs(tgt - ent); break
            if res is None: break
            out.append((idx[u], res)); k += 1
            if res > 0: break
            j = v
    return out

def stats(tr):
    s = pd.Series([x[1] for x in tr], index=[x[0] for x in tr]).sort_index(); eq = s.cumsum().to_numpy()
    dd = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return dict(profit=s.sum(), H1=s[s.index < '2026-07-01'].sum(), H2=s[s.index >= '2026-07-01'].sum(),
                win=100 * (s > 0).mean(), pf=s[s > 0].sum() / -s[s < 0].sum(), minbal=dd, tpd=len(s) / 218)

if __name__ == '__main__':
    rows = {}
    for ver, tr in (('Chosen', CH), ('+Both', CH + EX)):
        base = [(x[0], x[1]) for x in tr]
        rows[ver] = stats(base)
        for mx in (1, 2, 3):
            for tm in ('orig', '2R'):
                ex = reentries(tr, mx, tm)
                r = stats(base + ex); r['extra'] = len(ex); r['extra$'] = sum(p for _, p in ex); r['extra win'] = 100 * np.mean([p > 0 for _, p in ex])
                rows[f'{ver} +3micro x{mx} {tm}'] = r
    print(pd.DataFrame(rows).T.round(1).to_string())
