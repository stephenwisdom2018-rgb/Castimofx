"""Scale the main strategy's dollar settings with the market: factor f = average daily range of the last 20 days /
$110 (2026 normal), limited to 0.3-1.5, known before the trade. Main stop 30f, target 20f (small structures: their own
size if under 20f), re-entry extra 15f. Zone/MZ/F-E trades are already structure-based. Report on CASTIMO_FILES."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.reentry_v2 as R, research.more_trades as M, research.more_profit3 as P, research.micro3_reentry as MR, research.micro3_zone as Z, research.full_report as F
from castimofx.sweep import simulate_reentry

def factors(df):
    d = df.resample('1D').agg({'high': 'max', 'low': 'min'}).dropna()
    adr = (d.high - d.low).rolling(20, min_periods=5).mean().shift(1)
    return (adr / 110).clip(0.3, 1.5).reindex(df.index.normalize()).to_numpy()

def scaled_mains(ref=110, round_to=0.1):
    out = []
    for fi, (df, sp, *_) in enumerate(R.prep):
        fac = factors(df); sig = [s for s in P.M2.SIGS[fi] if s.with_boss]
        groups = {}
        for s in sig:
            f = fac[s.bar]; f = 1.0 if np.isnan(f) else round(f / round_to) * round_to
            size = abs(s.f - s.g); tp = max(5 * f, round(size, 1)) if size < 20 * f else 20 * f
            groups.setdefault((round(f, 2), round(tp, 1)), []).append(s)
        for (f, tp), g in groups.items():
            for x in simulate_reentry(df, g, 30 * f, tp, 15 * f, 5, sp, pivot=0):
                d = x.signal.direction
                if M.keep(fi, x.time, d):
                    T = x.signal.entry + d * (tp + (15 * f if 're-entry' in x.reason else 0))
                    out.append((x.time, x.pnl, fi, d, x.entry, T, x.exit_time))
    return out

if __name__ == '__main__':
    MZ = Z.micro_zone(per=3, g_rsi=32)
    SM = scaled_mains()
    def ver(main, fe, mz, re3):
        tr = MR.EAZ + main + (MR.FE if fe else [])
        return [(x[0], x[1]) for x in tr] + (MR.reentries(tr, 1, '2R') if re3 else []) + (MZ if mz else [])
    V = {'C': ver(MR.MAIN, 0, 0, 0), 'C scaled': ver(SM, 0, 0, 0), 'Full': ver(MR.MAIN, 1, 1, 1), 'Full scaled': ver(SM, 1, 1, 1)}
    T = pd.DataFrame({k: F.report(v) for k, v in V.items()})
    print(T.drop(['Jan-Jun', 'Jul-Nov']).to_string())
