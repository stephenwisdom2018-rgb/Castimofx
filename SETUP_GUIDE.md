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

## 2. MT5 auto-trading (Exness or any MT5 broker)

> **Start on a DEMO account.** Run it for at least 2–4 weeks before using real money.

1. On a Windows PC (or a VPS so it runs 24/5), open MT5 and log in to your **demo** account.
2. **File → Open Data Folder → MQL5 → Experts**. Copy `CastimofxSMC.mq5` into that folder.
3. In MT5, press **F4** to open MetaEditor, open the file, and press **F7 (Compile)**. It should say "0 errors".
4. Back in MT5, open a chart (for example EURUSD M15) and drag **CastimofxSMC** from the Navigator onto it.
5. Tick **Allow Algo Trading**, then turn on the **Algo Trading** button in the toolbar.
6. The top-left corner of the chart shows the structure, the last BOS/CHoCH, the active zones, and the position.

### Backtest it first, on your broker's real data
**View → Strategy Tester** → Expert: CastimofxSMC → symbol and M15 → Modelling: "Every tick based on real ticks" → choose a date range → **Start**.

### Main settings
| Setting | Default | Meaning |
|---|---|---|
| Swing length | 5 | Bigger means fewer, stronger swings and zones |
| Risk : reward | 2 | Take profit = 2 × the risk |
| Buy only in discount… | on | The premium/discount filter |
| Only zones created by a CHoCH | off | Turn on for reversal-only trading |
| Risk per trade % | 1 | % of balance lost if the stop is hit |
| Max spread (points) | 30 | No new orders when the spread is wider (raise it for gold) |
| Trade from/until hour | 0 / 24 | Server-time session filter (for example London + NY) |

One pending order and one open trade at a time per chart. Attach it to several charts to trade several pairs.
Give each chart a different **Magic number** only if you run two copies on the same symbol.
