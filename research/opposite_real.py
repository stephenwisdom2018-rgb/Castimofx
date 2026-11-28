"""ON HOLD #3 re-test: close-on-opposite exit on the TRUE data (one continuous file, real fills), 0.01.
A trade has no normal stop: it closes at its target, when the bot opens a trade the other way, or at a safety stop
($100 / $50 / none). Chosen = main + E-A zone; +Both adds F-E zone + double bottom (as in research/opposite_exit.py).
Arg: 2026 or 2025. Use CASTIMO_SKIP_HOURS=8-13 for the quality version."""
import sys, os
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.no_stop as N, research.strong_base as S, research.opposite_exit as O
Y = sys.argv[1]
S0, E0 = ('2026-01-01', '2026-11-26') if Y == '2026' else ('2025-02-01', '2025-08-01')
base = N.zone_trades() + N.main_trades()
both = base + N.zone_trades('FE') + [(x[2], x[3], x[4], x[5], x[6]) for x in S.double_bottom(2, detail=True)]
cols = {}
for name, tr in (('Chosen', base), ('+Both', both)):
    for hard in (None, 100, 50):
        R_, fl = O.run(tr, hard)
        R_ = R_[(R_.time >= S0) & (R_.time < E0)]; fl = fl[(pd.to_datetime(fl.index) >= S0) & (pd.to_datetime(fl.index) < E0)]
        s = R_.set_index('time').pnl.sort_index(); eq = s.cumsum().to_numpy(); mb = -(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
        d = s.groupby(s.index.normalize()).sum()
        mbf = max(mb, -fl.min()) if len(fl) else mb
        cols[f'{name} {"no stop" if not hard else f"${hard}"}'] = {'Profit': f'${s.sum():,.0f}', 'Win': f'{100*(s>0).mean():.0f}%',
            'Worst day': f'${d.min():.0f}', 'Worst open': f'${fl.min():.0f}', 'Min bal': f'${mbf:,.0f}', 'Safe bal': f'${1.5*mbf:,.0f}'}
print(Y, 'skip', os.environ.get('CASTIMO_SKIP_HOURS', 'none')); print(pd.DataFrame(cols).to_string())
