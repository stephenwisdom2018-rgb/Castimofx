"""EA test (v1.13, Jan 2026) showed many zone triggers with no real order: when the swing high H is confirmed,
price is often ALREADY above H, so a buy-stop cannot be placed (the EA skips). The Python backtest still fills
those at H (a price that is no longer there). This checks how many chosen-version zone trades are like that and
what they are worth: (a) as backtested, (b) skipped (EA today), (c) entered at market (the bar's open)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M
from research.zone_multi import zone

RE = dict(swings='3', target='2R', max=1)
rows = []
for fi, (df, sp, *_) in enumerate(R.prep):
    o, h, l = df.open.to_numpy(), df.high.to_numpy(), df.low.to_numpy(); n = len(df)
    for region in ('EA', 'FE'):
        for x in zone(df, sp, 40, 20, main=False, reent=RE, region=region)[0]:
            if not M.keep(fi, x[0], x[4]): continue
            d, u, entry = x[4], x[12], x[13]
            if x[6] == -1:          # zone re-entry: entry bar index is the entry time
                u = df.index.get_loc(x[0])
            lvl = entry - (sp[u] if d == 1 else 0)
            gap = (o[u] > lvl) if d == 1 else (o[u] < lvl)
            pnl = x[1]; mkt = pnl
            if gap:
                risk_px = abs(pnl) if pnl < 0 else None
                stop = entry - d * (abs(x[1]) if x[1] < 0 else x[1] / 2)   # stop/target levels kept as placed
                tgt = entry + d * (x[1] if x[1] > 0 else 2 * abs(x[1]))
                e2 = o[u] + (sp[u] if d == 1 else 0)
                mkt = None
                for v in range(u, n):
                    if (l[v] <= stop) if d == 1 else (h[v] + sp[v] >= stop): mkt = d * (stop - e2); break
                    if (h[v] >= tgt) if d == 1 else (l[v] + sp[v] <= tgt): mkt = d * (tgt - e2); break
                if mkt is None: mkt = 0.0
            rows.append((region, x[0], pnl, gap, mkt))
D = pd.DataFrame(rows, columns=['region', 't', 'pnl', 'gap', 'mkt'])
D = D[pd.to_datetime(D.t).dt.year == 2026]
for r, g in D.groupby('region'):
    G = g[g.gap]
    print(f'{r}: {len(g)} trades, {len(G)} already past the level ({100*len(G)/len(g):.0f}%) | '
          f'backtest ${g.pnl.sum():.0f}, those ${G.pnl.sum():.0f} | skip -> ${g[~g.gap].pnl.sum():.0f} | market -> ${g.pnl.sum()-G.pnl.sum()+G.mkt.sum():.0f}')
