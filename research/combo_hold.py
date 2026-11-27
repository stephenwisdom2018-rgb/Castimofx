"""Chosen version + both on-hold ideas at once: F-E zone (40 per structure, 20 days, 1 re-entry) and double bottom $2
above E (one per setup). All filters, stacking kept in the main/zone parts, 0.01."""
import sys
sys.path.insert(0, '.')
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.client_report as C, research.strong_base as S
from research.zone_multi import zone

RE = dict(swings='3', target='2R', max=1)
BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
FE = []
for fi, (df, sp, *_) in enumerate(R.prep):
    FE += [(x[0], x[1]) for x in zone(df, sp, 40, 20, main=False, reent=RE, region='FE')[0] if M.keep(fi, x[0], x[4])]
DB, seen = [], set()
for t, p in sorted(S.double_bottom(2)):
    if t not in seen: seen.add(t); DB.append((t, p))
if __name__ == '__main__':
    C.report('Chosen', BASE)
    C.report('Chosen + F-E zone', BASE + FE)
    C.report('Chosen + double bottom', BASE + DB)
    C.report('Chosen + F-E zone + double bottom', BASE + FE + DB)
