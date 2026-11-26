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

## Blind check, 6-8 Apr 2026: "takeout" structure (`structure='takeout'`)
The code missed the owner's buy trend on 6 Apr: a small lower high (4,667) broke its strict 6-swing staircase, so
sell stayed boss and the code sold twice into stop losses. New rule: a high only counts if it takes out the previous
counted high (lows mirrored); two highs taken = buy bias. With it, the code finds the owner's Tue 7 Apr buys
(4,666.60 at 01:02 and 4,661.40 at 19:02). Full 2026, base 0.01:
| Structure | No re-entry | RSI re-entry | Mixed, alternating |
|---|---|---|---|
| Strict 6-swing (old) | +$64 (drop -$616) | +$318 (-$686) | +$514 (-$1,458) |
| **Takeout** | +$16 (-$584) | **+$266 (-$339)**, 4 of 11 months lose | +$167 (-$1,301) |
| Takeout + H after G | +$36 (-$584) | +$286 (-$339) | +$126 (-$1,301) |

## RSI takeout exception (`takeout_counts=True`)
Owner's rule: a high counts at RSI 68 after a low at 32. Exception: a move that passes a previous high whose RSI
reached 68 counts as a high even without reaching 68 itself (lows mirrored). Full 2026, base 0.01:
| Rules | No re-entry | RSI re-entry | Mixed, alternating |
|---|---|---|---|
| Strict + exception | +$114 (drop -$626) | +$437 (-$559) | +$605 (-$1,171) |
| Takeout + exception | +$16 (-$584) | +$237 (-$373) | +$308 (-$1,221) |
| Takeout (for reference) | +$16 (-$584) | +$266 (-$339) | +$167 (-$1,301) |
Small changes, and still no strong edge across the year. The 3rd-low reversal rule is not coded yet.

## 3rd-low rules (full 2026, base 0.01)
Owner's counting: from F, G1 takes a low and H forms. If price goes below G1 without breaking H, H becomes F and the
new low is G2. No buy until a low takes out G2 (the 3rd low); then any breakout of the most recent high is a buy.
| Rules | No re-entry | RSI re-entry | Mixed, alternating |
|---|---|---|---|
| Strict + exception (reference) | +$114 (drop -$626) | +$437 (-$559) | +$605 (-$1,171) |
| Strict + exception + G2 must be swept | -$260 (-$480), 177 trades | +$82 (-$454) | -$120 (-$965) |
| Takeout + exception + G2 must be swept | -$490 (-$610), 123 trades | +$211 (-$279) | +$156 (-$596) |
| Strict + exception + draft reversal after 3 lows | -$103 (-$784) | +$169 (-$673) | +$383 (-$1,151) |
Requiring G2 to be swept halves the number of trades and does not improve results.

## BREAKTHROUGH: cancel the setup when G is swept (`cancel_on_g_sweep=True`)
Owner's rule: if price goes below G1 before breaking H, the setup is invalid (no second G). Wait for a fresh setup:
a sell staircase that sweeps a high, or 2 new higher highs then a sweep of a low.
Full 2026 (Jan 1 - Nov 25, Aug 1-25 missing), base 0.01 on $1,000, with `structure='takeout', takeout_counts=True`:
| Re-entry | Net | Worst drop | Trades | Losing months |
|---|---|---|---|---|
| No re-entry | +$40 | -$200 | 120 | 4 of 11 |
| **RSI re-entry, all 0.01** | **+$861** | **-$201** | 167 | 4 of 11 |
| Mixed re-entry, alternating | +$1,510 | -$550 | 199 | 4 of 11 |
By month (RSI re-entry): Jan -$69, Feb +$226, Mar +$132, Apr -$81, May +$33, Jun +$389, Jul -$66, Aug -$40,
Sep +$76, Oct +$129, Nov +$133. Trading both sides (no boss filter) gives almost the same result.
About 0.8 trades a day.
Tested: keeping the cancelled F-G1-H-G2 as an opposite setup (`flip_on_cancel=True`). With the boss filter it made
RSI +$755 (drop -$247) and mixed +$701 (-$1,002); trading both sides it made RSI +$48 and mixed -$303. **Waiting for a
fresh setup stays best.**
Bigger targets on the fresh-setup version ($20 stop, RSI re-entry): TP $20 +$861 (drop -$201), $40 +$741 (-$252),
$60 +$706 (-$405), $80 +$632 (-$487), $100 +$871 (-$379). **$20 stays best.**
G2 memory (`research/g2_memory_test.py`): after a cancelled setup, buy once when price first returns to G2 (sells
mirror it), with a $20 stop and $20 target. Over full 2026: 134-152 trades, 41-42% win, -$440 to -$560. **Not used.**
A-level memory (`research/a_level_test.py`): remember A of every structure. On a return to A, trade a small G-H-I
inside the zone ($20/$20, once per level). Over full 2026: only 14-21 trades, 43% win, -$40 to -$60. Not used.

## A/E zone memory (`research/ae_zone_test.py`): owner's idea, WORKS
Every completed structure A-F is remembered. When price comes back, a low that sweeps into the zone is G, then a
small H and I (3-candle swings; I not below G), and a break of H is a buy. $20 stop, $20 target, once per
structure, 30-day memory. Sells mirror it. Full 2026, 0.01 lot:
| G zone | RSI swings | Small swings |
|---|---|---|
| below E | -$60 (97 trades, 48% win) | +$500 (125 trades, 60% win, drop -$140) |
| **between A and E** | +$20 | **+$520 (124 trades, 60% win, drop -$120)** |
| below A | -$220 | +$180 (95 trades, drop -$320) |
Zone A-E by month: Jan +60, Feb +20, Mar +20, Apr -40, May +40, Jun 0, Jul +100, Aug +60, Sep +200, Oct +80, Nov -20.
**Combined with the main strategy** (fresh setup, RSI re-entry, 0.01): **+$1,381, worst drop -$221, 2 of 11 months
losing** (Jan -$9, Apr -$121).

## Entry search on A-F structures (`research/entry_search.py`)
80 entry variants were chosen on Jan - Jun 2026 and checked on Jul - Nov 2026 (unseen). Every one of the top 15 was
also profitable on the unseen months. Best:
- G sweeps into the zone **between E and A**; small H and I (3-candle swings); memory 3 days
- Entry: wick break of H. **Stop $1 below G** (minimum $5). **Target 2x the risk.**
- Jan - Jun: 65 trades, 45% win, **+$636**, worst drop -$149. Jul - Nov (unseen): 47 trades, 51% win, **+$311**,
  worst drop -$64. Total about +$947 at 0.01.
Reversal indicators as extra filters on this entry (`research/indicator_filter.py`): RSI divergence, stochastic cross,
engulfing / pin bar, MACD, Bollinger re-entry and volume spike. None beat "no filter" (+$636 / +$311). They removed
good trades along with bad ones. **No extra indicator.**

### More trades from the same structures (`research/zone_multi.py`), full 2026, 0.01 lot per trade
| Zone trades per structure (memory) | Zone alone | Zone + main strategy |
|---|---|---|
| 1 (3 days) | +$947, drop -$163, 0.5/day | **+$1,808, drop -$236, 1.3/day, 2 of 11 months losing** |
| 3 (3 days) | +$840, drop -$257 | +$1,701, drop -$344, 1.9/day |
| 10 (10 days) | +$1,607, drop -$424 | **+$2,468, drop -$361, 3.2/day, 1 of 11 months losing** |
| no limit (30 days) | +$2,174, drop -$663 | +$3,035, drop -$606, 4.4/day |
Trades can overlap (several open at once). The limits were picked on the same year, so treat these as optimistic.

### Owner's breakout-retest entry (`research/retest_entry.py`)
After H breaks, wait for price to come back to H or below with RSI hooking at 32 or below, then buy the break of
the last 3-candle high. Invalid below G. Full 2026, 0.01 lot:
| Stop / target, buys per H | Jan - Jun | Jul - Nov (unseen) |
|---|---|---|
| **$20/$20, 1 per H** | **63 trades, 56% win, +$140, drop -$80** | **43 trades, 56% win, +$100, drop -$80** |
| $20/$20, up to 3 | -$260 (drop -$420) | +$80 |
| below G, 2x target, 1 | -$471 (drop -$1,036) | +$385 |
Very steady (worst drop -$80), but small profit, about +$240 a year at 0.01.

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

## Breakout-retest v2: 3 white soldiers near a moving average (`research/soldiers_entry.py`)
Owner's correction: the entry is not a pivot break. After the H break, price comes back to H with RSI 30/32 hooked,
then buy when 3 white soldiers (3 bullish candles, each closing higher) form "inside the moving average".
Buy again each time price comes back to H, as often as possible, until an opposite trend forms or price goes below G.
Stop $20, target $20. The MA period and the meaning of "inside" were not given, so variants were tested.
| RSI | MA | soldiers | Jan-Jun | Jul-Nov |
|---|---|---|---|---|
| 32 | EMA50 | below MA | 285 tr, 52%, +$180, drop -$180 | 152 tr, 53%, +$200, drop -$320 |
| 32 | none | - | 297 tr, 51%, +$100, drop -$220 | 157 tr, 55%, +$300, drop -$240 |
| 32 | EMA20 | MA touches 1+ | 270 tr, 50%, -$40 | 155 tr, 55%, +$300 |
| 30 | EMA20 | MA touches all 3 | 136 tr, 46%, -$240 | 87 tr, 49%, -$20 |
About 2-3 trades/day, but only about 50% wins at 1:1, so profit is thin; v1 (1 per H, pivot break) was steadier.
Waiting for the owner's MA period and the exact meaning of "inside the MA".
