"""Same versions on 2025 (Feb-Jul, January = warm-up), one continuous M1 file, real fills, 0.01.
Build the file: research/full_2025.py makes data/XAUUSDb_M1_2025-01_2025-08.csv from the two 2025 files, then
CASTIMO_FILES=data/XAUUSDb_M1_2025-01_2025-08.csv CASTIMO_FILL=market python research/full_2025.py"""
import sys, os
sys.path.insert(0, '.')
import pandas as pd
OUT = 'data/XAUUSDb_M1_2025-01_2025-08.csv'
if not os.path.exists(OUT):
    D = pd.concat([pd.read_csv(f, sep='\t', dtype=str) for f in ('data/XAUUSDb_M1_2025-01_2025-04.csv', 'data/XAUUSDb_M1_2025-04_2025-08.csv')])
    D.drop_duplicates(['<DATE>', '<TIME>'], keep='last').sort_values(['<DATE>', '<TIME>']).to_csv(OUT, sep='\t', index=False)
if __name__ == '__main__' and os.environ.get('CASTIMO_FILES') == OUT:
    import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F
    from research.daily_green import daily
    MZ = Z.micro_zone(per=3, g_rsi=32); cols, monthly = {}, {}
    for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB), ('+Both no F-E', MR.CH + MR.DB)):
        T = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
        T = [x for x in T if pd.Timestamp('2025-02-01') <= pd.Timestamp(x[0]) < pd.Timestamp('2025-08-01')]
        r = F.report(T); dly = daily(T, start='2025-02-03', end='2025-07-31')
        cols[name] = {'Profit': r['Profit'], 'PF': r['PF'], 'Green days': dly['Green days'], 'Worst day': dly['Worst day'],
                      'Min bal': r['Min bal'], 'Safe bal': r['Safe bal']}
        s = pd.Series([p for t, p in T], index=pd.to_datetime([t for t, p in T])); monthly[name] = s.groupby(s.index.to_period('M')).sum().round(0)
    print(pd.DataFrame(cols).to_string()); print(pd.DataFrame(monthly).to_string())
