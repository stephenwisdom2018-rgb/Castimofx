# Castimofx Sweep EA (`CastimofxSweep.mq5`)

The MT5 bot for the chosen strategy **C+3m+MZ+FE** (see `research/SWEEP_RESULTS.md`).

## Install
1. MT5 -> File -> Open Data Folder -> `MQL5/Experts` -> copy `CastimofxSweep.mq5` there.
2. Open MetaEditor (F4), open the file, press **Compile** (F7). Send any errors to Claude.
3. In MT5, open an **XAUUSDb** chart (any timeframe). The bot always works on M1 bars.
   Open an M1 chart once so MT5 downloads at least 31 days of M1 history.
4. Drag **CastimofxSweep** from the Navigator onto the chart, tick **Allow Algo Trading**,
   set the **Inputs**, press OK. The Experts tab shows "replayed ... M1 bars ... Live."

## Inputs
| Input | Meaning |
|---|---|
| Account type | **Normal** or **Prop** |
| Lot mode | **Auto**: small-account modes, then 0.01 per $2,000 with half lot after 3 losses; **Fixed**: always the fixed lot |
| Fixed lot | Used in Fixed mode and on Prop accounts (prop $100k: 0.07) |
| Balance per 0.01 lot | Auto: $2,000 per 0.01 from $2,000 (0.01 below that) |
| Half lot after N losses | Auto: halve the lot after N losing trades in a row (0 = off) |
| Maximum lot | Cap per trade (default 0.20) |
| Small-account modes | Auto: below $200 = $100 mode, $200-399 = $200 mode, $400-999 = $400 mode, $1,000+ = full |
| Prop start balance / daily stop % / max drawdown stop % | Prop only: closes everything and stops for the day at the daily %, stops completely at the drawdown % |
| Magic number | Change it if you run several copies on one account |
| History replayed | Days of M1 the bot replays at start to remember structures and zones (31) |
| Trading on | false = the bot only logs signals (good for a first check) |

## Account modes (Auto lot mode, normal account)
| Balance | Trades taken | Max open | Stop cap |
|---|---|---|---|
| below $200 | main, E-A zone, 3-micro after those, MZ | 1 | $10 |
| $200-399 | same | 1 | $15 |
| $400-999 | main + E-A zone (no stacked copies) | - | - |
| $1,000+ | everything (main, E-A, F-E, 3-micro, MZ) | - | - |
The bot keeps trading on any balance; it only skips a trade when the free margin is too small.

## How it trades
- Main, zone and zone re-entry trades use **pending stop orders** at the level (H) while the setup is armed;
  they are refreshed every minute and removed when the setup ends or a filter blocks it.
- 3-micro re-entries and MZ trades are **market orders** right after the signal candle closes.
- Filters: RSI 14 on the right side of 50, no new trades at 15:00 and 23:00 server time, no trades when the
  last hour is tight (< 0.6x normal) or when ADX(14) on M15 is between 25 and 35.
- A new main trade closes an open main trade in the other direction.

## Differences from the Python backtest (expected small)
- The backtest ran several main-trade tracks in parallel (one per target size); the EA runs one main track.
- Filters for pending orders are checked on the last closed bar (the backtest used the trigger bar's close).
- Real fills, spread and slippage differ from bar-based fills.
Run it on **demo** first and compare with the backtest before real money.
