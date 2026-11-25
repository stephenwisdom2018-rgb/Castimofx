"""CHoCH + OTE strategy ("CHoCH OTE SELL / BUY").

This is the setup from the TikTok video (XAUUSD M15):

1. Price breaks structure against the trend: a **CHoCH** (change of character).
2. Draw a Fibonacci retracement over the leg that broke structure, from its origin
   (the swing high for a sell) to its extreme (the lowest low after the break).
   While price keeps running, the leg keeps extending.
3. Wait for price to retrace into the **OTE zone** (optimal trade entry), the
   62%-79% retracement, and enter with a limit order at 70.5% by default.
4. Stop beyond the leg origin (100%) plus a small ATR buffer.
5. Four take-profits: TP1 = 50% (equilibrium), TP2 = 0% (the leg extreme),
   TP3 = -27% and TP4 = -62% extensions. Part of the position closes at each,
   and the stop moves to breakeven once TP1 is hit.
6. "PSY" levels are psychological round numbers (every $25 on gold).

Optional filters (to try to make it more accurate, all off by default):
sweep of the previous swing before the CHoCH, OTE zone overlapping the order block,
a PSY level inside the OTE zone, displacement (strong breaking candle), minimum leg size,
a higher-timeframe trend filter and a session filter.

The backtest is bar by bar with no look-ahead and the same conservative fills as
`backtest.py`: orders placed at a bar's close fill from the next bar, and when the stop
and a target are both inside one candle, the stop counts first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .backtest import htf_trend, wilder_atr
from .smc import BULLISH, OrderBlock, SMCAnalyzer


@dataclass
class OteConfig:
    swing_length: int = 5
    allow_bos: bool = False  # also trade BOS (continuation) breaks, not only CHoCH
    ote_entry: float = 0.705  # entry retracement (0.62-0.79 is the OTE zone)
    ote_zone: tuple[float, float] = (0.62, 0.79)
    tp_levels: tuple[float, ...] = (0.5, 0.0, -0.27, -0.62)  # retracement levels of the leg
    tp_fractions: tuple[float, ...] = (0.25, 0.25, 0.25, 0.25)  # share of the position closed at each TP
    breakeven_after_tp1: bool = True
    sl_buffer_atr: float = 0.2
    min_leg_atr: float = 1.5  # skip legs smaller than this x ATR14
    max_leg_atr: float = 15.0
    expiry_bars: int = 48  # cancel the limit order if not filled within this many bars
    # filters
    require_sweep: bool = False  # the leg origin took out the previous swing (liquidity grab)
    require_ob_overlap: bool = False  # OTE zone overlaps the order block of the break
    psych_step: float = 0.0  # >0: a round number (multiple of this) must sit inside the OTE zone (25 for gold)
    displacement_atr: float = 0.0  # >0: the breaking candle's range must be at least this x ATR
    htf_factor: int = 0  # >1: trade only with the higher-timeframe structure trend
    session_hours: tuple[int, int] | None = None  # only fill orders between these hours (data time)


@dataclass
class OteSetup:
    direction: int
    origin: float  # leg start: the protected extreme (high for a sell)
    extreme: float  # leg end, extends while price keeps running
    created_at: int
    expires_at: int
    ob: OrderBlock
    swept: bool
    displaced: bool

    def level(self, f: float) -> float:
        """Price at retracement fraction f of the leg (0 = extreme, 1 = origin)."""
        return self.extreme + f * (self.origin - self.extreme)


@dataclass
class OteTrade:
    direction: int
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    stop: float
    targets: tuple[float, ...]
    tps_hit: int
    pnl: float
    r_multiple: float
    exit_reason: str  # "stop", "breakeven", "tp4", "end"

    @property
    def side(self) -> str:
        return "BUY" if self.direction == BULLISH else "SELL"


@dataclass
class OteResult:
    trades: list[OteTrade]
    equity: pd.Series
    initial_balance: float
    setups: int = 0
    skipped: dict = field(default_factory=dict)

    def stats(self) -> dict:
        tr = self.trades
        pnls = np.array([t.pnl for t in tr])
        wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
        end = float(self.equity.iloc[-1]) if len(self.equity) else self.initial_balance
        peak = self.equity.cummax()
        dd = float(((self.equity - peak) / peak).min() * 100) if len(self.equity) else 0.0
        n = len(tr)
        return {
            "trades": n,
            "tp1_hit_pct": round(100 * sum(t.tps_hit >= 1 for t in tr) / n, 1) if n else 0.0,
            "win_rate_pct": round(100 * len(wins) / n, 1) if n else 0.0,
            "full_stop_pct": round(100 * sum(t.exit_reason == "stop" and t.tps_hit == 0 for t in tr) / n, 1) if n else 0.0,
            "net_profit": round(end - self.initial_balance, 2),
            "return_pct": round(100 * (end - self.initial_balance) / self.initial_balance, 2),
            "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() < 0 else (float("inf") if len(wins) else 0.0),
            "avg_r": round(float(np.mean([t.r_multiple for t in tr])), 3) if n else 0.0,
            "max_drawdown_pct": round(dd, 2),
            "final_balance": round(end, 2),
        }


def _swept(ob: OrderBlock, analyzer: SMCAnalyzer) -> bool:
    """For a sell: the leg high ran above the previous swing high before the CHoCH (buy mirrored)."""
    kind = "high" if ob.direction != BULLISH else "low"
    origin = ob.range_high if ob.direction != BULLISH else ob.range_low
    prior = [s for s in analyzer.swings if s.kind == kind and s.index < ob.index]
    if not prior:
        return False
    return origin > prior[-1].price if ob.direction != BULLISH else origin < prior[-1].price


def _psych_inside(lo: float, hi: float, step: float) -> bool:
    return np.floor(hi / step) * step >= lo


def _zone_problem(s: OteSetup, cfg: OteConfig, atr: float) -> str | None:
    """Checks made on the final leg, when price first reaches the entry."""
    lo, hi = sorted((s.level(cfg.ote_zone[0]), s.level(cfg.ote_zone[1])))
    if abs(s.origin - s.extreme) > cfg.max_leg_atr * atr:
        return "leg size"
    if cfg.require_ob_overlap and not (s.ob.bottom <= hi and s.ob.top >= lo):
        return "no OB overlap"
    if cfg.psych_step > 0 and not _psych_inside(lo, hi, cfg.psych_step):
        return "no PSY level"
    return None


def run_ote_backtest(
    df: pd.DataFrame,
    cfg: OteConfig | None = None,
    initial_balance: float = 1000.0,
    risk_pct: float = 1.0,
    spread: float = 0.25,  # in price units (0.25 = 25 cents on gold)
) -> OteResult:
    cfg = cfg or OteConfig()
    if abs(sum(cfg.tp_fractions) - 1) > 1e-9 or len(cfg.tp_fractions) != len(cfg.tp_levels):
        raise ValueError("tp_fractions must sum to 1 and match tp_levels")
    analyzer = SMCAnalyzer(df, swing_length=cfg.swing_length)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = wilder_atr(df)
    bias = htf_trend(df, cfg.htf_factor, cfg.swing_length) if cfg.htf_factor > 1 else None
    hours = df.index.hour
    times = df.index

    def in_session(t: int) -> bool:
        if cfg.session_hours is None:
            return True
        a, b = cfg.session_hours
        return a <= hours[t] < b if a <= b else (hours[t] >= a or hours[t] < b)

    balance = initial_balance
    equity = np.empty(len(df))
    setup: OteSetup | None = None
    pos: dict | None = None
    trades: list[OteTrade] = []
    skipped: dict[str, int] = {}
    n_setups = 0

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    def take(p: dict, frac: float, price: float) -> None:
        nonlocal balance
        units = p["units"] * frac
        pnl = units * (price - p["entry"]) * p["dir"]
        balance += pnl
        p["pnl"] += pnl
        p["left"] -= frac

    def finish(p: dict, t: int, reason: str) -> None:
        trades.append(OteTrade(p["dir"], times[p["t"]], times[t], p["entry"], p["stop0"], p["targets"],
                               p["hit"], p["pnl"], p["pnl"] / p["risk_cash"], reason))

    for t in range(len(df)):
        # 1) manage the open position
        if pos is not None and pos["t"] < t:
            d = pos["dir"]
            stop_hit = (h[t] >= pos["stop"]) if d != BULLISH else (l[t] <= pos["stop"])
            if stop_hit:
                gap = (o[t] >= pos["stop"]) if d != BULLISH else (o[t] <= pos["stop"])
                take(pos, pos["left"], o[t] if gap else pos["stop"])
                finish(pos, t, "breakeven" if pos["stop"] == pos["entry"] else "stop")
                pos = None
            else:
                while pos["hit"] < len(pos["targets"]):
                    tp = pos["targets"][pos["hit"]]
                    if not ((l[t] <= tp) if d != BULLISH else (h[t] >= tp)):
                        break
                    take(pos, cfg.tp_fractions[pos["hit"]], tp)
                    pos["hit"] += 1
                    if pos["hit"] == 1 and cfg.breakeven_after_tp1:
                        pos["stop"] = pos["entry"]
                if pos["hit"] == len(pos["targets"]):
                    finish(pos, t, "tp4")
                    pos = None

        # 2) fill the pending OTE limit order (levels from the previous close)
        if setup is not None and pos is None and in_session(t):
            d = setup.direction
            entry = setup.level(cfg.ote_entry)
            touched = (h[t] >= entry) if d != BULLISH else (l[t] <= entry)
            reason = _zone_problem(setup, cfg, atr[setup.created_at]) if touched else None
            if reason:
                skip(reason)
                setup = None
            elif touched:
                fill = max(o[t], entry) if d != BULLISH else min(o[t], entry)
                buf = cfg.sl_buffer_atr * atr[setup.created_at]
                stop = setup.origin + buf if d != BULLISH else setup.origin - buf
                targets = tuple(setup.level(f) for f in cfg.tp_levels)
                if (fill < stop) if d != BULLISH else (fill > stop):
                    risk_cash = balance * risk_pct / 100
                    units = risk_cash / abs(stop - fill)
                    balance -= units * spread
                    pos = {"dir": d, "entry": fill, "stop": stop, "stop0": stop, "targets": targets, "hit": 0,
                           "units": units, "left": 1.0, "risk_cash": risk_cash, "pnl": -units * spread, "t": t}
                    if (h[t] >= stop) if d != BULLISH else (l[t] <= stop):
                        take(pos, 1.0, stop)
                        finish(pos, t, "stop")
                        pos = None
                setup = None

        # 3) update structure, extend / cancel the setup, look for a new CHoCH
        new_obs = analyzer.update(t)
        if setup is not None:
            d = setup.direction
            if (c[t] > setup.origin) if d != BULLISH else (c[t] < setup.origin):
                setup = None  # leg origin broken: the idea is wrong
            elif t >= setup.expires_at or analyzer.trend != d:
                setup = None
            elif (l[t] < setup.extreme) if d != BULLISH else (h[t] > setup.extreme):
                setup.extreme = l[t] if d != BULLISH else h[t]

        event = analyzer.events[-1] if analyzer.events else None
        for ob in new_obs:
            if event is None or (event.kind != "CHoCH" and not cfg.allow_bos):
                continue
            n_setups += 1
            d = ob.direction
            origin = ob.range_high if d != BULLISH else ob.range_low
            extreme = ob.range_low if d != BULLISH else ob.range_high
            s = OteSetup(d, origin, extreme, t, t + cfg.expiry_bars, ob, _swept(ob, analyzer),
                         (h[t] - l[t]) >= cfg.displacement_atr * atr[t])
            if abs(origin - extreme) < cfg.min_leg_atr * atr[t]:
                skip("leg size")
            elif cfg.require_sweep and not s.swept:
                skip("no sweep")
            elif cfg.displacement_atr > 0 and not s.displaced:
                skip("no displacement")
            elif bias is not None and bias[t] != d:
                skip("HTF trend")
            else:
                setup = s  # a new CHoCH replaces an unfilled older setup

        mark = 0.0 if pos is None else pos["units"] * pos["left"] * (c[t] - pos["entry"]) * pos["dir"]
        equity[t] = balance + mark

    if pos is not None:
        take(pos, pos["left"], c[-1])
        finish(pos, len(df) - 1, "end")
        equity[-1] = balance

    return OteResult(trades, pd.Series(equity, index=times, name="equity"), initial_balance, n_setups, skipped)
