"""Full report on 2025 and 2026 for the current chosen version and the 'Robust' combination."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.both_eval as E, research.full_report as F

VERS = {'Chosen': ['main', 'ea40', 'fe', 'mz', 're3_main', 're3_ea40', 're3_fe'],
        'Robust': ['main', 'ea40', 'mz', 'db', 're3_mz', 're3_db']}
cols = {}
for y in ('2025', '2026'):
    for name, parts in VERS.items():
        s = pd.concat([E.filt(E.D[y][p]) for p in parts]).sort_values('time')
        cols[f'{name} {y[2:]}'] = F.report(list(zip(s.time, s.pnl)))
T = pd.DataFrame(cols)[['Chosen 25', 'Robust 25', 'Chosen 26', 'Robust 26']]
print(T.drop(['Jan-Jun', 'Jul-Nov']).to_string())
T.to_csv('research/both_report.csv')
