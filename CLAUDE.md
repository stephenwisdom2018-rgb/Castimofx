# Instructions for Claude

## Pull requests
- The repository owner wants pull requests **merged automatically**: after opening a PR for finished work,
  merge it into `main` without asking again (unless checks fail or there is a merge conflict, in which case
  report it instead).

## Replies
- ALL tests (Python and MT5) are done at a fixed 0.01 lot before any lot sizing (EA: InpFixedLot=0.01).
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
- CHOSEN (27 Nov 2026) = "C+3m+MZ+FE" ($10,276, 41% win, PF 1.54, min balance $813, safe $1,219): C+3m+MZ plus the F-E zone (`research/micro3_reentry.py` FE list). Previous "C+3m+MZ": base C below + one 3-micro SMA 10 re-entry after each stop (2x risk; `research/micro3_reentry.py`) + 3-micro zone entries (`research/micro3_zone.py`, micro_zone(per=3, g_rsi=32)): $8,509, 44% win, PF 1.88, min balance $552 (safe $828). Base "C": main (stop $30, small-structure target, RSI re-entries with target = first target + $15) + E-A zone (up to 40 per structure, 20 days, 1 zone re-entry on a 3-candle high break, 2x risk, stacked copies KEPT) + RSI-50 side filter + skip 15:00 & 23:00 + consolidation filters (tight last hour, ADX M15 25-35). 2026 at 0.01: +$6,300, 46% win, PF 2.06, worst drop -17.5%, 3.3 trades/day. Code: `research/more_profit3.py` (zones(40, 20) + mains(sl=30, extra=15)). Owner target: +$10,000 at 0.01 before lot sizing, then +$20,000 with lot size before building the MT5 EA. Funded account rules: 4% daily, 10% max drawdown.
- F-E zone: ADOPTED into the chosen version on 27 Nov 2026 (no longer on hold).
- FINAL LOT PLAN (27 Nov 2026, modes CORRECTED): 0.01 per $2,000 + half lot after 3 losses in a row; small accounts: $200-399 = C+3m+MZ, 1 trade at a time, stops <= $15 ($820/yr); $400-999 = C without copies ($4,378/yr); $1,000+ full 0.01; $100 accounts not supported (minimum $200). Prop $100k 0.07. See SWEEP_RESULTS "CORRECTION".
- ON HOLD #2, remind the owner: double bottom $2 above E (+$1,029, total +$7,329, 41% win, 8 trades/day; `research/strong_base.py`). Maybe for the owner's own account.
- ON HOLD #3, remind the owner: "+ both" with close-on-opposite exit (no stop / +$100 / +$50 stop): +$16.2k / +$14.3k / +$11.0k, win 62-66%, min balance at 0.01 $3,767 / $1,813 / $1,315 (`research/opposite_exit.py`, `research/min_balance.py`).
- ON HOLD #4 (calm-market options, tested on 2025+2026): Robust (2025 $1,957 / 2026 $8,527) and Max (2025 $4,380 / 2026 $10,753, no consolidation filter, 30-46 trades/day, safe balance ~$2,000) (`research/both_eval.py`). Owner kept C+3m+MZ+FE because 2026 matters most; switch if gold calms down.
