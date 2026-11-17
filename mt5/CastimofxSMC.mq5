//+------------------------------------------------------------------+
//|                                               CastimofxSMC.mq5   |
//|  Smart Money Concepts supply & demand Expert Advisor             |
//|  Same rules as the Castimofx TradingView indicator:              |
//|   - track structure (BOS / CHoCH) on the chart timeframe         |
//|   - on a break, mark the demand / supply zone at the leg origin   |
//|   - buy demand in discount after bullish break, sell supply in    |
//|     premium after bearish break                                   |
//|   - limit order at the zone edge, stop beyond the zone,          |
//|     target = RR x risk, risk = % of balance                       |
//|   - cancel if structure flips, zone breaks or order expires       |
//+------------------------------------------------------------------+
#property copyright "Castimofx"
#property version   "1.00"
#property description "SMC supply & demand auto-trader (BOS / CHoCH + order blocks)"

#include <Trade/Trade.mqh>

input group "Market structure"
input int      InpSwingLen      = 5;      // Swing length (bars each side)
input int      InpObLookback    = 5;      // Order-block search (bars)
input int      InpHistoryBars   = 1500;   // Bars analysed

input group "Entries"
input double   InpRR            = 2.0;    // Risk : reward
input bool     InpDiscountOnly  = true;   // Buy only in discount / sell only in premium
input bool     InpChochOnly     = false;  // Only zones created by a CHoCH
input double   InpSlBufferAtr   = 0.1;    // Stop buffer beyond zone (x ATR14)
input double   InpMinStopAtr    = 0.3;    // Skip if stop smaller than (x ATR14)
input double   InpMaxStopAtr    = 4.0;    // Skip if stop bigger than (x ATR14)
input int      InpExpiryBars    = 96;     // Cancel unfilled order after (bars)

input group "Risk"
input double   InpRiskPct       = 1.0;    // Risk per trade (% of balance)
input double   InpMaxSpreadPts  = 30;     // Max spread to place orders (points)
input int      InpStartHour     = 0;      // Trade from hour (server time)
input int      InpEndHour       = 24;     // Trade until hour (server time)
input ulong    InpMagic         = 20251117; // Magic number

//--- analysis types
struct Zone
  {
   int      dir;          // 1 demand, -1 supply
   double   top;
   double   bot;
   int      created;      // bar index (oldest = 0) of the break
   datetime createdTime;
   double   eq;           // dealing-range equilibrium at creation
   bool     choch;
   bool     mitigated;
   bool     broken;
  };

CTrade   trade;
MqlRates g_rates[];
Zone     g_zones[];
int      g_trend = 0;
string   g_lastEvent = "-";
datetime g_lastBarTime = 0;
datetime g_pendingZoneTime = 0;   // zone behind our pending order
int      g_pendingDir = 0;

int OnBreak(const MqlRates &r[], int t, int swing, int dir);   // forward declaration

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpSwingLen < 2 || InpHistoryBars < 100 || InpRR <= 0 || InpRiskPct <= 0)
     {
      Print("Invalid inputs");
      return(INIT_PARAMETERS_INCORRECT);
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(20);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) { Comment(""); }

//+------------------------------------------------------------------+
//| Wilder ATR(14) of every bar                                      |
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
      if(t < len)
        {
         sum += tr;
         atr[t] = sum / (t + 1);
        }
      else
         atr[t] = (atr[t-1] * (len - 1) + tr) / len;
     }
  }

//+------------------------------------------------------------------+
//| Run the structure / zone state machine over all closed bars.     |
//| Returns the index of a zone created on the last closed bar, or -1 |
//| (if both sides broke on that bar, the later one is returned).     |
//+------------------------------------------------------------------+
int Analyze(const MqlRates &r[], int n)
  {
   ArrayResize(g_zones, 0);
   g_trend = 0;
   int    L = InpSwingLen;
   int    sh = -1, sl = -1;
   bool   shBroken = true, slBroken = true;
   int    newest = -1;

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
         if(isHigh) { sh = i; shBroken = false; }
         if(isLow)  { sl = i; slBroken = false; }
        }

      // 2. zones: broken (close through) / mitigated (touched)
      for(int z = 0; z < ArraySize(g_zones); z++)
        {
         if(g_zones[z].mitigated || g_zones[z].broken || g_zones[z].created >= t) continue;
         if(g_zones[z].dir == 1)
           {
            if(r[t].close < g_zones[z].bot)      g_zones[z].broken = true;
            else if(r[t].low <= g_zones[z].top)  g_zones[z].mitigated = true;
           }
         else
           {
            if(r[t].close > g_zones[z].top)      g_zones[z].broken = true;
            else if(r[t].high >= g_zones[z].bot) g_zones[z].mitigated = true;
           }
        }

      // 3. structure breaks
      if(sh >= 0 && !shBroken && r[t].close > r[sh].high)
        {
         shBroken = true;
         int idx = OnBreak(r, t, sh, 1);
         if(t == n - 1) newest = idx;
        }
      if(sl >= 0 && !slBroken && r[t].close < r[sl].low)
        {
         slBroken = true;
         int idx = OnBreak(r, t, sl, -1);
         if(t == n - 1) newest = idx;
        }
     }
   return newest;
  }

int OnBreak(const MqlRates &r[], int t, int swing, int dir)
  {
   bool choch = (g_trend == -dir);
   g_trend = dir;
   g_lastEvent = (choch ? "CHoCH " : "BOS ") + (dir == 1 ? "bullish" : "bearish") + " @ " +
                 DoubleToString(dir == 1 ? r[swing].high : r[swing].low, _Digits);

   // origin of the leg that broke structure
   int origin = swing;
   for(int k = swing; k <= t; k++)
     {
      if(dir == 1  && r[k].low  < r[origin].low)  origin = k;
      if(dir == -1 && r[k].high > r[origin].high) origin = k;
     }
   double rHigh, rLow;
   if(dir == 1)
     {
      rLow = r[origin].low; rHigh = r[origin].high;
      for(int k = origin; k <= t; k++) rHigh = MathMax(rHigh, r[k].high);
     }
   else
     {
      rHigh = r[origin].high; rLow = r[origin].low;
      for(int k = origin; k <= t; k++) rLow = MathMin(rLow, r[k].low);
     }

   // order block = last opposite-colour candle at / just before the origin
   int ob = origin;
   for(int j = origin; j >= MathMax(origin - InpObLookback, 0); j--)
     {
      bool opposite = (dir == 1) ? (r[j].close < r[j].open) : (r[j].close > r[j].open);
      if(opposite) { ob = j; break; }
     }

   Zone zn;
   zn.dir = dir;
   if(dir == 1)
     {
      zn.top = r[ob].high;
      zn.bot = r[ob].low;
      for(int k = ob; k <= origin; k++) zn.bot = MathMin(zn.bot, r[k].low);
     }
   else
     {
      zn.bot = r[ob].low;
      zn.top = r[ob].high;
      for(int k = ob; k <= origin; k++) zn.top = MathMax(zn.top, r[k].high);
     }
   zn.created     = t;
   zn.createdTime = r[t].time;
   zn.eq          = (rHigh + rLow) / 2.0;
   zn.choch       = choch;
   zn.mitigated   = false;
   zn.broken      = false;

   int size = ArraySize(g_zones);
   ArrayResize(g_zones, size + 1);
   g_zones[size] = zn;
   return size;
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
double NormalizePrice(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) return NormalizeDouble(p, _Digits);
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

double LotsForRisk(double stopDist)
  {
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickValue <= 0 || tickSize <= 0 || step <= 0 || stopDist <= 0) return 0;

   double lossPerLot = stopDist / tickSize * tickValue;
   double lots = MathFloor(riskMoney / lossPerLot / step) * step;
   if(lots < minLot)
     {
      PrintFormat("Risk %.2f too small for min lot %.2f (stop %.5f) - skipped", riskMoney, minLot, stopDist);
      return 0;
     }
   lots = MathMin(lots, maxLot);
   int volDigits = (int)MathMax(0, MathCeil(-MathLog10(step)));
   return NormalizeDouble(lots, volDigits);
  }

bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic)
         return true;
     }
   return false;
  }

// Delete our pending orders (all, or only those older than maxAgeSec / against the trend)
void ManagePendingOrders(bool deleteAll)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol || OrderGetInteger(ORDER_MAGIC) != (long)InpMagic) continue;

      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      int dir = (type == ORDER_TYPE_BUY_LIMIT) ? 1 : (type == ORDER_TYPE_SELL_LIMIT ? -1 : 0);
      if(dir == 0) continue;

      datetime setup = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      bool expired   = (TimeCurrent() - setup) >= (long)InpExpiryBars * PeriodSeconds(_Period);
      bool against   = (g_trend != dir);
      bool zoneBroken = false;
      if(g_pendingZoneTime != 0)
         for(int z = 0; z < ArraySize(g_zones); z++)
            if(g_zones[z].createdTime == g_pendingZoneTime && g_zones[z].dir == dir && g_zones[z].broken)
               zoneBroken = true;

      if(deleteAll || expired || against || zoneBroken)
        {
         if(trade.OrderDelete(ticket))
            PrintFormat("Cancelled order %I64u (%s)", ticket,
                        deleteAll ? "replaced" : expired ? "expired" : against ? "structure flipped" : "zone broken");
        }
     }
  }

bool InSession()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(InpStartHour <= InpEndHour) return dt.hour >= InpStartHour && dt.hour < InpEndHour;
   return dt.hour >= InpStartHour || dt.hour < InpEndHour;   // overnight window
  }

void PlaceOrder(const Zone &zn, double atr)
  {
   if(InpChochOnly && !zn.choch) return;
   if(InpDiscountOnly && ((zn.dir == 1 && zn.top > zn.eq) || (zn.dir == -1 && zn.bot < zn.eq)))
     {
      Print("Zone not in discount/premium - skipped");
      return;
     }

   double buf    = InpSlBufferAtr * atr;
   double entry  = NormalizePrice(zn.dir == 1 ? zn.top : zn.bot);
   double stop   = NormalizePrice(zn.dir == 1 ? zn.bot - buf : zn.top + buf);
   double risk   = MathAbs(entry - stop);
   double target = NormalizePrice(entry + zn.dir * InpRR * risk);
   if(risk < InpMinStopAtr * atr || risk > InpMaxStopAtr * atr)
     {
      PrintFormat("Stop %.5f outside %.1f-%.1f ATR - skipped", risk, InpMinStopAtr, InpMaxStopAtr);
      return;
     }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double spreadPts = (ask - bid) / _Point;
   if(spreadPts > InpMaxSpreadPts)
     {
      PrintFormat("Spread %.0f pts too wide - skipped", spreadPts);
      return;
     }
   double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 1) * _Point;
   if((zn.dir == 1 && ask - entry < minDist) || (zn.dir == -1 && entry - bid < minDist))
     {
      Print("Price already at / through the zone - skipped");
      return;
     }

   double lots = LotsForRisk(risk);
   if(lots <= 0) return;

   ManagePendingOrders(true);   // one pending order at a time: newest zone wins
   string comment = (zn.choch ? "CFX CHoCH" : "CFX BOS");
   bool ok = (zn.dir == 1)
             ? trade.BuyLimit(lots, entry, _Symbol, stop, target, ORDER_TIME_GTC, 0, comment)
             : trade.SellLimit(lots, entry, _Symbol, stop, target, ORDER_TIME_GTC, 0, comment);
   if(ok)
     {
      g_pendingZoneTime = zn.createdTime;
      g_pendingDir = zn.dir;
      PrintFormat("%s LIMIT %.2f lots @ %s SL %s TP %s", zn.dir == 1 ? "BUY" : "SELL", lots,
                  DoubleToString(entry, _Digits), DoubleToString(stop, _Digits), DoubleToString(target, _Digits));
     }
   else
      PrintFormat("Order failed: %u %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime barTime = iTime(_Symbol, _Period, 0);
   if(barTime == 0 || barTime == g_lastBarTime) return;   // act once per new bar

   int n = CopyRates(_Symbol, _Period, 1, InpHistoryBars, g_rates);   // closed bars, oldest first
   if(n < InpSwingLen * 4) return;
   g_lastBarTime = barTime;

   int newest = Analyze(g_rates, n);
   double atr[];
   ComputeAtr(g_rates, n, atr);

   ManagePendingOrders(false);

   bool inPos = HasPosition();
   if(newest >= 0 && !inPos && InSession())
      PlaceOrder(g_zones[newest], atr[n - 1]);

   int active = 0;
   for(int z = 0; z < ArraySize(g_zones); z++)
      if(!g_zones[z].mitigated && !g_zones[z].broken) active++;
   Comment(StringFormat("Castimofx SMC\nStructure: %s\nLast: %s\nActive zones: %d\nPosition: %s",
                        g_trend == 1 ? "BULLISH" : g_trend == -1 ? "BEARISH" : "-",
                        g_lastEvent, active, inPos ? "open" : "none"));
  }
//+------------------------------------------------------------------+
