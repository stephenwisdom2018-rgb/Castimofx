"""Command line: `python -m castimofx demo | backtest FILE | analyze FILE`."""

from __future__ import annotations

import argparse

import pandas as pd

from .backtest import BacktestConfig, run_backtest
from .data import load_csv, synthetic
from .smc import BULLISH, SMCAnalyzer, key_levels
from .strategy import StrategyConfig

PIP_SIZES = {"JPY": 0.01, "XAU": 0.1, "XAG": 0.01}


def pip_size_for(pair: str) -> float:
    pair = pair.upper()
    for key, size in PIP_SIZES.items():
        if key in pair:
            return size
    return 0.0001


def _strategy_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pair", default="EURUSD", help="symbol, used to pick the pip size (default EURUSD)")
    p.add_argument("--swing", type=int, default=5, help="swing length in bars (default 5)")
    p.add_argument("--rr", type=float, default=2.0, help="risk:reward target (default 2)")
    p.add_argument("--risk", type=float, default=1.0, help="%% of balance risked per trade (default 1)")
    p.add_argument("--balance", type=float, default=10_000, help="starting balance (default 10000)")
    p.add_argument("--spread", type=float, default=1.0, help="spread in pips (default 1)")
    p.add_argument("--sl-buffer", type=float, default=0.1, help="stop buffer beyond the zone, x ATR (default 0.1)")
    p.add_argument("--max-stop", type=float, default=4.0, help="skip zones whose stop is wider than this x ATR (default 4)")
    p.add_argument("--max-positions", type=int, default=1, help="trades open at the same time (default 1)")
    p.add_argument("--entry", choices=["edge", "mid", "market"], default="edge",
                   help="edge/mid = limit order in the zone, market = confirmation entry right after the break")
    p.add_argument("--htf", type=int, default=0, help="trend filter: timeframe this many times higher (16 on M15 = H4)")
    p.add_argument("--session", default="", help="only trade between these hours, e.g. 7-17")
    p.add_argument("--sweep", action="store_true", help="only trade breaks whose leg swept the previous swing")
    p.add_argument("--no-discount-filter", action="store_true", help="also trade zones on the wrong side of equilibrium")
    p.add_argument("--choch-only", action="store_true", help="only trade zones created by a CHoCH")
    p.add_argument("--trades", type=int, default=10, help="number of recent trades to list")


def _backtest(df: pd.DataFrame, args: argparse.Namespace) -> None:
    scfg = StrategyConfig(
        swing_length=args.swing, rr=args.rr, sl_buffer_atr=args.sl_buffer,
        pip_size=pip_size_for(args.pair), require_discount=not args.no_discount_filter,
        choch_only=args.choch_only, max_stop_atr=args.max_stop,
        max_positions=args.max_positions, entry_mode=args.entry, htf_factor=args.htf, require_sweep=args.sweep,
        session_hours=tuple(int(x) for x in args.session.split("-")) if args.session else None,
    )
    bcfg = BacktestConfig(initial_balance=args.balance, risk_pct=args.risk, spread_pips=args.spread)
    result = run_backtest(df, scfg, bcfg)

    print(f"\n{args.pair}  {df.index[0]} -> {df.index[-1]}  ({len(df)} bars)")
    print("-" * 52)
    for k, v in result.stats().items():
        print(f"{k:>18}: {v}")
    if result.trades and args.trades:
        print(f"\nLast {min(args.trades, len(result.trades))} trades:")
        for tr in result.trades[-args.trades:]:
            print(f"  {tr.entry_time:%Y-%m-%d %H:%M}  {tr.side:4}  in {tr.entry:.5f}  out {tr.exit:.5f}"
                  f"  {tr.reason:6}  {tr.r_multiple:+.2f}R  {tr.pnl:+.2f}")


def _analyze(df: pd.DataFrame, args: argparse.Namespace) -> None:
    a = SMCAnalyzer(df, swing_length=args.swing).run()
    last = df.iloc[-1]
    trend = {1: "BULLISH", -1: "BEARISH", 0: "UNDEFINED"}[a.trend]
    print(f"\n{args.pair}  last close {last.close:.5f} at {df.index[-1]}")
    print(f"Structure: {trend}")
    for ev in a.events[-5:]:
        side = "bullish" if ev.direction == BULLISH else "bearish"
        print(f"  {ev.kind:5} {side:7} through {ev.level:.5f} at {df.index[ev.index]}")
    rng = a.dealing_range()
    if rng:
        eq = (rng[0] + rng[1]) / 2
        zone = "PREMIUM" if last.close > eq else "DISCOUNT"
        print(f"Dealing range {rng[0]:.5f} - {rng[1]:.5f}, equilibrium {eq:.5f} -> price in {zone}")
    obs = a.active_order_blocks()[-6:]
    if obs:
        print("Unmitigated zones:")
        for ob in obs:
            kind = "DEMAND" if ob.direction == BULLISH else "SUPPLY"
            print(f"  {kind:6} {ob.bottom:.5f} - {ob.top:.5f}  (from {df.index[ob.index]})")
    levels = key_levels(df).iloc[-1].dropna()
    if not levels.empty:
        print("Key levels: " + "  ".join(f"{k} {v:.5f}" for k, v in levels.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="castimofx", description="SMC forex trading bot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="backtest on synthetic EURUSD-like data")
    demo.add_argument("--bars", type=int, default=8000)
    demo.add_argument("--seed", type=int, default=7)
    _strategy_args(demo)

    bt = sub.add_parser("backtest", help="backtest a CSV of OHLC candles")
    bt.add_argument("csv")
    _strategy_args(bt)

    an = sub.add_parser("analyze", help="print current structure, zones and key levels")
    an.add_argument("csv")
    _strategy_args(an)

    args = parser.parse_args(argv)
    if args.cmd == "demo":
        _backtest(synthetic(args.bars, seed=args.seed), args)
    elif args.cmd == "backtest":
        _backtest(load_csv(args.csv), args)
    else:
        _analyze(load_csv(args.csv), args)
    return 0
