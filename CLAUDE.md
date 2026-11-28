# Instructions for Claude

## Pull requests
- The repository owner wants pull requests **merged automatically**: after opening a PR for finished work,
  merge it into `main` without asking again (unless checks fail or there is a merge conflict, in which case
  report it instead).

## Replies
- ALL tests (Python and MT5) are done at a fixed 0.01 lot before any lot sizing (EA: InpFixedLot=0.01).
- Always include the minimum account balance at 0.01 (biggest $ drop with open trades; safe = 1.5x) when reporting a version. Owner goal: safe at $100.
- Keep replies to the user short and simple.
- Owner understands best this format: a long narrow table (e.g. every week: Week | Chosen | +Both), then a small Totals table (incl. min balance + safe), then 2-3 short "What it shows" bullets.
- Every new test must be run on BOTH versions: "Chosen" and "+Both" (chosen + F-E zone + double bottom $2, normal stops; `research/combo_hold.py`), and shown side by side in a narrow table (owner reads on a phone).

## Project notes
- MT5 Expert Advisors live in `mt5/`, the TradingView indicator in `tradingview/`, the Python backtester in `castimofx/`.
- Run `python -m pytest` before committing Python changes.
- The user tests MT5 code on XAUUSDb (broker suffix `b`) on M15, $1,000 demo account.
- Always report backtest results honestly, including losses.

## Castimofx gold sweep strategy (main project, read first)
- Full rules, final settings, all test results and decisions: `research/SWEEP_RESULTS.md`
- Strategy code: `castimofx/sweep.py`. Backtests: `research/`. Data: `data/` (XAUUSDb M15 2 years; M1 2026 in ONE continuous file `data/XAUUSDb_M1_2025-12_2026-11.csv` = Dec 2025 warm-up + 1 Jan-25 Nov 2026; use CASTIMO_FILES=that file)
- Student notes with diagrams (Claude Docs): https://claude.ai/artifact/MhcF2HYEdSP8kLX1wkwuBE
- The owner's server time is MT5 HF Markets (UTC+2 in winter); the owner is in Uganda (UTC+3).
- CHOSEN (27 Nov 2026) = "C+3m+MZ+FE" ($10,276, 41% win, PF 1.54, min balance $813, safe $1,219): C+3m+MZ plus the F-E zone (`research/micro3_reentry.py` FE list). Previous "C+3m+MZ": base C below + one 3-micro SMA 10 re-entry after each stop (2x risk; `research/micro3_reentry.py`) + 3-micro zone entries (`research/micro3_zone.py`, micro_zone(per=3, g_rsi=32)): $8,509, 44% win, PF 1.88, min balance $552 (safe $828). Base "C": main (stop $30, small-structure target, RSI re-entries with target = first target + $15) + E-A zone (up to 40 per structure, 20 days, 1 zone re-entry on a 3-candle high break, 2x risk, stacked copies KEPT) + RSI-50 side filter + skip 15:00 & 23:00 + consolidation filters (tight last hour, ADX M15 25-35). 2026 at 0.01: +$6,300, 46% win, PF 2.06, worst drop -17.5%, 3.3 trades/day. Code: `research/more_profit3.py` (zones(40, 20) + mains(sl=30, extra=15)). Owner target: +$10,000 at 0.01 before lot sizing, then +$20,000 with lot size before building the MT5 EA. Funded account rules: 4% daily, 10% max drawdown.
- OWNER CHOICE (28 Nov 2026): Robust + quality hours + day rule (stop new trades at +$20 day profit, or at break-even after a red start; restart at midnight), no flip, no copy/max-open limits. 2026 $7,325 / 2025 $474, max drawdown with open trades $435 / $494 (safe ~$650-$740). Not in the EA yet (planned v1.18).
- EA v1.17 (28 Nov 2026): InpQuality = no new trades 08:00-13:59 server (London morning loses in 2025+2026): 2026 Chosen $7,651 (min $845) / +Both $8,578 (min $1,007); 2025 $138 / $132.
- EA v1.16 (28 Nov 2026): input InpVersion = Chosen / +Both / +Both without F-E. TRUE 2026 at 0.01 (one continuous file, real fills): Chosen $7,043 (min $880), +Both $7,760 (min $1,026), +Both no F-E $6,774 (min $690). Rejected 28 Nov: small TP/SL, basket/grid (limits, stops, $1-$5), crash filters, day rules, reverse trading.
- FINAL LOT PLAN (27 Nov 2026, modes CORRECTED): 0.01 per $2,000 + half lot after 3 losses in a row; small accounts: $200-399 = C+3m+MZ, 1 trade at a time, stops <= $15 ($820/yr); $400-999 = C without copies ($4,378/yr); $1,000+ full 0.01; $100 accounts not supported (minimum $200). Prop $100k 0.07. See SWEEP_RESULTS "CORRECTION".
- ON HOLD #2, remind the owner: double bottom $2 above E (+$1,029, total +$7,329, 41% win, 8 trades/day; `research/strong_base.py`). Maybe for the owner's own account.
- ON HOLD #3 close-on-opposite: REJECTED 28 Nov on true data (2026 +$1k-$2.9k with min balance $1.7k-$12k; see SWEEP_RESULTS).
- ON HOLD #4 re-tested 28 Nov on true data + quality hours: Robust 2026 $6,902 / 2025 $225, min $549 (safe $823), worst day -$222; Max (CASTIMO_NO_CONS=1) 2026 $7,868 / 2025 $1,379, min $1,472 (`research/onhold_exact.py`). Not in the EA yet.
