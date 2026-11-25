# Castimofx SMC: setup guide

You get two tools that follow the same rules:

| File | What it does | Where it runs |
|---|---|---|
| `tradingview/castimofx_smc.pine` | **Indicator**: draws BOS/CHoCH, supply and demand zones, premium/discount, PDH/PDL/PWH/PWL/PMH/PML, BUY/SELL signals and a results table | TradingView (web, desktop, or the phone app once it's saved) |
| `mt5/CastimofxSMC.mq5` | **Auto-trader (Expert Advisor)**: places, manages and cancels trades on its own | MetaTrader 5 on a **PC or VPS**. EAs do not run in the MT5 phone app |

---

## 1. TradingView indicator (about 2 minutes, needs a browser or PC once)

1. Open tradingview.com and open a chart (for example EURUSD or XAUUSD on M15).
2. At the bottom, click **Pine Editor**, then **Open → New indicator**.
3. Delete everything in the editor and paste the whole contents of `castimofx_smc.pine`.
4. Click **Save** (name it "CFX SMC"), then **Add to chart**.
5. It now appears in the phone app too, under **Indicators → My scripts**.

### What you see on the chart
- **BOS** (dashed line) / **CHoCH** (solid line): structure breaks, green for bullish and red for bearish.
- **Green "Demand" / red "Supply" boxes**: the zones. They turn grey once price touches them and disappear when price closes through them.
- **Premium / Discount / Equilibrium**: the current dealing range. Buys come from the discount half, sells from the premium half.
- **Strong/Weak High/Low**: which extreme is protected by the current trend.
- **PDH PDL PWH PWL PMH PML**: previous day, week and month highs and lows.
- **Dotted line**: a pending BUY/SELL LIMIT. **▲ BUY / ▼ SELL**: the order filled. Red and green boxes show the stop and the target.
- **Results table** (top right): trades, win rate, net R, and profit factor on the history you're viewing.

### Phone alerts
Click **Alert (⏰) → Condition: CFX SMC → "Any alert() function call" → Create**.
You'll get messages like `BUY LIMIT EURUSD @ 1.08512 SL 1.08390 TP 1.08756`,
then "BUY filled", then "TP hit" / "SL hit".

---

## 2. MT5 auto-trader v2 (Exness or any MT5 broker)

The EA **draws the SMC picture on the MT5 chart** and trades it automatically:
BOS / CHoCH lines, demand (green) and supply (red) zones that turn grey when touched,
premium / discount / equilibrium, strong/weak high/low, PDH/PDL/PWH/PWL/PMH/PML.
A panel in the top-left shows each symbol's M15 and H4 trend, the last break, open trades and today's P/L.

> **Start on a DEMO account.** See "Honest results" below.

### Install
1. On a Windows PC (or VPS), open MT5 and log in to your **demo** account.
2. **File → Open Data Folder → MQL5 → Experts**. Copy `CastimofxSMC.mq5` there.
3. Press **F4** (MetaEditor), open the file, press **F7 (Compile)**. It should say "0 errors". If it shows errors, screenshot them and send them to me.
4. Open an **M15** chart (for example EURUSD), drag **CastimofxSMC** onto it, tick **Allow Algo Trading**, and switch on **Algo Trading** in the toolbar.

### Getting 3+ trades a day
On M15 with the default settings, each symbol gives roughly **1–2 trades a day**. Trade several symbols from one chart:

- **Symbols:** `EURUSD,GBPUSD,XAUUSD,GBPJPY,AUDUSD`
- **Broker suffix:** Exness Standard accounts use names like `EURUSDm`, so type `m`. Leave it empty if your symbols have no suffix.

With 5–6 symbols, expect around **6–12 trades a day** in total. The zones are drawn for the chart's own symbol.
Open another chart and attach the EA with the same symbol list if you also want to see another pair's zones.
In that case, give it a different **Magic number** and an empty symbol list, or it will double-trade.

### Settings
| Setting | Default | Meaning |
|---|---|---|
| Entry timeframe | M15 | Where zones and breaks are found |
| Trend filter timeframe | H4 | Only buy when H4 structure is bullish, only sell when it's bearish. Choose CURRENT to switch off |
| Entry type | Confirmation | **Confirmation** = enter right after the BOS/CHoCH candle closes. **Zone limit** = limit order at the zone edge |
| Swing length | 3 | Smaller = more swings, zones and trades |
| Risk : reward | 3 | Take profit = 3 × the risk |
| Only CHoCH / only sweeps | off | Fewer, "cleaner" trades (in testing they did *not* improve results) |
| Trade from / until hour | 0 / 24 | Server time. Exness server time = GMT. London+NY ≈ 7 to 17 |
| Risk per trade % | 0.5 | % of balance lost if the stop is hit |
| Max open trades per symbol / total | 3 / 6 | |
| Daily loss limit % | 3 | No new trades for the rest of the day once you're down this much |
| Max trades per day | 20 | |
| Max spread % of stop | 20 | Skips trades where the spread eats too much of the stop |

### Backtest in MT5 before going live
**View → Strategy Tester** → Expert: CastimofxSMC → symbol and M15 → Modelling: "Every tick based on real ticks"
→ a date range of **at least 1 year** → **Start**. For multi-symbol tests, fill in the Symbols input. MT5 loads them automatically.

---

## Honest results (read this)

I tested these rules in Python on **real M15 and M5 data for EURUSD, GBPUSD, USDJPY, AUDUSD, GBPJPY and gold**
(26 Aug to 17 Nov 2026, about 2.5 months), with spread included. I tuned on the first half and checked on the second half.

- The original zone-limit entry **lost money on every pair** (about −0.2 to −0.5R per trade).
  More trades (M5, smaller swings) **lost faster**, because tight zones make the spread a big share of each trade.
- I tried the H4 trend filter, a session filter, mid-zone entries, sweep confirmation, and 1.5 / 2 / 3 R:R targets: about 1,000 combinations.
  **None was reliably profitable on both halves.** The least-bad setting, which is now the default (confirmation entry + H4 filter, R:R 3),
  was close to break-even: about −0.07R and −0.03R per trade.
- 2.5 months of data is short, and the free data I used isn't your broker's feed. Your MT5 Strategy Tester
  with a year or more of Exness tick data is the real judge.

**Bottom line:** the bot does what you asked (draws the zones and trades them automatically, 3+ times a day), but
I have **no evidence yet that these rules make money**. Run it on demo, check the Strategy Tester, and only go live
if a long backtest *and* several weeks of demo both show profit.

