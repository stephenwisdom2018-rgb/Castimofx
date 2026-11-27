# Instructions for Claude

## Pull requests
- The repository owner wants pull requests **merged automatically**: after opening a PR for finished work,
  merge it into `main` without asking again (unless checks fail or there is a merge conflict, in which case
  report it instead).

## Replies
- Always include the minimum account balance at 0.01 (biggest $ drop with open trades; safe = 1.5x) when reporting a version. Owner goal: safe at $100.
- Keep replies to the user short and simple.
- Every new test must be run on BOTH versions: "Chosen" and "+Both" (chosen + F-E zone + double bottom $2, normal stops; `research/combo_hold.py`), and shown side by side in a narrow table (owner reads on a phone).

## Project notes
- MT5 Expert Advisors live in `mt5/`, the TradingView indicator in `tradingview/`, the Python backtester in `castimofx/`.
- Run `python -m pytest` before committing Python changes.
- The user tests MT5 code on XAUUSDb (broker suffix `b`) on M15, $1,000 demo account.
- Always report backtest results honestly, including losses.

## Castimofx gold sweep strategy (main project, read first)
- Full rules, final settings, all test results and decisions: `research/SWEEP_RESULTS.md`
- Strategy code: `castimofx/sweep.py`. Backtests: `research/`. Data: `data/` (XAUUSDb M15 2 years, M1 from 26 Aug 2026)
- Student notes with diagrams (Claude Docs): https://claude.ai/artifact/MhcF2HYEdSP8kLX1wkwuBE
- The owner's server time is MT5 HF Markets (UTC+2 in winter); the owner is in Uganda (UTC+3).
- CHOSEN (27 Nov 2026) = "C+3m": chosen version below + one 3-micro SMA 10 re-entry after each stop (2x risk; `research/micro3_reentry.py`): $7,288, 45% win, PF 1.99, min balance $536. Base "C": main (stop $30, small-structure target, RSI re-entries with target = first target + $15) + E-A zone (up to 40 per structure, 20 days, 1 zone re-entry on a 3-candle high break, 2x risk, stacked copies KEPT) + RSI-50 side filter + skip 15:00 & 23:00 + consolidation filters (tight last hour, ADX M15 25-35). 2026 at 0.01: +$6,300, 46% win, PF 2.06, worst drop -17.5%, 3.3 trades/day. Code: `research/more_profit3.py` (zones(40, 20) + mains(sl=30, extra=15)). Owner target: +$20,000 (lot size is the last step) before building the MT5 EA. Funded account rules: 4% daily, 10% max drawdown.
- ON HOLD, remind the owner at each decision: F-E zone option (+$1,176 more, win 42%, PF 1.58; `research/more_trades2.py`).
- ON HOLD #2, remind the owner: double bottom $2 above E (+$1,029, total +$7,329, 41% win, 8 trades/day; `research/strong_base.py`). Maybe for the owner's own account.
- ON HOLD #3, remind the owner: "+ both" with close-on-opposite exit (no stop / +$100 / +$50 stop): +$16.2k / +$14.3k / +$11.0k, win 62-66%, min balance at 0.01 $3,767 / $1,813 / $1,315 (`research/opposite_exit.py`, `research/min_balance.py`).
