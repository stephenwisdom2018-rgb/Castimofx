"""Final check of everything for the chosen version (C+3m+MZ+FE) on 2026, plus Chosen + double bottom side by side:
full report, monthly, account modes ($100/$200/$400/$1,000), lot sizing and the prop account."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F, research.start_200 as S, research.lot_final as L

MZd = Z.micro_zone(per=3, g_rsi=32, detail=True)
def re(tr): return [(a, c, b) for a, b, c in MR.reentries(tr, 1, '2R', with_exit=True)]
CH = MR.CH + MR.FE
CHOSEN = [(x[0], x[6], x[1]) for x in CH] + re(CH) + [(x[0], x[6], x[1]) for x in MZd]
PLUSDB = CHOSEN + [(x[0], x[6], x[1]) for x in MR.DB] + re(MR.DB)
print('== Full report (2026, 0.01)')
T = pd.DataFrame({'Chosen': F.report([(t, p) for t, e, p in CHOSEN]), '+DB': F.report([(t, p) for t, e, p in PLUSDB])})
print(T.to_string())
print('== Monthly (Chosen)')
s = pd.Series([p for t, e, p in CHOSEN], index=[t for t, e, p in CHOSEN]).sort_index()
print(s.groupby(s.index.strftime('%m %b')).agg(['sum', 'size']).round(0).to_string())

def mode(tr, maxopen=99, cap=1e9, dedupe=False):
    kept, seen, op = [], set(), []
    for t, e, p in sorted(tr):
        if (-p if p < 0 else p / 2) > cap: continue
        if dedupe and t in seen: continue
        op = [x for x in op if x > t]
        if len(op) >= maxopen: continue
        kept.append((t, e, p)); seen.add(t); op.append(e)
    return kept
V = S.versions()
modes = {'$100 mode': (V['C+3m+MZ'], dict(maxopen=1, cap=15), 100), '$200 mode': (V['C+3m+MZ'], dict(maxopen=2, cap=15), 200),
         '$400 mode': (V['C'], dict(dedupe=True), 400), '$1,000 full': (V['Chosen (+FE)'], {}, 1000)}
print('== Account modes (every start day)')
for k, (tr, kw, start) in modes.items():
    m = mode(tr, **kw); r = S.risk(m, start)
    print(f'{k:12} profit ${sum(p for _, _, p in m):6,.0f} | blown {r["blown"]:.1f}% | worst dip ${r["worst"]:.0f}')
print('== Lot sizing')
for start in (1000, 2000):
    r = L.sim(start, lambda b, s: max(1, int(b // 2000)), True)
    print(f'${start:,} start, 0.01 per $2,000 + half after 3 losses: end ${r["end"]:,.0f}, worst drop {r["worst"]:.0f}%, lowest ${r["low"]:,.0f}')
r = L.sim(100000, lambda b, s: 7)
print(f'Prop $100k at 0.07: profit ${r["end"]-100000:,.0f}, worst drop {-r["worst"]:.1f}% of peak')
