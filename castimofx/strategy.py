"""SMC order-block strategy.

Rules
-----
1. Track market structure (BOS / CHoCH) on the chart timeframe.
2. When structure breaks, mark the order block at the origin of the breaking leg.
3. Only trade with the structure: demand (buy) after a bullish break,
   supply (sell) after a bearish break.
4. Optional premium/discount filter: buy only if the demand zone sits in the
   discount half of the dealing range (below equilibrium); sell only from premium.
5. Entry: limit order at the near edge of the zone (top of demand / bottom of supply).
   Stop: beyond the far edge plus a buffer. Target: fixed risk-reward multiple.
6. Cancel the pending order if structure flips, the zone breaks, or it expires.
"""

from __future__ import annotations

from dataclasses import dataclass

from .smc import BULLISH, OrderBlock, SMCAnalyzer


@dataclass
class StrategyConfig:
    swing_length: int = 5
    rr: float = 2.0
    sl_buffer_pips: float = 2.0
    pip_size: float = 0.0001
    require_discount: bool = True  # premium/discount filter
    choch_only: bool = False  # only trade zones created by a CHoCH (reversal entries)
    min_stop_pips: float = 3.0
    max_stop_pips: float = 50.0
    order_expiry_bars: int = 96


@dataclass
class Order:
    direction: int
    entry: float
    stop: float
    target: float
    placed_at: int
    expires_at: int
    ob: OrderBlock


class SMCStrategy:
    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.cfg = config or StrategyConfig()

    def orders_for(self, new_obs: list[OrderBlock], analyzer: SMCAnalyzer, t: int) -> list[Order]:
        cfg = self.cfg
        orders = []
        last_event = analyzer.events[-1] if analyzer.events else None
        for ob in new_obs:
            if cfg.choch_only and (last_event is None or last_event.kind != "CHoCH"):
                continue
            if cfg.require_discount and not ob.in_optimal_zone:
                continue
            buffer = cfg.sl_buffer_pips * cfg.pip_size
            if ob.direction == BULLISH:
                entry, stop = ob.top, ob.bottom - buffer
                risk = entry - stop
                target = entry + cfg.rr * risk
            else:
                entry, stop = ob.bottom, ob.top + buffer
                risk = stop - entry
                target = entry - cfg.rr * risk
            risk_pips = risk / cfg.pip_size
            if not (cfg.min_stop_pips <= risk_pips <= cfg.max_stop_pips):
                continue
            orders.append(Order(ob.direction, entry, stop, target, t, t + cfg.order_expiry_bars, ob))
        return orders

    def should_cancel(self, order: Order, analyzer: SMCAnalyzer, t: int) -> bool:
        return (
            t >= order.expires_at
            or analyzer.trend != order.direction
            or order.ob.invalidated_at is not None
        )
