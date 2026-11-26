"""Castimofx gold sweep strategy (M1, RSI 14 at 70/30).

Rules as written in the student notes (Castimofx Gold Sweep Strategy):

* Swings come from RSI 14: a high counts only once RSI reached 70 or more,
  a low only once RSI reached 30 or less, and they alternate. A high is confirmed
  when RSI next reaches 30 (and a low when RSI next reaches 70), so nothing looks ahead.
* BUY staircase: lows A < C < E and highs B < D < F (the last three of each, alternating,
  ending on the high F).
* Sweep: after F, a wick takes out E. The low that forms is G.
* H is the next confirmed high after G, I the pullback after it. Buy when a wick breaks H.
* First G: if price goes below G before H breaks, the setup resets: that low becomes
  the new G (second G). From the second G on, the liquidity is finished: buy the break
  of the most recent high even if the pullback dips below G.
* SELL is the exact mirror.
* A new entry in the opposite direction closes the open trade (new trend leads).

Not modelled yet: the "unfinished buy" kept in memory after a trend change, and the
renaming of a failed buy's points into a sell staircase (the swing engine finds that
staircase on its own when it forms).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def rsi(close: np.ndarray, length: int = 14) -> np.ndarray:
    """Wilder RSI, as MT5 and TradingView compute it."""
    d = np.diff(close, prepend=close[0])
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(close), 50.0)
    au = up[1:length + 1].mean()
    ad = dn[1:length + 1].mean()
    for t in range(length + 1, len(close)):
        au = (au * (length - 1) + up[t]) / length
        ad = (ad * (length - 1) + dn[t]) / length
        out[t] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


@dataclass
class Swing:
    kind: str  # "H" or "L"
    price: float
    index: int  # bar of the extreme
    confirmed: int  # bar on which it became known


def rsi_swings(high, low, r, hi_level=70.0, lo_level=30.0) -> list[Swing]:
    """Alternating swings: a high is the top of a leg in which RSI reached 70, confirmed
    when RSI next reaches 30; a low is the mirror. A lower low before any valid high
    replaces the previous low (and the mirror for highs)."""
    swings: list[Swing] = []
    state = None  # "up": last swing is a low, looking for a high
    ext_p, ext_i, seen = None, None, False
    for t in range(len(high)):
        if state is None:
            if r[t] >= hi_level:
                state, ext_p, ext_i, seen = "up", high[t], t, True
            elif r[t] <= lo_level:
                state, ext_p, ext_i, seen = "down", low[t], t, True
            continue
        if state == "up":
            if high[t] > ext_p:
                ext_p, ext_i = high[t], t
            if r[t] >= hi_level:
                seen = True
            if r[t] <= lo_level and seen:
                swings.append(Swing("H", ext_p, ext_i, t))
                seg = low[ext_i:t + 1]
                k = int(np.argmin(seg))
                state, ext_p, ext_i, seen = "down", seg[k], ext_i + k, True
            elif not seen and swings and swings[-1].kind == "L" and low[t] < swings[-1].price:
                swings[-1] = Swing("L", low[t], t, t)  # the low extends
                ext_p, ext_i = high[t], t
        else:
            if low[t] < ext_p:
                ext_p, ext_i = low[t], t
            if r[t] <= lo_level:
                seen = True
            if r[t] >= hi_level and seen:
                swings.append(Swing("L", ext_p, ext_i, t))
                seg = high[ext_i:t + 1]
                k = int(np.argmax(seg))
                state, ext_p, ext_i, seen = "up", seg[k], ext_i + k, True
            elif not seen and swings and swings[-1].kind == "H" and high[t] > swings[-1].price:
                swings[-1] = Swing("H", high[t], t, t)
                ext_p, ext_i = low[t], t
    return swings


@dataclass
class Signal:
    direction: int  # 1 buy, -1 sell
    bar: int  # bar the wick broke H
    entry: float  # the H level (stop-order price)
    g: float  # sweep extreme (G)
    f: float  # F level
    second_g: bool
    with_boss: bool = True  # False = taken against the boss trend (an unfinished trade)


@dataclass
class _Setup:
    d: int
    e: float | None
    f: float | None
    start: int
    g: float | None = None
    second: bool = False
    h: float | None = None
    h_conf: int = -1
    e_pending: float | None = None
    f_idx: int = -1  # bar of the F extreme
    cont: bool = False  # continuation setup inside the boss trend
    g_idx: int = -1  # bar index when G was set (i_sweep mode)


def find_signals(df: pd.DataFrame, max_setup_bars: int = 600, hi_level: float = 68.0, lo_level: float = 32.0,
                 tol: float = 0.0, continuation: bool = True,
                 left_h: list | None = None, trend_changes: list | None = None,
                 replace_on_new_trend: bool = True, minor_e: int = 0,
                 trend_g_no_sweep: bool = False, i_sweep: int = 0,
                 i_sweep_level: str = "recent") -> tuple[list[Signal], list[Swing]]:
    """Signals from the sweep rules. `tol` = how close (in $) a wick must come to a level to
    count as taking it out (broker feeds differ by cents). With `continuation`, the boss trend
    keeps trading after each entry without building a new A to F: it only needs a new F,
    a sweep of the low before it (E), then H, I and the break."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    r = rsi(c)
    sw = rsi_swings(h, l, r, hi_level, lo_level)
    by_conf: dict[int, list[Swing]] = {}
    for s in sw:
        by_conf.setdefault(s.confirmed, []).append(s)

    # small pivots (minor_e candles each side): the sweep may take out the last small low before F
    piv_lo, piv_hi = [], []
    if minor_e:
        k = minor_e
        for i in range(k, len(df) - k):
            if l[i] == l[i - k:i + k + 1].min():
                piv_lo.append((i, l[i]))
            if h[i] == h[i - k:i + k + 1].max():
                piv_hi.append((i, h[i]))
    ik = i_sweep
    ip_lo, ip_hi = {}, {}  # small pivots for the I-sweep entry, keyed by confirmation bar
    if ik:
        for i in range(ik, len(df) - ik):
            if l[i] == l[i - ik:i + ik + 1].min():
                ip_lo[i + ik] = (i, l[i])
            if h[i] == h[i - ik:i + ik + 1].max():
                ip_hi[i + ik] = (i, h[i])
    import bisect
    lo_idx = [i for i, _ in piv_lo]
    hi_idx = [i for i, _ in piv_hi]

    def level_to_sweep(st: _Setup) -> float:
        """E, or with minor_e the last small low (buy) / high (sell) before F, whichever is nearer."""
        if not minor_e or st.f_idx < 0:
            return st.e
        idx, piv = (lo_idx, piv_lo) if st.d == 1 else (hi_idx, piv_hi)
        j = bisect.bisect_left(idx, st.f_idx) - 1
        if j < 0:
            return st.e
        lv = piv[j][1]
        return max(lv, st.e) if st.d == 1 else min(lv, st.e)

    known: list[Swing] = []
    setups: dict[int, _Setup | None] = {1: None, -1: None}
    signals: list[Signal] = []
    boss = 0

    def past(price: float, level: float, d: int) -> bool:
        """Price takes out `level` on the side away from direction d (a low for a buy)."""
        return price < level + tol if d == 1 else price > level - tol

    for t in range(len(df)):
        # 1) wick triggers on this bar (levels known before this bar)
        for d in (1, -1):
            s = setups[d]
            if s is None:
                continue
            if t - s.start > max_setup_bars:
                setups[d] = None
                continue
            if ik and s.g is not None:
                # I-sweep entry: after G, a small low must take out the previous small low (staying beyond G),
                # then buy the break of the most recent small high
                if not hasattr(s, "lows"):
                    s.lows, s.hi, s.swept = [], None, False
                pv = (ip_lo if d == 1 else ip_hi).get(t)
                if pv is not None and pv[0] > s.g_idx:
                    if (pv[1] < s.g) if d == 1 else (pv[1] > s.g):
                        if not s.second:
                            s.second, s.g = True, pv[1]  # went beyond G: this is the new G
                            s.lows, s.hi, s.swept = [], None, False
                            s.g_idx = pv[0]
                    else:
                        if s.lows and ((pv[1] < s.lows[-1]) if d == 1 else (pv[1] > s.lows[-1])):
                            s.swept = True
                        s.lows.append(pv[1])
                ph = (ip_hi if d == 1 else ip_lo).get(t)
                if ph is not None and ph[0] > s.g_idx:
                    if i_sweep_level == "highest" and s.hi is not None:
                        s.hi = max(s.hi, ph[1]) if d == 1 else min(s.hi, ph[1])
                    else:
                        s.hi = ph[1]
                if s.swept and s.hi is not None and ((h[t] > s.hi) if d == 1 else (l[t] < s.hi)):
                    signals.append(Signal(d, t, s.hi, s.g, s.f, s.second, boss == d))
                    setups[d] = None
                    if continuation and boss == d:
                        setups[d] = _Setup(d, e=None, f=None, start=t, cont=True)
                continue
            if s.g is not None and s.h is not None and t > s.h_conf:
                beyond_g = l[t] < s.g + tol if d == 1 else h[t] > s.g - tol
                broke_h = h[t] > s.h if d == 1 else l[t] < s.h
                if beyond_g and not s.second and not broke_h:
                    # first G swept: the next low is the second G; the latest high stays H
                    if left_h is not None:
                        left_h.append((d, s.h, t))  # an H left behind when its first G was swept
                    s.second, s.g = True, None
                    s.start = t
                    continue
                if broke_h:
                    signals.append(Signal(d, t, s.h, s.g, s.f, s.second, boss == d))
                    setups[d] = None  # the opposite setup stays: it may be an unfinished trade
                    if continuation and boss == d:
                        setups[d] = _Setup(d, e=None, f=None, start=t, cont=True)
        # 2) swings confirmed at this bar's close
        for s in by_conf.get(t, []):
            known.append(s)
            for d in (1, -1):
                st = setups[d]
                if st is None:
                    continue
                g_kind, h_kind = ("L", "H") if d == 1 else ("H", "L")
                if st.f is None:  # continuation: wait for the first new extreme in the trend
                    if s.kind == h_kind and len(known) >= 2:
                        st.f, st.e, st.start, st.f_idx = s.price, known[-2].price, t, s.index
                    continue
                st.start = t  # the setup is alive while its swings keep coming
                if s.kind == g_kind:
                    if st.g is None:
                        if past(s.price, level_to_sweep(st), d) or st.second or (trend_g_no_sweep and st.cont):
                            st.g, st.g_idx = s.price, s.index
                        else:
                            st.e_pending = s.price  # staircase continues: a new higher low
                    elif st.second:
                        st.g = min(st.g, s.price) if d == 1 else max(st.g, s.price)
                elif s.kind == h_kind and st.g is not None:
                    st.h, st.h_conf = s.price, t
                elif s.kind == h_kind and st.e_pending is not None:
                    higher = s.price > st.f if d == 1 else s.price < st.f
                    if higher:  # a new F: E and F move up the staircase
                        st.e, st.f, st.e_pending, st.start, st.f_idx = st.e_pending, s.price, None, t, s.index
            # new staircase completed by this swing?
            if len(known) >= 6:
                last = known[-6:]
                kinds = "".join(x.kind for x in last)
                p = [x.price for x in last]
                for d, pat in ((1, "LHLHLH"), (-1, "HLHLHL")):
                    up = d == 1
                    ok = kinds == pat and ((p[0] < p[2] < p[4] and p[1] < p[3] < p[5]) if up
                                           else (p[0] > p[2] > p[4] and p[1] > p[3] > p[5]))
                    if ok:
                        if boss != d and trend_changes is not None:
                            trend_changes.append((t, d))  # a new trend is confirmed
                        new_boss = boss != d
                        boss = d
                        # a new trend replaces an unfinished setup of the same side
                        if setups[d] is None or setups[d].g is None or (replace_on_new_trend and new_boss):
                            setups[d] = _Setup(d, e=p[4], f=p[5], start=t, f_idx=last[5].index)
    return signals, sw


@dataclass
class TradeResult:
    signal: Signal
    time: pd.Timestamp
    entry: float
    exit: float
    pnl: float  # $ per 0.01 lot (= price move in $)
    reason: str


def simulate(df: pd.DataFrame, signals: list[Signal], sl_mode: str, sl: float, tp: float,
             spread: np.ndarray | float = 0.05, max_bars: int = 1440) -> list[TradeResult]:
    """One trade at a time; an opposite signal closes the open trade at that bar's level.
    sl_mode "fixed": sl and tp in $. "g": stop beyond G + sl ($ buffer), tp in R multiples.
    Stop is assumed hit first when both are inside one bar."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sp = spread if isinstance(spread, np.ndarray) else np.full(len(df), spread)
    out: list[TradeResult] = []
    sigs = sorted(signals, key=lambda s: s.bar)
    nxt = 0
    pos = None
    for t in range(len(df)):
        while nxt < len(sigs) and sigs[nxt].bar < t:
            nxt += 1
        sig_now = sigs[nxt] if nxt < len(sigs) and sigs[nxt].bar == t else None
        if pos is not None:
            d = pos["d"]
            hit_sl = (l[t] <= pos["sl"]) if d == 1 else (h[t] + sp[t] >= pos["sl"])
            hit_tp = (h[t] >= pos["tp"]) if d == 1 else (l[t] + sp[t] <= pos["tp"])
            px = reason = None
            if True:
                if hit_sl:
                    gap = (o[t] < pos["sl"]) if d == 1 else (o[t] + sp[t] > pos["sl"])
                    px, reason = (o[t] if gap else pos["sl"]), "SL"
                elif hit_tp and t > pos["t"]:
                    px, reason = pos["tp"], "TP"
                elif sig_now is not None and sig_now.direction != d:
                    px, reason = sig_now.entry, "opposite"
                elif t - pos["t"] >= max_bars:
                    px, reason = c[t], "time"
            if reason:
                out.append(TradeResult(pos["sig"], df.index[pos["t"]], pos["entry"], px, (px - pos["entry"]) * d, reason))
                pos = None
        if pos is None and sig_now is not None:
            s = sig_now
            d = s.direction
            entry = (max(o[t], s.entry) + sp[t]) if d == 1 else min(o[t], s.entry)
            if sl_mode == "fixed":
                stop = entry - d * sl
                target = entry + d * tp
            else:
                stop = s.g - d * sl
                risk = (entry - stop) * d
                if risk <= 0:
                    continue
                target = entry + d * tp * risk
            pos = {"d": d, "entry": entry, "sl": stop, "tp": target, "t": t, "sig": s}
            # stop inside the entry bar
            if (l[t] <= stop) if d == 1 else (h[t] + sp[t] >= stop):
                out.append(TradeResult(s, df.index[t], entry, stop, (stop - entry) * d, "SL"))
                pos = None
    return out


def excursions(df: pd.DataFrame, signals: list[Signal], bars: int = 240, spread: float = 0.05):
    """Best (MFE) and worst (MAE) move in $ after each entry, within `bars` bars."""
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    rows = []
    for s in signals:
        a, b = s.bar, min(len(df), s.bar + bars)
        entry = s.entry + (spread if s.direction == 1 else 0)
        if s.direction == 1:
            mfe, mae = h[a:b].max() - entry, entry - l[a:b].min()
        else:
            mfe, mae = entry - (l[a:b].min() + spread), (h[a:b].max() + spread) - entry
        rows.append({"time": df.index[a], "dir": "BUY" if s.direction == 1 else "SELL", "entry": round(s.entry, 2),
                     "mfe": round(mfe, 2), "mae": round(mae, 2), "second_g": s.second_g})
    return pd.DataFrame(rows)


def simulate_reentry(df: pd.DataFrame, signals: list[Signal], sl: float, tp: float, extra_tp: float = 0.0,
                     max_reentries: int = 3, spread: np.ndarray | float = 0.05, hi_level: float = 68.0,
                     lo_level: float = 32.0, close_on_opposite: bool = True, pivot: int = 3,
                     reenter_at_entry: bool = False, trend_changes: list | None = None,
                     hedge: bool = False) -> list[TradeResult]:
    """Owner's re-entry rule: after a stop loss, wait for price to make a high then a low (buy;
    mirror for sell), and re-enter when a wick takes out that most recent high. The re-entry
    aims for the original take-profit level plus `extra_tp`, with the same $ stop.
    The high and low after the stop are small swings: `pivot` candles on each side (0 = RSI swings).
    Each re-entry is recorded as its own trade."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sp = spread if isinstance(spread, np.ndarray) else np.full(len(df), spread)
    if pivot:
        sw = []
        for i in range(pivot, len(df) - pivot):
            if h[i] == h[i - pivot:i + pivot + 1].max():
                sw.append(Swing("H", h[i], i, i + pivot))
            if l[i] == l[i - pivot:i + pivot + 1].min():
                sw.append(Swing("L", l[i], i, i + pivot))
    else:
        sw = rsi_swings(h, l, rsi(c), hi_level, lo_level)
    conf_at: dict[int, list[Swing]] = {}
    for s in sw:
        conf_at.setdefault(s.confirmed, []).append(s)
    sigs = {s.bar: s for s in sorted(signals, key=lambda s: s.bar)}
    tc = dict(trend_changes or [])
    out: list[TradeResult] = []
    pos = None  # open trade
    wait = None  # waiting to re-enter: {"d", "target", "left", "level", "sig", "seen_high"}
    for t in range(len(df)):
        sig_now = sigs.get(t)
        # manage an open trade
        if pos is not None:
            d = pos["d"]
            hit_sl = (l[t] <= pos["sl"]) if d == 1 else (h[t] + sp[t] >= pos["sl"])
            hit_tp = ((h[t] >= pos["tp"]) if d == 1 else (l[t] + sp[t] <= pos["tp"])) and t > pos["t"]
            px = reason = None
            if hit_sl:
                gap = (o[t] < pos["sl"]) if d == 1 else (o[t] + sp[t] > pos["sl"])
                px, reason = (o[t] if gap else pos["sl"]), "SL"
            elif hit_tp:
                px, reason = pos["tp"], "TP"
            elif close_on_opposite and sig_now is not None and sig_now.direction != d:
                px, reason = sig_now.entry, "opposite"
            elif tc.get(t, d) != d:
                px, reason = c[t], "new trend"
            if reason:
                out.append(TradeResult(pos["sig"], df.index[pos["t"]], pos["entry"], px, (px - pos["entry"]) * d,
                                       reason + ("" if pos["n"] == 0 else f" (re-entry {pos['n']})")))
                if reason == "SL" and pos["n"] < max_reentries:
                    wait = {"d": d, "target": pos["tp0"], "n": pos["n"] + 1, "level": None, "sig": pos["sig"],
                            "seen": False, "entry0": pos["entry0"]}
                pos = None
        # a new signal cancels any waiting re-entry and opens a trade
        if pos is None and sig_now is not None:
            wait = None
            d = sig_now.direction
            entry = (max(o[t], sig_now.entry) + sp[t]) if d == 1 else min(o[t], sig_now.entry)
            pos = {"d": d, "entry": entry, "sl": entry - d * sl, "tp": entry + d * tp, "tp0": entry + d * tp,
                   "t": t, "sig": sig_now, "n": 0, "entry0": entry}
            continue
        # waiting to re-enter: a high (buy) then a low must form, then price takes out that high
        if wait is not None and pos is None:
            d = wait["d"]
            ready = wait["level"] is not None and wait["seen"]
            back_at_entry = reenter_at_entry and ((h[t] >= wait["entry0"]) if d == 1 else (l[t] <= wait["entry0"]))
            if back_at_entry and not (ready and ((h[t] > wait["level"]) if d == 1 else (l[t] < wait["level"]))):
                wait["level"], ready = wait["entry0"], True  # price came back to the first entry: it is the recent high
            if ready:
                broke = h[t] >= wait["level"] if d == 1 else l[t] <= wait["level"]
                if broke:
                    entry = (max(o[t], wait["level"]) + sp[t]) if d == 1 else min(o[t], wait["level"])
                    target = wait["target"] + d * extra_tp
                    if (target - entry) * d > 0:
                        pos = {"d": d, "entry": entry, "sl": entry - d * sl, "tp": target, "tp0": wait["target"],
                               "t": t, "sig": wait["sig"], "n": wait["n"], "entry0": wait["entry0"]}
                    wait = None
            for s in conf_at.get(t, []):
                if wait is None:
                    break
                if s.kind == ("H" if d == 1 else "L"):
                    wait["level"], wait["seen"] = s.price, False
                elif wait["level"] is not None:
                    wait["seen"] = True  # the low after the high has formed
    return out
