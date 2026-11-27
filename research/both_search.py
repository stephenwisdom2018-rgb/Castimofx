"""Search combinations of parts and filters; keep those profitable in BOTH years. Rank by total profit with
2025 PF >= 1.1 and 2026 PF >= 1.4. Months: 2025 = 7, 2026 = 10."""
import itertools, sys
sys.path.insert(0, ".")
import pandas as pd
import research.both_eval as E

opt = ['fe', 'mz', 'db', 're3_mz', 're3_fe', 're3_db', 're3_ea40', 're3_main']
rows = []
for mainp in ('main', 'main_nosmall'):
    for eap in ('ea40', 'ea10'):
        for k in range(len(opt) + 1):
            for sub in itertools.combinations(opt, k):
                for rsi, hours, cons in itertools.product((True, False), repeat=3):
                    parts = [mainp, eap] + list(sub)
                    r = E.run(parts, rsi=rsi, hours=hours, cons=cons)
                    a, b = r['2025'], r['2026']
                    rows.append(dict(parts='+'.join(parts), rsi=rsi, hours=hours, cons=cons,
                                     p25=a['profit'], pf25=a['pf'], mb25=a['minbal'], p26=b['profit'], pf26=b['pf'], mb26=b['minbal'],
                                     m25=a['month'], m26=b['month'], tpd26=b['n'] / 218))
T = pd.DataFrame(rows)
T.to_csv('research/both_search.csv', index=False)
ok = T[(T.pf25 >= 1.1) & (T.pf26 >= 1.4)].copy()
ok['total'] = ok.p25 + ok.p26
pd.set_option('display.width', 250)
print('Best by total, PF25>=1.1 & PF26>=1.4:')
print(ok.sort_values('total', ascending=False).head(10).round(2).to_string(index=False))
ok2 = T[(T.pf25 >= 1.2) & (T.pf26 >= 1.5)].copy(); ok2['total'] = ok2.p25 + ok2.p26
print('\nBest by total, PF25>=1.2 & PF26>=1.5:')
print(ok2.sort_values('total', ascending=False).head(6).round(2).to_string(index=False))
