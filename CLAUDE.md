# Instructions for Claude

## Pull requests
- The repository owner wants pull requests **merged automatically**: after opening a PR for finished work,
  merge it into `main` without asking again (unless checks fail or there is a merge conflict, in which case
  report it instead).

## Replies
- Keep replies to the user short and simple.

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
- CHOSEN (27 Nov 2026): main + E-A zone (up to 20 per structure, 20 days, 1 zone re-entry on a 3-candle high break, 2x risk) + RSI-50 side filter + small-structure target + skip 15:00 & 23:00 + consolidation filters (tight last hour, ADX M15 25-35). 2026 at 0.01: +$5,671, 45% win, PF 2.04, worst drop -17.5%. Code: `research/more_trades.py`. Owner target: +$20,000 (lot size is the last step) before building the MT5 EA.
