"""'+ both' (chosen + F-E zone + double bottom, normal stops), 0.01: losing streaks, what follows a loss, pauses after
N losses in a row (live rule: count closed trades by exit time), and whether losing trades' targets are hit later."""
import sys, re
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.strong_base as S, research.client_report as C
from research.zone_multi import zone
from castimofx.sweep import simulate_reentry

RE = dict(swings='3', target='2R', max=1)
TR = []                                                   # (entry time, exit time, pnl, file, entry, d, target dist)
for fi, (df, sp, *_) in enumerate(R.prep):
    for region in ('EA', 'FE'):
        for x in zone(df, sp, 40, 20, main=False, reent=RE, region=region)[0]:
            if M.keep(fi, x[0], x[4]): TR.append((x[0], x[2], x[1], fi, x[13], x[4], x[1] if x[1] > 0 else -2 * x[1]))
    sig = [s for s in P.M2.SIGS[fi] if s.with_boss]; size = lambda s: abs(s.f - s.g)
    tp_of = lambda s: max(5, int(size(s))) if size(s) < 20 else 20
    for tp in sorted({tp_of(s) for s in sig}):
        for x in simulate_reentry(df, [s for s in sig if tp_of(s) == tp], 30, tp, 15, 5, sp, pivot=0):
            if M.keep(fi, x.time, x.signal.direction): TR.append((x.time, x.exit_time, x.pnl, fi, x.entry, x.signal.direction, None))
seen = set()
for x in sorted(S.double_bottom(2, detail=True)):
    if x[0] in seen: continue
    seen.add(x[0]); TR.append((x[0], x[7], x[1], x[2], x[5], x[4], x[6]))
TR.sort(key=lambda x: x[0])
pnl = np.array([x[2] for x in TR])

# streaks in entry order
w = pnl > 0; streak = []; n = 0
for x in w:
    if not x: n += 1
    else:
        if n: streak.append(n)
        n = 0
print(f'{len(TR)} trades, {100*w.mean():.0f}% win, ${pnl.sum():,.0f}')
print('losing streaks (in a row): longest', max(streak), '| ' + ', '.join(f'{k}+: {sum(s >= k for s in streak)}x' for k in (2, 3, 5, 8, 10)))
for k in (1, 2, 3, 5):
    nxt = [w[i] for i in range(k, len(w)) if not w[i-k:i].any()]
    print(f'  after {k} loss(es) in a row, next trade wins {100*np.mean(nxt):.0f}% ({len(nxt)} cases)')
print(f'  after a win, next trade wins {100*np.mean([w[i] for i in range(1, len(w)) if w[i-1]]):.0f}%')

# losers: was the target hit later (within 24 h after the stop)?
later = []
for t, ex, p, fi, e, d, tgt in TR:
    if p >= 0 or tgt is None: continue
    df = R.prep[fi][0]; j = df.index.get_loc(ex); T = e + d * tgt
    seg_h, seg_l = df.high.to_numpy()[j:j+1440], df.low.to_numpy()[j:j+1440]
    later.append(bool((seg_h >= T).any() if d == 1 else (seg_l <= T).any()))
print(f'losing trades whose target WAS hit within 24 h after the stop: {100*np.mean(later):.0f}% of {len(later)}')

def pause(nloss, hours):
    out, last_exit_losses, until = [], [], None
    closed = []                                            # (exit time, pnl) of taken trades
    for t, ex, p, *_ in TR:
        # count consecutive losses among trades closed before t
        done = sorted([c for c in closed if c[0] <= t])
        k = 0
        for c in reversed(done):
            if c[1] < 0: k += 1
            else: break
        if k >= nloss and done and t < done[-1][0] + pd.Timedelta(hours=hours): continue
        out.append((t, p)); closed.append((ex, p))
    return out
print(f'\n{"rule":32}| Jan-Jun | Jul-Nov | YEAR | trades/day')
print(f'{"+ both, no pause":32}| {M.st(sorted((x[0], x[2]) for x in TR))} | {len(TR)/C.DAYS:.1f}')
for nl in (1, 2, 3):
    for hr in (1, 2, 5, 24):
        tr = pause(nl, hr)
        print(f'{f"pause {hr}h after {nl} loss(es)":32}| {M.st(sorted(tr))} | {len(tr)/C.DAYS:.1f}', flush=True)

def comeback(hours=24, same_stop=True):
    """after a stop: if price comes back up to the original entry within `hours`, buy again there (stop and target
    the same distances as before). Zone / F-E / double-bottom trades only (main already re-enters)."""
    out = []
    for t, ex, p, fi, e, d, tgt in TR:
        if p >= 0 or tgt is None: continue
        df, sp = R.prep[fi][0], R.prep[fi][1]; h, l = df.high.to_numpy(), df.low.to_numpy(); n = len(h)
        j = df.index.get_loc(ex); risk = tgt / 2
        k = next((u for u in range(j + 1, min(n, j + hours * 60)) if ((h[u] >= e) if d == 1 else (l[u] <= e))), None)
        if k is None or not M.keep(fi, df.index[k], d): continue
        ent = e + (sp[k] if d == 1 else 0); st, T = ent - d * risk, ent + d * tgt
        for v in range(k, n):
            if (l[v] <= st) if d == 1 else (h[v] + sp[v] >= st): out.append((df.index[k], -risk)); break
            if v > k and ((h[v] >= T) if d == 1 else (l[v] + sp[v] <= T)): out.append((df.index[k], tgt)); break
    return out
