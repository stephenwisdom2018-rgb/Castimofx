import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from castimofx import load_csv, SMCAnalyzer

def sim(df, spacing=2.0, count=10, tp=20.0, bounce_zone=3.0, swing=3, balance=1000.0, spread=0.25, emergency=0.5, lot_value=1.0, verbose=False):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = SMCAnalyzer(df, swing_length=swing)
    trail_top = trail_bot = None; nsw = 0
    pending = []          # (dir, price)
    positions = []        # [dir, entry]
    grid_key = None; bounce_used = set(); bounce_order = None
    closed = []; peak = balance; maxdd = 0.0; min_equity = balance; stopped_at = None
    for t in range(len(df)):
        if stopped_at is None:
            # market bounce order from previous bar
            if bounce_order is not None:
                d = bounce_order; bounce_order = None
                for p in [p for p in positions if p[0] == -d]:
                    pnl = (o[t] - p[1]) * p[0] * lot_value - spread; balance += pnl; closed.append(pnl); positions.remove(p)
                pending = [x for x in pending if x[0] == d]
                positions.append([d, o[t], t])
            # limit fills (nearest first)
            for d, px in sorted(pending, key=lambda x: abs(x[1] - o[t])):
                if (d == -1 and h[t] >= px) or (d == 1 and l[t] <= px):
                    pending.remove((d, px))
                    for p in [p for p in positions if p[0] == -d]:
                        pnl = (px - p[1]) * p[0] * lot_value - spread; balance += pnl; closed.append(pnl); positions.remove(p)
                    pending = [x for x in pending if x[0] == d]
                    positions.append([d, max(px, o[t]) if d == -1 else min(px, o[t]), t])
            # take profits (positions from earlier bars)
            for p in list(positions):
                if p[2] < t and ((p[0] == -1 and l[t] <= p[1] - tp) or (p[0] == 1 and h[t] >= p[1] + tp)):
                    balance += tp * lot_value - spread; closed.append(tp * lot_value - spread); positions.remove(p)
            # worst-case equity inside the bar
            worst = balance + sum(((h[t] if p[0] == -1 else l[t]) - p[1]) * p[0] * lot_value for p in positions)
            min_equity = min(min_equity, worst)
            if positions and worst <= emergency * balance:
                for p in positions:
                    px = h[t] if p[0] == -1 else l[t]
                    pnl = (px - p[1]) * p[0] * lot_value - spread; balance += pnl; closed.append(pnl)
                positions = []; pending = []; stopped_at = df.index[t]
        eq = balance + sum((c[t] - p[1]) * p[0] * lot_value for p in positions)
        peak = max(peak, eq); maxdd = max(maxdd, (peak - eq) / peak)
        # structure update at bar close
        a.update(t)
        if len(a.swings) > nsw:
            for s in a.swings[nsw:]:
                if s.kind == "high": trail_top = s.price
                else: trail_bot = s.price
            nsw = len(a.swings)
        if trail_top is not None: trail_top = max(trail_top, h[t])
        if trail_bot is not None: trail_bot = min(trail_bot, l[t])
        if stopped_at is not None: continue
        if a.trend == -1 and trail_top is not None: key = (-1, round(trail_top, 2))
        elif a.trend == 1 and trail_bot is not None: key = (1, round(trail_bot, 2))
        else: key = None
        if key != grid_key:
            pending = []; grid_key = key
            if key:
                d, lvl = key
                pending = [(d, lvl - d * spacing * k) for k in range(1, count + 1)
                           if (d == -1 and lvl + spacing * k > c[t]) or (d == 1 and lvl - spacing * k < c[t])]
        # bounce entry
        if grid_key and grid_key not in bounce_used:
            d, lvl = grid_key
            first = lvl - d * spacing
            if d == -1 and h[t] >= lvl - bounce_zone and h[t] < first and c[t] < o[t] and c[t] < lvl:
                bounce_order = -1; bounce_used.add(grid_key)
            if d == 1 and l[t] <= lvl + bounce_zone and l[t] > first and c[t] > o[t] and c[t] > lvl:
                bounce_order = 1; bounce_used.add(grid_key)
    final = balance + sum((c[-1] - p[1]) * p[0] * lot_value for p in positions)
    cl = np.array(closed)
    return dict(final=round(final, 2), closed_trades=len(cl), win_rate=round(100 * (cl > 0).mean(), 1) if len(cl) else 0,
                biggest_loss=round(cl.min(), 2) if len(cl) else 0, max_dd_pct=round(100 * maxdd, 1),
                lowest_equity=round(min_equity, 2), emergency_stop=str(stopped_at), open_at_end=len(positions),
                days=df.index.normalize().nunique())

if __name__ == "__main__":
    D = sys.argv[1] if len(sys.argv) > 1 else "data"
    for tf in ("15m", "5m"):
        df = load_csv(f"{D}/XAUUSD_{tf}.csv")
        print(tf, sim(df))
        # also start the test on each week, to see how often a $1000 account survives
        starts = pd.date_range(df.index[0].normalize(), df.index[-1] - pd.Timedelta(days=14), freq="7D")
        res = [sim(df[df.index >= s]) for s in starts]
        print("   runs from each weekly start:", [(str(s.date()), r["final"], r["emergency_stop"][:10]) for s, r in zip(starts, res)])
