//+------------------------------------------------------------------+
//|                                               CastimofxSMC.mq5   |
//|  Smart Money Concepts supply & demand Expert Advisor  v2         |
//|                                                                  |
//|  - Draws BOS / CHoCH, supply & demand zones, premium / discount, |
//|    equilibrium, strong/weak highs & lows, PDH/PDL PWH/PWL PMH/PML |
//|  - Trades one or many symbols from a single chart                 |
//|  - Entry: CONFIRMATION (market right after the break, default)    |
//|           or ZONE LIMIT (limit order at the zone edge)            |
//|  - Higher-timeframe trend filter, session filter, sweep filter    |
//|  - Risk % per trade, max positions, daily loss limit              |
//+------------------------------------------------------------------+
#property copyright "Castimofx"
#property version   "2.00"
#property description "SMC supply & demand auto-trader with chart drawing (multi-symbol)"

#include <Trade/Trade.mqh>

enum ENUM_CFX_ENTRY
  {
   CFX_CONFIRM = 0,   // Confirmation: enter right after the BOS/CHoCH
   CFX_ZONE    = 1    // Zone limit: limit order at the zone edge
  };

input group "Symbols & timeframes"
input string          InpSymbols      = "";          // Symbols, comma separated (empty = this chart)
input string          InpSuffix       = "";          // Broker suffix added to each symbol (e.g. m)
input ENUM_TIMEFRAMES InpTF           = PERIOD_M15;  // Entry timeframe
input ENUM_TIMEFRAMES InpHTF          = PERIOD_H4;   // Trend filter timeframe (CURRENT = off)

input group "Market structure"
input int      InpSwingLen      = 3;      // Swing length (bars each side)
input int      InpObLookback    = 5;      // Order-block search (bars)
input int      InpHistoryBars   = 1500;   // Bars analysed

input group "Entries"
input ENUM_CFX_ENTRY InpEntry   = CFX_CONFIRM; // Entry type
input double   InpRR            = 3.0;    // Risk : reward
input bool     InpChochOnly     = false;  // Only CHoCH breaks (reversals)
input bool     InpSweepOnly     = false;  // Only breaks that swept liquidity first
input bool     InpDiscountOnly  = false;  // Zone mode: buy only in discount / sell only in premium
input double   InpSlBufferAtr   = 0.1;    // Stop buffer beyond zone (x ATR14)
input double   InpMinStopAtr    = 0.3;    // Skip if stop smaller than (x ATR14)
input double   InpMaxStopAtr    = 4.0;    // Skip if stop bigger than (x ATR14)
input int      InpExpiryBars    = 96;     // Zone mode: cancel unfilled order after (bars)
input int      InpStartHour     = 0;      // Trade from hour (server time)
input int      InpEndHour       = 24;     // Trade until hour (server time)

input group "Risk"
input double   InpRiskPct        = 0.5;   // Risk per trade (% of balance)
input double   InpMinLotMaxRisk  = 2.0;   // If min lot risks more than the above, still trade it up to this %
input int      InpMaxPosSymbol   = 3;     // Max open trades per symbol
input int      InpMaxPosTotal    = 6;     // Max open trades in total
input double   InpMaxDailyLoss   = 3.0;   // Stop new trades after losing this % today
input int      InpMaxTradesDay   = 20;    // Max new trades per day (all symbols)
input double   InpMaxSpreadPct   = 20.0;  // Skip if spread > this % of the stop distance
input ulong    InpMagic          = 20251117; // Magic number

input group "Drawing (this chart's symbol)"
input bool     InpDraw          = true;   // Draw on chart
input int      InpDrawBars      = 400;    // Draw objects from the last N bars
input color    InpDemandColor   = C'0,105,75';    // Demand zone
input color    InpSupplyColor   = C'130,35,35';   // Supply zone
input color    InpMitigColor    = C'70,70,70';    // Touched zone
input color    InpBullColor     = C'8,153,129';   // Bullish structure
input color    InpBearColor     = C'242,54,69';   // Bearish structure
input color    InpLevelColor    = clrSilver;      // Key levels

#define PREFIX "CFX_"

//+------------------------------------------------------------------+
//| SMC analysis                                                      |
//+------------------------------------------------------------------+
struct CfxZone
  {
   int      dir;          // 1 demand, -1 supply
   double   top;
   double   bot;
   int      obIdx;        // order-block candle
   int      created;      // bar of the structure break
   double   eq;           // dealing-range equilibrium at creation
   bool     choch;
   bool     swept;
   int      mitigatedAt;  // -1 = not touched
   int      brokenAt;     // -1 = not broken
  };

struct CfxEvent
  {
   int      dir;
   bool     choch;
   int      swingIdx;
   int      breakIdx;
   double   level;
  };

class CSmc
  {
public:
   int      trend;
   double   trailTop, trailBot;
   int      trailTopIdx, trailBotIdx;
   CfxZone  zones[];
   CfxEvent events[];
   int      newZones[];      // zones created on the last bar

   void Run(const MqlRates &r[], int n, int L, int lookback)
     {
      trend = 0;
      trailTop = 0; trailBot = 0; trailTopIdx = -1; trailBotIdx = -1;
      ArrayResize(zones, 0);
      ArrayResize(events, 0);
      ArrayResize(newZones, 0);
      ArrayResize(m_swIdx, 0);
      ArrayResize(m_swHigh, 0);
      int sh = -1, sl = -1;
      bool shBroken = true, slBroken = true;

      for(int t = 0; t < n; t++)
        {
         // 1. swing confirmed L bars after it forms
         int i = t - L;
         if(i >= L)
           {
            bool isHigh = true, isLow = true;
            for(int k = 1; k <= L; k++)
              {
               if(!(r[i].high > r[i-k].high) || !(r[i].high >= r[i+k].high)) isHigh = false;
               if(!(r[i].low  < r[i-k].low)  || !(r[i].low  <= r[i+k].low))  isLow  = false;
              }
            if(isHigh) { sh = i; shBroken = false; AddSwing(i, true);  trailTop = r[i].high; trailTopIdx = i; }
            if(isLow)  { sl = i; slBroken = false; AddSwing(i, false); trailBot = r[i].low;  trailBotIdx = i; }
           }
         if(trailTopIdx >= 0 && r[t].high > trailTop) { trailTop = r[t].high; trailTopIdx = t; }
         if(trailBotIdx >= 0 && r[t].low  < trailBot) { trailBot = r[t].low;  trailBotIdx = t; }

         // 2. zones: broken (close through) / mitigated (touched)
         for(int z = 0; z < ArraySize(zones); z++)
           {
            if(zones[z].mitigatedAt >= 0 || zones[z].brokenAt >= 0 || zones[z].created >= t) continue;
            if(zones[z].dir == 1)
              {
               if(r[t].close < zones[z].bot)      zones[z].brokenAt = t;
               else if(r[t].low <= zones[z].top)  zones[z].mitigatedAt = t;
              }
            else
              {
               if(r[t].close > zones[z].top)      zones[z].brokenAt = t;
               else if(r[t].high >= zones[z].bot) zones[z].mitigatedAt = t;
              }
           }

         // 3. structure breaks
         if(sh >= 0 && !shBroken && r[t].close > r[sh].high)
           {
            shBroken = true;
            int idx = OnBreak(r, t, sh, 1, lookback);
            if(t == n - 1) PushNew(idx);
           }
         if(sl >= 0 && !slBroken && r[t].close < r[sl].low)
           {
            slBroken = true;
            int idx = OnBreak(r, t, sl, -1, lookback);
            if(t == n - 1) PushNew(idx);
           }
        }
     }

private:
   int      m_swIdx[];
   bool     m_swHigh[];

   void AddSwing(int idx, bool isHigh)
     {
      int s = ArraySize(m_swIdx);
      ArrayResize(m_swIdx, s + 1);
      ArrayResize(m_swHigh, s + 1);
      m_swIdx[s] = idx;
      m_swHigh[s] = isHigh;
     }

   void PushNew(int idx)
     {
      int s = ArraySize(newZones);
      ArrayResize(newZones, s + 1);
      newZones[s] = idx;
     }

   int OnBreak(const MqlRates &r[], int t, int swing, int dir, int lookback)
     {
      bool choch = (trend == -dir);
      trend = dir;

      int e = ArraySize(events);
      ArrayResize(events, e + 1);
      events[e].dir = dir;
      events[e].choch = choch;
      events[e].swingIdx = swing;
      events[e].breakIdx = t;
      events[e].level = (dir == 1) ? r[swing].high : r[swing].low;

      // origin of the leg that broke structure
      int origin = swing;
      for(int k = swing; k <= t; k++)
        {
         if(dir == 1  && r[k].low  < r[origin].low)  origin = k;
         if(dir == -1 && r[k].high > r[origin].high) origin = k;
        }
      double rHigh = r[origin].high, rLow = r[origin].low;
      for(int k = origin; k <= t; k++)
        {
         if(dir == 1) rHigh = MathMax(rHigh, r[k].high);
         else         rLow  = MathMin(rLow, r[k].low);
        }

      // order block = last opposite-colour candle at / just before the origin
      int ob = origin;
      for(int j = origin; j >= MathMax(origin - lookback, 0); j--)
        {
         bool opposite = (dir == 1) ? (r[j].close < r[j].open) : (r[j].close > r[j].open);
         if(opposite) { ob = j; break; }
        }

      CfxZone zn;
      zn.dir = dir;
      zn.top = r[ob].high;
      zn.bot = r[ob].low;
      for(int k = ob; k <= origin; k++)
        {
         if(dir == 1) zn.bot = MathMin(zn.bot, r[k].low);
         else         zn.top = MathMax(zn.top, r[k].high);
        }
      zn.obIdx       = ob;
      zn.created     = t;
      zn.eq          = (rHigh + rLow) / 2.0;
      zn.choch       = choch;
      zn.mitigatedAt = -1;
      zn.brokenAt    = -1;

      // liquidity sweep: did the leg run past the previous swing of the same side?
      zn.swept = false;
      for(int s = ArraySize(m_swIdx) - 1; s >= 0; s--)
        {
         if(m_swHigh[s] == (dir == -1) && m_swIdx[s] < ob)
           {
            zn.swept = (dir == 1) ? (rLow < r[m_swIdx[s]].low) : (rHigh > r[m_swIdx[s]].high);
            break;
           }
        }

      int size = ArraySize(zones);
      ArrayResize(zones, size + 1);
      zones[size] = zn;
      return size;
     }
  };

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
CTrade   trade;
string   g_syms[];
datetime g_lastBar[];
string   g_status[];

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpSwingLen < 2 || InpHistoryBars < 200 || InpRR <= 0 || InpRiskPct <= 0)
     {
      Print("Invalid inputs");
      return(INIT_PARAMETERS_INCORRECT);
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);

   string list = InpSymbols;
   StringTrimLeft(list);
   StringTrimRight(list);
   string parts[];
   int cnt = 0;
   if(list == "")
     {
      ArrayResize(parts, 1);
      parts[0] = _Symbol;
      cnt = 1;
     }
   else
      cnt = StringSplit(list, ',', parts);

   ArrayResize(g_syms, 0);
   for(int i = 0; i < cnt; i++)
     {
      string s = parts[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "") continue;
      int sl = StringLen(InpSuffix);
      if(list != "" && sl > 0 && (StringLen(s) <= sl || StringSubstr(s, StringLen(s) - sl) != InpSuffix))
         s += InpSuffix;
      if(!SymbolSelect(s, true))
        {
         PrintFormat("Symbol %s not found at this broker - skipped (check the name / suffix)", s);
         continue;
        }
      int k = ArraySize(g_syms);
      ArrayResize(g_syms, k + 1);
      g_syms[k] = s;
     }
   if(ArraySize(g_syms) == 0)
     {
      Print("No valid symbols");
      return(INIT_PARAMETERS_INCORRECT);
     }
   ArrayResize(g_lastBar, ArraySize(g_syms));
   ArrayResize(g_status, ArraySize(g_syms));
   ArrayInitialize(g_lastBar, 0);
   for(int i = 0; i < ArraySize(g_status); i++) g_status[i] = g_syms[i] + ": waiting for data";

   EventSetTimer(1);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, PREFIX);
   Comment("");
  }

void OnTick()  { ProcessAll(); }
void OnTimer() { ProcessAll(); }

void ProcessAll()
  {
   bool any = false;
   for(int i = 0; i < ArraySize(g_syms); i++)
      if(Process(i)) any = true;
   if(any) ShowPanel();
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
void ComputeAtr(const MqlRates &r[], int n, double &atr[])
  {
   ArrayResize(atr, n);
   const int len = 14;
   double sum = 0;
   for(int t = 0; t < n; t++)
     {
      double tr = r[t].high - r[t].low;
      if(t > 0)
         tr = MathMax(tr, MathMax(MathAbs(r[t].high - r[t-1].close), MathAbs(r[t].low - r[t-1].close)));
      if(t < len) { sum += tr; atr[t] = sum / (t + 1); }
      else          atr[t] = (atr[t-1] * (len - 1) + tr) / len;
     }
  }

double NormPrice(string sym, double p)
  {
   int    digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) return NormalizeDouble(p, digits);
   return NormalizeDouble(MathRound(p / ts) * ts, digits);
  }

double LotsForRisk(string sym, double stopDist)
  {
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double step      = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double minLot    = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxLot    = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(tickValue <= 0 || tickSize <= 0 || step <= 0 || stopDist <= 0) return 0;

   double lossPerLot = stopDist / tickSize * tickValue;
   double lots = MathFloor(riskMoney / lossPerLot / step) * step;
   if(lots < minLot)
     {
      double minLotRisk = minLot * lossPerLot;
      double minLotPct  = minLotRisk / AccountInfoDouble(ACCOUNT_BALANCE) * 100.0;
      if(minLotPct <= InpMinLotMaxRisk)
        {
         PrintFormat("%s: using min lot %.2f (risks %.2f = %.2f%% of balance)", sym, minLot, minLotRisk, minLotPct);
         return minLot;
        }
      PrintFormat("%s: min lot %.2f would risk %.2f (%.2f%% of balance) - skipped", sym, minLot, minLotRisk, minLotPct);
      return 0;
     }
   lots = MathMin(lots, maxLot);
   int volDigits = (int)MathMax(0, MathCeil(-MathLog10(step)));
   return NormalizeDouble(lots, volDigits);
  }

int CountPositions(string sym)   // sym = "" -> all symbols
  {
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) continue;
      if(sym == "" || PositionGetString(POSITION_SYMBOL) == sym) c++;
     }
   return c;
  }

// today's closed P/L, floating P/L, and number of trades opened today
void TodayStats(double &closed, double &floating, int &opened)
  {
   closed = 0;
   floating = 0;
   opened = 0;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   datetime dayStart = StructToTime(dt);
   if(HistorySelect(dayStart, TimeCurrent() + 60))
     {
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         ulong d = HistoryDealGetTicket(i);
         if(d == 0 || HistoryDealGetInteger(d, DEAL_MAGIC) != (long)InpMagic) continue;
         long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
         if(entry == DEAL_ENTRY_IN) opened++;
         closed += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
        }
     }
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) continue;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
  }

bool InSession()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(InpStartHour <= InpEndHour) return dt.hour >= InpStartHour && dt.hour < InpEndHour;
   return dt.hour >= InpStartHour || dt.hour < InpEndHour;
  }

int HtfTrend(string sym)
  {
   if(InpHTF == PERIOD_CURRENT || PeriodSeconds(InpHTF) <= PeriodSeconds(InpTF)) return 0;
   MqlRates hr[];
   int n = CopyRates(sym, InpHTF, 1, 600, hr);
   if(n < InpSwingLen * 4) return 0;
   CSmc h;
   h.Run(hr, n, InpSwingLen, InpObLookback);
   return h.trend;
  }

bool HtfFilterOn() { return InpHTF != PERIOD_CURRENT && PeriodSeconds(InpHTF) > PeriodSeconds(InpTF); }

//+------------------------------------------------------------------+
//| Zone mode: cancel pending orders that are no longer valid        |
//| Order comment = "CFX Z <zone bar time>"                          |
//+------------------------------------------------------------------+
void ManagePending(string sym, CSmc &smc, const MqlRates &r[], int n, int htf)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != sym || OrderGetInteger(ORDER_MAGIC) != (long)InpMagic) continue;
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      int dir = (type == ORDER_TYPE_BUY_LIMIT) ? 1 : (type == ORDER_TYPE_SELL_LIMIT ? -1 : 0);
      if(dir == 0) continue;

      datetime setup = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      bool expired = (TimeCurrent() - setup) >= (long)InpExpiryBars * PeriodSeconds(InpTF);
      bool against = (smc.trend != dir) || (HtfFilterOn() && htf != dir);
      bool broken  = false;
      string cmt = OrderGetString(ORDER_COMMENT);
      if(StringFind(cmt, "CFX Z ") == 0)
        {
         datetime zt = (datetime)StringToInteger(StringSubstr(cmt, 6));
         for(int z = 0; z < ArraySize(smc.zones); z++)
            if(smc.zones[z].dir == dir && r[smc.zones[z].created].time == zt && smc.zones[z].brokenAt >= 0)
               broken = true;
        }
      if(expired || against || broken)
         if(trade.OrderDelete(ticket))
            PrintFormat("%s: cancelled order %I64u (%s)", sym, ticket, expired ? "expired" : against ? "trend flipped" : "zone broken");
     }
  }

//+------------------------------------------------------------------+
//| Entry                                                            |
//+------------------------------------------------------------------+
void TryEnter(string sym, CfxZone &zn, datetime zoneTime, double atr, int htf)
  {
   if(InpChochOnly && !zn.choch) return;
   if(InpSweepOnly && !zn.swept) return;
   if(HtfFilterOn() && htf != zn.dir)
     {
      PrintFormat("%s: %s against the %s trend - skipped", sym, zn.dir == 1 ? "buy" : "sell", TfName(InpHTF));
      return;
     }
   if(!InSession()) return;
   if(InpEntry == CFX_ZONE && InpDiscountOnly && ((zn.dir == 1 && zn.top > zn.eq) || (zn.dir == -1 && zn.bot < zn.eq)))
      return;
   if(CountPositions(sym) >= InpMaxPosSymbol || CountPositions("") >= InpMaxPosTotal) return;

   double closed, floating; int opened;
   TodayStats(closed, floating, opened);
   double pnl = closed + floating;
   double startBal = AccountInfoDouble(ACCOUNT_BALANCE) - closed;
   if(startBal > 0 && -pnl / startBal * 100.0 >= InpMaxDailyLoss)
     {
      PrintFormat("Daily loss limit reached (%.2f) - no new trades today", pnl);
      return;
     }
   if(opened >= InpMaxTradesDay) return;

   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   double buf = InpSlBufferAtr * atr;
   double stop = NormPrice(sym, zn.dir == 1 ? zn.bot - buf : zn.top + buf);
   double entry;
   if(InpEntry == CFX_CONFIRM) entry = (zn.dir == 1) ? ask : bid;
   else                        entry = NormPrice(sym, zn.dir == 1 ? zn.top : zn.bot);

   double risk = (zn.dir == 1) ? entry - stop : stop - entry;
   if(risk <= 0) return;
   if(risk < InpMinStopAtr * atr || risk > InpMaxStopAtr * atr)
     {
      PrintFormat("%s: stop %.1f ATR outside %.1f-%.1f - skipped", sym, risk / atr, InpMinStopAtr, InpMaxStopAtr);
      return;
     }
   if((ask - bid) > InpMaxSpreadPct / 100.0 * risk)
     {
      PrintFormat("%s: spread too wide for this stop - skipped", sym);
      return;
     }
   double target = NormPrice(sym, entry + zn.dir * InpRR * risk);
   double lots = LotsForRisk(sym, risk);
   if(lots <= 0) return;

   trade.SetTypeFillingBySymbol(sym);
   bool ok;
   string tag = (zn.choch ? "CHoCH" : "BOS");
   if(InpEntry == CFX_CONFIRM)
      ok = (zn.dir == 1) ? trade.Buy(lots, sym, 0, stop, target, "CFX " + tag)
                         : trade.Sell(lots, sym, 0, stop, target, "CFX " + tag);
   else
     {
      double minDist = (SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) + 1) * SymbolInfoDouble(sym, SYMBOL_POINT);
      if((zn.dir == 1 && ask - entry < minDist) || (zn.dir == -1 && entry - bid < minDist)) return;
      string cmt = "CFX Z " + IntegerToString((long)zoneTime);
      ok = (zn.dir == 1) ? trade.BuyLimit(lots, entry, sym, stop, target, ORDER_TIME_GTC, 0, cmt)
                         : trade.SellLimit(lots, entry, sym, stop, target, ORDER_TIME_GTC, 0, cmt);
     }
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   if(ok)
      PrintFormat("%s: %s %s %.2f lots @ %s SL %s TP %s", sym, zn.dir == 1 ? "BUY" : "SELL",
                  InpEntry == CFX_CONFIRM ? "market" : "limit", lots, DoubleToString(entry, digits),
                  DoubleToString(stop, digits), DoubleToString(target, digits));
   else
      PrintFormat("%s: order failed %u %s", sym, trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Per-symbol work on each new bar                                   |
//+------------------------------------------------------------------+
bool Process(int i)
  {
   string sym = g_syms[i];
   datetime bt = iTime(sym, InpTF, 0);
   if(bt == 0 || bt == g_lastBar[i]) return false;

   MqlRates r[];
   int n = CopyRates(sym, InpTF, 1, InpHistoryBars, r);   // closed bars, oldest first
   if(n < InpSwingLen * 10) return false;
   g_lastBar[i] = bt;

   CSmc smc;
   smc.Run(r, n, InpSwingLen, InpObLookback);
   double atr[];
   ComputeAtr(r, n, atr);
   int htf = HtfFilterOn() ? HtfTrend(sym) : 0;

   if(InpEntry == CFX_ZONE) ManagePending(sym, smc, r, n, htf);

   for(int k = 0; k < ArraySize(smc.newZones); k++)
     {
      int z = smc.newZones[k];
      TryEnter(sym, smc.zones[z], r[smc.zones[z].created].time, atr[n - 1], htf);
     }

   int active = 0;
   for(int z = 0; z < ArraySize(smc.zones); z++)
      if(smc.zones[z].mitigatedAt < 0 && smc.zones[z].brokenAt < 0) active++;
   string last = "-";
   int ne = ArraySize(smc.events);
   if(ne > 0)
      last = (smc.events[ne-1].choch ? "CHoCH " : "BOS ") + (smc.events[ne-1].dir == 1 ? "up" : "down");
   g_status[i] = StringFormat("%-10s %s %-4s  %s %-4s  last %-10s zones %2d  open %d", sym,
                              TfName(InpTF), TrendName(smc.trend),
                              HtfFilterOn() ? TfName(InpHTF) : "HTF", HtfFilterOn() ? TrendName(htf) : "off",
                              last, active, CountPositions(sym));

   if(InpDraw && sym == _Symbol) Draw(smc, r, n);
   return true;
  }

string TfName(ENUM_TIMEFRAMES tf) { return StringSubstr(EnumToString(tf), 7); }   // PERIOD_M15 -> M15

string TrendName(int t) { return t == 1 ? "BULL" : t == -1 ? "BEAR" : "-"; }

void ShowPanel()
  {
   double closed, floating; int opened;
   TodayStats(closed, floating, opened);
   double pnl = closed + floating;
   string txt = StringFormat("Castimofx SMC v2   entry: %s   RR 1:%.1f   risk %.2f%%\nToday: %d trades, P/L %.2f %s\n",
                             InpEntry == CFX_CONFIRM ? "confirmation" : "zone limit", InpRR, InpRiskPct,
                             opened, pnl, AccountInfoString(ACCOUNT_CURRENCY));
   for(int i = 0; i < ArraySize(g_status); i++) txt += g_status[i] + "\n";
   Comment(txt);
  }

//+------------------------------------------------------------------+
//| Drawing                                                          |
//+------------------------------------------------------------------+
void Rect(string name, datetime t1, double p1, datetime t2, double p2, color c, bool fill)
  {
   ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void Seg(string name, datetime t1, double p1, datetime t2, double p2, color c, ENUM_LINE_STYLE st, int w = 1)
  {
   ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, w);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void Txt(string name, datetime t, double p, string text, color c, ENUM_ANCHOR_POINT anchor, int size = 8)
  {
   ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void Draw(CSmc &smc, const MqlRates &r[], int n)
  {
   ObjectsDeleteAll(0, PREFIX);
   int from = MathMax(0, n - InpDrawBars);
   int ps = PeriodSeconds(InpTF);
   datetime right = r[n-1].time + 15 * ps;

   // premium / discount / equilibrium
   if(smc.trailTopIdx >= 0 && smc.trailBotIdx >= 0)
     {
      double eq = (smc.trailTop + smc.trailBot) / 2.0;
      datetime left = r[MathMin(smc.trailTopIdx, smc.trailBotIdx)].time;
      Rect(PREFIX + "prem", left, smc.trailTop, right, eq, C'45,20,24', true);
      Rect(PREFIX + "disc", left, eq, right, smc.trailBot, C'14,40,32', true);
      Seg(PREFIX + "eq", left, eq, right, eq, clrGray, STYLE_DASH);
      Txt(PREFIX + "eqt", right, eq, "Equilibrium", clrGray, ANCHOR_LEFT);
      Txt(PREFIX + "pt", right, smc.trailTop, "Premium", InpBearColor, ANCHOR_LEFT_UPPER);
      Txt(PREFIX + "dt", right, smc.trailBot, "Discount", InpBullColor, ANCHOR_LEFT_LOWER);
      Txt(PREFIX + "th", r[smc.trailTopIdx].time, smc.trailTop, smc.trend == -1 ? "Strong High" : "Weak High", InpBearColor, ANCHOR_LOWER);
      Txt(PREFIX + "tl", r[smc.trailBotIdx].time, smc.trailBot, smc.trend == 1 ? "Strong Low" : "Weak Low", InpBullColor, ANCHOR_UPPER);
     }

   // supply & demand zones
   for(int z = 0; z < ArraySize(smc.zones); z++)
     {
      CfxZone zn = smc.zones[z];
      if(zn.created < from || zn.brokenAt >= 0) continue;
      bool touched = zn.mitigatedAt >= 0;
      datetime t2 = touched ? r[zn.mitigatedAt].time : right;
      color c = touched ? InpMitigColor : (zn.dir == 1 ? InpDemandColor : InpSupplyColor);
      string nm = PREFIX + "z" + IntegerToString(z);
      Rect(nm, r[zn.obIdx].time, zn.top, t2, zn.bot, c, true);
      if(!touched)
         Txt(nm + "t", right, zn.dir == 1 ? zn.bot : zn.top, zn.dir == 1 ? "Demand" : "Supply",
             zn.dir == 1 ? InpBullColor : InpBearColor, zn.dir == 1 ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER, 7);
     }

   // BOS / CHoCH
   for(int e = 0; e < ArraySize(smc.events); e++)
     {
      CfxEvent ev = smc.events[e];
      if(ev.breakIdx < from) continue;
      color c = ev.dir == 1 ? InpBullColor : InpBearColor;
      string nm = PREFIX + "e" + IntegerToString(e);
      Seg(nm, r[ev.swingIdx].time, ev.level, r[ev.breakIdx].time, ev.level, c, ev.choch ? STYLE_SOLID : STYLE_DOT);
      datetime mid = r[(ev.swingIdx + ev.breakIdx) / 2].time;
      Txt(nm + "t", mid, ev.level, ev.choch ? "CHoCH" : "BOS", c, ev.dir == 1 ? ANCHOR_LOWER : ANCHOR_UPPER, 7);
     }

   // previous day / week / month highs & lows
   string names[6] = {"PDH", "PDL", "PWH", "PWL", "PMH", "PML"};
   ENUM_TIMEFRAMES tfs[3] = {PERIOD_D1, PERIOD_W1, PERIOD_MN1};
   for(int k = 0; k < 3; k++)
     {
      double hi = iHigh(_Symbol, tfs[k], 1), lo = iLow(_Symbol, tfs[k], 1);
      datetime l = r[MathMax(0, n - 40)].time;
      if(hi > 0)
        {
         Seg(PREFIX + names[2*k], l, hi, right, hi, InpLevelColor, STYLE_DOT);
         Txt(PREFIX + names[2*k] + "t", right, hi, names[2*k], InpLevelColor, ANCHOR_LEFT, 7);
        }
      if(lo > 0)
        {
         Seg(PREFIX + names[2*k+1], l, lo, right, lo, InpLevelColor, STYLE_DOT);
         Txt(PREFIX + names[2*k+1] + "t", right, lo, names[2*k+1], InpLevelColor, ANCHOR_LEFT, 7);
        }
     }
   ChartRedraw(0);
  }
//+------------------------------------------------------------------+
