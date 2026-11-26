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


def rsi_swings(high, low, r, hi_level=70.0, lo_level=30.0, takeout_counts: bool = False) -> list[Swing]:
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
            if takeout_counts and swings and swings[-1].kind == "L" and low[t] < swings[-1].price and ext_i < t:
                seg = high[swings[-1].index + 1:t + 1]
                k = int(np.argmax(seg))
                hi_i = swings[-1].index + 1 + k
                if hi_i < t:
                    swings.append(Swing("H", high[hi_i], hi_i, t))
                    state, ext_p, ext_i, seen = "down", low[t], t, True
                    continue
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
            if takeout_counts and swings and swings[-1].kind == "H" and high[t] > swings[-1].price and ext_i < t:
                # exception: the move passed a high whose RSI reached the line, so it counts as a high;
                # the lowest point before it is the low
                seg = low[swings[-1].index + 1:t + 1]
                k = int(np.argmin(seg))
                lo_i = swings[-1].index + 1 + k
                if lo_i < t:
                    swings.append(Swing("L", low[lo_i], lo_i, t))
                    state, ext_p, ext_i, seen = "up", high[t], t, True
                    continue
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
    g_swept: bool = True  # G took out a low on its way down


def find_signals(df: pd.DataFrame, max_setup_bars: int = 600, hi_level: float = 68.0, lo_level: float = 32.0,
                 tol: float = 0.0, continuation: bool = True,
                 left_h: list | None = None, trend_changes: list | None = None,
                 replace_on_new_trend: bool = True, minor_e: int = 0,
                 trend_g_no_sweep: bool = False, i_sweep: int = 0,
                 i_sweep_level: str = "recent", hybrid: bool = False,
                 h_after_g: bool = False, structure: str = "strict",
                 takeout_counts: bool = False, reversal_after: int = 0) -> tuple[list[Signal], list[Swing]]:
    """Signals from the sweep rules. `tol` = how close (in $) a wick must come to a level to
    count as taking it out (broker feeds differ by cents). With `continuation`, the boss trend
    keeps trading after each entry without building a new A to F: it only needs a new F,
    a sweep of the low before it (E), then H, I and the break."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    r = rsi(c)
    sw = rsi_swings(h, l, r, hi_level, lo_level, takeout_counts)
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

    # "takeout" structure: a high only counts if it takes out the previous counted high (lows mirrored);
    # smaller swings in between are ignored. Two highs taken = buy bias (two lows taken = sell bias).
    trk = {1: {"lvl": None, "base": None, "pull": None, "cnt": 0, "last_opp": None},
           -1: {"lvl": None, "base": None, "pull": None, "cnt": 0, "last_opp": None}}
    # reversal: after `reversal_after` lows taken in a row, buy the next break of the most recent high (mirror for sells)
    rev = {1: {"cnt": 0, "lvl": None, "ext": None, "level": None, "conf": -1},
           -1: {"cnt": 0, "lvl": None, "ext": None, "level": None, "conf": -1}}
    known: list[Swing] = []
    setups: dict[int, _Setup | None] = {1: None, -1: None}
    signals: list[Signal] = []
    boss = 0

    def past(price: float, level: float, d: int) -> bool:
        """Price takes out `level` on the side away from direction d (a low for a buy)."""
        return price < level + tol if d == 1 else price > level - tol

    for t in range(len(df)):
        # 0) reversal breakouts
        if reversal_after:
            for d in (1, -1):
                rv = rev[d]
                if rv["cnt"] >= reversal_after and rv["level"] is not None and t > rv["conf"]:
                    if (h[t] > rv["level"]) if d == 1 else (l[t] < rv["level"]):
                        signals.append(Signal(d, t, rv["level"], rv["ext"], rv["ext"], True, True))
                        rv["cnt"], rv["level"], rv["lvl"] = 0, None, None
                        setups[d] = None
        # 1) wick triggers on this bar (levels known before this bar)
        for d in (1, -1):
            s = setups[d]
            if s is None:
                continue
            if t - s.start > max_setup_bars:
                setups[d] = None
                continue
            if ik and s.g is not None and not (hybrid and s.g_swept):
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
            if reversal_after:
                for d in (1, -1):
                    rv = rev[d]
                    take_kind = "L" if d == 1 else "H"  # a buy reversal counts lows taken
                    if s.kind == take_kind:
                        lower = (rv["lvl"] is None) or ((s.price < rv["lvl"]) if d == 1 else (s.price > rv["lvl"]))
                        if rv["lvl"] is not None and lower:
                            rv["cnt"] += 1
                        if lower:
                            rv["lvl"], rv["ext"] = s.price, s.price
                    else:
                        if rv["cnt"] >= reversal_after:
                            rv["level"], rv["conf"] = s.price, t  # the most recent high: break it to buy
                        elif rv["level"] is None and rv["lvl"] is not None and rv["cnt"] == 0:
                            pass
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
                        swept = past(s.price, level_to_sweep(st), d) or st.second
                        if swept or (trend_g_no_sweep and st.cont):
                            st.g, st.g_idx, st.g_swept = s.price, s.index, swept
                        else:
                            st.e_pending = s.price  # staircase continues: a new higher low
                    elif st.second:
                        if (s.price < st.g) if d == 1 else (s.price > st.g):
                            st.g, st.g_idx = s.price, s.index
                elif s.kind == h_kind and st.g is not None:
                    if not h_after_g or s.index > st.g_idx:  # H must be a new high formed after G (never the first F)
                        st.h, st.h_conf = s.price, t
                elif s.kind == h_kind and st.e_pending is not None:
                    higher = s.price > st.f if d == 1 else s.price < st.f
                    if higher:  # a new F: E and F move up the staircase
                        st.e, st.f, st.e_pending, st.start, st.f_idx = st.e_pending, s.price, None, t, s.index
            if structure == "takeout":
                for d in (1, -1):
                    k = trk[d]
                    ext_kind = "H" if d == 1 else "L"  # the side that must be taken out
                    beyond = (lambda a, b: a > b) if d == 1 else (lambda a, b: a < b)
                    if s.kind == ext_kind:
                        if k["lvl"] is None:
                            k["lvl"], k["pull"] = s.price, None
                        elif beyond(s.price, k["lvl"]):
                            k["cnt"] += 1
                            if k["pull"] is not None:
                                k["base"] = k["pull"]
                            k["lvl"], k["pull"] = s.price, None
                            if k["cnt"] >= 2 and k["base"] is not None:
                                if boss != d and trend_changes is not None:
                                    trend_changes.append((t, d))
                                new_boss = boss != d
                                boss = d
                                if setups[d] is None or setups[d].g is None or (replace_on_new_trend and new_boss):
                                    setups[d] = _Setup(d, e=k["base"], f=s.price, start=t, f_idx=s.index)
                        k["last_opp"] = None
                    else:
                        k["pull"] = s.price if k["pull"] is None else (min(k["pull"], s.price) if d == 1 else max(k["pull"], s.price))
                        if k["base"] is not None and beyond(k["base"], s.price):
                            # the pullback took out the last counted low: the staircase is broken, start again
                            k["cnt"], k["base"], k["pull"] = 0, s.price, None
                            k["lvl"] = None
                continue
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
    exit_time: pd.Timestamp | None = None


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
                flipped = reason == "opposite"
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
                     hedge: bool = False, reentry_mode: str = "pivot", flip_tp: float | None = None,
                     be_at: float | None = None, reenter_after_be: bool = False,
                     limit_offset: float = 0.0, limit_tp: str = "own",
                     reentry_sl: float | None = None, friday_cutoff: int | None = None,
                     friday_close: bool = False, later_pivot: int | None = None,
                     fast: np.ndarray | None = None) -> list[TradeResult]:
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
    # mixed mode: the 1st re-entry uses `pivot` swings, later re-entries use `later_pivot` (0 = RSI swings)
    conf_later = conf_at
    if later_pivot is not None and later_pivot != pivot:
        if later_pivot:
            sw2 = []
            for i in range(later_pivot, len(df) - later_pivot):
                if h[i] == h[i - later_pivot:i + later_pivot + 1].max():
                    sw2.append(Swing("H", h[i], i, i + later_pivot))
                if l[i] == l[i - later_pivot:i + later_pivot + 1].min():
                    sw2.append(Swing("L", l[i], i, i + later_pivot))
        else:
            sw2 = rsi_swings(h, l, rsi(c), hi_level, lo_level)
        conf_later = {}
        for s2 in sw2:
            conf_later.setdefault(s2.confirmed, []).append(s2)
    sigs = {s.bar: s for s in sorted(signals, key=lambda s: s.bar)}
    tc = dict(trend_changes or [])
    out: list[TradeResult] = []
    idx_t = df.index
    dow = idx_t.dayofweek.to_numpy()
    hour = idx_t.hour.to_numpy()
    gap_after = np.r_[(idx_t[1:] - idx_t[:-1]).total_seconds() / 3600, 99]
    week_end = (dow == 4) & (gap_after > 6)  # last bar before the weekend
    no_new = (dow == 4) & (hour >= friday_cutoff) if friday_cutoff is not None else np.zeros(len(df), bool)
    fast_arr = fast if fast is not None else np.zeros(len(df), bool)
    mem = None  # a trade that triggered during a fast market, kept until the market calms
    pend = None  # limit order for a first entry (limit_offset > 0)
    pos = None  # open trade
    wait = None  # waiting to re-enter: {"d", "target", "left", "level", "sig", "seen_high"}
    for t in range(len(df)):
        sig_now = sigs.get(t)
        flipped = False
        if no_new[t] or (friday_close and week_end[t]):
            wait = None if friday_close else wait
        # manage an open trade
        if pos is not None:
            d = pos["d"]
            hit_sl = (l[t] <= pos["sl"]) if d == 1 else (h[t] + sp[t] >= pos["sl"])
            hit_tp = ((h[t] >= pos["tp"]) if d == 1 else (l[t] + sp[t] <= pos["tp"])) and t > pos["t"]
            px = reason = None
            if hit_sl:
                gap = (o[t] < pos["sl"]) if d == 1 else (o[t] + sp[t] > pos["sl"])
                px, reason = (o[t] if gap else pos["sl"]), ("BE" if pos.get("be") else "SL")
            elif hit_tp:
                px, reason = pos["tp"], "TP"
            elif close_on_opposite and sig_now is not None and sig_now.direction != d:
                px, reason = sig_now.entry, "opposite"
            elif tc.get(t, d) != d:
                px, reason = c[t], "new trend"
            elif friday_close and week_end[t]:
                px, reason = c[t], "friday close"
            # break-even: once the trade is $be_at in profit (checked after this bar), the stop moves to entry
            if not reason and be_at and not pos.get("be") and t > pos["t"]:
                best = (h[t] - pos["entry"]) if d == 1 else (pos["entry"] - (l[t] + sp[t]))
                if best >= be_at:
                    pos["sl"], pos["be"] = pos["entry"], True
            if reason:
                flipped = reason == "opposite"
                out.append(TradeResult(pos["sig"], df.index[pos["t"]], pos["entry"], px, (px - pos["entry"]) * d,
                                       reason + ("" if pos["n"] == 0 else f" (re-entry {pos['n']})"), df.index[t]))
                if (reason == "SL" or (reenter_after_be and reason == "BE")) and pos["n"] < max_reentries:
                    wait = {"d": d, "target": pos["tp0"], "n": pos["n"] + 1, "level": None, "sig": pos["sig"],
                            "seen": False, "entry0": pos["entry0"]}
                pos = None
        if no_new[t] and pos is None:
            pend = None
            continue
        # market calm again: take the remembered trade from where price is, if it is at or worse than its entry
        if mem is not None and pos is None and not fast_arr[t]:
            d = mem["d"]
            px = c[t] + (sp[t] if d == 1 else 0)
            if (mem["target"] - px) * d <= 0:
                mem = None  # target already reached: forget it
            elif (mem["entry"] - px) * d >= 0:
                pos = {"d": d, "entry": px, "sl": px - d * sl, "tp": mem["target"], "tp0": mem["tp0"],
                       "t": t, "sig": mem["sig"], "n": mem["n"], "entry0": mem["entry0"]}
                mem = None
                continue
        # pending limit order for a first entry: fill, or cancel if price runs to the target first
        if pend is not None and pos is None:
            d = pend["d"]
            if (h[t] >= pend["cancel"]) if d == 1 else (l[t] <= pend["cancel"]):
                pend = None
            elif (l[t] <= pend["level"]) if d == 1 else (h[t] + sp[t] >= pend["level"]):
                entry = pend["level"] + (sp[t] if d == 1 else 0)
                target = pend["tp"]
                pos = {"d": d, "entry": entry, "sl": entry - d * sl, "tp": target, "tp0": target,
                       "t": t, "sig": pend["sig"], "n": 0, "entry0": entry}
                pend = None
        if limit_offset and pos is None and sig_now is not None and not (wait is not None and reentry_mode == "signal"):
            d = sig_now.direction
            lvl = sig_now.entry - d * limit_offset
            tp_lvl = (lvl + d * tp) if limit_tp == "own" else (sig_now.entry + d * tp)
            pend = {"d": d, "level": lvl, "tp": tp_lvl, "cancel": sig_now.entry + d * tp, "sig": sig_now}
            wait = None
            continue
        # a new signal opens a trade; in "signal" mode a same-side signal after a stop is the re-entry
        if pos is None and sig_now is not None and fast_arr[t] and reentry_mode != "signal":
            d = sig_now.direction
            e0 = sig_now.entry
            mem = {"d": d, "entry": e0, "target": e0 + d * tp, "tp0": e0 + d * tp, "n": 0, "sig": sig_now, "entry0": e0}
            wait = None
            continue
        if pos is None and sig_now is not None:
            mem = None
            d = sig_now.direction
            entry = (max(o[t], sig_now.entry) + sp[t]) if d == 1 else min(o[t], sig_now.entry)
            if reentry_mode == "signal" and wait is not None and wait["d"] == d:
                target = wait["target"] + d * extra_tp
                if (target - entry) * d < tp:
                    target = entry + d * tp
                pos = {"d": d, "entry": entry, "sl": entry - d * sl, "tp": target, "tp0": wait["target"],
                       "t": t, "sig": sig_now, "n": wait["n"], "entry0": wait["entry0"]}
            else:
                this_tp = flip_tp if (flipped and flip_tp) else tp  # the trade that flips gets its own target
                pos = {"d": d, "entry": entry, "sl": entry - d * sl, "tp": entry + d * this_tp, "tp0": entry + d * this_tp,
                       "t": t, "sig": sig_now, "n": 0, "entry0": entry}
            wait = None
            continue
        if reentry_mode == "signal":
            continue
        # waiting to re-enter: a high (buy) then a low must form, then price takes out that high
        if wait is not None and pos is None:
            d = wait["d"]
            if reentry_mode == "entry_only":
                wait["level"], wait["seen"] = wait["entry0"], True
            ready = wait["level"] is not None and wait["seen"]
            back_at_entry = reenter_at_entry and ((h[t] >= wait["entry0"]) if d == 1 else (l[t] <= wait["entry0"]))
            if back_at_entry and not (ready and ((h[t] > wait["level"]) if d == 1 else (l[t] < wait["level"]))):
                wait["level"], ready = wait["entry0"], True  # price came back to the first entry: it is the recent high
            if ready:
                broke = h[t] >= wait["level"] if d == 1 else l[t] <= wait["level"]
                if broke:
                    entry = (max(o[t], wait["level"]) + sp[t]) if d == 1 else min(o[t], wait["level"])
                    target = wait["target"] + d * extra_tp
                    if fast_arr[t] and (target - entry) * d > 0:
                        mem = {"d": d, "entry": wait["level"], "target": target, "tp0": wait["target"],
                               "n": wait["n"], "sig": wait["sig"], "entry0": wait["entry0"]}
                    elif (target - entry) * d > 0:
                        rsl = reentry_sl if reentry_sl else sl
                        pos = {"d": d, "entry": entry, "sl": entry - d * rsl, "tp": target, "tp0": wait["target"],
                               "t": t, "sig": wait["sig"], "n": wait["n"], "entry0": wait["entry0"]}
                    wait = None
            for s in ((conf_at if wait["n"] <= 1 else conf_later) if wait is not None else {}).get(t, []):
                if wait is None:
                    break
                if s.kind == ("H" if d == 1 else "L"):
                    wait["level"], wait["seen"] = s.price, False
                elif wait["level"] is not None:
                    wait["seen"] = True  # the low after the high has formed
    return out
