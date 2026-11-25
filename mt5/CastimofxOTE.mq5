//+------------------------------------------------------------------+
//|                                               CastimofxOTE.mq5   |
//|  "CHoCH OTE" Expert Advisor                                       |
//|                                                                  |
//|  1. CHoCH: price closes through the last swing against the trend |
//|  2. Fibonacci over the leg that broke structure                   |
//|  3. Limit entry in the OTE zone (62-79%, default 70.5%)           |
//|  4. Stop beyond the leg origin + ATR buffer                       |
//|  5. TP1 50% / TP2 0% (leg extreme) / TP3 -27% / TP4 -62%,         |
//|     split over up to 4 orders, stop to breakeven after TP1        |
//|  Draws the setup, the "sell / buy zone" and PSY levels.           |
//|  Same rules as tradingview/castimofx_ote.pine and castimofx/ote.py|
//+------------------------------------------------------------------+
#property copyright "Castimofx"
#property version   "1.00"
#property description "CHoCH + OTE (Fibonacci 62-79%) auto-trader with 4 take-profits"

#include <Trade/Trade.mqh>

input group "Setup"
input ENUM_TIMEFRAMES InpTF      = PERIOD_M15; // Timeframe
input int      InpSwingLen       = 5;      // Swing length (bars each side)
input bool     InpAllowBos       = false;  // Also trade BOS (not only CHoCH)
input double   InpOteEntry       = 0.705;  // Entry level (fraction of the leg)
input double   InpOteLo          = 0.62;   // OTE zone from
input double   InpOteHi          = 0.79;   // OTE zone to
input double   InpSlBufferAtr    = 0.2;    // Stop buffer beyond leg origin (x ATR14)
input double   InpMinLegAtr      = 1.5;    // Min leg size (x ATR14)
input double   InpMaxLegAtr      = 15.0;   // Max leg size (x ATR14)
input int      InpExpiryBars     = 48;     // Cancel unfilled order after (bars)
input int      InpHistoryBars    = 1500;   // Bars analysed

input group "Take profits (Fibonacci level of the leg)"
input double   InpTp1            = 0.5;    // TP1 (0.5 = 50%)
input double   InpTp2            = 0.0;    // TP2 (0 = leg extreme)
input double   InpTp3            = -0.27;  // TP3
input double   InpTp4            = -0.62;  // TP4
input bool     InpBreakeven      = true;   // Move stop to breakeven once TP1 is reached

input group "Accuracy filters (all off = the plain setup)"
input bool     InpSweep          = false;  // Leg must sweep the previous swing
input bool     InpObOverlap      = false;  // OTE zone must overlap the order block
input bool     InpPsyFilter      = false;  // A PSY level must sit inside the OTE zone
input double   InpDisplAtr       = 0.0;    // Breaking candle at least (x ATR, 0 = off)
input ENUM_TIMEFRAMES InpHTF     = PERIOD_CURRENT; // Higher-timeframe trend filter (CURRENT = off)
input int      InpStartHour      = 0;      // Trade from hour (server time)
input int      InpEndHour        = 24;     // Trade until hour (server time)

input group "Risk"
input double   InpRiskPct        = 1.0;    // Risk per setup (% of balance, all orders together)
input double   InpMinLotMaxRisk  = 2.0;    // If min lot risks more than the above, still trade it up to this %
input double   InpMaxDailyLoss   = 3.0;    // Stop new trades after losing this % today
input double   InpMaxSpreadPct   = 15.0;   // Skip if spread > this % of the stop distance
input ulong    InpMagic          = 20261125; // Magic number

input group "Drawing"
input bool     InpDraw           = true;   // Draw on chart
input double   InpPsyBase        = 100.0;  // PSY: full level every (gold 100 -> 1/2 = 50, 1/4 = 25)
input int      InpPsyCount       = 4;      // PSY lines each side of price
input color    InpBuyColor       = C'8,153,129';
input color    InpSellColor      = C'242,54,69';
input color    InpEntryColor     = C'41,98,255';
input color    InpPsyColor       = C'156,39,176';

#define PREFIX "CFXOTE_"

CTrade   trade;
datetime g_lastBar = 0;
string   g_status = "waiting for data";

//+------------------------------------------------------------------+
//| Replay of the strategy over the history (same logic as ote.py)   |
//+------------------------------------------------------------------+
struct OteSetup
  {
   bool     active;
   int      dir;        // 1 buy, -1 sell
   double   origin;     // leg start (protected extreme)
   double   extreme;    // leg end
   int      created;    // bar index of the CHoCH
   int      originIdx;
   double   atr;
   double   obTop, obBot;
   int      obIdx;
   bool     choch;
  };

double Lvl(const OteSetup &s, double f) { return s.extreme + f * (s.origin - s.extreme); }

bool InSessionBar(datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   if(InpStartHour <= InpEndHour) return dt.hour >= InpStartHour && dt.hour < InpEndHour;
   return dt.hour >= InpStartHour || dt.hour < InpEndHour;
  }


class COte
  {
public:
   int      trend;
   OteSetup setup;      // pending setup after the last closed bar
   OteSetup last;       // last setup created (for drawing)
   int      nSetups;

   void Run(const MqlRates &r[], int n, const double &atr[], const int &htf[])
     {
      trend = 0;
      nSetups = 0;
      setup.active = false;
      last.active = false;
      int L = InpSwingLen;
      int shIdx = -1, slIdx = -1;
      bool shBroken = true, slBroken = true;
      int swI[]; double swP[]; bool swHigh[];
      ArrayResize(swI, 0); ArrayResize(swP, 0); ArrayResize(swHigh, 0);

      for(int t = 0; t < n; t++)
        {
         // fill (levels from the previous close): the setup is used up when price reaches the entry
         if(setup.active && InSessionBar(r[t].time))
           {
            double entry = Lvl(setup, InpOteEntry);
            bool touched = setup.dir == -1 ? r[t].high >= entry : r[t].low <= entry;
            if(touched) setup.active = false;
           }

         // swings confirmed L bars after they form
         int i = t - L;
         if(i >= L)
           {
            bool isH = true, isL = true;
            for(int k = 1; k <= L; k++)
              {
               if(!(r[i].high > r[i-k].high) || !(r[i].high >= r[i+k].high)) isH = false;
               if(!(r[i].low  < r[i-k].low)  || !(r[i].low  <= r[i+k].low))  isL = false;
              }
            if(isH) { shIdx = i; shBroken = false; AddSwing(swI, swP, swHigh, i, r[i].high, true); }
            if(isL) { slIdx = i; slBroken = false; AddSwing(swI, swP, swHigh, i, r[i].low, false); }
           }

         int brkDir = 0, brkFrom = -1;
         bool brkChoch = false;
         if(shIdx >= 0 && !shBroken && r[t].close > r[shIdx].high)
           { shBroken = true; brkChoch = trend == -1; trend = 1; brkDir = 1; brkFrom = shIdx; }
         if(slIdx >= 0 && !slBroken && r[t].close < r[slIdx].low)
           { slBroken = true; brkChoch = trend == 1; trend = -1; brkDir = -1; brkFrom = slIdx; }

         // extend / cancel the pending setup
         if(setup.active)
           {
            int d = setup.dir;
            if((d == -1 && r[t].close > setup.origin) || (d == 1 && r[t].close < setup.origin)
               || t >= setup.created + InpExpiryBars || trend != d)
               setup.active = false;
            else if(d == -1 && r[t].low < setup.extreme)  setup.extreme = r[t].low;
            else if(d == 1  && r[t].high > setup.extreme) setup.extreme = r[t].high;
           }

         // new CHoCH -> new setup
         if(brkDir != 0 && (brkChoch || InpAllowBos))
           {
            int d = brkDir;
            int oB = brkFrom;
            for(int k = brkFrom; k <= t; k++)
               if(d == -1 ? r[k].high > r[oB].high : r[k].low < r[oB].low) oB = k;
            double oP = d == -1 ? r[oB].high : r[oB].low;
            double ext = d == -1 ? r[oB].low : r[oB].high;
            for(int k = oB; k <= t; k++)
               ext = d == -1 ? MathMin(ext, r[k].low) : MathMax(ext, r[k].high);
            int obI = oB;
            for(int k = oB; k >= (int)MathMax(oB - 5, 0); k--)
               if(d == -1 ? r[k].close > r[k].open : r[k].close < r[k].open) { obI = k; break; }
            double obTop = r[obI].high, obBot = r[obI].low;
            for(int k = obI; k <= oB; k++)
              {
               if(d == -1) obTop = MathMax(obTop, r[k].high);
               else        obBot = MathMin(obBot, r[k].low);
              }
            bool swept = false;
            for(int k = ArraySize(swI) - 1; k >= 0; k--)
               if(swHigh[k] == (d == -1) && swI[k] < obI) { swept = d == -1 ? oP > swP[k] : oP < swP[k]; break; }

            nSetups++;
            bool ok = MathAbs(oP - ext) >= InpMinLegAtr * atr[t];
            ok = ok && (!InpSweep || swept);
            ok = ok && (InpDisplAtr <= 0 || r[t].high - r[t].low >= InpDisplAtr * atr[t]);
            if(InpHTF != PERIOD_CURRENT && PeriodSeconds(InpHTF) > PeriodSeconds(InpTF) && htf[t] != d) ok = false;
            if(ok)
              {
               setup.active = true; setup.dir = d; setup.origin = oP; setup.extreme = ext;
               setup.created = t; setup.originIdx = oB; setup.atr = atr[t];
               setup.obTop = obTop; setup.obBot = obBot; setup.obIdx = obI; setup.choch = brkChoch;
              }
           }
         if(setup.active) last = setup;
        }
     }

private:
   void AddSwing(int &idx[], double &px[], bool &hi[], int i, double p, bool isHigh)
     {
      int k = ArraySize(idx);
      ArrayResize(idx, k + 1); ArrayResize(px, k + 1); ArrayResize(hi, k + 1);
      idx[k] = i; px[k] = p; hi[k] = isHigh;
     }
  };

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
void ComputeAtr(const MqlRates &r[], int n, double &atr[])
  {
   ArrayResize(atr, n);
   double run = 0;
   for(int t = 0; t < n; t++)
     {
      double tr = t == 0 ? r[t].high - r[t].low
                  : MathMax(r[t].high - r[t].low, MathMax(MathAbs(r[t].high - r[t-1].close), MathAbs(r[t].low - r[t-1].close)));
      if(t < 14) { run += tr; atr[t] = run / (t + 1); }
      else atr[t] = (atr[t-1] * 13 + tr) / 14;
     }
  }

// structure trend of the higher timeframe, known at the close of each chart bar
void ComputeHtf(const MqlRates &r[], int n, int &htf[])
  {
   ArrayResize(htf, n);
   ArrayInitialize(htf, 0);
   if(InpHTF == PERIOD_CURRENT || PeriodSeconds(InpHTF) <= PeriodSeconds(InpTF)) return;
   MqlRates hr[];
   int hn = CopyRates(_Symbol, InpHTF, 1, 800, hr);
   if(hn < InpSwingLen * 4) return;
   int tr[];
   ArrayResize(tr, hn);
   int L = InpSwingLen, trend = 0, sh = -1, sl = -1;
   bool shB = true, slB = true;
   for(int t = 0; t < hn; t++)
     {
      int i = t - L;
      if(i >= L)
        {
         bool isH = true, isL = true;
         for(int k = 1; k <= L; k++)
           {
            if(!(hr[i].high > hr[i-k].high) || !(hr[i].high >= hr[i+k].high)) isH = false;
            if(!(hr[i].low  < hr[i-k].low)  || !(hr[i].low  <= hr[i+k].low))  isL = false;
           }
         if(isH) { sh = i; shB = false; }
         if(isL) { sl = i; slB = false; }
        }
      if(sh >= 0 && !shB && hr[t].close > hr[sh].high) { shB = true; trend = 1; }
      if(sl >= 0 && !slB && hr[t].close < hr[sl].low)  { slB = true; trend = -1; }
      tr[t] = trend;
     }
   int hp = PeriodSeconds(InpHTF), lp = PeriodSeconds(InpTF), j = -1;
   for(int t = 0; t < n; t++)
     {
      datetime closeT = r[t].time + lp;
      while(j + 1 < hn && hr[j+1].time + hp <= closeT) j++;
      htf[t] = j >= 0 ? tr[j] : 0;
     }
  }

double NormPrice(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) return NormalizeDouble(p, _Digits);
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

// total lots for the risk budget (0 = skip)
double TotalLots(double stopDist)
  {
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickValue <= 0 || tickSize <= 0 || step <= 0 || stopDist <= 0) return 0;
   double lossPerLot = stopDist / tickSize * tickValue;
   double lots = MathFloor(bal * InpRiskPct / 100.0 / lossPerLot / step) * step;
   if(lots < minLot)
     {
      double pct = minLot * lossPerLot / bal * 100.0;
      if(pct <= InpMinLotMaxRisk)
        {
         PrintFormat("Using min lot %.2f (risks %.2f%% of balance)", minLot, pct);
         return minLot;
        }
      PrintFormat("Min lot %.2f would risk %.2f%% of balance - setup skipped", minLot, pct);
      return 0;
     }
   return MathMin(lots, maxLot);
  }

double TodayPnl()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   double pnl = 0;
   if(HistorySelect(StructToTime(dt), TimeCurrent() + 60))
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         ulong d = HistoryDealGetTicket(i);
         if(d == 0 || HistoryDealGetInteger(d, DEAL_MAGIC) != (long)InpMagic) continue;
         if(HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
         pnl += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
        }
   return pnl;
  }

int OurPositions()
  {
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol) c++;
     }
   return c;
  }

void DeletePending()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetInteger(ORDER_MAGIC) == (long)InpMagic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         trade.OrderDelete(tk);
     }
  }

// pending orders of this EA: returns count and the entry price of the first one
int OurPending(double &price)
  {
   int c = 0;
   price = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetInteger(ORDER_MAGIC) != (long)InpMagic || OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      c++;
      price = OrderGetDouble(ORDER_PRICE_OPEN);
     }
   return c;
  }

// Comment of each order: "OTE <tp1 price>" so breakeven can be managed after a restart
void ManageBreakeven()
  {
   if(!InpBreakeven) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      string cm = PositionGetString(POSITION_COMMENT);
      if(StringFind(cm, "OTE ") != 0) continue;
      double tp1 = StringToDouble(StringSubstr(cm, 4));
      if(tp1 <= 0) continue;
      double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL), tp = PositionGetDouble(POSITION_TP);
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      bool reached = buy ? bid >= tp1 : ask <= tp1;
      bool needs = buy ? sl < open : (sl == 0 || sl > open);
      if(reached && needs) trade.PositionModify(tk, NormPrice(open), tp);
     }
  }

//+------------------------------------------------------------------+
//| Orders for the pending setup                                      |
//+------------------------------------------------------------------+
void PlaceSetup(const OteSetup &s)
  {
   double entry = NormPrice(Lvl(s, InpOteEntry));
   double buf = InpSlBufferAtr * s.atr;
   double stop = NormPrice(s.dir == -1 ? s.origin + buf : s.origin - buf);
   double tps[4];
   tps[0] = NormPrice(Lvl(s, InpTp1)); tps[1] = NormPrice(Lvl(s, InpTp2));
   tps[2] = NormPrice(Lvl(s, InpTp3)); tps[3] = NormPrice(Lvl(s, InpTp4));

   // already placed at this price?
   double cur;
   if(OurPending(cur) > 0 && MathAbs(cur - entry) < _Point * 0.5) return;
   DeletePending();

   // filters checked on the final leg (same as the backtest)
   double zLo = MathMin(Lvl(s, InpOteLo), Lvl(s, InpOteHi)), zHi = MathMax(Lvl(s, InpOteLo), Lvl(s, InpOteHi));
   if(MathAbs(s.origin - s.extreme) > InpMaxLegAtr * s.atr) { g_status = "setup skipped: leg too big"; return; }
   if(InpObOverlap && !(s.obBot <= zHi && s.obTop >= zLo)) { g_status = "setup skipped: no order-block overlap"; return; }
   double q = InpPsyBase / 4.0;
   if(InpPsyFilter && MathFloor(zHi / q) * q < zLo) { g_status = "setup skipped: no PSY level in OTE zone"; return; }
   if(!InSessionBar(TimeCurrent())) { g_status = "outside trading hours"; return; }
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   if(TodayPnl() <= -bal * InpMaxDailyLoss / 100.0) { g_status = "daily loss limit reached"; return; }

   double stopDist = MathAbs(stop - entry);
   double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(stopDist <= 0 || spread > stopDist * InpMaxSpreadPct / 100.0) { g_status = "spread too big for this stop"; return; }

   // limit order must be on the right side of price
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(s.dir == -1 && entry <= bid) return;
   if(s.dir == 1 && entry >= ask) return;

   double total = TotalLots(stopDist);
   if(total <= 0) { g_status = "lot too big for the risk setting"; return; }
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP), minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   int parts = (int)MathMin(4, MathFloor(total / minLot + 1e-9));
   if(parts < 1) parts = 1;
   // which TPs to use when the account is too small for 4 orders
   int use[4];
   if(parts == 1)      { use[0] = 1; }
   else if(parts == 2) { use[0] = 0; use[1] = 2; }
   else if(parts == 3) { use[0] = 0; use[1] = 1; use[2] = 2; }
   else                { use[0] = 0; use[1] = 1; use[2] = 2; use[3] = 3; }
   int volDigits = (int)MathMax(0, MathCeil(-MathLog10(step)));
   double each = MathMax(minLot, MathFloor(total / parts / step) * step);
   string cm = "OTE " + DoubleToString(tps[0], _Digits);
   datetime exp = 0;
   for(int k = 0; k < parts; k++)
     {
      double lots = NormalizeDouble(k == parts - 1 ? MathMax(minLot, total - each * (parts - 1)) : each, volDigits);
      bool ok = s.dir == -1 ? trade.SellLimit(lots, entry, _Symbol, stop, tps[use[k]], ORDER_TIME_GTC, exp, cm)
                            : trade.BuyLimit(lots, entry, _Symbol, stop, tps[use[k]], ORDER_TIME_GTC, exp, cm);
      if(!ok) PrintFormat("Order failed: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
   g_status = StringFormat("%s LIMIT %s  SL %s  TP1 %s TP2 %s TP3 %s TP4 %s  (%d order%s)",
                           s.dir == -1 ? "SELL" : "BUY", DoubleToString(entry, _Digits), DoubleToString(stop, _Digits),
                           DoubleToString(tps[0], _Digits), DoubleToString(tps[1], _Digits), DoubleToString(tps[2], _Digits),
                           DoubleToString(tps[3], _Digits), parts, parts > 1 ? "s" : "");
  }

//+------------------------------------------------------------------+
//| Drawing                                                           |
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

void Seg(string name, datetime t1, double p, datetime t2, color c, ENUM_LINE_STYLE st, int w = 1)
  {
   ObjectCreate(0, name, OBJ_TREND, 0, t1, p, t2, p);
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

void Draw(const COte &ote, const MqlRates &r[], int n)
  {
   ObjectsDeleteAll(0, PREFIX);
   if(!InpDraw) return;
   int ps = PeriodSeconds(InpTF);
   datetime right = r[n-1].time + 15 * ps;

   // PSY levels
   double q = InpPsyBase / 4.0;
   long base = (long)MathRound(r[n-1].close / q);
   for(int k = -InpPsyCount; k <= InpPsyCount; k++)
     {
      long m = base + k;
      double p = m * q;
      long r4 = ((m % 4) + 4) % 4;
      string kind = (r4 == 0) ? "PSY " : ((r4 == 2) ? "PSY 1/2 " : "PSY 1/4 ");
      Seg(PREFIX + "psy" + IntegerToString(k), r[MathMax(0, n - 150)].time, p, right, InpPsyColor, r4 == 0 ? STYLE_SOLID : STYLE_DOT, r4 == 0 ? 2 : 1);
      Txt(PREFIX + "psyt" + IntegerToString(k), right, p, kind + DoubleToString(p, 1), InpPsyColor, ANCHOR_LEFT, 7);
     }

   if(!ote.last.active) return;
   OteSetup s = ote.last;
   if(n - 1 - s.created > 200) return;
   color col = s.dir == -1 ? InpSellColor : InpBuyColor;
   datetime t0 = r[s.created].time;
   double entry = Lvl(s, InpOteEntry);
   double buf = InpSlBufferAtr * s.atr;
   double stop = s.dir == -1 ? s.origin + buf : s.origin - buf;

   Txt(PREFIX + "sig", r[s.originIdx].time, s.origin, (s.choch ? "CHoCH OTE " : "BOS OTE ") + (s.dir == -1 ? "SELL" : "BUY"),
       col, s.dir == -1 ? ANCHOR_LOWER : ANCHOR_UPPER, 9);
   Rect(PREFIX + "zone", r[s.obIdx].time, s.obTop, right, s.obBot, C'200,235,240');
   Txt(PREFIX + "zonet", r[s.obIdx].time, (s.obTop + s.obBot) / 2, s.dir == -1 ? "sell zone" : "buy zone", col, ANCHOR_LEFT, 8);
   Rect(PREFIX + "ote", t0, Lvl(s, InpOteLo), right, Lvl(s, InpOteHi), C'215,225,255');
   Rect(PREFIX + "sl", t0, entry, right, stop, C'255,215,215');
   Txt(PREFIX + "slt", right, stop, "SL " + DoubleToString(stop, _Digits), InpSellColor, ANCHOR_LEFT, 9);
   Seg(PREFIX + "entry", t0, entry, right, InpEntryColor, STYLE_SOLID, 2);
   Txt(PREFIX + "entryt", right, entry, (s.dir == -1 ? "SELL " : "BUY ") + DoubleToString(entry, _Digits), InpEntryColor, ANCHOR_LEFT, 9);
   double lv[4];
   lv[0] = InpTp1; lv[1] = InpTp2; lv[2] = InpTp3; lv[3] = InpTp4;
   for(int k = 0; k < 4; k++)
     {
      double p = Lvl(s, lv[k]);
      Seg(PREFIX + "tp" + IntegerToString(k), t0, p, right, InpBuyColor, STYLE_DASH);
      Txt(PREFIX + "tpt" + IntegerToString(k), right, p, "TP" + IntegerToString(k + 1) + "  " + DoubleToString(p, _Digits), InpBuyColor, ANCHOR_LEFT, 9);
     }
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Events                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpSwingLen < 2 || InpHistoryBars < 200 || InpRiskPct <= 0 || InpOteLo >= InpOteHi)
     {
      Print("Invalid inputs");
      return(INIT_PARAMETERS_INCORRECT);
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);
   trade.SetTypeFillingBySymbol(_Symbol);
   EventSetTimer(5);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, PREFIX);
   Comment("");
  }

void OnTimer() { OnTick(); }

void OnTick()
  {
   ManageBreakeven();

   datetime bar = iTime(_Symbol, InpTF, 0);
   if(bar == 0 || bar == g_lastBar) return;

   MqlRates r[];
   int n = CopyRates(_Symbol, InpTF, 1, InpHistoryBars, r);   // closed bars only, oldest first
   if(n < InpSwingLen * 4 + 20) return;
   g_lastBar = bar;

   double atr[];
   int htf[];
   ComputeAtr(r, n, atr);
   ComputeHtf(r, n, htf);
   COte ote;
   ote.Run(r, n, atr, htf);
   Draw(ote, r, n);

   if(OurPositions() > 0)
     {
      DeletePending();            // one setup at a time, like the backtest
      g_status = "trade open";
     }
   else if(ote.setup.active)
      PlaceSetup(ote.setup);
   else
     {
      DeletePending();
      g_status = "waiting for a CHoCH";
     }

   Comment(StringFormat("Castimofx CHoCH OTE  %s %s\nStructure: %s   setups in history: %d\n%s\nToday P/L: %.2f",
                        _Symbol, EnumToString(InpTF), ote.trend == 1 ? "BULLISH" : ote.trend == -1 ? "BEARISH" : "-",
                        ote.nSetups, g_status, TodayPnl()));
  }
