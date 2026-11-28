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

## Reversal entry (`research/reversal_entry.py`)
Owner's rule: clean A-F, G sweeps the most recent low. Buy as soon as price comes back to the swept level while RSI is
68+ (hooked), with no breakout needed. Stop $20, target $20. If stopped out below G, the next entry is at G with RSI 68+.
Sells mirror. `find_signals(g_events=[])` now records each G sweep as (direction, swept level, G, G bar, confirm bar).
| zone | RSI bars | RSI | per G | Jan-Jun | Jul-Nov |
|---|---|---|---|---|---|
| $2 | 3 | 70 | 1 | 57 tr, 47%, -$60, drop -$220 | 36 tr, 67%, +$240, drop -$60 |
| $2 | 1 | 68 | 1 | 110 tr, 44%, -$280 | 58 tr, 59%, +$200 |
| $5 | 1 | 70 | 3 | 196 tr, 40%, -$800 | 98 tr, 62%, +$480 |
Promised 80%+ was not reached: 59-67% in Jul-Nov, but only 37-48% in Jan-Jun, and about 0.5 trades/day.
Next step: compare with the owner's own example days to find what the code reads differently.

## Reversal entry v2: the level follows the newest swept low (`research/reversal_follow.py`)
If G1 is taken and G2 forms, the buy level becomes G1. If price stops on the way and sweeps another low, the level
becomes that swept low. Buy only inside the zone, with RSI 68+. Stop and target $20.
Best: zone $5, RSI 68, 1 bar, wait 3 days: Jan-Jun 245 tr, 52%, +$180, drop -$440 | Jul-Nov 97 tr, 61%, +$420, drop -$140.
Other variants: 45-63% wins. Still far from the owner's 80%+ and 2-4 trades/day, so the code probably reads the setup
differently. We need the owner's example trades to compare.

## Reversal entry v3: always the most recent low taken out, no time limit (`research/reversal_recent_low.py`)
Active from a buy G sweep until an opposite trend forms (a sell G sweep or a sell signal). The level is the most recent
low price took out (RSI swing lows, or 3-candle lows). Buy in the zone with RSI 68+. Stop and target $20.
Results: 33-57% wins, 1.1-1.5 trades/day. Best (RSI lows, $5 zone, 68): Jan-Jun 118 tr, 47%, -$160 | Jul-Nov 88 tr, 57%, +$240.
Not better than v2. We need the owner's real example trades to see what differs.
- With "RSI 32 must" added (the sweep below the low must reach RSI 32, then the return to the level needs RSI 68+):
  RSI lows, $5 zone: Jan-Jun 79 tr, 44%, -$180 | Jul-Nov 80 tr, 57%, +$240. No better. 3-candle lows give almost no trades.

## Owner's decision (26 Nov 2026): CHOSEN STRATEGY = main + E-A zone (up to 10 per structure)
"Our zone works. Only entries. We are taking this one now. It's better than all of them."
- Main strategy: takeout structure, RSI takeout exception, cancel on G sweep, RSI re-entries.
- Plus zone entries: G sweeps into the zone between E and A; small H and I (3-candle swings); wick break of H;
  stop $1 below G (min $5); target 2x risk; up to 10 trades per structure; structure memory 10 days.
- Full 2026 at 0.01 lot: +$2,468, worst drop -$361, 3.2 trades/day, 1 of 11 months losing (`research/zone_multi.py`).
- The retest, soldiers and reversal entries tested above are NOT used.
- Next: build the MT5 EA for this combination.

## Lot sizing on the chosen combination (`research/lot_sizing.py`)
Main + E-A zone (up to 10 per structure), 686 trades, 1 Jan - 25 Nov 2026. The balance grows as trades close
(closed trades only, so the real floating drop is a bit bigger).
| Start | Rule | End balance | Worst drop | Lowest balance |
|---|---|---|---|---|
| $100 / $200 | any rule | wiped out | | |
| $500 | fixed 0.01 | $2,968 | -53% | $245 |
| $500 | owner's rule (cushion + 0.01 per $500 + alternating re-entries) | $12,493 | -71% | $150 |
| $1,000 | fixed 0.01 | $3,468 | -27% | $745 |
| $1,000 | 0.01 per $1,000 | $5,349 | -27% | $745 |
| $1,000 | 0.01 per $500 | $8,143 | -59% | $738 |
| $1,000 | owner's rule | $12,282 | -65% | $644 |
The early-2026 loss (about -$255 at 0.01) wipes out $100 and $200 accounts. The safest growth is 0.01 per $1,000,
with a $1,000 minimum.

## Losing-trade traits (`research/loser_traits.py`, trades in `research/loser_traits_trades.csv`)
Every trade of the chosen combination got traits at entry: main/zone, buy/sell, nth trade in the structure, stop size,
hour, weekday, volatility (ATR vs normal), RSI, H1/M15 EMA50 trend, last-hour move, day range.
**No trait loses money in both halves.** Losers look like winners, so there is no clean "avoid this" pattern.
Weak in Jan-Jun only: zone stops under $15, RSI 32-50 at entry, price moving against the trade in the last hour, quiet market.
Strong in both halves: stop over $20 (45-50% win), RSI 68+ at entry (buys; 32- for sells), last hour moving $10+ the trade's way.
Filters (Jan-Jun | Jul-Nov):
- none: +$1,175 drop -$361 | +$1,293 drop -$201
- skip RSI < 50 at entry (buy; > 50 for sells): +$1,461 drop -$289 | +$1,223 drop -$198 (total +$2,684, best small gain)
- skip zone stop < $10: +$1,291 | +$1,094 (fewer trades, less profit)
- skip if price moved against in the last hour: +$1,335 | +$1,040

## Fresh zone, first touch only (`research/fresh_zone.py`), main + zone, full 2026, 0.01
| Zone rule | Year | Worst drop | Losing months |
|---|---|---|---|
| any touch, up to 10 (current choice) | **+$2,468** | -$361 | 1/11 |
| first touch, 1 trade | +$1,732 | -$324 | 2/11 |
| first touch until 1 zone height above E, up to 10 | +$1,637 | -$504 | 1/11 |
| first touch until close above E | +$972 | -$239 | 4/11 |
First touch only makes less money. Zone alone, first touch with 1 trade wins more often (43% / 54%) but makes only
+$871 for the year. **Keep any touch, up to 10.** Later touches of the zone are profitable too.

## Zone trades by structure size (E-A distance), full 2026, 0.01
Under $5: 7 tr, +$49 | $5-10: 13 tr, +$114 | $10-20: 45 tr, +$97 | $20-40: 110 tr, +$210 | over $40: 344 tr, +$1,138.
Every size makes money, so short structures stay in (no minimum size). Most trades come from big structures.

## Zone trades by F-E leg size (owner: "is a short structure considered?"), full 2026, 0.01
`find_signals(a_levels=...)` now stores (d, A, bar, E, F).
Zone trades by F-E: $5-10: 4 tr, -$31 | $10-15: 27 tr, +$93 | $15-20: 36 tr, +$219 | $20-30: 135 tr, +$80 | over $30: 317 tr, +$1,247.
Minimum F-E for zone trades (main + zone): none +$2,468 (drop -$361) | $10 +$2,499 | $15 +$2,407 (-$344) |
$20 +$2,188 | $30 +$2,108. Skipping short legs does not help (only under $10 loses, and those are just 4 trades).

## Small structures and the $20 target (`research/small_structure_tp.py`)
Owner: "a $20 target on a structure smaller than $20?" Main trades split by structure size (F - G):
under $20: 31 tr, 35% win, -$82 for the year | $20+: 136 tr, 44%, +$943.
The tests run the small and big groups separately, so the "current" figure here (+$1,041 main) differs from the real
+$861; compare the rows with each other only.
| Rule for structures under $20 (F - G) | Main alone | Main + zone | Worst drop (with zone) |
|---|---|---|---|
| target $20 (current) | +$1,041 | +$2,648 | -$344 |
| skip them | +$939 | +$2,547 | -$425 |
| **target = structure size (min $5)** | **+$1,246, 48% win** | **+$2,854** | -$360 |
With size = H - G instead, neither change helps. Best: target = F - G size when it is under $20 (Jan-Jun about the same,
Jul-Nov +$217 better).

## Hunting other losses: the rule must improve win rate, profit AND drop in both halves (owner's test)
Chosen combination now: Jan-Jun 433 tr, 34%, +$1,175, drop -$361 | Jul-Nov 253 tr, 43%, +$1,293, drop -$201.
Day / open-trade limits (`research/loss_controls.py`), none pass:
- stop after 3 losses in a day: +$1,477, 38%, -$359 | +$901, 44%, -$237 (2nd half worse)
- stop after 2 losses, -$40 or -$60 a day: less profit, bigger drops
- no buy while a sell is open: +$861, -$616 | +$1,378 ; max 3 open or max 2 same side: about the same or worse
Zone-trade changes (`zone(..., rr, be, g_rsi)`), none pass:
- G must reach RSI 32: +$350 | +$395 (much less)
- target 1.5R: 40% / 48% win, +$1,287 | +$1,062, drop -$369 | -$183 (higher win rate, but less profit in Jul-Nov)
- target 3R: +$654 (drop -$819) | +$1,710 ; breakeven at 1R: +$1,552 | +$947
Only "target = structure size when F - G is under $20" (main trades) improves all three for the main trades.

## Profit per $1 of drop (`research/ratio_test.py`), owner's measure
| Rule | Jan-Jun win / profit / drop / ratio | Jul-Nov | Year |
|---|---|---|---|
| current | 34% +$1,175 -$361 3.3 | 43% +$1,293 -$201 6.4 | 37% +$2,468 -$361 6.8 |
| RSI side filter | 36% +$1,461 -$289 5.1 | 43% +$1,223 -$198 6.2 | 38% +$2,684 -$289 9.3 |
| small-structure target | 35% +$1,218 -$360 3.4 | 46% +$1,636 -$170 9.6 | 39% +$2,854 -$360 7.9 |
| **both** | **37% +$1,504 -$270 5.6** | **46% +$1,566 -$155 10.1** | **40% +$3,070 -$270 11.4** |
**Both rules together improve win rate, profit AND drop in both halves.** Added to the chosen strategy:
1. Skip any entry (main or zone) where RSI 14 is on the wrong side of 50: buys need RSI >= 50, sells RSI <= 50.
2. Main trades: if the structure F - G is under $20, the target = F - G (minimum $5) instead of $20.
Profit factor (money won / money lost): before 1.23 (Jan-Jun), 1.66 (Jul-Nov), 1.35 (year).
Now (both rules): 1.33, 1.87, **1.48** (year). Won $9,473, lost $6,404.

## Re-entry ideas on the chosen strategy (`research/reentry_v2.py`, `simulate_reentry(reentry_tp=...)`)
Year at base 0.01: win / profit / drop / PF / profit per $1 drop.
| Re-entry high / target / lots | Year |
|---|---|
| **RSI high / first target + $10 / flat (current)** | **40% +$3,070 -$270 PF 1.48 R 11.4** |
| RSI / first target + $10 / 1-2-1-2 lots | 40% +$3,134 -$405 PF 1.44 R 7.7 |
| RSI / $20 from re-entry if above 1st entry, else first target + $10 / flat | 40% +$3,071 -$296 PF 1.48 R 10.4 |
| RSI / same, 1-2-1-2 | 40% +$3,093 -$456 R 6.8 |
| RSI / $20 if above, else $30 from re-entry / flat | 42% +$2,043 -$453 R 4.5 |
| 3-candle high (any target or lots) | +$1,142 to +$2,266, drop -$528 to -$1,002 |
Max re-entries (RSI, current target, flat): 0 = +$2,012 -$298 | 1 = +$1,947 | 2 = +$2,665 | 3 = +$2,702 | **5 = +$3,070 -$270**.
**Keep the current re-entry (RSI high, first target + $10, up to 5) with the SAME lot on every re-entry.**
Doubling the 2nd entry adds about $60 a year but raises the worst drop from -$270 to -$405, so the profit per $1 of
drop falls from 11.4 to 7.7. This replaces the alternating-lot idea in the earlier final plan.

## If every trade hit its target (chosen strategy, 2026, 0.01)
636 trades. If all hit target: +$23,181. Actual: +$3,070 (won $9,473, lost $6,404).
| Source | Trades | Actual | If all hit target |
|---|---|---|---|
| main first entries | 114 | **+$129** (won $1,149, lost $1,020) | $2,133 |
| main re-entries | 69 | +$1,137 | $5,797 |
| zone | 453 | +$1,803 | $15,251 |
All 381 losers were full stop-outs; no early closes. Of 255 winners, 254 hit the full target.
Loophole found: main first entries barely make money (+$129 from 114 trades); most main profit comes from re-entries.

## Skip the main first entry (`research/skip_first_entry.py`)
The bot watches the first entry without trading it, and takes the re-entries if it would have stopped out.
| | Jan-Jun | Jul-Nov | Year |
|---|---|---|---|
| current (main + zone) | 37% +$1,504 -$270 PF 1.33 | 46% +$1,566 -$155 PF 1.87 | 40% +$3,070 -$270 PF 1.48 R 11.4 |
| skip first entry | 33% +$1,472 -$318 PF 1.38 | 43% +$1,469 -$138 PF 2.00 | 37% +$2,941 -$318 PF 1.55 R 9.2 |
| main only, current | 45% +$672 -$200 | 55% +$594 -$120 | 48% +$1,266 -$200 PF 1.66 |
| main only, skip first | 32% +$640 -$160 | 45% +$497 -$80 | 36% +$1,137 -$160 PF 2.26 |
Fails the all-three test: higher profit factor, but lower win rate, less profit and a bigger drop with the zone.
**Keep the first entry.**

## Zone losing trades (`research/zone_losers.py`, trades in `research/zone_losers_trades.csv`)
453 zone trades (RSI-50 filter on), 37% win, +$1,803. Traits: stop size, G position in the zone, hours since the
structure, nth trade, E-A size, H-G / stop, hour, previous trade in the structure, buy/sell.
Only one bucket loses in BOTH halves: **the 2nd zone trade in a structure** (46 tr 30% -$82 | 31 tr 32% -$32).
Weak in Jan-Jun only: stops of $15-20 (17% win, -$386), a trade right after a winning zone trade (22%, -$252), buys.
Big stops (over $20) are the best zone trades (48-62% win).
Skip the 2nd zone trade (main + zone): Jan-Jun 38% +$1,586 drop -$378 | Jul-Nov 48% +$1,597 -$135 | year 41%
+$3,184 PF 1.58. More profit, higher win rate and profit factor, but the Jan-Jun drop grows from -$270 to -$378,
so it fails the all-three test. Skip 2nd and 3rd: +$2,690, -$255. Not adopted.

## Trades by hour of the day (`research/loss_by_hour.py`), chosen strategy, 2026, 0.01, server time
Losing hours: 23:00 loses in BOTH halves (19 tr, 21% win, -$117). 15:00 is the worst hour (39 tr, 28% win, -$319,
nearly all in Jan-Jun); 15:30 server is the US news time (8:30 New York). 13:00 -$117, 19:00 -$71, 07:00 -$24, 00:00 -$36.
Best hours: 17:00 (+$1,152, 59% win), 03:00 (+$693), 02:00 (+$390), 18:00 (+$364).
| No new trades at | Jan-Jun | Jul-Nov | Year |
|---|---|---|---|
| none (current) | 37% +$1,504 -$270 | 46% +$1,566 -$155 | +$3,070 -$270 PF 1.48 |
| 23:00-00:59 | 38% +$1,638 -$253 | 46% +$1,585 -$155 | +$3,223 -$253 PF 1.52 |
| 15:00 | 38% +$1,833 -$279 | 46% +$1,556 -$123 | +$3,389 -$279 PF 1.58 |
| **23:00 and 15:00** | **39% +$1,930 -$263** | **46% +$1,575 -$123** | **+$3,506 -$263 PF 1.62** |
Skipping 23:00 and 15:00 passes the all-three test in both halves. Caution: the hours were picked from the same
data. 23:00 loses in both halves; 15:00 has a reason (US news). Waiting for the owner's decision.

## Late join after the skipped hours (`research/late_join.py`)
No new trades at 15:00 and 23:00 server. When the hour ends, join a skipped trade that is still open, only if price is at
its entry or better, with the original stop and target.
- skip, no join: +$3,506, drop -$263, PF 1.62 (best)
- skip, join any: 12 trades joined, 2 won, 10 lost, -$205 -> +$3,300, PF 1.56
- skip, join main re-entries only: no trade qualified (same as no join)
The owner was right: a skipped trade still sitting at its entry after the hour usually goes on to the stop. **No late join.**
**PENDING (owner: "keep that in memory"):** skip new trades at 15:00 and 23:00 server (no late join). Not added yet.

## How long trades are held (`research/hold_time.py`), chosen strategy, 2026, 0.01
Median minutes held: main losers 118, winners 162 | zone losers 78, winners 148. **Losers die fast; winners take time.**
| Held | trades | win% | net |
|---|---|---|---|
| under 15 min | 60 | 32% | -$217 |
| 15-30 min | 64 | **16%** | -$474 |
| 30-60 min | 88 | 38% | -$204 |
| 1-2 h | 127 | 39% | -$134 |
| 2-4 h | 107 | 47% | +$513 |
| 4-8 h | 92 | 43% | +$429 |
| 8-24 h | 58 | 53% | +$1,211 |
| over 1 day | 40 | 57% | +$1,945 |
Time exits (close after N minutes, or only if losing) all make less: best is 480 min if losing, +$2,878 (vs +$3,070).
Cutting long trades cuts the winners. The losses happen in the first 2 hours: the trade goes straight to the stop.

## Better entry with a limit order (`research/better_entry.py`), same stop and target levels
How far winners went against us before reaching target: $1+ 89%, $3+ 69%, $5+ 52%, $10+ 25%, $20+ 5%.
Almost every trade goes into a loss first. Losers always fill a better limit (smaller loss); winners that never came
back are missed.
| Entry | Year win / profit / drop / PF |
|---|---|
| at signal (current) | 40% +$3,070 -$270 PF 1.48 |
| $1 better | 37% +$3,130 -$288 PF 1.52 |
| $2 better | 35% +$3,253 -$316 PF 1.58 |
| $3 better | 32% +$3,202 -$278 PF 1.61 |
| $5 better | 27% +$3,010 -$335 |
| $10 better | 25% +$1,941 |
| 10% of the stop better | 37% +$3,489 -$283 PF 1.61 (Jan-Jun +$1,915 -$283, Jul-Nov +$1,575 -$145) |
None passes the all-three test: the win rate always falls, because winners are missed, and the drop is not smaller.

## Consolidation at entry (`research/consolidation.py`, trades in `research/consolidation_trades.csv`)
Measures known before entry: last 1h / 4h range vs normal, ADX(14) M15, last-hour efficiency, Bollinger width M15.
Loses in BOTH halves: last 1h range under 0.6x normal (tight, true consolidation: 35 tr, -$177) and ADX M15 25-35
(185 tr, 28% / 36% win, -$463 / -$134). ADX under 15 (no trend) is actually good (51% / 65% win), and so is ADX over 35.
| Skip | Jan-Jun | Jul-Nov | Year |
|---|---|---|---|
| none (current) | 37% +$1,504 -$270 | 46% +$1,566 -$155 | +$3,070 -$270 PF 1.48 |
| tight last hour (<0.6x) | 38% +$1,635 -$234 | 46% +$1,611 -$155 | +$3,246 -$234 PF 1.54 |
| ADX 25-35 | 40% +$1,966 -$317 | 51% +$1,700 -$129 | +$3,666 -$317 PF 1.88 |
| **both** | **41% +$2,032 -$269** | **51% +$1,746 -$129** | **+$3,777 -$269 PF 1.97** |
"Skip tight last hour" and "skip both" pass the all-three test. Caution: ADX 25-35 is a middle band picked from the
same data (nearby bands 25-30 and 27-33 also help). Waiting for the owner's decision.
**PENDING (owner: "we're going to see"):** skip a tight last hour (<0.6x) and ADX M15 25-35. Not added yet.

## Losing trades by buy and sell (chosen strategy, 2026, 0.01)
| | trades | win% | lost | won | net | Jan-Jun | Jul-Nov |
|---|---|---|---|---|---|---|---|
| buys | 259 | 36% | -$3,242 | +$4,656 | +$1,414 | +$1,219 | +$195 |
| sells | 377 | 43% | -$3,162 | +$4,818 | +$1,656 | +$285 | +$1,371 |
Zone buys are the weakest (31% win). By month: buys make money Jan-Mar (gold rising), lose Apr-May; sells lose
Jan-Mar and win May-Nov (no buys at all Aug-Nov). Losses cluster in trades against the bigger trend of the month.

## Daily (big) trend handling (`research/daily_trend.py`)
Daily trend from finished days: EMA20 of daily closes, or the direction of the last 20-day breakout.
Trades against the daily trend still make money: EMA20 against 253 tr 35% +$1,263 (with 383 tr 44% +$1,806);
Breakout20 against 196 tr 40% +$1,019.
| Rule | EMA20 year | Breakout20 year |
|---|---|---|
| current | +$3,070 -$270 PF 1.48 | same |
| skip against | +$1,806 -$321 | +$2,050 -$642 |
| half lot against | +$2,438 -$210 (Jul-Nov drop worse: -$195) | +$2,560 -$435 |
| skip zone against | +$2,412 -$260 (Jul-Nov drop -$257) | +$2,600 -$446 |
None passes the all-three test. Counter-trend trades are profitable, so cutting them loses money. **No daily trend filter.**
Both pending filters together (hours + consolidation): Jan-Jun 42% +$2,171 -$283 | Jul-Nov 50% +$1,631 -$129 |
year +$3,802 PF 2.05. The Jan-Jun drop is worse than either filter alone, so combining them does not pass.

## ADOPTED (owner, 27 Nov 2026): both filters together
Added to the chosen strategy (main + E-A zone up to 10, RSI-50 side filter, small-structure target):
1. No new trades at 15:00 and 23:00 server time (no late join).
2. No new trades when the last 1h range is under 0.6x its 5-day median, or when ADX(14) on M15 (last finished bar)
   is between 25 and 35.
2026 at 0.01 ($1,000 start each half): **45% win, +$3,802, PF 2.05, worst drop -14.3% (Jan-Jun) / -8.9% (Jul-Nov)**.
Before: 40%, +$3,070, PF 1.48, -23.6% / -11.5%. The filters were found on 2026 data; confirm on new data.
Owner's target: push the strategy toward +$10,000 (2026, 0.01) before coding the EA.

## $20,000 push, step 1: more trades from the same structures (`research/more_trades.py`), 0.01, all filters on
Drops are % of a $1,000 start in each half. `zone(..., big_rr, reent)` added.
| Variant | Jan-Jun | Jul-Nov | Year |
|---|---|---|---|
| current (10 per structure, 10 days) | 42% +$2,171 -14.3% | 50% +$1,631 -8.9% | +$3,802 PF 2.05 |
| zone re-entry, RSI swings (any) | drops -56% to -146% | | rejected |
| zone re-entry, 3-candle, 2x risk, 1 | 40% +$2,737 -17.5% | 49% +$1,847 -9.3% | +$4,585 PF 1.96 |
| zone re-entry, 3-candle, 2x risk, 3 | 38% +$2,704 -20.4% | 50% +$2,157 -7.3% | +$4,861 |
| **up to 20 per structure, 10 days** | 43% +$2,421 -14.3% | 50% +$1,765 -8.4% | +$4,187 PF 2.10 |
| **up to 20 per structure, 20 days** | 42% +$2,426 -14.3% | 50% +$1,843 -8.0% | **+$4,269 PF 2.05** |
| up to 99, 30 days | 41% +$2,322 -14.3% | 51% +$2,124 -5.3% | +$4,446 PF 1.97 |
| 2.5x / 3x / 4x target when stop > $20 | +$2,097 / +$1,300 / +$1,540 | +$1,829 / +$2,026 / +$2,289 | worse drop in Jan-Jun |
| 20 per, 20 days + 3-candle re-entry 2x 1 | 41% +$3,344 -17.5% | 51% +$2,327 -7.4% | **+$5,671 PF 2.04** |
| 99 per, 30 days + same re-entry | 40% +$3,182 -17.5% | 52% +$2,750 -5.7% | +$5,933 PF 1.94 |
Passes the all-three test: up to 20 per structure, 20 days (+$4,269). Biggest gain with a small extra drop:
20 per, 20 days + one 3-candle zone re-entry (2x risk target), +$5,671, Jan-Jun drop -17.5% vs -14.3%.
Zone re-entries with 20 per structure, 20 days: 1 = +$5,671, drop -17.5%, PF 2.04 | 2 = +$6,053, drop -19.4%, PF 1.93.

## ADOPTED (owner, 27 Nov 2026): version B
Zone: up to 20 trades per structure, zone memory 20 days, plus 1 zone re-entry after a zone stop: wait for a 3-candle
high then low, re-enter on the break of that high, stop $1 beyond the lowest point since the stop (min $5), target 2x risk.
All filters stay. 2026 at 0.01: 652 trades, 45% win, **+$5,671**, PF 2.04, worst drop -17.5% (Jan-Jun) / -7.4% (Jul-Nov),
1 losing month (Apr -$107). Code: `zone(df, sp, 20, 20, reent=dict(swings='3', target='2R', max=1))` + filters in
`research/more_trades.py`.

## More options on top of version B (`research/more_trades2.py`), 0.01, all filters on
| Variant | Jan-Jun | Jul-Nov | Year |
|---|---|---|---|
| version B | 41% +$3,344 -17.5% | 51% +$2,327 -7.4% | +$5,671 PF 2.04 |
| + main against-boss signals | 41% +$3,372 -17.5% | 51% +$2,347 -7.3% | +$5,719 PF 2.05 (only 2 extra trades) |
| main target $30 when F-G >= $50 | 41% +$3,334 -19.4% | 50% +$2,317 | +$5,651 |
| main target $40 when F-G >= $50 | 40% +$3,222 -21.8% | | +$5,589 |
| + zone between F and E | 39% +$3,845 -16.2% | 47% +$3,003 -6.1% | +$6,847 PF 1.58, 1,344 trades |
F-E zone alone: 692 tr, 39%, +$1,176, PF 1.19. It adds +$1,176 and lowers the drop, but the win rate (45% -> 42%) and
profit factor (2.04 -> 1.58) fall, so it fails the all-three test. Against-boss signals: harmless, almost no trades.
**ON HOLD (owner: "keep reminding me"):** the F-E zone (+$1,176, total +$6,847, drop -16.2%, but win 42%, PF 1.58).
Remind the owner of it at each decision point.

## GLITCH FOUND (chart review of the worst days): stacked duplicate zone trades
Worst days 2026 (version B): 23 Mar -$145, 21 Apr -$102, 13 Mar -$89. On 13 Mar 18:24 the bot opened 4 buys at the
same price (5037.86): overlapping structures each took the same H break as a zone trade and as a zone re-entry.
One setup was traded several times, which works like a hidden bigger lot. 172 of the zone trades in version B were
such duplicates. With only 1 zone trade per minute and side:
| Version | Stacked (as reported before) | 1 trade per setup |
|---|---|---|
| 10 per, 10 days (old chosen) | +$3,802, -14.3%, PF 2.05 | +$3,365, -14.3%, PF 1.98 |
| 20 per, 20 days | +$4,269, -14.3%, PF 2.05 | +$3,610, -14.3%, PF 1.97 |
| 20 per, 20 days, 1 re-entry (B) | +$5,671, -17.5%, PF 2.04 | **+$3,994, -15.3%, PF 1.97** |
| 99 per, 30 days, 1 re-entry | +$5,933, -17.5% | +$4,132, -15.3%, PF 1.91 |
Earlier results also include some stacking (e.g. the old +$2,468). Win rate is the same either way (45%), so the stacked
trades are not worse trades; they are extra size on setups where two structures agree. Owner to decide.

## Clean version B (1 trade per setup, `research/version_b.py`) is the new base: 480 tr, 45%, +$3,994, -15.3%, PF 1.97
Chart review, more checks:
- Very big zone stops (23 Mar: $80 and $65 stops) are NOT a problem: stops over $60 won 54-100%, +$1,103.
  Skipping stops over $30 / $40 / $60: +$2,683 / +$2,807 / +$2,891 (much worse).
- Many buys in a falling market (21 Apr, 7 trades): max 1 zone trade open per side +$3,559; max 2 +$3,973.
  Pause 60 min after a zone loss: 46% win, +$3,570, -14.6%, PF 2.07. Pause 240 min: **48% win, +$3,635, -14.7%,
  PF 2.21** (higher win rate and PF, slightly smaller drop, but $359 less profit).
Owner rule from now: **anything that lowers profit is rejected.**
Worst days of clean B: 23 Mar -$145 (2 zone sells, $80 and $65 stops), 29 Jul -$73 (zone buys and sells taken in
turns, 8 trades: two opposite structures active together), 21 Apr -$72 (4 zone buys + 1 main buy in a fall).
No main and zone trade at the same minute. Blocking a zone trade against an opposite zone trade: +$3,590 to +$3,749
(less profit), rejected.

## OWNER DECISION (27 Nov 2026): KEEP STACKING
Version B stays as first reported: +$5,671 at 0.01, 45% win, PF 2.04, worst drop -17.5%. When overlapping structures
take the same setup, every copy is traded (up to 4 at one price). Note for the EA and the lot-size step: stacked copies
mean up to ~4x the base lot on one setup, so the real exposure per setup can be 0.04 on a 0.01 base.
"Clean B" (+$3,994) is kept only as a reference.

## Owner's funded account: Top One Trader $50,000 (passed 24 Nov 2026). Rules: daily loss 4% ($2,000), max drawdown 10% ($5,000)
Version B at 0.01 (2026): worst drawdown -$380, worst day -$145, year +$5,671 (closed trades only).
Lot that just touches the limits: 0.13 (2026 would be about +$74,600). Half the limits for safety: 0.07 (about +$37,300).
Optimistic: closed trades only (floating losses are bigger), stacking can open up to 4 copies, and one past year.
Do not run the bot on the funded account until it is tested live on demo.

## More profit on version B (`research/more_profit3.py`), stacking kept, 0.01, all filters
| Variant | Year |
|---|---|
| version B | 45% +$5,671 -17.5% PF 2.04 |
| main re-entry target +$5 / +$15 / +$20 (vs +$10) | +$5,467 / +$5,725 / +$5,436 |
| main stop $15 / $25 / $30 (vs $20) | +$5,273 (-21.6%) / +$5,667 (-16.1%) / +$5,725 (46%) |
| zone 30 / 40 / 50 per structure, 20 days | +$6,045 / **+$6,212** / +$6,092 (all -17.5%) |
| zone memory 30 days | less |
| zone re-entry target 2.5x / 3x | +$5,549 / +$5,249, drop -20.2% |
| **zone 40 + main stop $30 + main re-entry target +$15** | **46% +$6,300 -17.5% PF 2.06** (Jan-Jun 42% +$3,674; Jul-Nov 53% +$2,626 -6.1%) |
Best: zone up to 40 per structure (20 days), main stop $30, main re-entry target = first target + $15.
More profit, same worst drop, win rate and PF the same or higher. Waiting for the owner's OK.

## ADOPTED (owner, 27 Nov 2026): the NEW version
Version B + zone up to 40 per structure (20 days) + main stop $30 + main re-entry target = first target + $15.
2026 at 0.01: 713 trades (3.3/day), 46% win, **+$6,300**, PF 2.06, worst drop -17.5%; 101 winning days, 59 losing.
Code: `research/more_profit3.py` -> `zones(40, 20) + mains(sl=30, extra=15)`.

## Client view: winning / losing / no-trade days and bad streaks (`research/bad_days.py`)
Chosen version, 217 trading days: winning 101 (47%), losing 59 (27%), no trade 57 (26%).
Bad-day streaks (losing OR no trade): longest 7 days (25 Sep - 5 Oct); 3+ days 18 times, 5+ days 6 times.
Losing-day streaks only: longest 4; 3+ days 5 times.
A client connecting on any day is in profit after 1 day 47% | 3 days 65% | 5 days 72% | 10 days 82% | 20 days 93%
(worst: -$148 after 1 day, -$210 after 5 days, at 0.01).
With the on-hold F-E zone added: no-trade days fall to 13%, winning days 53%, but losing days 34%, longest bad streak 6,
and worse client losses (-$319 after 1 day). Year +$6,951 but PF 1.51.

## Trades for quiet days (`research/quiet_days.py`)
Live rule: extra trades only if the bot has taken no trade yet today (max 1, 2 or all per day).
| Extra pool on quiet days | Extra trades | Win | Extra $ | Year | No-trade days |
|---|---|---|---|---|---|
| F-E zone, max 1 | 92 | 37% | -$223 | +$6,078 | 13% |
| blocked trades (filters), max 1 | 78 | 41% | -$253 | +$6,047, drop -15.5% | 18% |
| both, max 1 | 133 | 41% | -$258 | +$6,043 | 8% |
| both, all | 541 | 37% | -$958 | +$5,343, drop -37.8% | 8% |
Every quiet-day pool LOSES money: the days are quiet because the setups there are poor. Fewer no-trade days, but more
losing days (27% -> 32-40%). Rejected (owner's rule: nothing that lowers profit).

## After the target is hit (`research/after_tp.py`)
235 winning targets. In the next 4 hours price went $10+ further our way 69% and $10+ back against 69%; $20+ either
way 40%; median $16.7 both ways. After the target, price is a coin flip: it does not clearly continue or reverse.
- Pullback continuation trade (3-candle low then high break, 2x risk): 127 tr, 31% win, -$67 -> total +$6,233.
- Reversal trade (3-candle high then low break the other way, 2x risk): 105 tr, 28% win, -$233 -> total +$6,067.
Both lose money. Rejected.

## Owner's idea: after the target, let price run $X more, then trade (`research/after_tp_ext.py`)
Reversal after the run (3-candle high then low break, the other way, stop beyond the top, 2x risk):
run $10: 59 tr 19% win -$480 | $20: 49 tr 16% -$488 | $20 + RSI 68/32: 40 tr 18% -$401 | $30: 23 tr 17% -$310.
A run usually keeps going: reversals fail badly. Rejected.
Continuation after the run (pullback, then 3-candle high break the same way, 2x risk):
$10: 83 tr 23% -$191 | $20: 53 tr 30% -$13 | **$30: 28 tr 36% +$124 -> total +$6,425, 46% win, -17.5%, PF 2.04**.
Small gain from only 28 trades (could be luck). Waiting for the owner.
Owner dropped the after-target trades.

## Strong base above E (pullback that never reaches the zone) (`research/strong_base.py`)
| Extra trades (+ chosen version) | Extra | Total | Win | Drop | PF |
|---|---|---|---|---|---|
| none (chosen) | | +$6,300 | 46% | -17.5% | 2.06 |
| RSI base (G above E reaches RSI 32) | 200 tr 41% +$444 | +$6,745 | 45% | -19.7% | 1.88 |
| RSI base 30 | 174 tr 37% +$59 | +$6,359 | 44% | -17.4% | 1.84 |
| double bottom $1 (1 per setup) | 528 tr 37% +$782 | +$7,082 | 42% | -19.3% | 1.79 |
| **double bottom $2 (1 per setup)** | 1,035 tr 37% +$1,029 | **+$7,329** | 41% | **-17.4%** | 1.62 |
| double bottom $3 (1 per setup) | 1,545 tr 37% +$1,635 | +$7,935 | 40% | -19.3% | 1.53 |
Double bottoms are seen by many overlapping structures (with copies: $2 = 1,819 trades, +$8,057), so copies were
removed. They add profit, but the win rate falls (46% -> 40-42%) and many more trades (about 8/day for $2).
Waiting for the owner.

## Base inside the entry-target band after a win (`research/band_base.py`)
After a winning target, price pulls back below the target but never back to the entry, builds a base (30-240 min,
range any / <=$10 / <=$15), then continues: enter on the break of the base high or of the post-target high; stop $1
below the base low, 2x risk. Results swing between -$214 and +$164 depending on the settings (fragile):
- base high, 60 min, range <=$10: 36 tr, 44%, +$111 -> total +$6,411, 46% win, drop -15.8%, PF 2.04
- base high, 120 min, range <=$15: 46 tr, 39%, +$107 -> total +$6,407, 46% win, drop -14.7%, PF 2.01
- post-target high, 60 min, any range: 87 tr, 36%, +$164 -> total +$6,465, 45% win, drop -13.5%, PF 1.90
Neighbouring settings lose money, so these small gains may be luck. Waiting for the owner.

## Client report: chosen vs chosen + double bottom $2 (`research/client_report.py`), 0.01
| | Chosen | + double bottom $2 |
|---|---|---|
| year | +$6,300, 46%, -17.5%, PF 2.06 | +$7,329, 41%, -17.4%, PF 1.62 |
| trades / day | 3.3 | 8.0 |
| wins / day, avg win | 1.5, +$37 | 3.3, +$27 |
| losses / day, avg loss | 1.8, -$16 | 4.7, -$12 |
| avg day | +$29 | +$34 |
| winning / losing / no-trade days | 47% / 27% / 26% | 56% / 37% / 7% |
| longest bad streak (loss or no trade) | 7 | 5 |
| longest losing streak | 4 (once) | 4 (5 times) |
| client in profit after 1 / 5 / 10 / 20 days | 47 / 72 / 82 / 93% | 56 / 72 / 80 / 89% |
| client worst after 10 / 20 days | -$180 / -$154 | -$310 / -$435 |
**ON HOLD #2 (owner, 27 Nov 2026):** double bottom $2 above E (+$1,029; total +$7,329, 41% win, 8 trades/day).
Good for the owner's own account, but win rate falls and clients' worst stretches deepen. Remind the owner.

## Common traits of losing trades -> reversal idea (`research/loser_common.py`, `research/loser_common_trades.csv`)
Chosen version, 713 trades. Traits known at entry: trade type, direction vs today's move and yesterday's move,
distance from today's open, yesterday's high/low already swept, last-4h move, nth trade today, ADX, RSI, weekday.
**No group loses money in both halves**, so there is no group to trade in reverse (reversing a profitable group loses).
The losers are spread evenly; after all the filters, the remaining losses look like normal noise.
Strong groups found: RSI 68-80 at entry (buys; 20-32 for sells): 61% / 73% win, +$2,792. Trades against today's move
make most of the money (+$4,665), which fits the sweep (reversal) nature of the strategy.
Weak only in Jan-Jun: main first entries (-$152), trades $5-20 with today's move (24% win), 2nd trade of the day (29%).

## Bigger target when RSI is already 68+ at entry (`research/hot_rsi_target.py`, `zone(..., hot_rr)`)
| Variant | Jan-Jun | Jul-Nov | Year |
|---|---|---|---|
| chosen | 42% +$3,674 -17.5% | 53% +$2,626 | +$6,300, 46%, PF 2.06 |
| zone hot target 2.5x | +$3,619 | +$2,816 | +$6,434, 45%, PF 2.05 |
| zone hot target 3x | +$3,306 | +$3,059 | +$6,365 |
| zone hot target 4x | 40% +$3,354 | 51% +$3,242 | +$6,596, 44%, -17.5%, PF 2.06 |
| main hot target $30 / $40 | | | +$5,797 / +$5,801, drop -31% |
Zone 4x adds +$296 for the year, but Jan-Jun makes $320 less and the win rate falls to 44% (gain only in Jul-Nov).
Main: much worse. Not convincing.

## Two more options (`research/two_options.py`; `zone(..., region='BA', ba_frac, need_i)`)
1. Zone below A (G past A, then the same zone trade rules), added to the chosen version:
| Below-A zone | Extra | Total | Win | Drop | PF |
|---|---|---|---|---|---|
| up to 1 depth, 40/structure | 274 tr 45% +$1,082 | +$7,382 | 46% | **-35.6%** | 1.84 |
| up to 0.25 depth, 1/structure | 41 tr +$239 | +$6,539 | 46% | -19.6% | 2.02 |
| up to 0.5 depth, 1/structure | 48 tr 46% +$451 | +$6,751 | 46% | -19.6% | 2.03 |
| **up to 0.5 depth, 5/structure** | 114 tr 46% +$1,016 | **+$7,316** | 46% | -23.2% | 2.04 |
The 0.5-depth, 5-per-structure version gains in BOTH halves (Jan-Jun +$756, Jul-Nov +$260), same win rate and PF,
but the Jan-Jun drop grows from -17.5% to -23.2%.
2. Faster zone entry (first H break after G, no I): +$5,843, drop -20.3%, 43% win. Worse. Rejected.
Below-A zone with a smaller drop (0.5 depth, 5/structure):
- stop a structure after its 1st loss: 65 tr +$638 -> +$6,938, -22.4% | after 2 losses: +$6,899, -23.2%
- **only when RSI is 68+ at entry (32- for sells): 9 tr, 89% win, +$318 -> +$6,618, 47% win, -17.5%, PF 2.11.**
  Passes the all-three test (same drop), but only 9 trades in the year: could be luck.

**Owner's adoption rule for new ideas (27 Nov 2026):** clients may connect prop-firm accounts (via Duplikium /
Castimofx.com, any MT5), so a new idea must add MORE than $1,000 AND lower the drop AND raise the win rate.
Small gains are not worth it. The number of trades also matters: clients want to see the bot trading.

## How many times the zone was tested before a zone trade (`research/level_tests.py`)
Zone trades by number of separate visits below E (buys) before entry:
1st 51 tr (+$527) | 2nd 44 (+$504) | 3rd 36 (+$220) | 4th-5th 67 (-$4) | 6th+ 415 tr (+$3,515, most of the zone money).
Price usually tests the zone many times before the trade comes.
| Rule | Year | Trades/day |
|---|---|---|
| all (chosen) | +$6,300, 46%, -17.5%, PF 2.06 | 3.3 |
| only the 1st test | +$2,066, 56%, -14.7%, PF 2.39 | 0.7 |
| 2+ tests | +$5,774, 47%, -16.6% | 3.0 |
| 3+ tests | +$5,270, 46%, -16.9% | 2.8 |
Requiring more tests cuts trades and profit; the first test only gives a higher win rate but far fewer trades and
a third of the profit. Keep all tests.

## Both on-hold ideas together (`research/combo_hold.py`), 0.01
| | Chosen | + F-E | + double bottom | + both |
|---|---|---|---|---|
| year | +$6,300 | +$6,951 | +$7,329 | **+$7,979** |
| win / PF | 46% / 2.06 | 41% / 1.51 | 41% / 1.62 | 40% / 1.41 |
| worst drop | -17.5% | -18.0% | -17.4% | -21.5% |
| trades/day | 3.3 | 7.0 | 8.0 | 11.7 |
| winning / losing / no-trade days | 47/27/26% | 53/34/13% | 56/37/7% | 56/39/5% |
| client worst after 1 / 20 days | -$148 / -$154 | -$319 / -$465 | -$182 / -$435 | -$356 / -$653 |
Both together: +$1,679 more profit and almost no empty days, but lower win rate (40%), bigger drop (-21.5%) and
deeper client losses. Fails the owner's rule (drop and win rate get worse). Still on hold.

## No stop loss (`research/no_stop.py`), 0.01 -- DANGEROUS, rejected
Trades stay open until the target (main: first entries only). Floating losses marked at each day's end.
| | Hit target | Still open at data end | Total | Worst trade against | Worst floating loss |
|---|---|---|---|---|---|
| chosen | 91% | 65 trades (-$25,481) | **-$7,456** | -$1,176 | **-$18,616** |
| + both | 94% | 215 trades (-$65,853) | +$2,646 | -$1,176 | **-$52,224** |
A 91-94% "win rate", but the few trades that never come back are enormous (held up to 102 days, $1,176 against).
At 0.01 a $1,000 account would be wiped out many times. Never trade without a stop.

## Close on an opposite trade instead of a stop (`research/opposite_exit.py`), 0.01, main first entries only
| Version | Year | Win | Drop | PF | Worst day | Worst open loss |
|---|---|---|---|---|---|---|
| chosen (normal stops, reference) | +$6,300 | 46% | -17.5% | 2.06 | -$148 | |
| chosen, opposite exit, no stop | -$2,246 | 77% | -257% | 0.87 | -$4,785 | -$11,502 |
| chosen, opposite + $100 safety stop | +$5,472 | 74% | -64% | 1.61 | -$700 | -$1,662 |
| chosen, opposite + $50 safety stop | +$5,106 | 69% | -36% | 1.64 | -$350 | -$413 |
| + both, opposite exit, no stop | **+$16,165** | 66% | -69% | 1.76 | -$1,732 | -$2,609 |
| + both, opposite + $100 safety stop | +$14,197 | 65% | -41% | 1.63 | -$784 | -$1,223 |
| + both, opposite + $50 safety stop | +$10,923 | 62% | -31% | 1.47 | -$594 | -$807 |
Win rate rises a lot (62-77%) and "+ both" makes much more, but drops and worst days are 2-10x bigger. Profit per
1% of drop is about the same as the chosen version (~$350), so it behaves like a bigger lot, not a better edge.
Fails the owner's rule for clients. Possibly for the owner's own account.
Full comparison, 0.01 (chosen | both opposite | both opposite + $100 stop | both opposite + $50 stop):
profit $6,300 | $16,165 | $14,197 | $10,923; win 46 | 66 | 65 | 62%; PF 2.06 | 1.76 | 1.63 | 1.47;
drop -18 | -69 | -41 | -31%; trades/day 3.3 | 15.3 (all three); avg month $590 | $1,570 | $1,374 | $1,052;
worst day -$148 | -$1,732 | -$784 | -$594; worst week -$103 | -$1,841 | -$756 | -$684;
worst month -$73 | -$1,303 | -$258 | -$438; worst open loss - | -$2,609 | -$1,223 | -$807;
winning days 47 | 68 | 63 | 59%; losing days 27 | 26 | 31 | 35%; client in profit after 20 days 93 | 77 | 80 | 85%.

## Minimum account balance at 0.01 (`research/min_balance.py`) -- ALWAYS REPORT THIS FROM NOW ON (owner)
Biggest peak-to-low $ drop of the account, closed trades plus open trades' floating losses (hourly). Minimum balance =
that drop; safe balance = 1.5x. Owner's goal: a version that is safe on a $100 account at 0.01.
| Version | Profit | Drop closed | Drop with open trades | Min balance | Safe balance |
|---|---|---|---|---|---|
| chosen (main first entries only here) | +$5,073 | $374 | $439 | $439 | ~$660 |
| + both, opposite exit | +$16,229 | $3,632 | $3,767 | $3,767 | ~$5,650 |
| + both, opposite + $100 stop | +$14,260 | $1,299 | $1,813 | $1,813 | ~$2,720 |
| + both, opposite + $50 stop | +$10,982 | $1,246 | $1,315 | $1,315 | ~$1,970 |
A $100 stop does not cap the account drop at $100: about 15 trades a day, several open at once, losses add up.
**ON HOLD #3 (owner, 27 Nov 2026):** "+ both" with opposite exit (no stop / + $100 stop / + $50 stop). Owner's view:
lot sizing would make these worse; the chosen version with its stops, properly lot-sized, can reach the money target
with less drawdown. Remind the owner.

## '+ both' losing streaks and pauses (`research/loss_streaks.py`), 0.01, normal stops
2,560 trades, 40% win, +$7,979. Losses come in clusters: after a loss the next trade wins only 27% (after 2, 3 or 5
losses: 25-27%), after a win the next trade wins 59%. Longest losing streak 25 trades; 10+ in a row 22 times
(many trades open at once in the same move, so they lose together).
Pause after N losses in a row (live: closed trades), year profit: after 1 loss 1/2/5/24 h: $5,497 / $5,243 / $4,578 /
$2,730; after 2: $5,790 / $5,016 / $4,390 / $2,724; after 3: $7,547 / $6,933 / $6,791 / $5,026. All lower than no pause
($7,979), drops mostly worse. Rejected: when a loss closes, the next trades of the same move are already open.
Losers' targets hit within 24 h after the stop: 57%. Come-back re-entry at the original entry within 4 h: 634 tr, 37%,
+$683 (total +$8,662, but Jan-Jun lower and drop -21.9%); within 24 h: +$37. Not convincing.
Idea for the lot-size step: wins follow wins (59%), losses follow losses (73%), so a smaller lot after a loss and
normal after a win may cut drops.

## Smaller lot after losses, chosen version (`research/lot_after_loss.py`), base 0.02, reduced 0.01
Chosen version streaks: after a loss the next trade wins 32%, after a win 63%. Live rule (closed trades only):
| Rule | Profit | Biggest $ drop (= min balance) | Worst day | Profit per $1 drop |
|---|---|---|---|---|
| always 0.01 | $6,300 | $374 | -$148 | 16.9 |
| always 0.02 | $12,601 | $747 | -$295 | 16.9 |
| 0.01 after 1 loss | $8,287 | $468 | -$269 | 17.7 |
| 0.01 after 2 losses | $8,687 | $468 | -$269 | 18.6 |
| **0.01 after 3 losses in a row** | **$11,069** | **$531** | -$269 | **20.8** |
| 0.01 after 4 losses | $11,382 | $596 | -$290 | 19.1 |
| 0.01 after 5 / 6 losses | $11,450 / $12,320 | $745 / $721 | | 15.4 / 17.1 |
Best: base 0.02, drop to 0.01 after 3 losses in a row until the next win. 23% more profit per $1 of drop than a
fixed lot; gains in both halves. Min balance about $531 (closed trades; safe ~$800). For the lot-size step.

## '$100 mode' search (`research/safe_100.py`, grid in `research/safe_100_grid.csv`), 0.01
Levers: stop cap ($10/15/20/none), 1 trade open at a time, daily loss limit ($20/30), main stop ($10-30).
**No setting is safe on $100 at 0.01**: the smallest possible drop is $84 (safe $126), and that version makes only
+$162 a year. Best per account size:
| Safe balance | Setting | Profit | Drop | Win |
|---|---|---|---|---|
| ~$190 | stop cap $10, 1 open, main stop $10 | +$1,057 | $128 | 35% |
| ~$270 | stop cap $15, 1 open, main stop $10 | +$1,499 | $182 | 38% |
| ~$320 | no cap, 1 open, main stop $30 | +$2,786 | $212 | 44% |
| ~$560 | chosen (stacking, all trades) | +$6,300 | $374 | 46% |
Real fix for $100 clients: a CENT account (100x smaller contract), where 0.01 risks 1/100: the chosen version's
$374 drop becomes $3.74. Or set a $300-$600 minimum and use the 1-open mode for small accounts.

**Owner (27 Nov 2026): keep the 4-version table (Chosen, +F-E, +DB, +Both). From now on every test runs on BOTH
"Chosen" and "+Both" (normal stops).** Reference: Chosen $6,300 46% PF 2.06 -18% min bal $440 | +Both $7,979 40%
PF 1.41 -22% min bal $900.
Owner: cent accounts are NOT an option (27 Nov 2026).

## Owner's moving average = SMA 10 on close (M1), confirmed (4272.969 at 2026.03.23 13:03). "Inside" for buys =
candles above the line (sell: below). As an entry filter (`research/sma10_side.py`), 0.01:
| | Profit | Win | PF | Min balance (closed) | Trades/day |
|---|---|---|---|---|---|
| Chosen | $6,300 | 46% | 2.1 | $374 | 3.3 |
| Chosen, last candle on the right side | $5,940 | 46% | 2.0 | $374 | 3.1 |
| Chosen, last 3 candles on the right side | $4,768 | 47% | 2.1 | $326 | 2.3 |
| +Both | $7,979 | 40% | 1.4 | $797 | 11.7 |
| +Both, last candle | $7,795 | 40% | 1.4 | $751 | 11.2 |
| +Both, last 3 candles | $6,597 | 41% | 1.5 | $526 | 7.4 |
As a filter on our entries it cuts profit. The owner uses it differently: "3 micro" re-entries inside the SMA 10 after
a stop (23 Mar example). That is the next test. (EMA/SMA 20/50 guesses in `research/ma_side.py`, also worse.)

## Owner's '3 micro inside SMA 10' re-entry after a stop (`research/micro3_reentry.py`), 0.01
After a stop, within 24 h: 3 rising candles (each closing higher, all closes above SMA 10; sells mirror), enter at the
3rd close, stop $1 beyond the extreme since the stop (min $5), target = first target ('orig') or 2x risk.
| Version | Profit | Jan-Jun | Jul-Nov | Win | PF | Min bal | Trades/day |
|---|---|---|---|---|---|---|---|
| Chosen | $6,300 | $3,674 | $2,626 | 46% | 2.1 | $374 | 3.3 |
| Chosen + 3micro x1, 2R | **$7,288** | $4,109 | $3,179 | 45% | 2.0 | $536 | 4.1 |
| Chosen + 3micro x1, orig | $6,525 | $3,472 | $3,053 | 44% | 1.9 | $536 | 4.1 |
| +Both | $7,979 | $3,770 | $4,210 | 40% | 1.4 | $797 | 11.7 |
| +Both + 3micro x1, 2R | **$10,089** | $5,132 | $4,957 | 39% | 1.4 | $923 | 15.1 |
| +Both + 3micro x2, 2R | $10,175 | $5,014 | $5,161 | 38% | 1.4 | $971 | 16.2 |
Best: one 3-micro re-entry with a 2x-risk target. Extra trades win 41% (Chosen) / 36% (+Both) and add +$988 /
+$2,110, with gains in BOTH halves. Cost: min balance up ($374 -> $536; $797 -> $923), win rate down ~1 point.
Real edge (profit in both halves), but fails the strict owner rule (drop must fall). Waiting for the owner.

## Skip big stops only on wild days (`research/wild_day_stops.py`), Chosen and +Both, 0.01
Wild = last 4 h range above 1.5x / 2x / 3x its 5-day median; big stop = over $30 / $40 / $60.
Chosen: $6,300 -> $3,950-$5,171 (min balance $374 -> $302, worst day unchanged -$148).
+Both: $7,979 -> $5,672-$7,453 (min balance about the same, worst day -$356 -> -$271).
Every version loses $800-$2,300 of profit: big-stop trades on wild days are mostly big winners (23 Mar was the
exception). Rejected.

## Full report: Chosen / Chosen+3micro / +Both / +Both+3micro (`research/full_report.py`, `research/full_report.csv`), 0.01
```
,Chosen,Chosen+3m,+Both,+Both+3m
Profit,"$6,300","$7,288","$7,979","$10,089"
Jan-Jun,"$3,674","$4,109","$3,770","$5,132"
Jul-Nov,"$2,626","$3,179","$4,210","$4,957"
Win,46%,45%,40%,39%
PF,2.06,1.99,1.41,1.40
Drop,-18%,-22%,-22%,-25%
Min bal,$374,$536,$797,$923
Safe bal,$560,$804,"$1,196","$1,385"
Trades/day,3.3,4.1,11.8,15.2
Avg day,$29,$34,$37,$46
Avg week,$143,$166,$181,$229
Avg month,$590,$689,$757,$969
Best day,$547,$547,$539,$600
Worst day,$-148,$-220,$-356,$-367
Worst week,$-103,$-155,$-412,$-340
Worst month,$-73,$-5,$-607,$-768
Losing months,1/10,1/10,1/10,1/10
Win days,47%,47%,56%,60%
Lose days,27%,26%,39%,35%
Empty days,26%,26%,5%,5%
Bad streak,7,7,5,4
Profit 20d,93%,95%,89%,89%
```

## 3-micro combos: C+3m / +F-E / +DB / +Both (`research/full_report_3m_combos.csv`), 0.01
```
,C+3m,C+3m+FE,C+3m+DB,C+3m+Both
Profit,"$7,288","$9,055","$8,322","$10,089"
Jan-Jun,"$4,109","$5,136","$4,105","$5,132"
Jul-Nov,"$3,179","$3,920","$4,217","$4,957"
Win,45%,41%,40%,39%
PF,1.99,1.54,1.53,1.40
Drop,-22%,-24%,-29%,-25%
Min bal,$536,$742,$608,$923
Safe bal,$804,"$1,113",$912,"$1,385"
Trades/day,4.1,8.9,10.4,15.2
Avg day,$34,$42,$38,$46
Avg week,$166,$206,$189,$229
Avg month,$689,$866,$792,$969
Best day,$547,$600,$591,$600
Worst day,$-220,$-282,$-174,$-367
Worst week,$-155,$-269,$-268,$-340
Worst month,$-5,$-334,$-439,$-768
Losing months,1/10,1/10,1/10,1/10
Win days,47%,56%,57%,60%
Lose days,26%,31%,36%,35%
Empty days,26%,13%,6%,5%
Bad streak,7,6,5,4
Profit 20d,95%,95%,86%,89%
```

## ADOPTED (owner, 27 Nov 2026): C + 3micro
Chosen version + one '3 micro inside SMA 10' re-entry after each stop (2x risk target; `research/micro3_reentry.py`,
`reentries(CH, 1, '2R')`). 2026 at 0.01: $7,288, 45% win, PF 1.99, drop -22%, min balance $536 (safe $804),
4.1 trades/day, 1 losing month (Apr -$5). Monthly C+3m: Jan $116, Feb $1,428, Mar $1,284, Apr -$5, May $560,
Jun $727, Jul $1,676, Aug* $399 (26-31 Aug only), Sep $493, Oct $268, Nov $344.
Owner: target is +$10,000 at 0.01 BEFORE lot sizing (then lot size to $20,000+).
C+3m, client connecting on a random day (0.01): in profit after 1 day 47% (26% flat), 3 days 69%, 5 days 72%,
10 days 87%, 20 days 95%. Typical (median) result: 1 day $0, 5 days +$93, 10 days +$232, 20 days +$625.
Worst: -$220 after 1 day, -$324 after 10 days, -$108 after 20 days. Longest bad streak 7 days, losing streak 4.
EA memory: zones live 20 days, so at start the bot must load about 30 days of M1 history to rebuild structures,
zones and open setups.

## 3-micro zone entry (MZ) (`research/micro3_zone.py`): after a 3-candle low G in the E-A zone that reached RSI 32, enter on '3 micro inside SMA 10' (within 4 h, before G breaks), stop $1 beyond G (min $5), 2x risk, up to 3 per structure. 120-581 trades tested; best = 3 per structure + RSI 32: 286 tr, 39% win, +$1,221.
Without RSI 32 and limits: 3,211 trades, drop -63% (rejected). Full report (`research/full_report_microzone.csv`):
```
,C+3m,C+3m+MZ,B+3m,B+3m+MZ
Profit,"$7,288","$8,509","$10,089","$11,310"
Jan-Jun,"$4,109","$4,991","$5,132","$6,013"
Jul-Nov,"$3,179","$3,518","$4,957","$5,296"
Win,45%,44%,39%,39%
PF,1.99,1.88,1.40,1.41
Drop,-22%,-26%,-25%,-27%
Min bal,$536,$552,$923,$851
Safe bal,$804,$828,"$1,385","$1,277"
Trades/day,4.1,5.4,15.2,16.5
Avg day,$34,$39,$46,$52
Avg week,$166,$193,$229,$257
Avg month,$689,$792,$969,$1072
Best day,$547,$670,$600,$740
Worst day,$-220,$-190,$-367,$-367
Worst week,$-155,$-137,$-340,$-257
Worst month,$-5,$-17,$-768,$-696
Losing months,1/10,1/10,1/10,1/10
Win days,47%,52%,60%,61%
Lose days,26%,29%,35%,35%
Empty days,26%,19%,5%,5%
Bad streak,7,7,4,4
Profit 20d,95%,97%,89%,92%
```
C+3m+MZ gains in both halves, min balance only +$16, worst day/week better, 97% of clients up after 20 days, fewer empty days (19%). Win -1 point, PF 1.99 -> 1.88, drop % -22 -> -26. Waiting for the owner.

## Owner's version: 3 micro AFTER the H break, on a pullback below H (`research/micro3_after_h.py`)
After H breaks, price comes back below H (G not broken), then 3 micro inside SMA 10 -> enter, 2x risk, 24 h window.
| Version | Year | Extra |
|---|---|---|
| C+3m | $7,288, 45%, -22%, PF 1.99 | |
| + after-H, 1 per H, stop at G | $7,619, -61% | 431 tr 35% +$331 |
| + after-H, 1 per H, stop below lowest since break | $7,850, -33%, PF 1.70 | 433 tr 36% +$562 |
| + after-H, 3 per H | $7,370-$7,441, -52 to -56% | +$82 to +$152 |
| B+3m | $10,089, 39%, -25% | |
| + after-H (any) | $8,403-$10,175, drops -33 to -56% | -$1,686 to +$86 |
Much weaker than the 3-micro zone entry before the H break (MZ: +$1,221, drop -26%). After-H rejected.

## Improvers side by side (`research/full_report_mz_afterh.csv`): C+3m / +MZ / +AfterH (1 per H, stop at lowest) / both
```
,C+3m,+MZ,+AfterH,+MZ+AfterH
Profit,"$7,288","$8,509","$7,850","$9,071"
Jan-Jun,"$4,109","$4,991","$4,703","$5,585"
Jul-Nov,"$3,179","$3,518","$3,147","$3,486"
Win,45%,44%,42%,42%
PF,1.99,1.88,1.70,1.67
Drop,-22%,-26%,-33%,-48%
Min bal,$536,$552,$615,$674
Safe bal,$804,$828,$922,"$1,011"
Trades/day,4.1,5.4,6.1,7.4
Avg day,$34,$39,$36,$42
Avg week,$166,$193,$178,$206
Avg month,$689,$792,$750,$853
Best day,$547,$670,$586,$709
Worst day,$-220,$-190,$-298,$-348
Worst week,$-155,$-137,$-224,$-219
Worst month,$-5,$-17,$-199,$-332
Losing months,1/10,1/10,1/10,1/10
Win days,47%,52%,49%,49%
Lose days,26%,29%,31%,36%
Empty days,26%,19%,19%,14%
Bad streak,7,7,6,6
Profit 20d,95%,97%,95%,98%
```
MZ is the clear improver; AfterH lowers Jul-Nov and raises drop/worst day; together the drop is -48%.

## ADOPTED (owner, 27 Nov 2026): C+3m+MZ = $8,509 at 0.01
C+3m + 3-micro zone entries (G in E-A zone with RSI <= 32, 3 micro inside SMA 10 within 4 h before G breaks,
stop $1 beyond G, 2x risk, up to 3 per structure; `research/micro3_zone.py`, micro_zone(per=3, g_rsi=32)).
44% win, PF 1.88, drop -26%, min balance $552 (safe $828), 5.4 trades/day. Owner: keep pushing to $10,000.

## Pushing C+3m+MZ to $10,000
- MZ settings grid (per 3/5/10, RSI 30/32/35, wait 4/8 h): best stays per 3, RSI 32 (+$1,221). RSI 30 or 35 give about half.
- 3m re-entry after MZ stops: +$297 to +$522 but drop -34%. MZ in F-E area: +$113/+$263. MZ below A: +$39/+$165, drop -31/-36%. Rejected.
- With the on-hold zones (`research/full_report_mz_fe_db.csv`):
```
,C+3m+MZ,+FE,+DB
Profit,"$8,509","$10,276","$9,543"
Jan-Jun,"$4,991","$6,017","$4,987"
Jul-Nov,"$3,518","$4,259","$4,556"
Win,44%,41%,39%
PF,1.88,1.54,1.53
Drop,-26%,-27%,-28%
Min bal,$552,$813,$577
Safe bal,$828,"$1,219",$866
Trades/day,5.4,10.2,11.7
Avg day,$39,$47,$44
Avg week,$193,$234,$217
Avg month,$792,$968,$895
Best day,$670,$740,$714
Worst day,$-190,$-282,$-183
Worst week,$-137,$-291,$-237
Worst month,$-17,$-262,$-367
Losing months,1/10,1/10,1/10
Win days,52%,56%,59%
Lose days,29%,35%,35%
Empty days,19%,10%,6%
Bad streak,7,6,4
Profit 20d,97%,96%,87%
```
C+3m+MZ+FE reaches $10,276 (both halves up), but win 41%, PF 1.54, min balance $813, worst month -$262.

## ADOPTED (owner, 27 Nov 2026): C+3m+MZ+FE = $10,276 at 0.01 (target reached)
C+3m+MZ plus the F-E zone (zone trades with G between F and E, 3-micro re-entries after their stops too).
2,221 trades, 41% win, PF 1.54, drop -27%, min balance $813 (safe $1,219), 10.2 trades/day.
Monthly: Jan $456 | Feb $2,383 | Mar $1,583 | Apr -$262 | May $1,237 | Jun $620 | Jul $2,274 | Aug* $591 |
Sep $446 | Oct $365 | Nov $582. Best days: 2 Feb $740, 3 Mar $644, 26 Mar $531. Worst: 6 Apr -$282,
23 Mar -$264, 15 Oct -$250. Winning / losing / empty days 56 / 35 / 10%. Longest losing-day streak 4 (twice),
longest bad streak 6. Losing trades in a row: longest 28 (many open together in one move); 10+ in a row 36 times.
Client in profit after 1/5/10/20 days: 56/73/86/96%; worst after 10 days -$544.

## OUT-OF-SAMPLE TEST: 2025 Q1 (2 Jan - 1 Apr 2025), never seen before (`research/run_chosen.py`)
Data: `data/XAUUSDb_M1_2025-01_2025-04.csv` (owner export). Run: CASTIMO_FILES=<file> python research/run_chosen.py.
Nothing changed in the rules.
| | C+3m+MZ | C+3m+MZ+FE |
|---|---|---|
| Profit (3 months) | $406 | **$763** |
| Win / PF | 39% / 1.30 | 41% / 1.38 |
| Drop / min balance | -13% / $173 | -13% / $159 (safe $238) |
| Trades/day | 5.4 | 8.5 |
| Avg month | $102 | $191 |
| Worst day / week | -$110 / -$90 | -$110 / -$110 |
| Losing months | 0/3 | 0/3 |
| Win / lose / empty days | 56 / 31 / 12% | 61 / 31 / 6% |
| Client up after 20 days | 93% | 100% |
Monthly (C+3m+MZ+FE): Jan $130, Feb $316, Mar $297. The rules STILL WORK on unseen data (every month positive,
PF 1.38), but profit is much smaller than 2026 (2026 Q1 = $4,422). Gold was ~$2,600-3,100 and much calmer in 2025,
and our stops/targets are fixed dollars ($20/$30), so fewer and smaller moves. Profit scales with gold volatility.

## OUT-OF-SAMPLE 2025 Jan-Jul (two owner exports) -- HONEST: the additions do NOT hold up
Data: `data/XAUUSDb_M1_2025-01_2025-04.csv`, `data/XAUUSDb_M1_2025-04_2025-08.csv`.
C+3m+MZ+FE monthly: Jan $130, Feb $316, Mar $297, Apr -$153, May -$74, Jun -$468, Jul $53 -> total **$82**,
PF 1.01, drop -53%, min balance $1,038, 4 of 8 months losing, client up after 20 days only 52%.
C+3m+MZ: $135, PF 1.02, drop -47%.
By part (`research/parts_report.py`), 2025 Jan-Jul:
| Part | Profit | Win |
|---|---|---|
| main | +$151 | 66% |
| E-A zone | +$142 | 36% |
| F-E zone | +$10 | 37% |
| MZ (3-micro zone entry) | -$42 | 32% |
| 3m re-entry | -$179 | 34% |
The core (main + E-A zone) still makes money on unseen data; the newer additions (3m re-entry, MZ, F-E) were fitted
to 2026 and lose or break even in 2025. Fixed-dollar stops/targets ($20/$30) were tuned on 2026 gold ($4,000-5,000,
very volatile); 2025 gold was $2,600-3,300. Next idea: scale stops/targets with price or volatility, test on both years.
2025 Jan-Jul full table (`research/report_2025.py`): C $292 (PF 1.08, drop -31%, min bal $503) | C+3m $176 |
C+3m+MZ $135 | C+3m+MZ+FE $82 (PF 1.01, min bal $1,038). Every addition makes 2025 worse. Losing months: Apr, Jun
(and 1-day Aug) for all versions; Jun 2025 is the worst month (-$251 to -$468).
Same months compared, Jan-Jul 2026 vs Jan-Jul 2025 (C | C+3m | C+3m+MZ | +FE):
profit 2026 $4,870 | $5,785 | $6,799 | $8,292 vs 2025 $292 | $176 | $135 | $82;
PF 2026 1.92 | 1.89 | 1.80 | 1.50 vs 2025 1.08 | 1.04 | 1.02 | 1.01;
min balance 2026 $374 | $536 | $552 | $813 vs 2025 $503 | $715 | $749 | $1,038;
avg month 2026 $696 | $826 | $971 | $1,185 vs 2025 $37 | $22 | $17 | $10.
Both years lose in April; 2025 also loses in June. The strategy earns about 20x more in 2026 than in 2025.

## Trying to fix 2025 (`research/scaled_main.py`, `research/regime.py`)
Daily range: 2025 $36-64 (1.3-1.9% of price) vs 2026 $92-167 (2.3-3.4%).
1. Main stop/target/extra scaled by 20-day range / $110: 2025 C $292 -> $193, Full $82 -> -$11; 2026 unchanged
   (C $6,374, Full $10,233). Does not help.
2. Trade only when the 20-day range is >= 1.5% or 2% of price: 2025 C -$328 / -$117, Full -$872 / -$441 (worse:
   calm Q1 2025 was the good part); 2026 C $5,874 / $5,689, Full $9,649 / $9,038. Does not help.
Conclusion: the 2026 results are much better than what 2025 shows. The core C keeps a small edge in 2025 (PF 1.08);
the 2026 additions (3m, MZ, F-E) do not. Next: tune on 2025 + 2026 together and keep only rules that help BOTH years.

## BOTH YEARS as one test set (`research/both_build.py`, `both_eval.py`, `both_search.py`, `both_report.py`)
Every part built without filters on 2025 Jan-Jul and 2026 Jan-Nov, tagged, then combined. With filters:
- Profitable in BOTH years: main (+$151 / +$1,540), E-A zone 40 (+$142 / +$4,761), MZ (+$35 / +$515), double bottom (+$968 / +$1,029), 3m after MZ (+$78 / +$670), 3m after F-E (+$74 / +$989), 3m after DB (+$584 / +$13). F-E zone itself +$10 / +$650.
- Losing in 2025: 3m re-entry after main (-$100) and after E-A zone (-$327).
- Filters: RSI-50 and hours help both years overall; the consolidation filter costs 2025 money but raises 2026 PF.
Search over 4,096 valid combinations (re-entries only with their own base part), PF 2025 >= 1.1 and 2026 >= 1.4.
**Robust = main + E-A zone 40 + MZ + double bottom + 3m after MZ + 3m after DB, all filters.**
```
,Chosen 25,Robust 25,Chosen 26,Robust 26
Profit,$-16,"$1,957","$10,563","$8,527"
Jan-Jun,$-16,"$1,957","$5,962","$4,409"
Jul-Nov,$0,$0,"$4,601","$4,118"
Win,36%,37%,40%,38%
PF,1.00,1.13,1.50,1.46
Drop,-62%,-20%,-33%,-28%
Min bal,"$1,301",$616,$951,$774
Safe bal,"$1,952",$925,"$1,426","$1,161"
Trades/day,13.6,23.4,11.0,12.1
Avg day,$-0,$13,$49,$39
Avg week,$-1,$63,$240,$194
Avg month,$-2,$245,$981,$790
Best day,$211,$276,$878,$743
Worst day,$-285,$-280,$-433,$-164
Worst week,$-411,$-399,$-294,$-199
Worst month,$-471,$-391,$-658,$-475
Losing months,4/8,3/8,1/10,1/10
Win days,48%,58%,55%,55%
Lose days,48%,39%,34%,39%
Empty days,4%,3%,12%,6%
Bad streak,5,6,6,5
Profit 20d,45%,70%,93%,85%
```
(Chosen here = $10,563 / -$16 because re-entries are counted per trade; earlier runs gave $10,276 / $82.)

## Own chart review of 6 Jun 2025 (worst 2025 day) -> two fixes tested on both years (`research/both_fixes.py`)
6 Jun 2025: gold fell all day (3375 -> 3307). Main correctly SOLD at 09:44 (-$30), but the E-A zone took 9 BUYS
(4 setups + stacked copies), all lost (-$115). Fix A: no stacked copies. Fix B: no zone-type trade against the
main strategy's latest direction.
| | C 25 | C 25 A+B | C 26 | C 26 A+B | Robust 25 | Robust 25 B | Robust 26 | Robust 26 B |
|---|---|---|---|---|---|---|---|---|
| Profit | $292 | $232 | $6,300 | $3,918 | $1,957 | $1,280 | $8,527 | $7,516 |
| PF | 1.08 | 1.17 | 2.06 | 2.24 | 1.13 | 1.17 | 1.46 | 1.64 |
| Min bal | $503 | $264 | $374 | $203 | $616 | $630 | $774 | $555 |
| Worst month | -$251 | -$103 | -$73 | +$14 | -$391 | -$103 | -$475 | -$174 |
Both fixes make the bot SAFER (smaller worst months, higher PF) but cost profit in both years. Under the owner's
profit-first rule they are not adopted; kept as a "safe mode" option.

## 'Max' versions: keep 2026 above $10,000 AND make 2025 strong (`research/both_report_max.csv`)
Max = main + E-A zone + F-E zone + MZ + double bottom + 3m re-entries after MZ, F-E, DB and main; RSI-50 and hours filters, NO consolidation filter. Max+ also adds 3m after E-A.
```
,Max 25,Max+ 25,Max 26,Max+ 26
Profit,"$4,380","$3,999","$10,753","$12,342"
Jan-Jun,"$4,380","$3,999","$5,283","$6,234"
Jul-Nov,$0,$0,"$5,470","$6,107"
Win,37%,36%,36%,36%
PF,1.15,1.12,1.22,1.23
Drop,-32%,-32%,-74%,-86%
Min bal,$818,"$1,074","$1,342","$1,416"
Safe bal,"$1,226","$1,611","$2,012","$2,124"
Trades/day,46.5,49.7,30.1,32.4
Avg day,$29,$26,$50,$57
Avg week,$141,$129,$244,$280
Avg month,$548,$500,$1007,$1164
Best day,$395,$395,$855,$1088
Worst day,$-445,$-418,$-493,$-493
Worst week,$-366,$-423,$-510,$-559
Worst month,$-72,$-181,$-562,$-1010
Losing months,1/8,2/8,1/10,1/10
Win days,61%,60%,59%,59%
Lose days,38%,39%,39%,39%
Empty days,1%,1%,2%,2%
Bad streak,5,5,8,6
Profit 20d,84%,85%,91%,88%
```
Max: 2025 $4,380 (PF 1.15, 1 losing month) and 2026 $10,753 (PF 1.22). Cost: ~30-46 trades/day, min balance $818-$1,342, worst day ~-$450-$490, 2026 drop -74%.

## OWNER DECISION (27 Nov 2026): KEEP C+3m+MZ+FE ($10,276 in 2026)
"We keep this since we are not trading 2025 any more." Robust and Max stay ON HOLD as calmer-market options.
Risk noted to the owner: in a calm market like 2025 Jan-Jul this version broke even ($82, -$16 per-trade method).
Watch live results; if gold's daily range falls toward 2025 levels (~$40-65), switch to Max or Robust.

## LOT SIZING on the chosen version C+3m+MZ+FE, 2026 (`research/lot_final.py`)
Lot set from the closed-trade balance at each entry. Closed trades only, no slippage; compounding results above
~$50k are not realistic (broker limits, slippage, stacked copies), so read them as "very strong", not as promises.
| Start | Rule | End | Worst drop | Lowest |
|---|---|---|---|---|
| $1,000 | fixed 0.01 | $11,276 | -27% | $854 |
| $1,000 | 0.01 per $2,000 + half after 3 losses | $54,009 | -27% | $854 |
| $1,000 | 0.01 per $1,500 + half after 3 losses | $93,939 | -36% | $854 |
| $1,000 | 0.01 per $1,000 (+half) | $1.1M ($725k) | -61% (-49%) | $854 |
| $1,000 | 0.01 per $500 / old cushion rule | $21M | -93% | $790 |
| $2,000 | fixed 0.01 | $12,276 | -14% | $1,854 |
| $2,000 | 0.01 per $2,000 + half after 3 losses | $67,704 | -25% | $1,854 |
| $2,000 | 0.01 per $1,500 + half after 3 losses | $169,533 | -33% | $1,854 |
The old rule (0.01 per $500) is far too aggressive (-93% drop). Recommended for clients: 0.01 per $2,000 (balance)
with half lot after 3 losses in a row; for growth: 0.01 per $1,500 with the same safety rule.
Prop $100,000 (fixed lots, limits 4%/day, 10% total): 0.05 = +$51k, max drop $3.2k (3.2%), worst day ~$1.4k |
0.07 = +$72k, $4.2k (4.2%), worst day ~$2.0k | 0.09 = +$92k, $5.1k, worst day ~$2.5k | 0.12 = +$123k, $6.3k,
worst day ~$3.4k. Time to +8% ($8,000): 0.07 median 30 days (worst 79); 0.09 median 23 days (worst 70).
Recommended prop lot: 0.07 (half the drawdown limit, worst day half the daily limit).

## $200 clients (`research/start_200.py`, `research/mode_200.py`, grid in `research/mode_200.csv`), 2026, 0.01
Every possible start day checked (closed trades). Chosen version: a $200 account blows on 23% of start days
(C+3m+MZ 11%, C 6%). "$200 mode" search (version, no copies, max open trades, stop cap):
| $200 mode | Profit | Blown | Lose $150+ | Worst dip |
|---|---|---|---|---|
| C, no copies | $4,378 | 0% | 6% | -$193 (almost all of $200) |
| C, 1 trade at a time | $2,786 | 0% | 7% | -$187 |
| **C+3m+MZ, max 2 open, stop <= $15** | **$2,000** | **0%** | **0%** | **-$112** |
Recommended $200 mode: C+3m+MZ, at most 2 trades open, skip trades with stops over $15, 0.01 lot.
About $2,000 a year on $200 (+1,000%), worst dip -$112 from any start day. Move to the full version at ~$1,200+.
$400 start at 0.01 (2026, every start day): Chosen blows on 5.5% of start days (worst dip -$745), C+3m+MZ 2.8%
(-$581), C 0% (-$331, too close). "$400 mode" = C without copies: $4,378/yr, never blown, worst dip -$193
(keeps ~$200 left). Alternative C+3m+MZ one trade at a time: $3,135, worst dip -$229.
Levels: $200-399 -> $200 mode; $400-1,199 -> $400 mode; $1,200-1,999 -> full 0.01; $2,000+ -> 0.01 per $2,000.

## $100 mode (`research/mode_100.csv`), 2026, 0.01, every start day
Best never-blown modes with worst dip <= $70: C+3m+MZ, 1 trade at a time, skip stops over $15: $1,606/yr, worst dip
-$70 | Chosen, 1 at a time, stop <= $10: $1,262, -$63 | C, no copies, max 2 open, stop <= $10: $1,070, -$62.
Margin note: one 0.01 gold position needs ~$45 margin at 1:100 (gold ~$4,500), so $100 accounts need 1 trade at a
time or higher leverage. The EA can switch modes automatically by balance before each trade:
$100-199 -> $100 mode | $200-399 -> $200 mode | $400-999 -> $400 mode | $1,000+ -> full 0.01 | $2,000+ -> 0.01 per $2,000.

## FINAL CHECK (27 Nov 2026, `research/final_check.py`): everything re-run from scratch, all numbers reproduced
Tests: 15 passed. Chosen C+3m+MZ+FE 2026 at 0.01: $10,276, 41% win, PF 1.54, drop -27%, min balance $813 (safe
$1,219), 10.2 trades/day, 1 losing month (Apr -$262), 96% of clients up after 20 days. Chosen + double bottom:
$11,310, PF 1.41, worst month -$696 (on hold).
Modes (every start day, 0.01): $100 mode $1,606 (worst dip -$70) | $200 mode $2,000 (-$112) | $400 mode $4,378
(-$193) | $1,000 full $10,276 (-$745); none blown.
Lot sizing: $1,000 -> $54,009 (-27%), $2,000 -> $67,704 (-25%) with 0.01 per $2,000 + half after 3 losses.
Prop $100k at 0.07: +$71,931, worst drop 4.2%.
Caveats: one year of data (2026); in calm 2025 this version broke even (Robust/Max on hold for that case);
closed-trade results, no extra slippage. Next: build the MT5 EA and run it on demo.

## $100 mode details (C+3m+MZ, 1 trade at a time, stops <= $15), 2026, 0.01
401 trades: 1.8/day, 9.1/week, 40/month. Wins 47% (avg +$18.6), losses avg -$9.1, PF 1.84. Profit $1,606:
$7.4/day, $36/week, $156/month. Best day $99, worst day -$50, worst week -$22, worst month +$73: NO losing month.
Win / lose / empty days 46 / 24 / 31%. From $100 on 1 Jan: $1,706 at the end, lowest $81, biggest peak-to-low drop
$85. From any start day: worst dip -$70, typical -$11. Monthly: Jan $81, Feb $157, Mar $166, Apr $83, May $257,
Jun $73, Jul $394, Sep $136, Oct $122, Nov $87.

## Owner's lot ladder: 0.01 per $200 (0.05 at $1,000, 0.10 at $2,000 ...) and 0.01 per $100, 2026
| Trades | Start | 0.01 per $200 | 0.01 per $100 |
|---|---|---|---|
| Chosen (all trades, stacking) | $200 | BLOWN | BLOWN |
| Chosen | $1,000 | BLOWN | BLOWN |
| $100 mode (1 trade at a time, stops <= $15) | $200 | huge, worst drop -32%, lowest $181 | huge, -59% |
| $100 mode | $1,000 | huge, -35%, lowest $909 | huge, -59% |
The ladder blows the full version (many trades open at once, copies, big stops). It only works with the
one-trade-at-a-time mode with small stops: 0.01 per $200 gives a -32 to -35% worst drop. End balances are
unrealistic (compounding to millions); treat as 'very strong growth'.
$200 mode (C+3m+MZ, max 2 open, stops <= $15) with 0.01 per $200 from $200, monthly end balance: Jan $309, Feb $417,
Mar $709, Apr $752, May $2,728, Jun $3,125, Jul $32,031, Aug $45,249, Sep $106,322, Oct $261,483, Nov $284,160.
Worst drop -47%, lowest $178. Lots pass 1.00 from July: not realistic (slippage, broker limits); cap the lot.
Same with the lot CAPPED at 0.20 (owner): Jan $309, Feb $417, Mar $709, Apr $752, May $2,728, Jun $3,160, Jul $14,092,
Aug $15,631, Sep $19,614, Oct $24,123, Nov $24,928. $200 -> ~$24,900 in 2026. Worst drop -47% (largest $ drop
$2,208), lowest $178. At 0.20 a typical month is +$800 to +$4,500 (Jul +$10,900).
$400 mode (C, no copies) with 0.01 per $200 capped at 0.20, from $400 (`research/mode_ladder.py 400 400`):
Jan $492, Feb $9,771, Mar $17,338, Apr $16,800 (-$538), May $22,406, Jun $29,369, Jul $44,772, Aug $46,037,
Sep $58,341, Oct $60,359, Nov $68,261. Worst drop -55% (largest $4,350), lowest $199 (half the start).

## Owner's lot rule: 0.01 below $500, 0.02 at $500, +0.01 per extra $500 (lot = floor(balance/500)+1), 2026
| Mode | Start | Cap 0.20: end | Worst drop | Lowest |
|---|---|---|---|---|
| $100 mode | $200 | $8,277 | -25% | $181 |
| $100 mode | $1,000 | $19,414 | -17% | $949 |
| $200 mode | $200 | $15,140 | -35% | $178 |
| $200 mode | $1,000 | $25,767 | -26% | $941 |
| $400 mode | $200 | $53,632 | -83% | $37 |
| $400 mode | $1,000 | $66,902 | -40% | $636 |
| Full chosen | $200 | $152,076 | -85% | $54 |
| Full chosen | $1,000 | $175,168 | -64% | $644 |
Without the cap the full version reaches millions with -93 to -94% drops (not realistic). With this rule the
one-trade / two-trade modes stay safe (-17% to -35%); the full version and $400 mode become too risky.

## FINAL PLAN (owner: "we go back to our best"), 27 Nov 2026
Strategy: C+3m+MZ+FE. Lot sizing: 0.01 per $2,000 of balance, half lot after 3 losses in a row (back after a win).
Small accounts use automatic modes at 0.01: $100-199 $100 mode | $200-399 $200 mode | $400-999 $400 mode |
$1,000-1,999 full 0.01 | $2,000+ full, 0.01 per $2,000. Prop $100k: 0.07 fixed.
2026: $1,000 -> ~$54,000 (-27%), $2,000 -> ~$67,700 (-25%), prop +$72k (-4.2%). Next: build the MT5 EA.

## CORRECTION (27 Nov 2026): small-account modes were too optimistic (`research/modes_fixed.py`, `modes_fixed.csv`)
Bug: the mode tests estimated each trade's stop from its result (loss = stop, win = target/2). That is exact for
2x-risk trades but WRONG for main trades (stop always $30): main winners passed the "$15 stop cap" while main losers
were skipped. Recomputed with the true stop:
| Mode (2026, 0.01) | Old (wrong) | Corrected |
|---|---|---|
| $100 mode (C+3m+MZ, 1 open, stop <= $15) | $1,606, never blown at $100, worst -$70 | $820, blown 2.3% of starts at $100, worst -$121 |
| $200 mode (C+3m+MZ, 2 open, stop <= $15) | $2,000, worst -$112 | $1,162, blown 0.8% at $200, worst -$201 |
| $400 mode (C, no copies) | $4,378 | $4,378 (unchanged, no cap) |
Corrected best: $200-399 -> C+3m+MZ, 1 trade at a time, stop <= $15: $820/yr, never blown at $200, worst dip -$121.
$100 accounts: only C+3m+MZ 1 open stop <= $10 never blows ($223/yr, worst dip -$96): not recommended; minimum $200.
Also wrong (used the biased list): "$200 mode 0.01 per $200 capped 0.20 -> $24,928" and the $500-step rule on the
$100/$200 modes. Corrected $200 mode with 0.01 per $200 capped 0.20 from $200: $4,249 at the end of Nov, worst drop
-42%, lowest $159. $400 mode, full version, lot sizing and prop results are NOT affected.
Owner (27 Nov 2026): keep ALL modes in the EA, including the $100 mode; the bot must keep trading on any balance
(even $10-$20), using the smallest mode, and only skip a trade when the broker's free margin is not enough.
EA ladder: below $200 -> C+3m+MZ, 1 trade at a time, stops <= $10 | $200-399 -> same, stops <= $15 |
$400-999 -> C without copies | $1,000+ -> full, 0.01, then 0.01 per $2,000 (half lot after 3 losses).

## Stop-and-reverse after a stop (owner's idea; `research/flip_after_stop.py`), 2026, 0.01
When a trade hits its stop, trade the other way at once from the stop price, same risk, target 1x or 2x that risk.
| | Chosen | +flip 1R | +flip 1R filt | | +Both | +flip 1R |
|---|---|---|---|---|---|---|
| Profit | $10,276 | **$11,769** | $11,260 | | $11,310 | $13,177 |
| Win | 41% | 44% | 44% | | 39% | 43% |
| PF | 1.54 | 1.47 | 1.48 | | 1.41 | 1.36 |
| Drop (% of a $1,000 start) | -27% | -42% | -35% | | -27% | -50% |
| Min balance (biggest $ drop) | $813 | **$676** | $686 | | $851 | $682 |
| Worst day | -$282 | -$407 | -$418 | | -$367 | -$413 |
| Worst month | -$262 | **+$53** | -$132 | | -$696 | -$311 |
| Losing months | 1/10 | **0/10** | 1/10 | | 1/10 | 1/10 |
Flips: 895, 54% win, +$1,493 (1R); 2R flips win only 34% (+$361). Flip 1R on Chosen: +$1,493, higher win rate,
smaller biggest $ drop, no losing month; but a deeper early % drop and worse worst day. Waiting for the owner.
Flip with a DOUBLE lot (0.02 on the flip, normal lot elsewhere), Chosen 2026: $13,262 (vs $11,769 at 0.01 flips,
$10,276 without), 44% win, PF 1.43, drop -60%, biggest $ drop $937, worst day -$691, worst week -$418, worst month
+$13, no losing month, clients up after 20 days 92%. More money, but the worst day more than doubles.

## Flip grid: stop size and target, both versions, both halves (`research/flip_grid.py`, `research/flip_grid.csv`)
Flip stop = 0.5x / 1x / 1.5x the losing trade's risk; target = 0.5x-2x the flip stop. Most settings add money only in
Jan-Jun and slightly reduce Jul-Nov (e.g. Chosen 1x/1x: H1 +$1,761, H2 -$268). Balanced settings (both halves up):
- Chosen, flip stop 0.5x, target 1.5x: $11,276 (H1 $6,970 / H2 $4,306 vs $6,017 / $4,259), win 42%, PF 1.50,
  biggest $ drop $610 (vs $813), worst day -$352, worst month -$251, better in 8 of 10 months.
- +Both, flip stop 0.5x, target 2x: $12,900 (H1 $7,571 / H2 $5,328 vs $6,013 / $5,296), PF 1.39, biggest $ drop $766
  (vs $851), worst month -$617 (vs -$696), better in 9 of 10 months.
Highest profit but unbalanced: Chosen 1.5x/0.75x $12,089 (H2 flat, worst day -$484); 1x/1x $11,769 (H2 lower).

## EA v1.10 (27 Nov 2026, owner): balanced flip added; no maximum lot; risk shrinks as the account grows
Flip after a stop of a main/zone trade: opposite trade, stop 0.5x the stopped trade's risk, target 1.5x (full mode
and prop). Lot: <= $10k 0.01 per $2,000; $10k-50k 0.05 + 0.01 per $4,000; > $50k 0.15 + 0.01 per $8,000
($100k = 0.21, $500k = 0.71); half lot after 3 losses; small-account modes unchanged; prop 0.07 per $100k.

## $200 account: flips in the $200 mode? (`research/mode200_flip.py`), 0.01
The EA (v1.10) turns flips off below $1,000 by design (flips were only tested on the full version). Checked now:
| | January 2026 | All 2026 |
|---|---|---|
| $200 mode, no flips (EA today) | $200 -> $222 (lowest $159), 23 trades | $200 -> $1,030 (lowest $159) |
| $200 mode with flips | $200 -> $191 (lowest $157), 30 trades, 7 flips | $200 -> $1,133 (lowest $157), 101 flips |
Flips in the $200 mode: worse in January, +$103 over the year, win 43% vs 41%. Small gain; kept off for small accounts.

## Flips in every account mode (`research/flip_all_modes.py`), 2026, 0.01, every start day
| Mode | Flips off | Flips on | Blown (off / on) | Worst dip (off / on) | Jan (off / on) |
|---|---|---|---|---|---|
| $100 mode | $225 | $248 | 0% / 1.9% at $100 | -$94 / -$103 | $11 / -$9 |
| $200 mode | $830 | $933 | 0% / 0% | -$121 / -$100 | $22 / -$9 |
| $400 mode | $4,409 | $4,740 | 0% / 0% | -$193 / -$204 | $168 / $231 |
| Full | $10,276 | $11,276 | 0% / 0% | -$745 / -$577 | $529 / $634 |
EA v1.11: flips ON from $200 up (and prop), OFF in the $100 mode (it adds blow-ups there).

## First EA tester run (owner, "Castimofx Jesus" = CastimofxSweep v1.11), XAUUSDb M1, Jan 2026, $1,000, 1-min OHLC
Report: net -$118.77, 85 trades, PF 0.84, max equity drop $477 (37%). Compared with the Python backtest for January
(+$561 at 0.01; `research/backtest_jan2026_trades.csv` vs `research/ea_test_jan2026_trades.csv`):
| Jan 2026 | EA trades | EA $ | Backtest trades | Backtest $ |
|---|---|---|---|---|
| main + re-entries | 12 | -$89 | 14 | -$110 |
| zone E-A (+ re) | 20 | +$74 | 26 | +$298 |
| zone F-E (+ re) | 15 | +$68 | 50 | +$327 |
| 3 micro | 4 | -$37 | 19 | +$73 |
| MZ | 10 | -$52 | 17 | -$133 |
| flips | 24 | -$61 | 52 | +$105 |
Causes found: (1) the balance fell below $1,000, so the EA switched to the $400 mode (no F-E, 3 micro or MZ) for
much of the month: by design, but not comparable with the backtest; (2) BUG: a setup could be traded twice when the
broker filled the pending order but the bar check did not see the break (Z23, F42, F36, Z43 ...). Fixed in v1.12:
a key that got a real fill since it was armed is not placed again. Next test: deposit $3,000 (full mode, 0.01).
Flips in the EA test (Jan 2026): 24 flips, only 5 won (21%), -$61. The backtest flip check started on the bar AFTER
the stop (it ignored the rest of the stop bar). Worst case (the stop bar counts): flips win 38% and add only +$319
for 2026 (not +$1,001); Jan +$82. So the flip gain was partly a backtest artifact; real flips look weaker.
Watch flips in the next EA test before trusting them.

## Hedge at the stop instead of closing (owner's question; `research/hedge_at_stop.py`), 2026, 0.01
At the stop level the trade stays open and an opposite hedge (same lot) opens. Hedge target k x risk; the hedge closes
at -1R if price returns to the entry; re-hedge only after price comes back above the stop level and crosses it again
(the first version re-hedged beyond the stop level and gave impossible results: fixed). Original closes at its target
or a hard stop m x risk. Worst-case order inside each bar (bad events first).
| | Chosen | k0.5 m2 | k0.5 m3 | k1 m2 | k1 m3 |
|---|---|---|---|---|---|
| Profit | $10,276 | $12,225 | $14,472 | $11,800 | $13,686 |
| Jan-Jun / Jul-Nov | $6,017 / $4,259 | $7,088 / $5,137 | $7,958 / $6,513 | $6,750 / $5,049 | $7,125 / $6,561 |
| Win / PF | 41% / 1.54 | 49% / 1.59 | 56% / 1.61 | 48% / 1.60 | 54% / 1.61 |
| Biggest $ drop | $813 | $1,339 | $1,806 | $1,138 | $1,609 |
| Worst day | -$282 | -$509 | -$849 | -$517 | -$766 |
| Worst month / losing months | -$262 / 1 | +$5 / 0 | -$144 / 1 | -$414 / 1 | -$533 / 1 |
+Both: $11,310 -> $14,733 (k0.5 m2) / $18,859 (k0.5 m3). Hedging adds money in both halves and raises the win rate,
but the account carries 2 positions per stopped trade, so the biggest $ drop and worst day grow a lot. Caveats:
brokers with FIFO / no-hedge rules (and some prop firms) do not allow it; swaps on longer holds not counted.
**ON HOLD #5 (owner, 27 Nov 2026):** hedge at the stop (k0.5, hard stop 2x): $12,225 / +Both $14,733, win 49%,
no losing month, but biggest $ drop $1,339 and worst day -$509; needs hedging allowed by the broker.

## Scale-in at different prices, each add with its own target (owner; `research/scale_in.py`), 2026, 0.01
How the bot stacks today: copies from overlapping structures are the SAME trade (same price, stop and target); other
trades (zones, re-entries, MZ, 3 micro) are at different prices and each has its own stop and target.
Test: when a trade goes a x risk against us, add a trade there (same stop level, own target rr x its own risk).
| | Chosen | add 0.5R, 1x | add 0.5R, 2x | add 0.33R x2, 1x | add 0.33R x2, 2x |
|---|---|---|---|---|---|
| Profit | $10,276 | $10,176 | $10,718 | $11,052 | $10,863 |
| Win / PF | 41% / 1.54 | 44% / 1.43 | 38% / 1.43 | 46% / 1.40 | 37% / 1.35 |
| Biggest $ drop | $813 | $931 | $833 | $876 | $1,451 |
| Worst day / month | -$282 / -$262 | -$369 / -$558 | -$393 / -$709 | -$438 / -$697 | -$481 / -$933 |
Adds win about half the time with 1x targets but add little money (best +$776) and make worst days and months much
deeper (same on +Both). Not adopted.

## Shared take profit for trades open together (owner; `research/shared_tp.py`), 2026, 0.01
Rules for main, E-A and F-E trades open in the same direction: own TP (today; replica $10,249 vs $10,276), 'first'
(a new trade takes the oldest open trade's TP), 'newest' (all move to the newest trade's TP). Own stops kept.
| | own | first | newest | | +Both own | first | newest |
|---|---|---|---|---|---|---|---|
| Profit | $10,249 | $11,106 | $9,576 | | $11,282 | $12,374 | $10,276 |
| Jan-Jun | $5,990 | $5,733 | $6,042 | | $5,986 | $5,912 | $5,535 |
| Jul-Nov | $4,259 | $5,373 | $3,534 | | $5,296 | $6,462 | $4,741 |
| Win / PF | 41% / 1.54 | 40% / 1.58 | 40% / 1.51 | | 39% / 1.41 | 38% / 1.46 | 38% / 1.38 |
| Biggest $ drop | $813 | $874 | $686 | | $862 | $904 | $820 |
'First TP' adds ~$860-1,090 but only in Jul-Nov (Jan-Jun slightly lower), win rate not higher, drop slightly bigger.
'Newest TP' is worse. Each trade keeping its own TP stays. Not adopted.

## Shared TP test (27 Nov 2026) - REJECTED, keep each trade's own TP
Chosen 2026 at 0.01: own TP $10,249 | first-trade TP $11,106 (unbalanced: Jul-Nov weaker) | newest TP $9,576.
+Both: own $11,282 | first $12,374 | newest $10,276 (`research/shared_tp.py`).
Newest-TP effect on older trades: 186 of 1,525 changed; of 169 winners, 79 became smaller wins and 19 became losses;
17 losers became wins; none closed at a tiny profit (<$3; TP is never set below entry). Net -$673.

## Second EA tester run (owner, v1.12), XAUUSDb M1, 1-29 Jan 2026, $3,000 (full mode, 0.01), 1-min OHLC
Report: net +$102 (+$136 before commission/swap), 148 trades, win 36%, PF 1.08, max equity drop $629 (18.6%).
Trades: `research/ea_test_jan2026_3k_trades.csv`. Python backtest same days: +$608, 159 trades.
| Jan 1-29 | EA | Backtest |
|---|---|---|
| main + re | 12, -$188 | 14, -$110 |
| zone E-A + re | 28, +$210 | 24, +$289 |
| zone F-E + re | 24, -$60 | 42, +$161 |
| 3 micro | 28, +$246 | 17, +$210 |
| MZ | 22, +$15 | 13, +$51 |
| flips | 34, -$87 (won 29%) | 49, +$7 |
The double-fill bug is gone. Biggest gap: F-E zone - the EA placed no F-E orders on 8-9, 14, 23, 27 Jan where the
backtest traded (about +$120 there), and took some the backtest did not. Likely a filter/zone difference; needs the tester
Journal log (zone lines) to find. Flips lost again (2nd test).

## Commission and swap (from the owner's v1.12 tester report, HFM XAUUSDb)
Real costs at 0.01: commission $0.10 per trade; swap on buys -$0.74 per night (x3 Wednesday night); sells paid no swap
in the test (worst case assumed -$0.74 too). Backtest already includes the spread. 2026 at 0.01:
| | Chosen | +Both |
|---|---|---|
| Gross (backtest) | $10,276 | $11,310 |
| Commission | -$222 | -$359 |
| Swap (sells free / sells charged) | -$176 / -$388 | -$191 / -$483 |
| Net | $9,878 / $9,666 | $10,760 / $10,467 |
Costs take 4-7%, not the profit. The EA vs backtest gap in the Jan test ($136 vs $608 gross) is trade differences
(F-E zone, flips, mains), not costs: costs were only $34 that month.

## EA v1.13 (28 Nov 2026, owner): flips switched OFF
Flips lost in both EA tests (Jan 2026: 21% and 29% win, -$61 and -$87). Code kept; `FLIPS_ON = false`.

## IMPORTANT: zone backtest fills were partly unreal (found from the owner's v1.13 Journal, 28 Nov 2026)
The Journal showed many zone triggers with no real order (e.g. F-E #48, #50, #62, #64, Jan 2026). Cause: when the
swing high H is confirmed, price is often already above H. The EA cannot place a buy stop there and skips. The Python
backtest still filled those trades AT H, a price that was already gone. `research/zone_gap_check.py`, 2026, 0.01:
| | E-A zone | F-E zone |
|---|---|---|
| Trades / already past the level | 613 / 226 (37%) | 812 / 309 (38%) |
| Backtest (as before) | $4,761 | $650 |
| Skip those (EA today) | $2,996 | -$490 |
| Enter at market instead | $4,220 | $16 |
So about $2,900 of the chosen $10,276 came from impossible fills; realistic is about $7,400 (skip) to $9,100 (market).
F-E is worth about $0 once fills are real. Next: EA enters at market when already past the level; re-check F-E.

## GROSS vs NET FIX (28 Nov 2026): MT5 full year v1.13 vs backtest
MT5 v1.13, 2026.01.01-11.27, $3,000, lots grew 0.01->0.05: net $7,110, PF 1.15, 36% win, 2,073 trades.
Per 0.01 (each trade scaled to 0.01, costs included; `research/mt5_report_tags.py`): **+$4,623** (costs -$408).
Backtest with old fills (at the level even if price already passed): $10,276. With REAL fills (zone entries
bought at the bar open when price already passed, skip if > 0.5x risk; `CASTIMO_FILL=market`,
`research/real_fills.py`): Chosen **$9,176**, 40% win, PF 1.47, min balance $880 (safe $1,320);
+Both $10,209, PF 1.37, min $903 (safe $1,354).
By type, 2026 at 0.01 (`research/real_fills_by_type.py`):
```
type  MT5 tr   MT5 $  BT tr   BT $
Z      268   1,229    379   2,803
ZR     163     889    204   1,443
F      336    -750    514     -39
FR     176      85    284      45
M+R     98     783    100   1,540
ZM     418     432    286   1,221
3M     614   1,956    402   2,164
All  2,073   4,623  2,169   9,177
```
The F-E zone loses in both (MT5 -$750). MT5 takes fewer zone trades (skipped when price is past the level:
fixed in EA v1.14 = market entry) but MORE micro-zone (ZM) and 3-micro trades than the backtest.
EA v1.14: market entry when price is already past the level (same stop/target, max 0.5x risk away) +
input InpFixedLot (test only, 0 = automatic lots) so MT5 and Python can be compared at 0.01.

### Trade-by-trade match, MT5 v1.13 vs backtest (28 Nov 2026, all at 0.01)
Trades taken by BOTH give the same money (main $815 vs $783, Z $2,652 vs $2,711, ZM $1,031 vs $1,084,
3M $2,037 vs $2,107): the EA copies the rules correctly. The gap comes from trades only one side has:
- Backtest data holes: no M1 for Dec 2025, 1-25 Aug 2026 and 25-27 Nov, and each data file restarts the
  structures. MT5 sees those structures; their trades mostly LOST (MT5-only ZM 136 tr -$599, Z 163 tr -$533,
  most in Aug-Nov). So the backtest was too optimistic there.
- MT5 missed winners the backtest has (main 27 tr +$757 incl. 6 Feb +$350; zone 315 tr +$1,535): partly the
  "price already past the level" skips, fixed in v1.14.
Monthly MT5 vs backtest: Jan -$278/+$391, Feb $1,413/$2,251, Mar $1,340/$1,396, Apr $242/-$312, May $681/$997,
Jun $604/$470, Jul $1,138/$2,040, Aug -$114/$590, Sep $21/$459, Oct -$351/$309, Nov -$73/$586.
MT5 at 0.01 by removal: all $4,623 (min $761) | no F/FR $5,289, PF 1.41 (min $780, safe $1,170) |
no F/FR/ZM $4,857, PF 1.52 (min $534). EA v1.15: F-E zone switched off (FE_ON = false).
Next: one continuous M1 file (Dec 2025 - Nov 2026) so the backtest sees exactly what MT5 sees.

### Daily green test (28 Nov 2026, owner: clients need money every day; `research/daily_green.py`)
Real fills, F-E off, 2026 at 0.01. Smaller targets for zone/MZ/3-micro (main unchanged):
```
            C 2R   +DB 2R  C 1R   +DB 1R  C 0.5R +DB 0.5R
Profit      $7,998 $9,032  $3,678 $4,531  $2,494 $3,500
Trade win   44%    39%     54%    46%     69%    56%
Green days  49%    58%     51%    58%     52%    57%
Avg day     $37    $41     $17    $21     $11    $16
Worst day   -$192  -$187   -$331  -$264   -$251  -$184
Min bal     $555   $617    $448   $900    $330   $835
```
Higher trade win does NOT give more green days (stays 49-58%); it only shrinks the average day.
MT5 trade list: daily target / daily loss stop / one trade at a time / stop after N losses: green days 45-50%.

## TRUE 2026 BASE (28 Nov 2026): one continuous M1 file, real fills, 0.01 (`research/full_2026.py`)
Owner sent Dec 2025 and 3-31 Aug 2026. `data/XAUUSDb_M1_2025-12_2026-11.csv` = Dec 2025 (warm-up) + Jan-Nov 2026,
no file restarts. Results 1 Jan - 25 Nov 2026:
```
            F-E off  Chosen  F-E off+DB  +Both
Profit      $6,057   $7,043  $7,405      $8,391
PF          1.44     1.27    1.30        1.22
Green days  48%      52%     58%         58%
Avg day     $26      $30     $31         $36
Worst day   -$245    -$293   -$326       -$360
Min bal     $795     $880    $683        $968
Safe bal    $1,192   $1,320  $1,025      $1,452
Trades/day  6.3      11.8    13.7        19.2
```
Monthly Chosen: Jan $298, Feb $2,251, Mar $1,396, Apr $125, May $997, Jun $470, Jul $2,009, Aug $34,
Sep -$113, Oct -$413, Nov -$10. Sep-Nov now loses in the backtest too, like MT5 (MT5 v1.13 Chosen at 0.01: $4,623).
The old $10,276 came from impossible fills (~$1,100) and data holes / file restarts (~$2,100).

### Day rules on the true 2026 data (28 Nov 2026, `research/day_rules.py`, 0.01)
```
rule          Chosen: $ / green / worst / min   +Both: $ / green / worst / min
none          7,043 53% -372  867               8,391 57% -428  862
dedupe copies 3,545 51% -169  494               4,426 53% -211  548
3 loss/side   4,050 48% -287  892               4,604 50% -314  749
cap -$100/day 3,296 50% -406 1,295              4,552 53% -448 1,468
trend H4      3,625 51% -252  684               4,787 54% -279  876
trend D1      5,911 50% -468  984               7,788 54% -518 1,177 (0 losing months)
mom 24h       4,871 48% -225  624               6,190 54% -254  760
no ZM         6,448 52% -356  835               7,796 58% -412  881
no F          7,199 53% -372  822               8,547 56% -428  680
```
No rule raises green days; every rule that cuts the worst day cuts profit about as much.
### Fixed daily pay from the account (`research/daily_pay.py`, 2026, 0.01, day-end balances)
$20/day every weekday: Chosen ends +$2,363 above the start, +Both +$3,711, +Both no F +$3,866.
Start money needed (day-end only): $392-$575; use the safe balance (~$1,300-1,450) to cover open trades.

### 2% of the deposit paid every weekday, deposit returned at year end (`research/pay_2pct.py`, 2026, 0.01)
```
deposit per 0.01   $1,000         $1,500        $2,000
Chosen left        +$2,363        +$23          -$2,317 (account empty in Nov)
+Both no F left    +$3,867        +$1,527       -$813
```
Works only with 0.01 per ~$1,000 or less. Sep-Nov the balance fell every month in every case.

### Owner idea: small take-profit + small stop (28 Nov 2026, `research/small_tp_sl.py`, true 2026, 0.01)
First move of 3,022 Chosen entries: +$2 before -$2 = 49%, +$3/-$3 50%, +$5/-$5 51%, +$10/-$10 51% (a coin flip).
Fixed exits on the same entries (both hit in one candle = loss): Chosen TP2/SL2 -$402, TP3/SL3 -$320,
TP5/SL5 -$122, TP5/SL10 +$378 (best), TP10/SL10 +$158; +Both best TP5/SL10 +$1,084 (69% win, min $710).
Normal exits: Chosen $7,043, +Both $8,391. The money comes from the few big runs, not from the first move.
REJECTED: small TP/SL removes the edge.

### Live crash filters (28 Nov 2026, `research/crash_filter.py`, true 2026, 0.01)
77 of 234 days in 2026 moved > $100 from the open (a third of all days: "crash" is normal for gold now).
```
filter          Chosen $ / green / worst wk / min    +Both $ / green / worst wk / min
none            7,043 53% -383  867                  8,391 57% -353  862
day $50 against 5,287 51% -520 1,061 (471 skipped)   6,558 56% -534 1,027
fast $15/60min  5,217 52% -416  746 (469 skipped)    6,694 59% -564 1,079
wild 2.5x range 6,332 53% -383 1,039 (90 skipped)    7,400 59% -454  976
```
REJECTED: every live crash filter loses profit and does not cut the worst week or the min balance
(the trades against a fast move also catch the big turns).

### Owner idea: BASKET / grid (28 Nov 2026, `research/basket.py`, true 2026, 0.01 per order)
Of 3,022 entries, 2,772 reach +$10 within 4 days; how far against us first: half $8, 70% $19, 80% $31, 90% $57, 95% $88.
Basket stop $B, pendings every $S, each $10 TP:
```
         Chosen $ / min bal      +Both $ / min bal
B10/S5   +165   / $1,167         +913    / $1,287
B20/S10  -1,851 / $2,496         -2,331  / $3,494
B30/S10  -4,734 / $5,142         -8,197  / $8,929
B50/S10  -12,236 / $13,948       -16,880 / $18,429
```
Win 60-73% but one basket stop loses many orders at once. REJECTED (normal exits: $7,043 / $8,391).

### Owner idea v2: basket PER ENTRY, close all at the entry's own $ target (28 Nov 2026, `research/basket2.py`)
True 2026, 0.01 per order, pendings every $S down to the entry's stop (x1) or 2x stop. Same-method baseline "1 order".
```
              Chosen $ / green d / worst day / min    +Both $ / green d / worst day / min
1 order       5,740 51%  -378  1,026                  6,899 56%  -435  1,004
S5 stop x1    4,635 57% -1,141 2,775                  5,022 57% -1,289 2,944
S3 stop x1    4,518 58% -1,687 3,186                  5,898 59% -1,595 3,427
S5 stop x2    3,129 64% -5,453 6,001                 -1,226 59% -6,333 6,954
S3 stop x2   -2,622 68% -7,379 9,853                 -6,662 64% -7,166 12,792
```
More green days (up to 64-68%) and win 73-80%, but less profit and 3-12x the money needed. REJECTED.

### Owner idea v3: basket with STOP orders (add with the move) (28 Nov 2026, `research/basket3.py`, 2026, 0.01/order)
```
           Chosen $ / win / worst day / min      +Both $ / win / worst day / min
1 order    5,869 36%  -378 1,026                 7,028 36%  -435 1,004
stops $2   1,680 58% -1,169 3,254                1,501 57% -1,169 4,973
stops $3   1,492 53% -1,459 3,853                  635 52% -1,665 4,872
stops $5     637 48% -1,964 4,195                  595 47% -1,964 3,908
stops $10  4,293 42% -1,005 1,872                5,224 41% -1,035 2,680
```
REJECTED: the basket reaches the $ target early (runners cut), and reversals hit the stop with 2-4 orders.

### Basket spacing $1-$5 (28 Nov 2026, `research/basket_spacing.py`, 2026, 0.01/order)
Limits (against us): Chosen $2,711/$4,827/$4,518/$3,033/$4,635 for $1-$5; +Both $5,409/$7,174/$5,898/$4,335/$5,022.
Best +Both limits $2: $7,174, 62% green days, worst day -$2,513, min bal $4,877 (1 order: $7,028, 56%, -$435, $1,004).
Stops (with the move): Chosen -$1,391/$1,680/$1,492/-$2,040/$637; +Both -$4,436/$1,501/$635/-$2,379/$595.
REJECTED: limits $2 = same profit for ~5x the money; stops always worse.

## EA v1.16 (28 Nov 2026): version input Chosen / +Both / +Both without F-E
Double bottom added to the EA (pending buy stop at the top, no fill on the pivot's own bar, market entry if
price is already past, max 0.5x risk). Python double bottom now uses the same real fills (`CASTIMO_FILL=market`).
True 2026 (`research/full_2026.py`), 0.01:
```
            Chosen  +Both   +Both no F-E
Profit      $7,043  $7,760  $6,774
PF          1.27    1.22    1.30
Green days  52%     56%     53%
Worst day   -$293   -$350   -$315
Min bal     $880    $1,026  $690
Safe bal    $1,320  $1,539  $1,034
```
(+Both with the old touch fills for the double bottom was $8,391.)

## WARNING (28 Nov 2026): 2025 with real fills LOSES (`research/full_2025.py`, Feb-Jul 2025, 0.01)
One continuous 2025 file (Jan = warm-up), real fills:
```
            Chosen   +Both    +Both no F-E
Profit      -$800    -$607    -$293
PF          0.92     0.96     0.98
Green days  47%      53%      53%
Min bal     $1,456   $1,860   $1,333
```
Monthly Chosen: Feb +$229, Mar +$243, Apr -$444, May -$263, Jun -$582, Jul +$17.
(The old "Robust 2025 $1,957" used touch fills.) With Sep-Nov 2026 also losing, the edge is NOT stable:
it made money in strong trends (Feb-Mar, Jul 2026) and loses in other markets.

## QUALITY TRADES (28 Nov 2026): what the best trades have in common (`research/quality.py`, `research/quality_run.py`)
Traits checked on every Chosen trade, 2026 AND 2025 (a trait must hold in both years): type, side, hour, weekday,
risk, RSI, ADX, last-hour range, H4/D1 trend, 4h/24h move, yesterday's range, trades already today.
Only clear one in both years: trades opened 08:00-13:59 server (London morning) lose: 2026 -$1,109, 2025 -$837.
(Asia hours 00-04 and evening 19-22 win in both. F-E zone loses in both. Others flip between years.)
Exact backtest with no new trades 08:00-13:59 (CASTIMO_SKIP_HOURS=8-13), real fills, 0.01:
```
            2026 Chosen  +Both    2025 Chosen  +Both
Profit      $7,651       $8,578   $138         $132
  (before)  $7,043       $7,760   -$800        -$607
Trades/day  8.6          12.2     8.3          14.9
Green wks   67%          73%      46%          58%
Worst wk    -$329        -$351    -$233        -$280
Min bal     $845         $1,007   $842         $948
Safe bal    $1,267       $1,510   $1,263       $1,421
```
Without the F-E zone: 2026 $6,506 / +DB $7,433 (min $693 / $670); 2025 $220 / $215 (min $580 / $668).
EA v1.17: input InpQuality (default on) = no new trades 08:00-13:59 server.

## ON-HOLD RE-TEST on TRUE data (28 Nov 2026), real fills, quality hours on (no new trades 08-13), 0.01
Close-on-opposite (`research/opposite_real.py`): 2026 Chosen no stop -$9,273 (min $12,271), $100 stop $1,032,
$50 stop $2,499; +Both $1,338 / $1,075 / $2,920 (min $1,747-$3,320). 2025: Chosen $293 / $173 / -$32, +Both
-$499 / -$553 / -$613. REJECTED (the old +$16k used touch fills and split files).
Robust / Max exact (`research/onhold_exact.py`; Max with CASTIMO_NO_CONS=1):
```
             Chosen  +Both   Robust  Max
2026 profit  $7,651  $8,578  $6,902  $7,868
2025 profit  $138    $132    $225    $1,379
Trades/day   8.6     12.2    8.1     19.9
Green wks 26 67%     73%     67%     62%
Worst day 26 -$305   -$321   -$222   -$936
Worst wk 26  -$329   -$351   -$243   -$820
Min bal 26   $845    $1,007  $549    $1,472
Safe bal 26  $1,267  $1,510  $823    $2,208
Min bal 25   $842    $948    $503    $768
```
Robust = smallest risk (best profit per $ of safe balance); Max = only one clearly positive in 2025.

### Owner idea: NO stop, every trade must take profit (28 Nov 2026, `research/no_stop_real.py`, true data, 0.01)
```
                 2026 Chosen  2026 +Both   2025 Chosen  2025 +Both
Took profit      92%          93%          94%          94%
Closed profit    $18,274      $60,101      $7,180       $29,016
Worst open loss  -$57,571     -$158,338    -$8,047      -$32,779
Drawdown (min)   $43,984      $109,779     $5,469       $23,312
```
REJECTED: 7-8% of trades never come back and their open losses are far bigger than all the profit.

## OWNER DAY PLAN (28 Nov 2026, `research/day_stop.py`): stop for the day at +$X, or at break-even after a loss
Quality hours on, true data, real fills, 0.01. Bot stops OPENING trades; open trades run to their exit.
Best rule in every version and both years: "+$20 & BE" (stop when the day is +$20, or back to $0 after being red).
```
               2026 $  green  min    2025 $  green  min
Chosen none    7,651   54%    865    138     44%    806
Chosen +20&BE  6,568   57%    710    731     50%    370
+Both none     8,578   55%    880    132     53%    953
+Both +20&BE   7,909   62%    672    912     59%    485
Robust none    6,902   54%    501    225     50%    508
Robust +20&BE  7,325   60%    337    474     57%    443
```
Max 4-5 trades/day: profit falls by more than half in 2026 (rejected).
Robust +20&BE: more profit in both years, more green days, smallest money needed (min $337, safe ~$506).

### Owner day plan v2: protect profit (stop after giving back $G from the day's best) (`research/day_trail.py`)
2026: helps Chosen / +Both a little (+Both give back 40 / +20: $8,706, drawdown $493 vs $7,909 / $672), Robust no.
2025: worse in EVERY version (e.g. +Both $912 -> $459-$749, Robust $474 -> $203-$401).
KEEP the current rule (+$20 target, or break-even after a red start): best over both years.

### Day target size (`research/day_target_grid.py`): +$20 / 30 / 40 / 60 / 80 / 100 (all with break-even after a red start)
Robust 2026 $7,325 / 7,264 / 7,214 / 7,077 / 7,014 / 6,845 (min $337-$422); 2025 $474 / 323 / 278 / 329 / 364 / 380.
+$20 is best or equal in every version and both years (more green days, smaller min balance). KEEP +$20.

### Week rule on top of the day rule (`research/week_rule.py`, 0.01)
Day rule alone already gives green weeks: Chosen 67% / 65% (2026 / 2025), +Both 77% / 69%, Robust 79% / 65%.
Week break-even stop: Robust green weeks 88% / 73% but profit $7,325 -> $5,214 and $474 -> $58; +Both 2025 -$110.
Week +$60/+$100 targets and -$60/-$100 caps: less profit, green weeks about the same. NOT adopted.

### Money management 1: max copies / max open trades (`research/money_mgmt.py`, day rule on, 0.01)
Robust: day rule only 2026 $7,325 / 2025 $474 (min $337 / $443, worst day -$226 / -$186);
copies 2: $6,897 / $561 (min $328 / $399, worst day -$197 / -$149, green weeks 81% / 69%);
max open 3: $5,425 / $205 (worst week -$94 / -$176, min $241 / $571). Chosen/+Both: copies 1-2 and max open 3-5
cut 2025 profit a lot. Option: Robust + max 2 copies (a bit safer, -$428 in 2026, +$87 in 2025).

### Flip re-test with quality hours + day rule (`research/flip_day_rule.py`, 0.01)
Flips alone: 2026 624 flips 43% win +$315 (Robust 274, +$182); 2025 -$19 (Robust -$2) = about break-even.
With the day rule: Chosen $6,568 -> $6,695 / 2025 $731 -> $1,080; +Both $7,909 -> $8,112 / $912 -> $1,388;
Robust $7,325 -> $7,050 / $474 -> $586. Worst day 2026 worse: -$611 / -$601 / -$333 (was -$438 / -$428 / -$226).
Small gain for Chosen / +Both, mixed for Robust, bigger worst days. Not adopted unless the owner wants it.

### Max drawdown WITH open trades (hourly marks), quality hours + day rule (`research/float_dd.py`, 0.01)
2026: Chosen $846, +Both $736, Robust $435 (closed-only $710 / $672 / $337). 2025: $342 / $495 / $494.
Robust safe (1.5x) = $652 (2026) / $741 (2025).

### Robust + day rule WITH the lot plan, start $1,000 (`research/lot_weekly.py`)
0.01 per $2,000 (EA LotUnits), half lot after 3 losses in a row, day target $20 per 0.01.
2026: +$11,237 -> $12,237, lot 0.01 -> 0.05, green weeks 75%, worst week -$627, max drawdown with open trades
$1,563 (12% of the $13,179 peak, Nov), lowest balance $751 (Jan). 2025 (Feb-Jul): +$238 -> $1,238, lot 0.01,
green weeks 69%, max drawdown $619 (38% of the $1,646 peak), lowest balance $991.

Flat 0.01 per $1,000 (`research/lot_weekly.py 2026 1000 1000`): 2026 $1,000 -> $79,835 (lot up to 0.90), green weeks 77%,
worst week -$7,306, max drawdown with open trades $21,909 (24% of the $92,792 peak), lowest balance $751 (Jan).
2025: lot never above 0.01 (balance < $2,000): $1,238, max drawdown $619 (38%).
