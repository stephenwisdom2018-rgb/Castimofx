"""Fixes found on 6 Jun 2025, tested on both years: A) no stacked copies of zone-type trades (1 per minute and side),
B) no zone-type trade against the main strategy's latest direction (last main trade before it)."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.both_eval as E, research.full_report as F

ZONEISH = ('ea40', 'mz', 'db', 're3_mz', 're3_db', 'fe')
def build(y, parts, dedupe=False, align=False):
    P = E.D[y]
    main = E.filt(P['main']).sort_values('time') if 'main' in parts else E.filt(P['main']).sort_values('time')
    mt, md = main.time.to_numpy(), main.d.to_numpy()
    out = []
    for p in parts:
        df = E.filt(P[p])
        if p in ZONEISH:
            if dedupe: df = df.drop_duplicates(subset=['time', 'd'])
            if align:
                k = np.searchsorted(mt, df.time.to_numpy(), side='left') - 1
                last = np.where(k >= 0, md[np.clip(k, 0, None)], 0)
                df = df[(last == 0) | (last == df.d.to_numpy())]
        out.append(df)
    s = pd.concat(out).sort_values('time')
    return list(zip(s.time, s.pnl))

if __name__ == '__main__':
    VERS = {'C': ['main', 'ea40'], 'Robust': ['main', 'ea40', 'mz', 'db', 're3_mz', 're3_db']}
    for name, parts in VERS.items():
        cols = {}
        for y in ('2025', '2026'):
            for tag, kw in (('', {}), (' A', dict(dedupe=True)), (' B', dict(align=True)), (' A+B', dict(dedupe=True, align=True))):
                cols[f'{y[2:]}{tag}'] = F.report(build(y, parts, **kw))
        T = pd.DataFrame(cols)
        print(f'== {name}'); print(T.loc[['Profit', 'Win', 'PF', 'Drop', 'Min bal', 'Avg month', 'Worst day', 'Worst month', 'Losing months', 'Profit 20d']].to_string())
