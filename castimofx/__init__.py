"""Castimofx - Smart Money Concepts (SMC) forex trading bot."""

from .backtest import BacktestConfig, BacktestResult, run_backtest
from .data import load_csv, synthetic
from .smc import BEARISH, BULLISH, SMCAnalyzer, key_levels
from .strategy import SMCStrategy, StrategyConfig

__all__ = [
    "BULLISH", "BEARISH", "SMCAnalyzer", "key_levels", "SMCStrategy", "StrategyConfig",
    "BacktestConfig", "BacktestResult", "run_backtest", "load_csv", "synthetic",
]
