"""Smart Money Concepts (SMC) market-structure analysis.

Detects the same things drawn on a typical SMC chart:

* Swing highs / lows (fractal pivots)
* BOS   - break of structure (trend continuation)
* CHoCH - change of character (first break against the current trend)
* Order blocks - demand (bullish) and supply (bearish) zones at the origin of
  the move that broke structure
* Equilibrium - the 50% level of the dealing range (premium above, discount below)
* Previous day / week / month highs and lows (PDH, PDL, PWH, PWL, PMH, PML)

Everything is computed bar by bar with no look-ahead: a swing is only "known"
`swing_length` bars after it forms, exactly as it would be in live trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BULLISH = 1
BEARISH = -1


@dataclass
class Swing:
    kind: str  # "high" or "low"
    index: int  # bar where the pivot formed
    price: float
    confirmed_at: int  # first bar on which the pivot is known
    broken: bool = False


@dataclass
class StructureEvent:
    kind: str  # "BOS" or "CHoCH"
    direction: int  # BULLISH or BEARISH
    index: int  # bar that closed through the level
    level: float
    swing_index: int


@dataclass
class OrderBlock:
    direction: int  # BULLISH = demand zone, BEARISH = supply zone
    top: float
    bottom: float
    index: int  # the order-block candle
    created_at: int  # bar the structure break confirmed it
    range_high: float  # dealing range at creation
    range_low: float
    mitigated_at: int | None = None
    invalidated_at: int | None = None

    @property
    def equilibrium(self) -> float:
        return (self.range_high + self.range_low) / 2

    @property
    def in_optimal_zone(self) -> bool:
        """Demand in discount (below 50%) or supply in premium (above 50%)."""
        if self.direction == BULLISH:
            return self.top <= self.equilibrium
        return self.bottom >= self.equilibrium

    @property
    def active(self) -> bool:
        return self.mitigated_at is None and self.invalidated_at is None


def find_swings(high: np.ndarray, low: np.ndarray, length: int) -> list[Swing]:
    """Fractal pivots: a high greater than the `length` bars on each side (low mirrored)."""
    swings: list[Swing] = []
    n = len(high)
    for i in range(length, n - length):
        left_h, right_h = high[i - length : i], high[i + 1 : i + length + 1]
        if high[i] > left_h.max() and high[i] >= right_h.max():
            swings.append(Swing("high", i, float(high[i]), i + length))
        left_l, right_l = low[i - length : i], low[i + 1 : i + length + 1]
        if low[i] < left_l.min() and low[i] <= right_l.min():
            swings.append(Swing("low", i, float(low[i]), i + length))
    swings.sort(key=lambda s: (s.confirmed_at, s.index))
    return swings


@dataclass
class SMCAnalyzer:
    """Incremental SMC state machine. Call `update(t)` once per bar, in order."""

    df: pd.DataFrame
    swing_length: int = 5
    ob_lookback: int = 5  # bars to search back from the leg origin for the OB candle

    trend: int = 0
    swing_high: Swing | None = None
    swing_low: Swing | None = None
    events: list[StructureEvent] = field(default_factory=list)
    order_blocks: list[OrderBlock] = field(default_factory=list)
    swings: list[Swing] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.o = self.df["open"].to_numpy(float)
        self.h = self.df["high"].to_numpy(float)
        self.l = self.df["low"].to_numpy(float)
        self.c = self.df["close"].to_numpy(float)
        self._pending = find_swings(self.h, self.l, self.swing_length)
        self._ptr = 0
        self._last_t = -1

    # ------------------------------------------------------------------ update
    def update(self, t: int) -> list[OrderBlock]:
        """Process bar `t` (after it closes). Returns order blocks created on this bar."""
        if t != self._last_t + 1:
            raise ValueError(f"update() must be called sequentially; expected {self._last_t + 1}, got {t}")
        self._last_t = t

        self._confirm_swings(t)
        self._update_order_blocks(t)

        new_obs: list[OrderBlock] = []
        sh, sl = self.swing_high, self.swing_low
        if sh is not None and not sh.broken and self.c[t] > sh.price:
            sh.broken = True
            new_obs += self._on_break(t, sh, BULLISH)
        if sl is not None and not sl.broken and self.c[t] < sl.price:
            sl.broken = True
            new_obs += self._on_break(t, sl, BEARISH)
        return new_obs

    def run(self) -> "SMCAnalyzer":
        for t in range(len(self.df)):
            self.update(t)
        return self

    # --------------------------------------------------------------- internals
    def _confirm_swings(self, t: int) -> None:
        while self._ptr < len(self._pending) and self._pending[self._ptr].confirmed_at <= t:
            s = self._pending[self._ptr]
            self._ptr += 1
            self.swings.append(s)
            if s.kind == "high":
                self.swing_high = s
            else:
                self.swing_low = s

    def _update_order_blocks(self, t: int) -> None:
        for ob in self.order_blocks:
            if not ob.active or ob.created_at >= t:
                continue
            if ob.direction == BULLISH:
                if self.c[t] < ob.bottom:
                    ob.invalidated_at = t
                elif self.l[t] <= ob.top:
                    ob.mitigated_at = t
            else:
                if self.c[t] > ob.top:
                    ob.invalidated_at = t
                elif self.h[t] >= ob.bottom:
                    ob.mitigated_at = t

    def _on_break(self, t: int, swing: Swing, direction: int) -> list[OrderBlock]:
        kind = "CHoCH" if self.trend == -direction else "BOS"
        self.trend = direction
        self.events.append(StructureEvent(kind, direction, t, swing.price, swing.index))

        # The leg that broke structure starts at the extreme between the swing and now.
        seg = slice(swing.index, t + 1)
        if direction == BULLISH:
            origin = swing.index + int(np.argmin(self.l[seg]))
            range_low, range_high = float(self.l[origin]), float(self.h[origin : t + 1].max())
        else:
            origin = swing.index + int(np.argmax(self.h[seg]))
            range_low, range_high = float(self.l[origin : t + 1].min()), float(self.h[origin])

        # Order block = last opposite-coloured candle at/just before the leg origin.
        ob_idx = origin
        for j in range(origin, max(origin - self.ob_lookback, 0) - 1, -1):
            opposite = self.c[j] < self.o[j] if direction == BULLISH else self.c[j] > self.o[j]
            if opposite:
                ob_idx = j
                break

        if direction == BULLISH:
            top, bottom = float(self.h[ob_idx]), float(self.l[ob_idx : origin + 1].min())
        else:
            top, bottom = float(self.h[ob_idx : origin + 1].max()), float(self.l[ob_idx])

        ob = OrderBlock(direction, top, bottom, ob_idx, t, range_high, range_low)
        self.order_blocks.append(ob)
        return [ob]

    # ----------------------------------------------------------------- queries
    def active_order_blocks(self, direction: int | None = None) -> list[OrderBlock]:
        return [ob for ob in self.order_blocks if ob.active and (direction is None or ob.direction == direction)]

    def dealing_range(self) -> tuple[float, float] | None:
        if self.swing_high is None or self.swing_low is None:
            return None
        return self.swing_low.price, self.swing_high.price

    def equilibrium(self) -> float | None:
        rng = self.dealing_range()
        return None if rng is None else (rng[0] + rng[1]) / 2


def _period_keys(index: pd.DatetimeIndex, period: str) -> pd.DatetimeIndex:
    if period == "D":
        return index.normalize()
    if period == "W":
        # The forex week opens Sunday ~22:00 UTC; shift so Sunday-evening bars join Monday's week.
        shifted = index + pd.Timedelta(hours=2)
        return shifted.normalize() - pd.to_timedelta(shifted.dayofweek, unit="D")
    if period == "M":
        return index.to_period("M").to_timestamp()
    raise ValueError(period)


def key_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Previous day/week/month high & low for each bar (PDH, PDL, PWH, PWL, PMH, PML)."""
    out = pd.DataFrame(index=df.index)
    for period in ("D", "W", "M"):
        keys = _period_keys(df.index, period)
        grouped = df.groupby(keys).agg(high=("high", "max"), low=("low", "min"))
        prev = grouped.shift(1)  # previous *traded* period, so Monday's PDH is Friday's high
        out[f"P{period}H"] = prev["high"].reindex(keys).to_numpy()
        out[f"P{period}L"] = prev["low"].reindex(keys).to_numpy()
    return out
