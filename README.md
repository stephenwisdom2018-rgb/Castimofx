# Castimofx

A forex trading bot built on **Smart Money Concepts (SMC)**, the style of chart
with BOS / CHoCH labels, supply and demand zones, equilibrium and PDL / PWL / PML levels.

> ⚠️ This is a research and backtesting tool. It does not place real trades yet.
> Forex trading is high risk. Backtest and paper-trade before risking money.

## What it detects

| Concept | Meaning |
|---|---|
| **Swing high / low** | Fractal pivots, confirmed only after `--swing` bars, so there is no look-ahead |
| **BOS** | Break of structure: a candle closes through a swing in the trend's direction |
| **CHoCH** | Change of character: the first break against the current trend |
| **Order block** (demand / supply zone) | The last opposite-coloured candle at the origin of the move that broke structure |
| **Equilibrium** | 50% of the dealing range. Above it is *premium*, below it is *discount* |
| **PDH/PDL, PWH/PWL, PMH/PML** | Previous day, week and month highs and lows |

## Strategy

1. Follow structure: only buy after a bullish BOS/CHoCH, only sell after a bearish one.
2. Mark the order block that caused the break.
3. Buy from demand zones in **discount**, sell from supply zones in **premium**.
4. Place a limit entry at the zone edge, with the stop beyond the zone (+ buffer) and the target at a fixed R:R (default 1:2).
5. Cancel the order if structure flips, the zone breaks, or it isn't filled within 96 bars.
6. Risk a fixed % of the balance per trade (default 1%).

## Usage

```bash
pip install -r requirements.txt

python -m castimofx demo                       # backtest on synthetic data
python -m castimofx backtest EURUSD_M15.csv    # backtest your own candles
python -m castimofx analyze  EURUSD_M15.csv    # current structure, zones, key levels

# options
python -m castimofx backtest XAUUSD_M15.csv --pair XAUUSD --rr 3 --risk 0.5 --spread 2.5
python -m castimofx backtest GBPJPY_M15.csv --pair GBPJPY --choch-only
python -m castimofx backtest EURUSD_M15.csv --no-discount-filter
```

The CSV needs a time column plus open/high/low/close. Exports from MT4/MT5
(`<DATE>,<TIME>,<OPEN>,...`), TradingView and Dukascopy all work.

## Backtest assumptions (kept conservative)

- Orders placed on a bar's close can only fill from the next bar.
- If the stop and the target are both touched in one candle, the stop counts first.
- The spread is charged on every trade. P&L is in the quote currency.

## Tests

```bash
python -m pytest
```

## Roadmap

- [ ] Connect a broker for paper and then live trading (OANDA API or MetaTrader 5)
- [ ] Higher-timeframe bias (for example, H4 structure filtering M15 entries)
- [ ] Liquidity-sweep confirmation and fair value gaps
- [ ] Session filter (London / New York) and news avoidance
- [ ] Chart output with zones drawn
