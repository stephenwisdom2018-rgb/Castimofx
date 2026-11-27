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
