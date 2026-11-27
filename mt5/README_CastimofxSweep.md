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
Everything is automatic. The only choice is the **account type**.
| Input | Meaning |
|---|---|
| Account type | **Normal** (default) or **Prop** |
| Prop start balance | Prop only. The lot is set automatically: 0.07 per $100,000 |
| Prop daily stop % / max drawdown stop % | Prop only: closes everything and stops for the day at the daily %, stops completely at the drawdown % |
| Magic number | Change it only if you run several copies on one account |
| History replayed | Days of M1 the bot replays at start (31) |
| Trading on | false = the bot only logs signals (good for a first check) |

Normal accounts: lot is automatic, with no maximum. Small-account modes below $1,000, then the lot grows with the
balance but more slowly on big accounts (less risk on money already made); half lot after 3 losses in a row.
| Balance | Lot |
|---|---|
| $1,000 - $3,999 | 0.01 |
| $4,000 / $6,000 / $10,000 | 0.02 / 0.03 / 0.05 |
| $30,000 / $50,000 | 0.10 / 0.15 |
| $100,000 / $250,000 / $500,000 | 0.21 / 0.40 / 0.71 |

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
- Flip: when a main or zone trade hits its stop, the bot trades the other way at once (stop = half the stopped
  trade's risk, target = 1.5x that stop). From $200 up and on prop accounts (not in the $100 mode).

## Differences from the Python backtest (expected small)
- The backtest ran several main-trade tracks in parallel (one per target size); the EA runs one main track.
- Filters for pending orders are checked on the last closed bar (the backtest used the trigger bar's close).
- Real fills, spread and slippage differ from bar-based fills.
Run it on **demo** first and compare with the backtest before real money.
