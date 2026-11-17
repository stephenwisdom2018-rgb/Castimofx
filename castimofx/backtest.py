"""Bar-by-bar backtester with risk-based position sizing.

Fill assumptions (deliberately conservative):
* Orders placed after bar t closes can first fill on bar t+1.
* A limit buy fills at the entry price, or at the open if the bar gaps below it.
* If the stop and the target are both inside one bar, the stop is assumed hit first.
* On the bar an order fills, only the stop is checked (the target is checked from the next bar).
* Spread is charged once per trade as a cost of `spread_pips`.
* Several positions may be open at once (`StrategyConfig.max_positions`).
* P&L is in the quote currency (USD for EURUSD, GBPUSD, XAUUSD, ...).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .smc import BULLISH, SMCAnalyzer
from .strategy import Order, SMCStrategy, StrategyConfig


@dataclass
class BacktestConfig:
    initial_balance: float = 10_000.0
    risk_pct: float = 1.0
    spread_pips: float = 1.0


@dataclass
class Trade:
    direction: int
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    stop: float
    target: float
    units: float
    pnl: float
    r_multiple: float
    reason: str  # "target", "stop", "end"

    @property
    def side(self) -> str:
        return "BUY" if self.direction == BULLISH else "SELL"


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity: pd.Series
    config: BacktestConfig
    analyzer: SMCAnalyzer = field(repr=False)

    def stats(self) -> dict:
        trades = self.trades
        start = self.config.initial_balance
        end = float(self.equity.iloc[-1]) if len(self.equity) else start
        pnls = np.array([t.pnl for t in trades])
        wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
        peak = self.equity.cummax()
        max_dd = float(((self.equity - peak) / peak).min() * 100) if len(self.equity) else 0.0
        return {
            "trades": len(trades),
            "win_rate_pct": round(100 * len(wins) / len(trades), 1) if trades else 0.0,
            "net_profit": round(end - start, 2),
            "return_pct": round(100 * (end - start) / start, 2),
            "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() < 0 else float("inf") if len(wins) else 0.0,
            "avg_r": round(float(np.mean([t.r_multiple for t in trades])), 2) if trades else 0.0,
            "max_drawdown_pct": round(max_dd, 2),
            "final_balance": round(end, 2),
            "trades_per_day": round(len(trades) / max(1, self.equity.index.normalize().nunique()), 2),
        }


def wilder_atr(df: pd.DataFrame, length: int = 14) -> np.ndarray:
    """ATR as used by TradingView's ta.atr and the MT5 EA (SMA seed, then Wilder smoothing)."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    prev_c = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    tr[0] = h[0] - l[0]
    atr = np.empty_like(tr)
    running = 0.0
    for t, x in enumerate(tr):
        if t < length:
            running += x
            atr[t] = running / (t + 1)
        else:
            atr[t] = (atr[t - 1] * (length - 1) + x) / length
    return atr


def htf_trend(df: pd.DataFrame, factor: int, swing_length: int) -> np.ndarray:
    """Structure trend of a higher timeframe (factor x the chart timeframe), known at each chart bar's close."""
    step = df.index.to_series().diff().median()
    htf_step = step * factor
    htf = df.resample(htf_step).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    a = SMCAnalyzer(htf, swing_length=swing_length)
    trend = np.empty(len(htf), int)
    for i in range(len(htf)):
        a.update(i)
        trend[i] = a.trend
    htf_close = htf.index + htf_step
    ltf_close = df.index + step
    idx = np.searchsorted(htf_close.values, ltf_close.values, side="right") - 1
    return np.where(idx >= 0, trend[np.clip(idx, 0, None)], 0)


def run_backtest(
    df: pd.DataFrame,
    strategy_config: StrategyConfig | None = None,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    scfg = strategy_config or StrategyConfig()
    cfg = config or BacktestConfig()
    strategy = SMCStrategy(scfg)
    analyzer = SMCAnalyzer(df, swing_length=scfg.swing_length)

    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = wilder_atr(df)
    bias = htf_trend(df, scfg.htf_factor, scfg.swing_length) if scfg.htf_factor > 1 else None
    hours = df.index.hour
    sess = scfg.session_hours

    def in_session(t: int) -> bool:
        if sess is None:
            return True
        a, b = sess
        return a <= hours[t] < b if a <= b else (hours[t] >= a or hours[t] < b)
    times = df.index
    spread = cfg.spread_pips * scfg.pip_size

    balance = cfg.initial_balance
    equity = np.empty(len(df))
    pending: list[Order] = []
    positions: list[dict] = []
    trades: list[Trade] = []

    def close(p: dict, t: int, price: float, reason: str) -> None:
        nonlocal balance
        pnl = p["units"] * (price - p["entry"]) * p["dir"] - p["units"] * spread
        balance += pnl
        trades.append(Trade(p["dir"], times[p["t"]], times[t], p["entry"], price, p["stop"], p["target"],
                            p["units"], pnl, pnl / p["risk_cash"], reason))

    for t in range(len(df)):
        # 1) manage open positions (stop first if both are inside the bar)
        for p in list(positions):
            d, stop, target = p["dir"], p["stop"], p["target"]
            exit_px = reason = None
            if d == BULLISH:
                if o[t] <= stop:
                    exit_px, reason = o[t], "stop"
                elif l[t] <= stop:
                    exit_px, reason = stop, "stop"
                elif h[t] >= target:
                    exit_px, reason = max(o[t], target), "target"
            else:
                if o[t] >= stop:
                    exit_px, reason = o[t], "stop"
                elif h[t] >= stop:
                    exit_px, reason = stop, "stop"
                elif l[t] <= target:
                    exit_px, reason = min(o[t], target), "target"
            if reason:
                close(p, t, exit_px, reason)
                positions.remove(p)

        # 2) fill pending limit orders, newest first, up to max_positions
        for order in sorted(pending, key=lambda x: -x.placed_at):
            if not in_session(t):
                break
            if len(positions) >= scfg.max_positions:
                break
            d = order.direction
            market = np.isnan(order.entry)
            touched = market or (l[t] <= order.entry if d == BULLISH else h[t] >= order.entry)
            if not touched:
                continue
            pending.remove(order)
            if market:
                fill = o[t]
            else:
                fill = min(o[t], order.entry) if d == BULLISH else max(o[t], order.entry)
            if (d == BULLISH and fill <= order.stop) or (d != BULLISH and fill >= order.stop):
                continue  # gapped through the whole zone
            target = fill + d * scfg.rr * abs(fill - order.stop) if market else order.target
            risk_cash = balance * cfg.risk_pct / 100
            p = {"dir": d, "entry": fill, "stop": order.stop, "target": target,
                 "units": risk_cash / abs(fill - order.stop), "risk_cash": risk_cash, "t": t}
            if (l[t] <= order.stop) if d == BULLISH else (h[t] >= order.stop):
                close(p, t, order.stop, "stop")  # stopped inside the fill bar
            else:
                positions.append(p)

        # 3) update structure with the closed bar, then manage orders
        new_obs = analyzer.update(t)
        pending = [x for x in pending if not strategy.should_cancel(x, analyzer, t)
                   and (bias is None or bias[t] == x.direction)]
        new_orders = strategy.orders_for(new_obs, analyzer, t, atr[t])
        if bias is not None:
            new_orders = [x for x in new_orders if bias[t] == x.direction]
        pending += new_orders

        mark = sum(p["units"] * (c[t] - p["entry"]) * p["dir"] for p in positions)
        equity[t] = balance + mark

    for p in positions:
        close(p, len(df) - 1, c[-1], "end")
    if len(df):
        equity[-1] = balance

    return BacktestResult(trades, pd.Series(equity, index=times, name="equity"), cfg, analyzer)
