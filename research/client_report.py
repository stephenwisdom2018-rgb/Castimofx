"""Client report for a trade list: trades per day, wins / losses per day, average win / loss, winning / losing /
no-trade days, bad streaks, and what a client who connects on a random day sees."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.bad_days as B, research.more_trades as M

DAYS = sum(len(set(df.index.date)) for df, *_ in R.prep)
def report(name, tr):
    s = pd.Series([p for t, p in tr], index=[t for t, p in tr]); w, l = s[s > 0], s[s < 0]
    print(f'\n=== {name} ===')
    print(f'year: {M.st(sorted(tr)).split("|")[-1].strip()}')
    print(f'trades {len(s)/DAYS:.1f}/day | wins {len(w)/DAYS:.1f}/day avg +${w.mean():.1f} | losses {len(l)/DAYS:.1f}/day avg -${-l.mean():.1f} | avg day +${s.sum()/DAYS:.1f}')
    B.report('days', tr)

if __name__ == '__main__':
    import research.more_profit3 as P, research.strong_base as S
    BASE = P.zones(40, 20) + P.mains(sl=30, extra=15)
    db, seen = [], set()
    for t, p in sorted(S.double_bottom(2)):
        if t in seen: continue
        seen.add(t); db.append((t, p))
    report('Chosen version', BASE)
    report('Chosen + double bottom $2', BASE + db)
