"""ON HOLD #4 re-test: Robust and Max on the TRUE data (continuous files, real fills; research/both_real2025.pkl and
both_real2026.pkl from research/both_build.py with BOTH_TAG=real<year>), with and without the quality hours (08-13).
Robust = main + E-A zone 40 + MZ + double bottom + 3m after MZ + 3m after DB, all filters.
Max = main + E-A + F-E + MZ + DB + 3m after MZ, F-E, DB, main; RSI + hours filters, NO consolidation filter.
Chosen = main + E-A + F-E + MZ + 3m after main, E-A, F-E, all filters. +Both = Chosen + DB + 3m after DB."""
import pickle
import numpy as np, pandas as pd
D = {y: pickle.load(open(f'research/both_real{y}.pkl', 'rb')) for y in ('2025', '2026')}
PER = {'2025': ('2025-02-01', '2025-08-01'), '2026': ('2026-01-01', '2026-11-26')}
VERS = {'Chosen': (['main', 'ea40', 'fe', 'mz', 're3_main', 're3_ea40', 're3_fe'], True),
        '+Both': (['main', 'ea40', 'fe', 'mz', 'db', 're3_main', 're3_ea40', 're3_fe', 're3_db'], True),
        'Robust': (['main', 'ea40', 'mz', 'db', 're3_mz', 're3_db'], True),
        'Max': (['main', 'ea40', 'fe', 'mz', 'db', 're3_mz', 're3_fe', 're3_db', 're3_main'], False)}

def run(parts, cons, quality, y):
    a, b = PER[y]; out = []
    for p in parts:
        df = D[y][p]; df = df[(df.time >= a) & (df.time < b)]
        k = df.rsi_ok.to_numpy() & ~df.hour.isin([15, 23]).to_numpy()
        if quality: k &= ~df.hour.between(8, 13).to_numpy()
        if cons: k &= ~((df.rng60 < 0.6) | ((df.adx > 25) & (df.adx <= 35))).to_numpy()
        out.append(df[k])
    s = pd.concat(out).set_index('time').pnl.sort_index(); eq = s.cumsum().to_numpy()
    mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    days = pd.bdate_range(a, pd.Timestamp(b) - pd.Timedelta(days=1)); d = s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0)
    w = d.resample('W').sum()
    return f'${s.sum():,.0f}', f'{len(s)/len(days):.0f}', f'{100*(d>0).mean():.0f}%', f'{100*(w>0).mean():.0f}%', f'${mb:,.0f}'

if __name__ == '__main__':
    for q in (False, True):
        rows = {}
        for v, (parts, cons) in VERS.items():
            r5, r6 = run(parts, cons, q, '2025'), run(parts, cons, q, '2026')
            rows[v] = {'2026 $': r6[0], '2025 $': r5[0], 'Tr/day 26': r6[1], 'Green d 26': r6[2], 'Green wk 26': r6[3], 'Green wk 25': r5[3],
                       'Min bal 26': r6[4], 'Min bal 25': r5[4]}
        print('quality hours ON' if q else 'quality hours OFF'); print(pd.DataFrame(rows).to_string())
