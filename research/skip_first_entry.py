"""Skip the main strategy's first entry: the bot still watches it (a 'virtual' trade). If it would hit its stop, the
bot takes the re-entries as usual. Zone trades unchanged. Chosen strategy, full 2026, 0.01 lot."""
import sys, re
sys.path.insert(0, '.')
import research.reentry_v2 as R
from castimofx.sweep import simulate_reentry

def run(skip_first, skip_zone=False):
    tr = []
    for df, sp, r, z, groups in R.prep:
        if not skip_zone: tr += [(t, p) for t, p, d, rv in z if R.ok(d, rv)]
        for g, tp in groups:
            for x in simulate_reentry(df, g, 20, tp, 10, 5, sp, pivot=0):
                if not R.ok(x.signal.direction, r[x.time]): continue
                m = re.search(r're-entry (\d+)', x.reason); k = int(m.group(1)) if m else 0
                if skip_first and k == 0: continue
                tr.append((x.time, x.pnl))
    return sorted(tr)

if __name__ == '__main__':
    print(f'{"":30}| Jan-Jun                              | Jul-Nov                              | YEAR')
    print(f'{"current":30}| {R.st(run(False))}')
    print(f'{"skip main first entry":30}| {R.st(run(True))}')
    print(f'{"main only, current":30}| {R.st(run(False, True))}')
    print(f'{"main only, skip first entry":30}| {R.st(run(True, True))}')
