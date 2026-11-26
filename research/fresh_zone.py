"""Supply/demand idea: trade the E-A zone on its FIRST touch only (fresh zone). The first visit ends when price
closes back above E, or when it rises one zone height above E. Main strategy unchanged. Full 2026, 0.01 lot."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from castimofx import load_csv
from research.zone_multi import zone, FILES

def st(tr):
    s = pd.Series([x[1] for x in tr], index=[x[0] for x in tr]).sort_index()
    out = []
    for a, b in (('2026-01-01', '2026-07-01'), ('2026-07-01', '2027-01-01')):
        q = s[(s.index >= a) & (s.index < b)]; eq = q.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]
        out.append(f'{len(q):3} tr {100*(q>0).mean():3.0f}% ${q.sum():6.0f} drop ${(eq-pk).min():5.0f}')
    eq = s.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0, eq])[1:]; m = s.groupby(s.index.month).sum()
    return ' | '.join(out) + f' | year ${s.sum():6.0f} drop ${(eq-pk).min():5.0f} losing months {(m<0).sum()}/11'

if __name__ == '__main__':
    data = [(load_csv(f), pd.read_csv(f, sep='\t')['<SPREAD>'].to_numpy(float) / 100) for f in FILES]
    print(f'{"zone rule (+ main)":40}| Jan-Jun                          | Jul-Nov                          | full year')
    for name, per, fresh in (('any touch, up to 10 (current)', 10, None), ('any touch, 1 trade', 1, None),
                             ('first touch, close above E ends it', 10, 'close above E'),
                             ('first touch, 1 zone-height above ends', 10, 'one zone-height above E'),
                             ('first touch, 1 trade', 1, 'one zone-height above E')):
        z, m = [], []
        for df, sp in data:
            a, b = zone(df, sp, per, 10, fresh); z += a; m += b
        print(f'{name:40}| {st(z + m)}')
        print(f'{"   zone alone":40}| {st(z)}')
