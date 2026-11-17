"""Bar-by-bar backtester with risk-based position sizing.

Fill assumptions (deliberately conservative):
* Orders placed after bar t closes can first fill on bar t+1.
* A limit buy fills at the entry price, or at the open if the bar gaps below it.
* If the stop and the target are both inside one bar, the stop is assumed hit first.
* On the bar an order fills, only the stop is checked (the target is checked from the next bar).
* Spread is charged once per trade as a cost of `spread_pips`.
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
        }


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
    times = df.index
    spread = cfg.spread_pips * scfg.pip_size

    balance = cfg.initial_balance
    equity = np.empty(len(df))
    pending: list[Order] = []
    position: dict | None = None
    trades: list[Trade] = []

    def close(t: int, price: float, reason: str) -> None:
        nonlocal balance, position
        p = position
        gross = p["units"] * (price - p["entry"]) * p["dir"]
        pnl = gross - p["units"] * spread
        balance += pnl
        trades.append(Trade(p["dir"], times[p["t"]], times[t], p["entry"], price, p["stop"], p["target"],
                            p["units"], pnl, pnl / p["risk_cash"], reason))
        position = None

    for t in range(len(df)):
        # 1) manage open position
        if position is not None:
            d, stop, target = position["dir"], position["stop"], position["target"]
            if d == BULLISH:
                if o[t] <= stop:
                    close(t, o[t], "stop")
                elif l[t] <= stop:
                    close(t, stop, "stop")
                elif h[t] >= target:
                    close(t, max(o[t], target), "target")
            else:
                if o[t] >= stop:
                    close(t, o[t], "stop")
                elif h[t] >= stop:
                    close(t, stop, "stop")
                elif l[t] <= target:
                    close(t, min(o[t], target), "target")

        # 2) fill pending orders (one position at a time; newest order first)
        if position is None:
            for order in sorted(pending, key=lambda x: -x.placed_at):
                d = order.direction
                touched = l[t] <= order.entry if d == BULLISH else h[t] >= order.entry
                if not touched:
                    continue
                fill = min(o[t], order.entry) if d == BULLISH else max(o[t], order.entry)
                stop_dist = abs(fill - order.stop)
                if (d == BULLISH and fill <= order.stop) or (d != BULLISH and fill >= order.stop):
                    pending.remove(order)  # gapped through the whole zone; skip
                    continue
                risk_cash = balance * cfg.risk_pct / 100
                units = risk_cash / stop_dist
                position = {"dir": d, "entry": fill, "stop": order.stop, "target": order.target,
                            "units": units, "risk_cash": risk_cash, "t": t}
                pending.remove(order)
                stop_hit = l[t] <= order.stop if d == BULLISH else h[t] >= order.stop
                if stop_hit:
                    close(t, order.stop, "stop")
                break

        # 3) update structure with the closed bar, then manage orders
        new_obs = analyzer.update(t)
        pending = [x for x in pending if not strategy.should_cancel(x, analyzer, t)]
        pending += strategy.orders_for(new_obs, analyzer, t)

        mark = 0.0
        if position is not None:
            mark = position["units"] * (c[t] - position["entry"]) * position["dir"]
        equity[t] = balance + mark

    if position is not None:
        close(len(df) - 1, c[-1], "end")
        equity[-1] = balance

    return BacktestResult(trades, pd.Series(equity, index=times, name="equity"), cfg, analyzer)
