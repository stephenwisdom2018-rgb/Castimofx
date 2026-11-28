"""Step 2 of the gross/net fix: the chosen version with REAL fills only. Zone entries whose bar opened past the level
are bought at that open (EA v1.14: same stop/target levels, skipped if more than 0.5x risk away) instead of at the
level. Run: CASTIMO_FILL=market python research/real_fills.py (or touch = old backtest). Chosen and +Both
(+ double bottom $2), 0.01."""
import sys, os
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_zone as Z, research.micro3_reentry as MR, research.full_report as F

MZ = Z.micro_zone(per=3, g_rsi=32)
cols = {}
for name, tr in (('Chosen', MR.CH + MR.FE), ('+Both', MR.CH + MR.FE + MR.DB)):
    T = [(x[0], x[1]) for x in tr] + MR.reentries(tr, 1, '2R') + MZ
    T = [x for x in T if pd.Timestamp(x[0]).year == 2026]
    cols[f'{name} ({os.environ.get("CASTIMO_FILL", "touch")})'] = F.report(T)
print(pd.DataFrame(cols).to_string())
