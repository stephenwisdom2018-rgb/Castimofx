"""Owner: find the traits of the most profitable trades so the bot takes only QUALITY trades.
Step 1 (this file): every Chosen / +Both trade with traits the bot can see LIVE at entry, saved to CSV per data file.
  CASTIMO_FILES=<file> CASTIMO_FILL=market python research/quality.py <out.csv>
Traits: type, side, hour, weekday, risk $, RSI(14) M1, ADX M15, last-hour range ratio, H4 / D1 trend (close vs EMA
on the bar before), move in the last 4 h / 24 h in our direction, yesterday's range, trades already taken today."""
import sys
sys.path.insert(0, '.')
import numpy as np, pandas as pd
import research.day_rules as D, research.more_trades as M

df = D.df; c = df.close; F = M.FEAT[0]
def trend(rule, n):
    x = c.resample(rule).last().dropna(); e = x.ewm(span=n).mean()
    return ((x - e) / e * 100).shift(1).reindex(df.index, method='ffill')
H4, D1 = trend('4h', 50), trend('1D', 20)
mom4, mom24 = (c - c.shift(240)).shift(1), (c - c.shift(1440)).shift(1)
dr = (df.high.resample('1D').max() - df.low.resample('1D').min()).dropna().shift(1).reindex(df.index.normalize()).to_numpy()
ydr = pd.Series(dr, index=df.index)

if __name__ == '__main__':
    rows = []
    for v, X in D.VERS.items():
        for e, ex, p, d, tag in X:
            if v == '+Both' and tag != 'DB': continue          # +Both = Chosen rows + DB rows
            risk = -p if p < 0 else (p / 2 if tag != 'M' else 30.0)
            rows.append(dict(t=e, exit=ex, pnl=p, d=d, tag=tag, ver='both' if tag == 'DB' else 'chosen', hour=e.hour, wd=e.dayofweek,
                             risk=risk if tag != 'M' else 30.0, rsi=F.rsi.at[e], adx=F.adx.at[e], rng=F.rng60.at[e],
                             h4=H4.at[e] * d, d1=D1.at[e] * d, m4=mom4.at[e] * d, m24=mom24.at[e] * d, ydr=ydr.at[e]))
    T = pd.DataFrame(rows).sort_values('t')
    T['n_today'] = T.groupby([T.t.dt.date]).cumcount()
    T.to_csv(sys.argv[1], index=False); print(len(T), T.pnl.sum().round(0))
