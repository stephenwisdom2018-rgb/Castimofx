"""Loading price data (OHLC candles) and generating synthetic data for demos."""

from __future__ import annotations

import numpy as np
import pandas as pd

_TIME_COLUMNS = ("time", "datetime", "date", "timestamp", "gmt time", "local time")


def load_csv(path: str) -> pd.DataFrame:
    """Load an OHLC CSV (MT4/MT5, TradingView, Dukascopy-style exports all work).

    Needs a time column plus open/high/low/close. Column names are case-insensitive.
    Returns a DataFrame indexed by timestamp with columns open, high, low, close.
    """
    df = pd.read_csv(path, sep=None, engine="python")  # comma, tab (MT5 export) or semicolon
    df.columns = [c.strip().lower().strip("<>") for c in df.columns]

    # MT4/MT5 exports often split date and time into two columns.
    if "date" in df.columns and "time" in df.columns:
        df["datetime"] = df["date"].astype(str) + " " + df["time"].astype(str)
        df = df.drop(columns=["date", "time"])

    time_col = next((c for c in _TIME_COLUMNS if c in df.columns), None)
    if time_col is None:
        raise ValueError(f"No time column found. Expected one of {_TIME_COLUMNS}, got {list(df.columns)}")

    missing = {"open", "high", "low", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")

    ts = df[time_col]
    if pd.api.types.is_numeric_dtype(ts):
        unit = "ms" if ts.iloc[0] > 1e11 else "s"
        index = pd.to_datetime(ts, unit=unit)
    else:
        index = pd.to_datetime(ts, dayfirst=False)

    out = df[["open", "high", "low", "close"]].astype(float)
    out.index = pd.DatetimeIndex(index, name="time")
    out = out[~out.index.duplicated()].sort_index()
    return validate(out)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex")
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    if bad.any():
        raise ValueError(f"{int(bad.sum())} candles have high/low inconsistent with open/close")
    return df


def synthetic(
    bars: int = 5000,
    start_price: float = 1.0850,
    freq: str = "15min",
    seed: int | None = 7,
    volatility: float = 0.0006,
) -> pd.DataFrame:
    """Random-walk forex-like candles with alternating trend regimes (for demos and tests)."""
    rng = np.random.default_rng(seed)
    drift = np.zeros(bars)
    i = 0
    while i < bars:
        length = int(rng.integers(150, 600))
        drift[i : i + length] = rng.normal(0, volatility * 0.15)
        i += length

    returns = drift + rng.normal(0, volatility, bars)
    close = start_price * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[start_price], close[:-1]])
    wick = np.abs(rng.normal(0, volatility * 0.6, (2, bars))) * close
    high = np.maximum(open_, close) + wick[0]
    low = np.minimum(open_, close) - wick[1]

    index = pd.date_range("2025-01-06", periods=bars, freq=freq, name="time")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=index)
