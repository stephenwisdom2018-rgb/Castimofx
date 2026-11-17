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
   Buffer and allowed stop size are measured in ATR(14), so the same settings
   work on EURUSD, JPY pairs and gold.
6. Cancel the pending order if structure flips, the zone breaks, or it expires.
"""

from __future__ import annotations

from dataclasses import dataclass

from .smc import BULLISH, OrderBlock, SMCAnalyzer


@dataclass
class StrategyConfig:
    swing_length: int = 5
    rr: float = 2.0
    pip_size: float = 0.0001  # used for the spread
    require_discount: bool = True  # premium/discount filter
    choch_only: bool = False  # only trade zones created by a CHoCH (reversal entries)
    sl_buffer_atr: float = 0.1
    min_stop_atr: float = 0.3
    max_stop_atr: float = 4.0
    order_expiry_bars: int = 96
    max_positions: int = 1  # trades open at the same time
    entry_mode: str = "edge"  # "edge" = near edge of the zone, "mid" = 50% of the zone,
    #                           "market" = enter at the next open right after the break (confirmation entry)
    require_sweep: bool = False  # the breaking leg must have swept the previous swing (liquidity grab)
    session_hours: tuple[int, int] | None = None  # (start, end) hour in data time; orders placed/filled only inside
    htf_factor: int = 0  # >1: only trade with the trend of a timeframe this many times higher (e.g. 4 on M15 = H1)


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

    def orders_for(self, new_obs: list[OrderBlock], analyzer: SMCAnalyzer, t: int, atr: float) -> list[Order]:
        cfg = self.cfg
        orders = []
        last_event = analyzer.events[-1] if analyzer.events else None
        for ob in new_obs:
            if cfg.choch_only and (last_event is None or last_event.kind != "CHoCH"):
                continue
            if cfg.require_discount and cfg.entry_mode != "market" and not ob.in_optimal_zone:
                continue
            if cfg.require_sweep and not self._swept(ob, analyzer):
                continue
            buffer = cfg.sl_buffer_atr * atr
            mid = (ob.top + ob.bottom) / 2
            if ob.direction == BULLISH:
                entry, stop = (mid if cfg.entry_mode == "mid" else ob.top), ob.bottom - buffer
                risk = entry - stop
                target = entry + cfg.rr * risk
            else:
                entry, stop = (mid if cfg.entry_mode == "mid" else ob.bottom), ob.top + buffer
                risk = stop - entry
                target = entry - cfg.rr * risk
            if cfg.entry_mode == "market":
                close = float(analyzer.c[t])
                risk = abs(close - stop)
                if (ob.direction == BULLISH and close <= stop) or (ob.direction != BULLISH and close >= stop):
                    continue
                entry, target = float("nan"), float("nan")  # filled at next open; target set from the fill
            if not (cfg.min_stop_atr * atr <= risk <= cfg.max_stop_atr * atr):
                continue
            expiry = t + 1 if cfg.entry_mode == "market" else t + cfg.order_expiry_bars  # market: next bar only
            orders.append(Order(ob.direction, entry, stop, target, t, expiry, ob))
        return orders

    @staticmethod
    def _swept(ob: OrderBlock, analyzer: SMCAnalyzer) -> bool:
        """Did the leg that broke structure first run the stops beyond the previous swing?"""
        kind = "low" if ob.direction == BULLISH else "high"
        extreme = ob.range_low if ob.direction == BULLISH else ob.range_high
        prior = [s for s in analyzer.swings if s.kind == kind and s.index < ob.index]
        if not prior:
            return False
        level = prior[-1].price
        return extreme < level if ob.direction == BULLISH else extreme > level

    def should_cancel(self, order: Order, analyzer: SMCAnalyzer, t: int) -> bool:
        return (
            t >= order.expires_at
            or analyzer.trend != order.direction
            or order.ob.invalidated_at is not None
        )
