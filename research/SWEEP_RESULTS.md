# Castimofx gold sweep strategy: status and results

Student notes (with diagrams): https://claude.ai/artifact/MhcF2HYEdSP8kLX1wkwuBE

## Final settings (chosen by the owner and by the tests)
- XAUUSDb, M1, RSI 14 with lines at 68 / 32 (a high counts at RSI >= 68, a low at <= 32)
- Sweep tolerance $1 (broker feeds differ by cents)
- A sweep is always required: G takes out E or the last small (5-candle) low before F
- Entry: a wick breaks H (sell = mirror)
- Stop $20, target $20
- After a stop loss: wait for a small high then a low (3-candle swings, the owner's choice),
  re-enter on the break of that high, aiming for the original target + $10, up to 5 re-entries.
  Alternative kept as a switch: RSI-confirmed swings (`pivot=0`): +$701 total, max drawdown about 8%
  instead of about 17%.
- An opposite signal closes the open trade and flips
- Unfinished trades (against the boss trend): OFF

Code: `castimofx.sweep.find_signals(df, tol=1.0, minor_e=5)` then
`simulate_reentry(df, [s for s in signals if s.with_boss], 20, 20, 10, 5, spread)`.

## Results on 0.01 lot, $1,000 account (spread from the MT5 export)
| Period | Trades/day | Net | Max drawdown | Losing weeks |
|---|---|---|---|---|
| 28 Aug - 30 Sep 2026 (not used for tuning) | 1.7 | +$342 | 17.2% | 3 of 6 |
| 1 Oct - 25 Nov 2026 (used for tuning) | 1.9 | +$607 | 15.8% | 1 of 9 |
| **Total, about 3 months** | | **+$949** | about 17% | 4 of 15 |

Other entry options tested (kept in the code as switches): I-sweep entry (`i_sweep=3,
i_sweep_level='highest'`, +$937 total), two-path rule (`hybrid=True`, +$800), both entries
together (+$859). Left-behind H levels as stop orders: 71% TP rate vs 62% random on 28 trades
(`research/left_h_test.py`), not proven yet.

## Stop / target comparison ($20 stop, 28 Aug - 25 Nov, 0.01 lot)
| Target | Net | Max drawdown | Losing weeks |
|---|---|---|---|
| **$20 (chosen)** | **+$950** | 17% | 4 of 15 |
| $30 | +$882 | 18% | 6 of 15 |
| $40 | +$905 | 20% | 6 of 15 |

Stop sizes compared with a $20 target (same period): $10 stop +$951 (119 stop losses), $15 stop +$945,
**$20 stop +$950 (61 stop losses, kept)**, $30 stop +$835, $40 stop +$727 (deepest drawdown).

$5 stop / $20 target: +$881, but 205 stop losses out of 261 trades, and live slippage would hurt it. Not used.
Break-even (stop to entry at +$5 / +$10 / +$15): +$415 / +$385 / +$514, against +$950 without it. With re-entry after a break-even exit: +$539 / +$800 / +$822, and the Sep drawdown worsened to 20-25%. **No break-even.**

Boss-trend filter stays on: trades against the boss trend are skipped (owner's decision, 26 Nov 2026).

## Account modes (owner's decision, 26 Nov 2026)
Results for 1 Oct to 25 Nov 2026 (`research/grid_stack_test.py`). Each position is 0.01 lot per $1,000. All positions share the $20 stop and close at the trade's target.
| Mode | Positions | Sizing | Net | Max drawdown | Worst day |
|---|---|---|---|---|---|
| Personal | 10, $1 apart | full | +367% | about 45% from peak | about 63% of start |
| Clients | 1 position (no stacking) | 0.01 lot per $500 of balance (0.01 up to $500, 0.02 up to $1,000, 0.03 at $1,500, 0.12 at $6,000) | about +120% | about 32% | |
| Prop firm | 10, $1 apart | 10% of balance | +37% | 16.5% of account | 6.3% |
| (Prop at 6%, for reference) | 10, $1 apart | 6% of balance | +22% | 9.9% | 3.8% |
Warning: at 10% sizing, the prop mode would break typical prop limits (10% total, 5% daily). Check the firm's rules.

## Re-entry limit (client account, $1,000 at 0.02 lot, one trade at a time)
| Max re-entries | Total, 28 Aug - 25 Nov | Worst drop |
|---|---|---|
| 1 | +$1,465 | 42% (Sep) |
| 2 | +$1,327 | 58% (Sep) |
| **5 (kept)** | **+$1,899** | **31%** |

## Other checks (kept the original plan)
- News filter (60 minutes around US news at 15:30 / 17:00 server time and FOMC): it cut profit and did not reduce drawdown. No filter.
- Bigger target for trades that flip the position: $30 / $40 / $60 gave $940 / $990 / $931 against $950, from only 7 flips in 3 months. Kept $20.

## Re-entry lot pattern (owner's decision: alternate)
Base 0.01 per $1,000, 28 Aug - 25 Nov 2026:
| Lots: first entry, then re-entries | Net | Max drawdown |
|---|---|---|
| all 0.01 | +$950 | 16-17% |
| 0.01, then 0.02 for every re-entry | +$1,739 | 24-26% |
| **0.01, then 0.02, 0.01, 0.02, 0.01, 0.02 (alternate, kept)** | **+$1,828** | **19-20%** |
| 0.01, 0.02, then 0.01 | +$1,481 | 15-21% |
| double every re-entry (0.02, 0.04, ...) | +$5,079 | 97%: do not use |

Also tested and rejected: a first entry as a limit order $5 or $10 below (+$532 to +$744),
and re-entering only when price is back at the first entry (+$354 to +$656).
Friday rules (alternating lots): as now +$1,828; no new trades after Fri 20:00 +$1,675; that plus closing at Friday's close +$1,521, with no drawdown improvement. **Kept: hold over the weekend.**
Swap, commission and slippage are not included.

## Out-of-sample test, Jan - Mar 2026 (IMPORTANT)
Final plan (mixed re-entry, alternating lots, base 0.01), XAUUSDb M1, 1 Jan - 1 Apr 2026 (`research/final_plan_test.py`):
| Month | Trades | Net | Worst drop |
|---|---|---|---|
| Jan | 40 | -$38 | -$180 |
| Feb | 48 | -$32 | -$240 |
| Mar | 53 | -$172 | -$430 |
| **Total** | 143 | **-$301** | **-$490** |
Losing weeks: 9 of 13. First entries alone were break-even (50% hit TP at 1:1); the re-entry chains lost.
Gold rose from 4318 to 4748 in Jan - Mar, while Aug - Nov was a strong fall (4661 to 3447), where sells made most
of the profit. The edge seen in Aug - Nov looks market-dependent. Do not put client money on it until May - Aug is
tested and the difference is understood.

## Full 2026 test (Jan 1 - Nov 25, missing Aug 1-25), base 0.01 on $1,000
| Period | No re-entry | Micro re-entry, all 0.01 | Final plan (mixed, alternating) |
|---|---|---|---|
| Jan - Mar | +$20 | -$434 | -$301 |
| Apr - Jul | -$316 | -$398 | -$748 (Apr alone -$811) |
| Aug 26 - Nov 25 | +$360 | +$938 | +$1,563 |
| **All 2026** | **+$64** (worst drop -$616) | **+$106** (-$1,188) | **+$514** (-$1,458) |
**Verdict:** across 2026 the coded rules have no reliable edge. The profit came from the Aug - Nov fall, and the
worst drops would have wiped a $1,000 account at 0.01. Not ready for clients. Next: compare the owner's real trades on
losing months (for example April 2026) with the code's trades, to find where the code reads the rules differently.

## Blind check, 25 Feb 2026, and two fixes (full 2026)
The owner's trades on 25 Feb: SELL at 5,180.5 (11:03, after the 5,210 high) and BUY at 5,191.5 (16:56). The code
missed the sell, skipped the buy (against the boss trend), and bought the break of the first F at 03:14 instead.
Fix 1 (`h_after_g=True`: H must form after G) and fix 2 (both sides, no boss filter), full 2026 at base 0.01:
| Rules | No re-entry | RSI re-entry | Mixed, alternating |
|---|---|---|---|
| Old | +$64 | +$318 | +$514 |
| Fix 1 | +$84 | +$338 | +$472 |
| Fix 2 | -$258 | -$149 | -$22 |
| Fix 1 + 2 | -$238 | -$129 | -$64 |
Fix 1 changes very little. Fix 2 makes results worse. The owner's sell after a sweep of the high in a buy trend
is still not coded.

## Final plan (saved 26 Nov 2026, owner's decision)
- Re-entry swings: **mixed**. The 1st re-entry uses micro (3-candle) swings; the 2nd and later use RSI-confirmed swings (68/32).
  Code: `simulate_reentry(..., pivot=3, later_pivot=0)`.
- Lots: re-entries alternate double / normal (first entry L, then 2L, L, 2L, L, 2L).
- Base lot L = the bigger of:
  - the cushion rule: 0.01 until the balance is $100 above the client's own starting balance, then 0.02
  - the scaling rule: 0.01 per $500 of balance ($1,000 = 0.02, $1,500 = 0.03, $3,000 = 0.06)
- Re-entry results with alternating lots at base 0.01, 28 Aug - 25 Nov: micro +$1,828 (worst drop $286);
  RSI +$1,043 ($100); **mixed +$1,643 ($160)**.
- Lot rule, single run from 28 Aug: $200 -> $5,461 (dipped to $60 first); $1,000 -> $10,576 (worst drop 19%).
  $100 accounts were wiped out on 7% of start days, including a start on 28 Aug. Results are optimistic
  (one mostly winning period, compounding, no swap, commission or slippage).

Fast-market filters tested and **not used** (mixed re-entry, alternating lots): pausing with trade memory on
speed ($10 in 5 min, $15 or $20 in 10 min) or on ATR (2x or 2.5x normal) made +$1,436 to +$1,569, against +$1,643
without a filter. Skipping trades against the M15 or H1 EMA50 trend made +$1,523 or +$1,001. None reduced the worst
drop (-$160).

## MT5 bot design notes (owner's decisions)
- On start (or after a VPS restart), the bot loads the last 2-3 days of M1 and replays the rules, so it knows the
  boss trend, swings, sweeps and the current G / H / I. It then takes any setup that triggers after it starts.
- Missed trades (triggered before the bot started, stop and target not hit yet), 0.01 lot, original stop and target:
  - in drawdown up to $10: join at market (tested: $0-5 averaged +$3.49 per join, $5-10 averaged +$1.97)
  - in drawdown more than $10: skip (tested: $10-15 averaged -$0.70, $15-20 averaged -$2.50)
  - in profit: wait; join only if price pulls back into the $0-10 drawdown zone, otherwise skip
  - if a joined trade hits its stop, the normal re-entry chain follows
- If a missed trade already hit its stop and a re-entry is waiting, the bot takes that re-entry at **0.01**
  (no real loss to recover), aiming for the original target + $10.

## Next steps
1. Owner exports XAUUSDb M1 from 1 Jan to 26 Aug 2026; run the final settings on it unchanged.
2. Then build the MT5 Expert Advisor with the final settings, test in the Strategy Tester, then demo.
