# Castimofx – XAUUSD Sweep EA (MT5)

`MQL5/Experts/XAUUSD_SweepEA.mq5` trades the M1 gold setup from *XAUUSD Sweep Setup Notes*:
a rising staircase (A–F), a sweep below E into a strong zone (G), a lower high (H),
a pullback (I), and an entry when price breaks H (L). The sell is the same picture upside down.

## Install

1. Copy `XAUUSD_SweepEA.mq5` into your terminal's `MQL5/Experts/` folder
   (MetaTrader 5 → File → Open Data Folder).
2. Open it in MetaEditor and press **Compile** (F7).
3. Attach it to an **XAUUSD** chart. The EA always reads M1 and M5 itself, so any chart timeframe works.
4. Test it in the **Strategy Tester** first (model *Every tick based on real ticks*),
   then run it on a demo account before using real money.

## How the notes become code

| Notes | Code |
|---|---|
| A high reads RSI ≥ 70, a low RSI ≤ 30 | A swing only counts if it is a fractal (`SwingDepth` bars each side) **and** RSI(14) reaches the level within `RsiWindow` bars of it. Swings are merged into an alternating high/low list. |
| Each point is confirmed by the next | A swing is confirmed once `SwingDepth` closed candles sit on its right and the opposite swing follows. |
| C > A, D > B, E > C, F breaks B and D | Checked on the last 8 swings (A…H). |
| G sweeps below E, RSI ≤ 30 on M1 **and** M5 | `vG < vE` plus an M5 RSI check around G's time. |
| H lower than F | `vH < vF`. |
| I stays above G | The lowest price after H must stay above G. |
| L: buy when price breaks H | `EntryMode` (tick break or M1 close). |
| K: price falls from H below G → void | The setup is dropped, the mode stays the same, and the next setup only needs F‑G‑H‑I‑L. |
| Rule 9: the next trade in the same direction needs only F, G, H, I, L | `g_needFull` is cleared after a trade or a void. The full A–H setup is needed only at start. |
| Rules 7–8: the mode switches only on a full opposite setup | The EA watches for the opposite setup all the time. When its L triggers, it closes all trades and pending orders, switches mode and opens the new trade. |
| Rule 10: 1 instant order + 19 pending, $2 apart, all close at first entry + $20 | Market order, then `PendingOrders` limit orders `GridStepUSD` apart against the trade. Every order carries the same TP (first entry ± `TargetUSD`), and the EA also closes the whole basket when price reaches it. |
| 0.02 lot at $4,000 equity | `ScaleLotWithEquity`: lot = 0.01 × (1 + ⌊equity / 4000⌋). |

## Your open questions are settings

| # | Question | Input | Default |
|---|---|---|---|
| 1 | Entry at L: tick break or candle close? | `EntryMode` | Tick break |
| 2 | Where do the pending orders sit? | Below the buy (above the sell), as the notes assume | – |
| 3 | After the buy, price falls below G? | `AfterGBreak` | Close everything |
| 4 | Must I read RSI ≤ 30? Is E above C? | `RequireIRsi`, `RequireEAboveC` | No / Yes |
| 5 | Must G also go below C? | `RequireGBelowC` | No |
| 6 | Leverage | Not needed in code. `MaxMarginUsePct` caps the grid so it fits your free margin. | 50 % |

The notes also asked for some numbers. These are the starting values:
`SwingDepth = 3` candles each side, RSI read at candle close (±1 bar),
`MaxSetupBars = 600` M1 bars (10 hours), `MaxSpreadUSD = 0.60`.

## Safety limits (from the notes' suggestions)

- `MaxLossPct = 15`: close everything if the floating loss reaches 15 % of the balance (0 = off).
- `AfterGBreak = Close all`: G is used as the void line after entry too.
- `MaxMarginUsePct`: stop adding pending orders when free margin gets low.
- `PendingOrders`: lower it (for example 9) while the account is small.
- `MaxSpreadUSD`, `UseSessionFilter`: skip wide spreads or quiet hours.
- `MaxChaseUSD`: skip the entry if price is already more than $1 past H. With `EntryMode = candle close`, raise it to about 3.

## Logs and chart

- Every event (ARMED, VOID_K, TRIGGER, ENTRY, SWITCH, BASKET_END …) is written to the Experts log
  and to `Files/Common/SweepEA_<symbol>.csv`. Use this to count the real win rate and the worst loss.
- When a setup is armed, A…H are drawn on the chart. The green dashed line is the H break level
  and the magenta dotted line is the G void line.
- Mode and basket state are saved in terminal global variables, so a restart picks up where it left off.
  Set `ResetStateOnStart = true` to start fresh.

## Risk reminder

The grid has no stop loss of its own. A $38 move against the first entry fills all 20 orders,
which is about a $380 floating loss at 0.01 lot. Judge the EA by its worst drawdown in the tester,
not by its win rate.
