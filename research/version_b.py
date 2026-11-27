"""Version B, cleaned: main (small-structure target) + zone (20 per structure, 20 days, 1 zone re-entry),
all filters, ONLY 1 zone trade per setup (same minute and side). Builds the trade list with details for review."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_trades2 as M2
from research.zone_multi import zone

def zone_clean(**kw):
    Z = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        Z += [x + (fi,) for x in zone(df, sp, 20, 20, main=False, reent=M2.RE1, **kw)[0] if M.keep(fi, x[0], x[4])]
    seen, out = set(), []
    for x in sorted(Z, key=lambda x: x[0]):
        if (x[0], x[4]) in seen: continue
        seen.add((x[0], x[4])); out.append(x)
    return out

ZONE = zone_clean()
MAIN = M2.main_trades()
if __name__ == '__main__':
    print('version B clean |', M.st(sorted([(x[0], x[1]) for x in ZONE] + MAIN)))
