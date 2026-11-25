import numpy as np
import pandas as pd
import pytest

from castimofx import BEARISH, BULLISH, OteConfig, run_ote_backtest
from castimofx.cli import main


def candles(closes, wick=0.2):
    c = np.asarray(closes, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame(
        {"open": o, "high": np.maximum(o, c) + wick, "low": np.minimum(o, c) - wick, "close": c},
        index=pd.date_range("2026-01-05", periods=len(c), freq="15min"),
    )


def zigzag(points, steps=6):
    out = []
    for a, b in zip(points[:-1], points[1:]):
        out += list(np.linspace(a, b, steps, endpoint=False))
    return out + [points[-1]]


# uptrend, CHoCH down from 3500 to 3440, retrace to ~3485 (inside 62-79%), then a sell-off
SELL_PATH = [3400, 3450, 3430, 3480, 3460, 3500, 3440, 3486, 3380, 3370]


def test_choch_ote_sell_enters_in_ote_zone_and_hits_targets():
    df = candles(zigzag(SELL_PATH))
    res = run_ote_backtest(df, OteConfig(swing_length=3, min_leg_atr=0.5), spread=0.0)
    assert len(res.trades) == 1
    tr = res.trades[0]
    assert tr.direction == BEARISH
    leg_hi, leg_lo = df.high.iloc[30], df.low.iloc[36:42].min()
    expected_entry = leg_lo + 0.705 * (leg_hi - leg_lo)
    assert tr.entry == pytest.approx(expected_entry, abs=0.01)
    assert tr.stop > leg_hi
    assert tr.targets[1] == pytest.approx(leg_lo)  # TP2 = leg low
    assert tr.tps_hit == 4 and tr.exit_reason == "tp4"
    assert tr.pnl > 0


def test_buy_is_mirror_of_sell():
    df = candles(zigzag([7000 - p for p in SELL_PATH]))
    tr = run_ote_backtest(df, OteConfig(swing_length=3, min_leg_atr=0.5), spread=0.0).trades
    assert len(tr) == 1 and tr[0].direction == BULLISH and tr[0].tps_hit == 4


def test_breakeven_after_tp1():
    # sell fills, drops to TP1 (50%), then rallies through the old stop
    df = candles(zigzag([3400, 3450, 3430, 3480, 3460, 3500, 3440, 3486, 3468, 3520]))
    tr = run_ote_backtest(df, OteConfig(swing_length=3, min_leg_atr=0.5), spread=0.0).trades[0]
    assert tr.tps_hit == 1 and tr.exit_reason == "breakeven"
    assert tr.pnl > 0  # a quarter banked at TP1, rest closed at entry
    tr2 = run_ote_backtest(df, OteConfig(swing_length=3, min_leg_atr=0.5, breakeven_after_tp1=False),
                           spread=0.0).trades[0]
    assert tr2.exit_reason == "stop" and tr2.pnl < tr.pnl


def test_filters_can_block_the_setup():
    df = candles(zigzag(SELL_PATH))
    res = run_ote_backtest(df, OteConfig(swing_length=3, min_leg_atr=0.5, psych_step=1000), spread=0.0)
    assert not res.trades and res.skipped.get("no PSY level") == 1
    res = run_ote_backtest(df, OteConfig(swing_length=3, min_leg_atr=0.5, psych_step=10), spread=0.0)
    assert len(res.trades) == 1  # OTE zone is 3477-3487: 3480 sits inside


def test_no_positive_bias_on_random_walk():
    rng = np.random.default_rng(1)
    n, sub = 4000, 15
    p = 3500 * np.exp(np.cumsum(rng.normal(0, 0.0003, n * sub))).reshape(n, sub)
    o = np.r_[3500, p[:-1, -1]]
    df = pd.DataFrame({"open": o, "high": np.maximum(p.max(1), o), "low": np.minimum(p.min(1), o),
                       "close": p[:, -1]}, index=pd.date_range("2026-01-05", periods=n, freq="15min"))
    st = run_ote_backtest(df, OteConfig(), spread=0.0).stats()
    assert st["trades"] > 20
    assert st["avg_r"] < 0.25  # no edge can come from the backtester itself


def test_tp_fractions_validated():
    with pytest.raises(ValueError):
        run_ote_backtest(candles(zigzag(SELL_PATH)), OteConfig(tp_fractions=(0.5, 0.5, 0.5, 0.5)))


def test_cli_ote(capsys):
    assert main(["ote", "--trades", "2"]) == 0
    assert "tp1_hit_pct" in capsys.readouterr().out


def test_load_mt5_tab_export(tmp_path):
    from castimofx import load_csv
    p = tmp_path / "x.csv"
    p.write_text("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\r\n"
                 "2024.11.26\t01:00:00\t2625.09\t2628.02\t2625.02\t2628.02\t684\t0\t4\r\n"
                 "2024.11.26\t01:15:00\t2628.03\t2628.58\t2625.89\t2625.96\t726\t0\t5\r\n")
    df = load_csv(str(p))
    assert len(df) == 2 and df.close.iloc[-1] == 2625.96
