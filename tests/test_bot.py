import numpy as np
import pandas as pd
import pytest

from castimofx import (BULLISH, BEARISH, SMCAnalyzer, StrategyConfig, key_levels, load_csv,
                       run_backtest, synthetic)
from castimofx.cli import main, pip_size_for
from castimofx.smc import find_swings


def candles(closes, start="2025-01-06", freq="15min", wick=0.0002):
    c = np.asarray(closes, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame(
        {"open": o, "high": np.maximum(o, c) + wick, "low": np.minimum(o, c) - wick, "close": c},
        index=pd.date_range(start, periods=len(c), freq=freq),
    )


def zigzag(points, steps=6):
    out = []
    for a, b in zip(points[:-1], points[1:]):
        out += list(np.linspace(a, b, steps, endpoint=False))
    return out + [points[-1]]


def test_swings_are_confirmed_only_after_right_side_bars():
    df = candles(zigzag([1.10, 1.12, 1.11, 1.13]))
    swings = find_swings(df.high.to_numpy(), df.low.to_numpy(), 3)
    assert swings, "expected pivots"
    for s in swings:
        assert s.confirmed_at == s.index + 3


def test_bos_and_choch_detection():
    # Up-trend making higher highs, then a sharp drop through the last higher low.
    df = candles(zigzag([1.100, 1.120, 1.110, 1.130, 1.118, 1.140, 1.125, 1.090, 1.095]))
    a = SMCAnalyzer(df, swing_length=3).run()
    kinds = [(e.kind, e.direction) for e in a.events]
    assert ("BOS", BULLISH) in kinds
    assert ("CHoCH", BEARISH) in kinds
    # The CHoCH must come after the bullish BOS.
    first_bull = next(i for i, k in enumerate(kinds) if k[1] == BULLISH)
    choch = kinds.index(("CHoCH", BEARISH))
    assert choch > first_bull
    assert a.trend == BEARISH


def test_order_block_created_on_break_and_sits_at_leg_origin():
    df = candles(zigzag([1.100, 1.120, 1.110, 1.130, 1.118, 1.140]))
    a = SMCAnalyzer(df, swing_length=3).run()
    bull = [ob for ob in a.order_blocks if ob.direction == BULLISH]
    assert bull
    ob = bull[-1]
    assert ob.bottom < ob.top
    assert ob.range_low <= ob.bottom
    assert ob.index <= ob.created_at


def test_analyzer_has_no_lookahead():
    """Results up to bar t must not change when future bars are appended."""
    df = synthetic(1500, seed=3)
    cut = 900
    full = SMCAnalyzer(df).run()
    part = SMCAnalyzer(df.iloc[:cut]).run()
    assert [(e.kind, e.index) for e in full.events if e.index < cut] == [(e.kind, e.index) for e in part.events]
    assert [(o.index, o.top, o.bottom) for o in full.order_blocks if o.created_at < cut] == \
           [(o.index, o.top, o.bottom) for o in part.order_blocks]


def test_backtest_runs_and_stats_are_consistent():
    result = run_backtest(synthetic(4000, seed=11))
    stats = result.stats()
    assert stats["trades"] == len(result.trades) > 0
    assert stats["final_balance"] == pytest.approx(10_000 + sum(t.pnl for t in result.trades), abs=0.01)
    for t in result.trades:
        assert t.exit_time >= t.entry_time
        # 1% risk with the stop as worst case (allowing for spread and small gaps)
        assert t.r_multiple > -1.6


def test_trades_respect_stops_and_targets():
    result = run_backtest(synthetic(4000, seed=5), StrategyConfig(rr=3.0))
    for t in result.trades:
        if t.reason == "target":
            assert t.r_multiple > 2.5
        if t.reason == "stop":
            assert t.r_multiple < 0


def test_key_levels_previous_day():
    df = candles(np.r_[np.linspace(1.10, 1.12, 96), np.linspace(1.12, 1.11, 96)])
    lv = key_levels(df)
    assert np.isnan(lv["PDH"].iloc[0])
    day2 = lv.loc["2025-01-07"]
    assert day2["PDH"].iloc[0] == pytest.approx(df.loc["2025-01-06", "high"].max())
    assert day2["PDL"].iloc[0] == pytest.approx(df.loc["2025-01-06", "low"].min())


def test_load_mt_style_csv(tmp_path):
    p = tmp_path / "eurusd.csv"
    p.write_text("<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<TICKVOL>\n"
                 "2025.01.06,00:00,1.1000,1.1010,1.0990,1.1005,100\n"
                 "2025.01.06,00:15,1.1005,1.1020,1.1000,1.1015,120\n")
    df = load_csv(str(p))
    assert list(df.columns) == ["open", "high", "low", "close"]
    assert len(df) == 2 and df.index[1] == pd.Timestamp("2025-01-06 00:15")


def test_pip_sizes():
    assert pip_size_for("EURUSD") == 0.0001
    assert pip_size_for("USDJPY") == 0.01
    assert pip_size_for("XAUUSD") == 0.1


def test_cli_demo_and_analyze(tmp_path, capsys):
    assert main(["demo", "--bars", "2000"]) == 0
    p = tmp_path / "d.csv"
    synthetic(1500).to_csv(p)
    assert main(["analyze", str(p)]) == 0
    out = capsys.readouterr().out
    assert "win_rate_pct" in out and "Structure:" in out


def test_confirmation_entry_fills_next_bar_open_and_targets_rr():
    df = synthetic(4000, seed=2)
    r = run_backtest(df, StrategyConfig(entry_mode="market", rr=2.0, require_discount=False))
    assert r.trades
    opens = df["open"]
    for t in r.trades:
        assert t.entry == pytest.approx(opens.loc[t.entry_time])
        assert t.target == pytest.approx(t.entry + (2.0 if t.direction == BULLISH else -2.0) * abs(t.entry - t.stop))


def test_max_positions_allows_overlapping_trades():
    df = synthetic(6000, seed=4)
    one = run_backtest(df, StrategyConfig(max_positions=1, require_discount=False))
    many = run_backtest(df, StrategyConfig(max_positions=3, require_discount=False))

    def max_overlap(trades):
        ev = sorted([(t.entry_time, 1) for t in trades] + [(t.exit_time, -1) for t in trades], key=lambda x: (x[0], x[1]))
        cur = best = 0
        for _, d in ev:
            cur += d
            best = max(best, cur)
        return best

    assert max_overlap(one.trades) <= 1
    assert len(many.trades) >= len(one.trades)


def test_htf_filter_only_trades_with_higher_timeframe_trend():
    from castimofx.backtest import htf_trend
    df = synthetic(4000, seed=8)
    bias = htf_trend(df, 16, 3)
    r = run_backtest(df, StrategyConfig(swing_length=3, htf_factor=16, entry_mode="market", require_discount=False))
    pos = {ts: i for i, ts in enumerate(df.index)}
    for t in r.trades:
        assert bias[pos[t.entry_time] - 1] == t.direction  # decided on the previous bar's close


def test_session_filter():
    df = synthetic(4000, seed=9)
    r = run_backtest(df, StrategyConfig(entry_mode="market", session_hours=(7, 17), require_discount=False))
    assert r.trades
    assert all(7 <= t.entry_time.hour < 17 for t in r.trades)


def test_load_mt5_tab_export(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\r\n"
                 "2024.11.26\t01:00:00\t2625.09\t2628.02\t2625.02\t2628.02\t684\t0\t4\r\n"
                 "2024.11.26\t01:15:00\t2628.03\t2628.58\t2625.89\t2625.96\t726\t0\t5\r\n")
    df = load_csv(str(p))
    assert len(df) == 2 and df.close.iloc[-1] == 2625.96
