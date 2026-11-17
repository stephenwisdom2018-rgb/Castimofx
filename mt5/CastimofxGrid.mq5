//+------------------------------------------------------------------+
//|                                              CastimofxGrid.mq5   |
//|  Castimofx V5 GRID - SMC Strong High / Strong Low limit grids    |
//|                                                                  |
//|  Rules                                                           |
//|  1. No per-trade stop loss                                       |
//|  2. Strong High -> SELL LIMITS above it (count x spacing)        |
//|  3. Strong Low  -> BUY LIMITS below it                           |
//|     When the Strong level changes, pending orders are deleted    |
//|     and a new grid is placed                                     |
//|  4. A new BUY closes all SELLS (and vice versa), no hedging      |
//|  5. Bounce entry: price reaches the zone, does not hit the first |
//|     limit and the candle closes back -> market entry             |
//|  Each position: fixed take profit distance                       |
//|  Emergency: close everything if equity <= X% of balance          |
//+------------------------------------------------------------------+
#property copyright "Castimofx"
#property version   "5.00"
#property description "SMC Strong High/Low grid (no stop loss) with emergency equity stop"

#include <Trade/Trade.mqh>

input group "Structure"
input ENUM_TIMEFRAMES InpTF        = PERIOD_M15; // Timeframe for Strong High / Low
input int      InpSwingLen         = 3;          // Swing length (bars each side)
input int      InpHistoryBars      = 1500;       // Bars analysed

input group "Grid"
input double   InpLot              = 0.01;   // Lot per order
input int      InpCount            = 10;     // Orders per grid
input double   InpSpacing          = 2.0;    // Distance between orders (price, e.g. $2 on gold)
input double   InpTP               = 20.0;   // Take profit per position (price distance, e.g. $20)
input bool     InpBounce           = true;   // Bounce entry (rule 5)
input double   InpBounceZone       = 3.0;    // Bounce: price must come this close to the level (price)

input group "Safety"
input double   InpEmergencyPct     = 50.0;   // Close ALL if equity falls to this % of balance (0 = off)
input bool     InpStopAfterEmergency = true; // After emergency close, stop trading until EA is re-attached
input double   InpMaxSpread        = 1.0;    // Don't place new orders if spread is above this (price)
input ulong    InpMagic            = 20260505; // Magic number

input group "Drawing"
input bool     InpDraw          = true;
input int      InpDrawBars      = 400;
input color    InpDemandColor   = C'0,105,75';
input color    InpSupplyColor   = C'130,35,35';
input color    InpMitigColor    = C'70,70,70';
input color    InpBullColor     = C'8,153,129';
input color    InpBearColor     = C'242,54,69';
input color    InpGridColor     = clrGold;

#define PREFIX "CFXG_"

//+------------------------------------------------------------------+
//| SMC analysis (same engine as CastimofxSMC)                       |
//+------------------------------------------------------------------+
struct CfxZone
  {
   int      dir;
   double   top;
   double   bot;
   int      obIdx;
   int      created;
   int      mitigatedAt;
   int      brokenAt;
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

   void Run(const MqlRates &r[], int n, int L)
     {
      trend = 0;
      trailTop = 0; trailBot = 0; trailTopIdx = -1; trailBotIdx = -1;
      ArrayResize(zones, 0);
      ArrayResize(events, 0);
      int sh = -1, sl = -1;
      bool shBroken = true, slBroken = true;

      for(int t = 0; t < n; t++)
        {
         int i = t - L;
         if(i >= L)
           {
            bool isHigh = true, isLow = true;
            for(int k = 1; k <= L; k++)
              {
               if(!(r[i].high > r[i-k].high) || !(r[i].high >= r[i+k].high)) isHigh = false;
               if(!(r[i].low  < r[i-k].low)  || !(r[i].low  <= r[i+k].low))  isLow  = false;
              }
            if(isHigh) { sh = i; shBroken = false; trailTop = r[i].high; trailTopIdx = i; }
            if(isLow)  { sl = i; slBroken = false; trailBot = r[i].low;  trailBotIdx = i; }
           }
         if(trailTopIdx >= 0 && r[t].high > trailTop) { trailTop = r[t].high; trailTopIdx = t; }
         if(trailBotIdx >= 0 && r[t].low  < trailBot) { trailBot = r[t].low;  trailBotIdx = t; }

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

         if(sh >= 0 && !shBroken && r[t].close > r[sh].high) { shBroken = true; OnBreak(r, t, sh, 1); }
         if(sl >= 0 && !slBroken && r[t].close < r[sl].low)  { slBroken = true; OnBreak(r, t, sl, -1); }
        }
     }

private:
   void OnBreak(const MqlRates &r[], int t, int swing, int dir)
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

      int origin = swing;
      for(int k = swing; k <= t; k++)
        {
         if(dir == 1  && r[k].low  < r[origin].low)  origin = k;
         if(dir == -1 && r[k].high > r[origin].high) origin = k;
        }
      int ob = origin;
      for(int j = origin; j >= MathMax(origin - 5, 0); j--)
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
      zn.obIdx = ob;
      zn.created = t;
      zn.mitigatedAt = -1;
      zn.brokenAt = -1;
      int size = ArraySize(zones);
      ArrayResize(zones, size + 1);
      zones[size] = zn;
     }
  };

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
CTrade   trade;
datetime g_lastBar     = 0;
int      g_gridDir     = 0;      // -1 sell grid, 1 buy grid, 0 none
double   g_gridLevel   = 0;
bool     g_bounceUsed  = false;
bool     g_stopped     = false;
string   g_info        = "";

int OnInit()
  {
   if(InpCount < 1 || InpSpacing <= 0 || InpTP <= 0 || InpLot <= 0)
      return(INIT_PARAMETERS_INCORRECT);
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, PREFIX);
   Comment("");
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
double NormPrice(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) return NormalizeDouble(p, _Digits);
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

bool IsOurs()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic;
  }

int CountPos(int dir)   // dir 0 = all
  {
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsOurs()) continue;
      int d = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      if(dir == 0 || d == dir) c++;
     }
   return c;
  }

double FloatingPL()
  {
   double p = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsOurs()) continue;
      p += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   return p;
  }

void ClosePositions(int dir)   // dir 0 = all
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsOurs()) continue;
      int d = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      if(dir == 0 || d == dir)
         trade.PositionClose(ticket);
     }
  }

void DeletePending(int dir)    // dir 0 = all
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol || OrderGetInteger(ORDER_MAGIC) != (long)InpMagic) continue;
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      int d = (type == ORDER_TYPE_BUY_LIMIT || type == ORDER_TYPE_BUY_STOP) ? 1 : -1;
      if(dir == 0 || d == dir)
         trade.OrderDelete(ticket);
     }
  }

//+------------------------------------------------------------------+
//| Rule 4: newest position direction wins, opposite side is closed  |
//+------------------------------------------------------------------+
void EnforceOneDirection()
  {
   long newestTime = 0;
   int  newestDir  = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsOurs()) continue;
      long tm = PositionGetInteger(POSITION_TIME_MSC);
      if(tm > newestTime)
        {
         newestTime = tm;
         newestDir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
        }
     }
   if(newestDir != 0 && CountPos(-newestDir) > 0)
     {
      PrintFormat("New %s entered - closing all %s positions", newestDir == 1 ? "BUY" : "SELL", newestDir == 1 ? "SELL" : "BUY");
      ClosePositions(-newestDir);
      DeletePending(-newestDir);
     }
  }

//+------------------------------------------------------------------+
//| Safety: equity stop                                              |
//+------------------------------------------------------------------+
void CheckEmergency()
  {
   if(InpEmergencyPct <= 0 || CountPos(0) == 0) return;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= balance * InpEmergencyPct / 100.0)
     {
      PrintFormat("EMERGENCY: equity %.2f <= %.0f%% of balance %.2f - closing everything", equity, InpEmergencyPct, balance);
      ClosePositions(0);
      DeletePending(0);
      g_gridDir = 0;
      g_gridLevel = 0;
      if(InpStopAfterEmergency) g_stopped = true;
     }
  }

//+------------------------------------------------------------------+
//| Grid placement                                                   |
//+------------------------------------------------------------------+
void PlaceGrid(int dir, double level)
  {
   DeletePending(0);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask - bid > InpMaxSpread)
     {
      PrintFormat("Spread %.2f too wide - grid not placed, will retry next bar", ask - bid);
      return;
     }
   g_gridDir = dir;
   g_gridLevel = level;
   g_bounceUsed = false;
   double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 1) * _Point;
   int placed = 0;
   for(int k = 1; k <= InpCount; k++)
     {
      double price = NormPrice(level - dir * InpSpacing * k);   // sells above the high, buys below the low
      double tp    = NormPrice(price + dir * InpTP);
      bool ok = false;
      if(dir == -1 && price - bid > minDist)
         ok = trade.SellLimit(InpLot, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, "CFX G" + IntegerToString(k));
      if(dir == 1 && ask - price > minDist)
         ok = trade.BuyLimit(InpLot, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, "CFX G" + IntegerToString(k));
      if(ok) placed++;
     }
   PrintFormat("%s GRID at Strong %s %s: %d limit orders, every %.2f, TP %.2f, no SL",
               dir == -1 ? "SELL" : "BUY", dir == -1 ? "High" : "Low", DoubleToString(level, _Digits), placed, InpSpacing, InpTP);
  }

void BounceEntry(const MqlRates &bar)
  {
   if(!InpBounce || g_bounceUsed || g_gridDir == 0) return;
   double first = g_gridLevel - g_gridDir * InpSpacing;
   bool sell = (g_gridDir == -1 && bar.high >= g_gridLevel - InpBounceZone && bar.high < first &&
                bar.close < bar.open && bar.close < g_gridLevel);
   bool buy  = (g_gridDir == 1 && bar.low <= g_gridLevel + InpBounceZone && bar.low > first &&
                bar.close > bar.open && bar.close > g_gridLevel);
   if(!sell && !buy) return;
   g_bounceUsed = true;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask - bid > InpMaxSpread) return;
   bool ok = sell ? trade.Sell(InpLot, _Symbol, 0, 0, NormPrice(bid - InpTP), "CFX bounce")
                  : trade.Buy(InpLot, _Symbol, 0, 0, NormPrice(ask + InpTP), "CFX bounce");
   if(ok) PrintFormat("BOUNCE %s at market (zone tested, limits not reached)", sell ? "SELL" : "BUY");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   CheckEmergency();
   EnforceOneDirection();
   if(g_stopped)
     {
      Comment("Castimofx GRID V5 - STOPPED after emergency close. Re-attach the EA to start again.");
      return;
     }

   datetime bt = iTime(_Symbol, InpTF, 0);
   if(bt != 0 && bt != g_lastBar)
     {
      MqlRates r[];
      int n = CopyRates(_Symbol, InpTF, 1, InpHistoryBars, r);
      if(n > InpSwingLen * 10)
        {
         g_lastBar = bt;
         CSmc smc;
         smc.Run(r, n, InpSwingLen);

         int dir = 0;
         double level = 0;
         if(smc.trend == -1 && smc.trailTopIdx >= 0) { dir = -1; level = smc.trailTop; }
         if(smc.trend ==  1 && smc.trailBotIdx >= 0) { dir =  1; level = smc.trailBot; }

         if(dir != 0 && (dir != g_gridDir || MathAbs(level - g_gridLevel) > _Point / 2))
            PlaceGrid(dir, level);          // new Strong level -> delete pending, new grid
         else
            BounceEntry(r[n - 1]);

         if(InpDraw) Draw(smc, r, n);
        }
     }

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   Comment(StringFormat("Castimofx GRID V5   %s  lot %.2f x %d  every %.2f  TP %.2f  NO SL\n"
                        "Grid: %s at Strong %s %s\n"
                        "Open: %d buys, %d sells   Floating P/L: %.2f\n"
                        "Balance %.2f   Equity %.2f   Emergency close at equity %.2f",
                        _Symbol, InpLot, InpCount, InpSpacing, InpTP,
                        g_gridDir == -1 ? "SELL" : g_gridDir == 1 ? "BUY" : "none",
                        g_gridDir == -1 ? "High" : "Low", DoubleToString(g_gridLevel, _Digits),
                        CountPos(1), CountPos(-1), FloatingPL(),
                        balance, AccountInfoDouble(ACCOUNT_EQUITY), balance * InpEmergencyPct / 100.0));
  }

//+------------------------------------------------------------------+
//| Drawing                                                          |
//+------------------------------------------------------------------+
void Rect(string name, datetime t1, double p1, datetime t2, double p2, color c)
  {
   ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void Seg(string name, datetime t1, double p1, datetime t2, double p2, color c, ENUM_LINE_STYLE st)
  {
   ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void Txt(string name, datetime t, double p, string text, color c, ENUM_ANCHOR_POINT anchor)
  {
   ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 7);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void Draw(CSmc &smc, const MqlRates &r[], int n)
  {
   ObjectsDeleteAll(0, PREFIX);
   int from = MathMax(0, n - InpDrawBars);
   datetime right = r[n-1].time + 15 * PeriodSeconds(InpTF);

   for(int z = 0; z < ArraySize(smc.zones); z++)
     {
      CfxZone zn = smc.zones[z];
      if(zn.created < from || zn.brokenAt >= 0) continue;
      bool touched = zn.mitigatedAt >= 0;
      color c = touched ? InpMitigColor : (zn.dir == 1 ? InpDemandColor : InpSupplyColor);
      Rect(PREFIX + "z" + IntegerToString(z), r[zn.obIdx].time, zn.top, touched ? r[zn.mitigatedAt].time : right, zn.bot, c);
     }
   for(int e = 0; e < ArraySize(smc.events); e++)
     {
      CfxEvent ev = smc.events[e];
      if(ev.breakIdx < from) continue;
      color c = ev.dir == 1 ? InpBullColor : InpBearColor;
      string nm = PREFIX + "e" + IntegerToString(e);
      Seg(nm, r[ev.swingIdx].time, ev.level, r[ev.breakIdx].time, ev.level, c, ev.choch ? STYLE_SOLID : STYLE_DOT);
      Txt(nm + "t", r[(ev.swingIdx + ev.breakIdx) / 2].time, ev.level, ev.choch ? "CHoCH" : "BOS", c,
          ev.dir == 1 ? ANCHOR_LOWER : ANCHOR_UPPER);
     }
   if(smc.trailTopIdx >= 0)
      Txt(PREFIX + "th", r[smc.trailTopIdx].time, smc.trailTop, smc.trend == -1 ? "Strong High" : "Weak High", InpBearColor, ANCHOR_LOWER);
   if(smc.trailBotIdx >= 0)
      Txt(PREFIX + "tl", r[smc.trailBotIdx].time, smc.trailBot, smc.trend == 1 ? "Strong Low" : "Weak Low", InpBullColor, ANCHOR_UPPER);

   if(g_gridDir != 0)
     {
      datetime left = r[MathMax(0, n - 30)].time;
      Seg(PREFIX + "lvl", left, g_gridLevel, right, g_gridLevel, InpGridColor, STYLE_SOLID);
      Txt(PREFIX + "lvlt", right, g_gridLevel, g_gridDir == -1 ? "SELL GRID above" : "BUY GRID below", InpGridColor, ANCHOR_LEFT);
     }
   ChartRedraw(0);
  }
//+------------------------------------------------------------------+
