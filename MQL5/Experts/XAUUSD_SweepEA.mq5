//+------------------------------------------------------------------+
//|                                              XAUUSD_SweepEA.mq5  |
//|  M1 gold "staircase -> sweep -> strong zone -> break of H" EA    |
//|  Built from "XAUUSD Sweep Setup Notes" (A..L points, rules 1-10) |
//+------------------------------------------------------------------+
#property copyright "Castimofx"
#property version   "1.00"
#property description "Buys/sells the A-B-C-D-E-F-G-H-I-L sweep structure on M1."
#property description "Instant order + grid of pending orders, all closing at first entry +/- $20."

#include <Trade\Trade.mqh>

//--- open questions from the notes are exposed as inputs
enum ENUM_ENTRY_MODE
  {
   ENTRY_TICK_BREAK   = 0, // Q1-A: the moment price goes beyond H
   ENTRY_CANDLE_CLOSE = 1  // Q1-B: after an M1 candle closes beyond H
  };
enum ENUM_AFTER_G_BREAK
  {
   AFTER_G_CLOSE_ALL = 0,  // Q3-A: close everything if price crosses G after entry
   AFTER_G_HOLD      = 1   // Q3-B: hold until target / opposite setup / loss limit
  };
enum ENUM_START_MODE
  {
   START_BUY  = 1,         // Buy mode
   START_SELL = -1         // Sell mode
  };

//==================================================================
input group "Structure (M1 swings)"
input int    SwingDepth         = 3;     // Candles on each side of a swing high/low
input int    LookbackBars       = 1500;  // M1 bars scanned for the structure
input int    RsiPeriod          = 14;    // RSI period
input double RsiHigh            = 70.0;  // A high must read RSI >= this
input double RsiLow             = 30.0;  // A low must read RSI <= this
input int    RsiWindow          = 1;     // RSI may hit the level within +/- N bars of the swing
input int    M5RsiWindow        = 1;     // G check on M5: +/- N M5 bars around G
input bool   RequireEAboveC     = true;  // Q4: E must be above C (buy) / below C (sell)
input bool   RequireGBelowC     = false; // Q5: G must also sweep C, not only E
input bool   RequireIRsi        = false; // Q4: pullback I must read RSI <= 30 (buy) / >= 70 (sell)
input bool   ReducedNeedsFBreak = true;  // Rule 9 setups (F-G-H-I-L): F must break the previous high
input bool   SwitchNeedsFull    = true;  // Mode switch needs the full A..E staircase the other way
input int    MaxSetupBars       = 600;   // Drop a setup if it is older than this many M1 bars

input group "Entry & mode"
input ENUM_ENTRY_MODE EntryMode = ENTRY_TICK_BREAK; // Q1: entry at L
input double MaxChaseUSD        = 1.0;   // Skip if price is already this far past H
input ENUM_START_MODE StartMode = START_BUY; // Mode at start (notes: buy)
input bool   ResetStateOnStart  = false; // Ignore saved mode/basket state at start

input group "Grid & target (rule 10)"
input double TargetUSD          = 20.0;  // Target: price move from first entry (J)
input int    PendingOrders      = 19;    // Pending orders after the instant one
input double GridStepUSD        = 2.0;   // Distance between pending orders
input double BaseLot            = 0.01;  // Lot per order
input bool   ScaleLotWithEquity = true;  // +BaseLot for every EquityPerLotStep of equity
input double EquityPerLotStep   = 4000.0;// 0.02 lot at $4,000, 0.03 at $8,000 ...

input group "Safety"
input ENUM_AFTER_G_BREAK AfterGBreak = AFTER_G_CLOSE_ALL; // Q3: price crosses G after entry
input double MaxLossPct         = 15.0;  // Close all if floating loss reaches % of balance (0 = off)
input double MaxMarginUsePct    = 50.0;  // Grid may use at most this % of free margin
input double MaxSpreadUSD       = 0.60;  // Max spread at entry in $ (0 = off)
input bool   UseSessionFilter   = false; // Trade only between the hours below (server time)
input int    SessionStartHour   = 7;
input int    SessionEndHour     = 20;

input group "Misc"
input long   MagicNumber        = 26110701;
input bool   DrawSetups         = true;  // Draw A..H on the chart
input bool   WriteCsvLog        = true;  // Log every setup/trade to Files\Common\SweepEA_<symbol>.csv

//==================================================================
struct Swing
  {
   int      type;   // +1 high, -1 low
   double   price;
   datetime time;
  };

// pt[0..7] = A B C D E F G H
#define P_A 0
#define P_B 1
#define P_C 2
#define P_D 3
#define P_E 4
#define P_F 5
#define P_G 6
#define P_H 7

struct Setup
  {
   bool     armed;
   int      dir;     // +1 buy setup, -1 sell setup
   bool     full;    // full A..H or reduced (rule 9)
   int      first;   // first meaningful point index
   Swing    pt[8];
  };

CTrade   trade;
int      hRsiM1 = INVALID_HANDLE;
int      hRsiM5 = INVALID_HANDLE;

int      g_mode       = 1;      // +1 buy mode, -1 sell mode
bool     g_needFull   = true;   // next same-direction setup needs A..E
datetime g_lastBar    = 0;
Setup    g_setup[2];            // [0] buy setup, [1] sell setup
datetime g_lastUsedG[2];        // G already traded / voided per direction

bool     g_basketActive = false;
int      g_basketDir    = 0;
double   g_basketTarget = 0;
double   g_basketG      = 0;
double   g_basketBal    = 0;

const string LETTERS = "ABCDEFGH";

//+------------------------------------------------------------------+
int Idx(int d) { return d > 0 ? 0 : 1; }
string DirName(int d) { return d > 0 ? "BUY" : "SELL"; }

//+------------------------------------------------------------------+
//| Logging                                                          |
//+------------------------------------------------------------------+
void Log(string ev, string details)
  {
   Print("[SweepEA] ", ev, " | ", details);
   if(!WriteCsvLog)
      return;
   int f = FileOpen("SweepEA_" + _Symbol + ".csv",
                    FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(f == INVALID_HANDLE)
      return;
   FileSeek(f, 0, SEEK_END);
   FileWrite(f, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), ev, details,
             DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
             DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2));
   FileClose(f);
  }

string SetupText(const Setup &st)
  {
   string s = DirName(st.dir) + (st.full ? " full" : " reduced");
   for(int k = st.first; k < 8; k++)
      s += " " + StringSubstr(LETTERS, k, 1) + "=" + DoubleToString(st.pt[k].price, _Digits) +
           "@" + TimeToString(st.pt[k].time, TIME_MINUTES);
   return s;
  }

//+------------------------------------------------------------------+
//| State persistence (survives terminal restarts)                   |
//+------------------------------------------------------------------+
string GV(string k) { return "SWP_" + IntegerToString(MagicNumber) + "_" + _Symbol + "_" + k; }

void SaveState()
  {
   if(MQLInfoInteger(MQL_TESTER))
      return;
   GlobalVariableSet(GV("mode"), g_mode);
   GlobalVariableSet(GV("needFull"), g_needFull ? 1 : 0);
   GlobalVariableSet(GV("bActive"), g_basketActive ? 1 : 0);
   GlobalVariableSet(GV("bDir"), g_basketDir);
   GlobalVariableSet(GV("bTarget"), g_basketTarget);
   GlobalVariableSet(GV("bG"), g_basketG);
   GlobalVariableSet(GV("bBal"), g_basketBal);
   GlobalVariableSet(GV("usedG0"), (double)g_lastUsedG[0]);
   GlobalVariableSet(GV("usedG1"), (double)g_lastUsedG[1]);
  }

void LoadState()
  {
   if(MQLInfoInteger(MQL_TESTER) || ResetStateOnStart || !GlobalVariableCheck(GV("mode")))
      return;
   g_mode         = (int)GlobalVariableGet(GV("mode"));
   g_needFull     = GlobalVariableGet(GV("needFull")) > 0.5;
   g_basketActive = GlobalVariableGet(GV("bActive")) > 0.5;
   g_basketDir    = (int)GlobalVariableGet(GV("bDir"));
   g_basketTarget = GlobalVariableGet(GV("bTarget"));
   g_basketG      = GlobalVariableGet(GV("bG"));
   g_basketBal    = GlobalVariableGet(GV("bBal"));
   g_lastUsedG[0] = (datetime)GlobalVariableGet(GV("usedG0"));
   g_lastUsedG[1] = (datetime)GlobalVariableGet(GV("usedG1"));
  }

//+------------------------------------------------------------------+
//| Position / order helpers                                         |
//+------------------------------------------------------------------+
void CountBasket(int &pos, int &ord, double &pl, int &posDir, double &posTp)
  {
   pos = 0; ord = 0; pl = 0; posDir = 0; posTp = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol ||
         PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      pos++;
      pl += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      posDir = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      posTp  = PositionGetDouble(POSITION_TP);
     }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol ||
         OrderGetInteger(ORDER_MAGIC) != MagicNumber)
         continue;
      ord++;
     }
  }

void DeletePendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol ||
         OrderGetInteger(ORDER_MAGIC) != MagicNumber)
         continue;
      trade.OrderDelete(t);
     }
  }

void CloseAll()
  {
   DeletePendings();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol ||
         PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      trade.PositionClose(t);
     }
   DeletePendings(); // in case one filled while closing
  }

double CalcLot()
  {
   double lot = BaseLot;
   if(ScaleLotWithEquity && EquityPerLotStep > 0)
      lot = BaseLot * (1.0 + MathFloor(AccountInfoDouble(ACCOUNT_EQUITY) / EquityPerLotStep));
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step > 0)
      lot = MathFloor(lot / step + 1e-9) * step;
   lot = MathMax(vmin, MathMin(vmax, lot));
   return NormalizeDouble(lot, 2);
  }

bool FiltersOk(string &why)
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(MaxSpreadUSD > 0 && ask - bid > MaxSpreadUSD)
     {
      why = "spread " + DoubleToString(ask - bid, _Digits);
      return false;
     }
   if(UseSessionFilter)
     {
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      bool in = SessionStartHour <= SessionEndHour
                ? (dt.hour >= SessionStartHour && dt.hour < SessionEndHour)
                : (dt.hour >= SessionStartHour || dt.hour < SessionEndHour);
      if(!in)
        {
         why = "outside session";
         return false;
        }
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Swing detection: fractal swings that also hit the RSI level,     |
//| merged into an alternating high/low list (oldest first).         |
//+------------------------------------------------------------------+
bool RsiHits(const double &rsi[], int i, int lastClosed, int type)
  {
   for(int k = MathMax(0, i - RsiWindow); k <= MathMin(lastClosed, i + RsiWindow); k++)
     {
      double v = rsi[k];
      if(v < 0 || v > 100)
         continue; // not calculated yet
      if(type > 0 && v >= RsiHigh)
         return true;
      if(type < 0 && v <= RsiLow)
         return true;
     }
   return false;
  }

void AddSwing(Swing &out[], int &n, int type, double price, datetime t)
  {
   if(n > 0 && out[n - 1].type == type)
     {
      // two highs (or lows) in a row: keep the more extreme one
      if((type > 0 && price > out[n - 1].price) || (type < 0 && price < out[n - 1].price))
        {
         out[n - 1].price = price;
         out[n - 1].time  = t;
        }
      return;
     }
   ArrayResize(out, n + 1, 256);
   out[n].type  = type;
   out[n].price = price;
   out[n].time  = t;
   n++;
  }

int BuildSwings(Swing &out[])
  {
   MqlRates r[];
   double   rsi[];
   ArraySetAsSeries(r, false);
   ArraySetAsSeries(rsi, false);
   int total = CopyRates(_Symbol, PERIOD_M1, 0, LookbackBars, r);
   if(total < SwingDepth * 2 + 20)
      return 0;
   if(CopyBuffer(hRsiM1, 0, 0, total, rsi) != total)
      return 0;

   ArrayResize(out, 0);
   int n = 0;
   int lastClosed = total - 2;   // total-1 is the forming bar
   for(int i = SwingDepth; i <= lastClosed - SwingDepth; i++)
     {
      bool isH = true, isL = true;
      for(int j = 1; j <= SwingDepth; j++)
        {
         if(!(r[i].high > r[i - j].high && r[i].high >= r[i + j].high))
            isH = false;
         if(!(r[i].low < r[i - j].low && r[i].low <= r[i + j].low))
            isL = false;
        }
      if(isH)
         isH = RsiHits(rsi, i, lastClosed, +1);
      if(isL)
         isL = RsiHits(rsi, i, lastClosed, -1);

      if(isH && isL)
        {
         if(r[i].close >= r[i].open)
           { AddSwing(out, n, -1, r[i].low, r[i].time); AddSwing(out, n, +1, r[i].high, r[i].time); }
         else
           { AddSwing(out, n, +1, r[i].high, r[i].time); AddSwing(out, n, -1, r[i].low, r[i].time); }
        }
      else if(isH)
         AddSwing(out, n, +1, r[i].high, r[i].time);
      else if(isL)
         AddSwing(out, n, -1, r[i].low, r[i].time);
     }
   return n;
  }

//+------------------------------------------------------------------+
//| G must also be extreme on M5 RSI (strong zone)                   |
//+------------------------------------------------------------------+
bool M5RsiOk(datetime t, int d)
  {
   int sh = iBarShift(_Symbol, PERIOD_M5, t, false);
   if(sh < 0)
      return false;
   int from = MathMax(0, sh - M5RsiWindow);
   int cnt  = sh + M5RsiWindow - from + 1;
   double buf[];
   if(CopyBuffer(hRsiM5, 0, from, cnt, buf) != cnt)
      return false;
   for(int i = 0; i < cnt; i++)
     {
      if(buf[i] < 0 || buf[i] > 100)
         continue;
      if(d > 0 && buf[i] <= RsiLow)
         return true;
      if(d < 0 && buf[i] >= RsiHigh)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Pattern match. Works for both directions: every price is         |
//| multiplied by d, so the sell is the buy upside down.             |
//+------------------------------------------------------------------+
bool MatchPattern(const Swing &s[], int n, int d, bool full, Setup &st)
  {
   if(n < 4)
      return false;
   // H is the latest "up point" (a high for buys, a low for sells).
   // The very last swing may be the pullback I.
   int h = n - 1;
   if(s[h].type != d)
      h--;
   if(h < 0 || s[h].type != d)
      return false;

   int need = full ? 7 : (ReducedNeedsFBreak ? 4 : 3);
   if(h < need)
      return false;

   for(int k = 0; k < 8; k++)
     {
      int idx = h - 7 + k;
      if(idx >= 0)
         st.pt[k] = s[idx];
      else
        { st.pt[k].type = 0; st.pt[k].price = 0; st.pt[k].time = 0; }
     }
   st.dir   = d;
   st.full  = full;
   st.first = full ? P_A : (ReducedNeedsFBreak ? P_D : P_E);
   st.armed = false;

   double vA = st.pt[P_A].price * d, vB = st.pt[P_B].price * d, vC = st.pt[P_C].price * d;
   double vD = st.pt[P_D].price * d, vE = st.pt[P_E].price * d, vF = st.pt[P_F].price * d;
   double vG = st.pt[P_G].price * d, vH = st.pt[P_H].price * d;

   if(full)
     {
      if(!(vC > vA))
         return false;                       // C above A
      if(!(vD > vB))
         return false;                       // D above B
      if(RequireEAboveC && !(vE > vC))
         return false;                       // E above C (Q4)
      if(!(vF > vD && vF > vB))
         return false;                       // F breaks B and D
      if(RequireGBelowC && !(vG < vC))
         return false;                       // G below C too (Q5)
     }
   else if(ReducedNeedsFBreak && !(vF > vD))
      return false;                          // F breaks previous high

   if(!(vG < vE))
      return false;                          // G sweeps E
   if(!(vH < vF))
      return false;                          // H lower than F
   if(st.pt[P_G].time <= g_lastUsedG[Idx(d)])
      return false;                          // this G was already used

   // setup age
   int ageBars = iBarShift(_Symbol, PERIOD_M1, st.pt[st.first].time, false);
   if(ageBars < 0 || ageBars > MaxSetupBars)
      return false;

   // after H (closed bars), price must not have already broken H or G
   int sh = iBarShift(_Symbol, PERIOD_M1, st.pt[P_H].time, false);
   if(sh > 1)
     {
      double hi = iHigh(_Symbol, PERIOD_M1, iHighest(_Symbol, PERIOD_M1, MODE_HIGH, sh - 1, 1));
      double lo = iLow(_Symbol, PERIOD_M1, iLowest(_Symbol, PERIOD_M1, MODE_LOW, sh - 1, 1));
      double up = d > 0 ? hi : lo;   // furthest move in trade direction
      double dn = d > 0 ? lo : hi;   // furthest move against
      if(up * d > vH)
         return false;   // already broke H
      if(dn * d < vG)
         return false;   // already voided (K)
     }

   // strong zone: G extreme on M5 RSI as well
   if(!M5RsiOk(st.pt[P_G].time, d))
      return false;

   st.armed = true;
   return true;
  }

//+------------------------------------------------------------------+
//| Chart drawing                                                    |
//+------------------------------------------------------------------+
void DrawSetup(const Setup &st)
  {
   if(!DrawSetups || MQLInfoInteger(MQL_OPTIMIZATION))
      return;
   string pre = st.dir > 0 ? "SWP_B_" : "SWP_S_";
   ObjectsDeleteAll(0, pre);
   color c = st.dir > 0 ? clrDodgerBlue : clrOrangeRed;
   for(int k = st.first; k < 8; k++)
     {
      string nm = pre + StringSubstr(LETTERS, k, 1);
      ObjectCreate(0, nm, OBJ_TEXT, 0, st.pt[k].time, st.pt[k].price);
      ObjectSetString(0, nm, OBJPROP_TEXT, StringSubstr(LETTERS, k, 1));
      ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
      ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, 10);
      ObjectSetInteger(0, nm, OBJPROP_ANCHOR, st.pt[k].type > 0 ? ANCHOR_LOWER : ANCHOR_UPPER);
      if(k > st.first)
        {
         string ln = pre + "L" + IntegerToString(k);
         ObjectCreate(0, ln, OBJ_TREND, 0, st.pt[k - 1].time, st.pt[k - 1].price,
                      st.pt[k].time, st.pt[k].price);
         ObjectSetInteger(0, ln, OBJPROP_COLOR, c);
         ObjectSetInteger(0, ln, OBJPROP_RAY_RIGHT, false);
        }
     }
   datetime tEnd = st.pt[P_H].time + 60 * 60;
   string hn = pre + "Hbreak";
   ObjectCreate(0, hn, OBJ_TREND, 0, st.pt[P_H].time, st.pt[P_H].price, tEnd, st.pt[P_H].price);
   ObjectSetInteger(0, hn, OBJPROP_COLOR, clrLime);
   ObjectSetInteger(0, hn, OBJPROP_STYLE, STYLE_DASH);
   string gn = pre + "Gvoid";
   ObjectCreate(0, gn, OBJ_TREND, 0, st.pt[P_G].time, st.pt[P_G].price, tEnd, st.pt[P_G].price);
   ObjectSetInteger(0, gn, OBJPROP_COLOR, clrMagenta);
   ObjectSetInteger(0, gn, OBJPROP_STYLE, STYLE_DOT);
  }

//+------------------------------------------------------------------+
//| Basket (instant order + pending grid)                            |
//+------------------------------------------------------------------+
bool OpenBasket(int d, double gPrice)
  {
   double lot = CalcLot();
   double P   = d > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double tp  = NormalizeDouble(P + d * TargetUSD, _Digits);

   bool ok = d > 0 ? trade.Buy(lot, _Symbol, 0, 0, tp, "SWP L")
                   : trade.Sell(lot, _Symbol, 0, 0, tp, "SWP L");
   if(!ok || (trade.ResultRetcode() != TRADE_RETCODE_DONE && trade.ResultRetcode() != TRADE_RETCODE_PLACED))
     {
      Log("ORDER_FAIL", DirName(d) + " instant order failed: " + IntegerToString(trade.ResultRetcode()) +
          " " + trade.ResultRetcodeDescription());
      return false;
     }
   double fill = trade.ResultPrice() > 0 ? trade.ResultPrice() : P;

   g_basketActive = true;
   g_basketDir    = d;
   g_basketTarget = tp;
   g_basketG      = gPrice;
   g_basketBal    = AccountInfoDouble(ACCOUNT_BALANCE);

   // pending grid against the trade, all with the same target
   double budget = AccountInfoDouble(ACCOUNT_MARGIN_FREE) * MaxMarginUsePct / 100.0;
   double used   = 0;
   int    placed = 0;
   ENUM_ORDER_TYPE mt = d > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   for(int k = 1; k <= PendingOrders; k++)
     {
      double price = NormalizeDouble(fill - d * k * GridStepUSD, _Digits);
      double m = 0;
      if(!OrderCalcMargin(mt, _Symbol, lot, price, m))
         break;
      if(used + m > budget)
        {
         Log("MARGIN_CAP", "stopped grid at " + IntegerToString(placed) + " pending orders");
         break;
        }
      string cm = "SWP grid " + IntegerToString(k);
      bool pk = d > 0 ? trade.BuyLimit(lot, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, cm)
                      : trade.SellLimit(lot, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, cm);
      if(pk)
        {
         used += m;
         placed++;
        }
      else
         Log("ORDER_FAIL", cm + ": " + trade.ResultRetcodeDescription());
     }
   Log("ENTRY", DirName(d) + " L=" + DoubleToString(fill, _Digits) + " lot=" + DoubleToString(lot, 2) +
       " target=" + DoubleToString(tp, _Digits) + " G=" + DoubleToString(gPrice, _Digits) +
       " pendings=" + IntegerToString(placed));
   SaveState();
   return true;
  }

void EndBasket(string reason)
  {
   if(!g_basketActive)
      return;
   double res = AccountInfoDouble(ACCOUNT_BALANCE) - g_basketBal;
   Log("BASKET_END", DirName(g_basketDir) + " " + reason + " result=" + DoubleToString(res, 2));
   g_basketActive = false;
   g_basketDir    = 0;
   SaveState();
  }

void ManageBasket()
  {
   if(!g_basketActive)
      return;
   int pos, ord, pdir;
   double pl, ptp;
   CountBasket(pos, ord, pl, pdir, ptp);

   if(pos == 0)
     {
      // target hit by broker TP (or closed by hand): remove leftover pendings
      DeletePendings();
      EndBasket(ord > 0 ? "target hit" : "closed");
      return;
     }

   int d = g_basketDir;
   double px = d > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   if(g_basketTarget > 0 && (px - g_basketTarget) * d >= 0)
     {
      CloseAll();
      EndBasket("target hit");
      return;
     }
   if(AfterGBreak == AFTER_G_CLOSE_ALL && g_basketG > 0 && (px - g_basketG) * d < 0)
     {
      CloseAll();
      EndBasket("price crossed G");
      return;
     }
   if(MaxLossPct > 0 && pl <= -AccountInfoDouble(ACCOUNT_BALANCE) * MaxLossPct / 100.0)
     {
      CloseAll();
      EndBasket("max loss " + DoubleToString(pl, 2));
      return;
     }
  }

//+------------------------------------------------------------------+
//| Setup life cycle                                                 |
//+------------------------------------------------------------------+
void OnNewBar()
  {
   // timeouts
   for(int i = 0; i < 2; i++)
     {
      if(!g_setup[i].armed)
         continue;
      int age = iBarShift(_Symbol, PERIOD_M1, g_setup[i].pt[g_setup[i].first].time, false);
      if(age > MaxSetupBars)
        {
         g_setup[i].armed = false;
         g_lastUsedG[i]   = g_setup[i].pt[P_G].time;
         Log("TIMEOUT", SetupText(g_setup[i]));
        }
     }

   Swing s[];
   int n = BuildSwings(s);
   if(n == 0)
      return;

   // same direction as the current mode
   int d = g_mode;
   if(!g_basketActive && !g_setup[Idx(d)].armed)
     {
      Setup st;
      if(MatchPattern(s, n, d, g_needFull, st))
        {
         g_setup[Idx(d)] = st;
         Log("ARMED", SetupText(st));
         DrawSetup(st);
        }
     }
   // opposite direction: a full setup switches the mode
   int od = -g_mode;
   if(!g_setup[Idx(od)].armed)
     {
      Setup st;
      if(MatchPattern(s, n, od, SwitchNeedsFull, st))
        {
         g_setup[Idx(od)] = st;
         Log("ARMED_SWITCH", SetupText(st));
         DrawSetup(st);
        }
     }
  }

void CheckTriggers()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   for(int i = 0; i < 2; i++)
     {
      if(!g_setup[i].armed)
         continue;
      int    d = g_setup[i].dir;
      double H = g_setup[i].pt[P_H].price;
      double G = g_setup[i].pt[P_G].price;

      // K: price goes back through G before the break -> void
      if((bid - G) * d < 0)
        {
         g_setup[i].armed = false;
         g_lastUsedG[i]   = g_setup[i].pt[P_G].time;
         if(d == g_mode)
            g_needFull = false; // rule: wait for a new F, G, H, I, L only
         Log("VOID_K", SetupText(g_setup[i]));
         SaveState();
         continue;
        }

      // L: break of H
      bool brk;
      if(EntryMode == ENTRY_TICK_BREAK)
         brk = (bid - H) * d > 0;
      else
         brk = iTime(_Symbol, PERIOD_M1, 1) > g_setup[i].pt[P_H].time &&
               (iClose(_Symbol, PERIOD_M1, 1) - H) * d > 0;
      if(!brk)
         continue;

      // I: pullback after H must hold beyond G (and optionally hit RSI)
      int sh    = iBarShift(_Symbol, PERIOD_M1, g_setup[i].pt[P_H].time, false);
      int start = EntryMode == ENTRY_TICK_BREAK ? 0 : 1;
      int cnt   = sh - start;
      if(cnt < 1)
         continue;
      double iPx = d > 0 ? iLow(_Symbol, PERIOD_M1, iLowest(_Symbol, PERIOD_M1, MODE_LOW, cnt, start))
                         : iHigh(_Symbol, PERIOD_M1, iHighest(_Symbol, PERIOD_M1, MODE_HIGH, cnt, start));
      bool iOk = (iPx - G) * d > 0;
      if(iOk && RequireIRsi)
        {
         double buf[];
         iOk = false;
         if(CopyBuffer(hRsiM1, 0, start, cnt, buf) == cnt)
            for(int k = 0; k < cnt; k++)
               if((d > 0 && buf[k] <= RsiLow) || (d < 0 && buf[k] >= RsiHigh))
                 { iOk = true; break; }
        }
      if(!iOk)
        {
         g_setup[i].armed = false;
         g_lastUsedG[i]   = g_setup[i].pt[P_G].time;
         Log("NO_I", "H broken without a valid pullback I. " + SetupText(g_setup[i]));
         SaveState();
         continue;
        }

      if((bid - H) * d > MaxChaseUSD)
        {
         g_setup[i].armed = false;
         g_lastUsedG[i]   = g_setup[i].pt[P_G].time;
         Log("MISSED", "price already " + DoubleToString((bid - H) * d, 2) + " past H. " + SetupText(g_setup[i]));
         SaveState();
         continue;
        }

      string why = "";
      bool filtersOk = FiltersOk(why);

      if(d == g_mode)
        {
         if(g_basketActive)
           {
            g_setup[i].armed = false;
            continue;
           }
         if(!filtersOk)
            continue; // stay armed, retry next tick (MaxChaseUSD limits how late)
         g_setup[i].armed = false;
         g_lastUsedG[i]   = g_setup[i].pt[P_G].time;
         Log("TRIGGER", "L " + SetupText(g_setup[i]));
         if(OpenBasket(d, G))
            g_needFull = false;
         SaveState();
        }
      else
        {
         // full opposite setup confirmed: close everything and switch mode
         Setup st = g_setup[i];
         g_lastUsedG[i] = st.pt[P_G].time;
         Log("SWITCH", DirName(g_mode) + " -> " + DirName(d) + " " + SetupText(st));
         CloseAll();
         EndBasket("mode switch");
         g_mode     = d;
         g_needFull = false;
         g_setup[0].armed = false;
         g_setup[1].armed = false;
         if(filtersOk)
            OpenBasket(d, G);
         else
            Log("SKIP", "switch entry blocked: " + why);
         SaveState();
         return;
        }
     }
  }

//+------------------------------------------------------------------+
//| Expert events                                                    |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("[SweepEA] Warning: built for XAUUSD, running on ", _Symbol);

   hRsiM1 = iRSI(_Symbol, PERIOD_M1, RsiPeriod, PRICE_CLOSE);
   hRsiM5 = iRSI(_Symbol, PERIOD_M5, RsiPeriod, PRICE_CLOSE);
   if(hRsiM1 == INVALID_HANDLE || hRsiM5 == INVALID_HANDLE)
     {
      Print("[SweepEA] Could not create RSI handles");
      return INIT_FAILED;
     }

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(50);

   g_mode     = (int)StartMode;
   g_needFull = true;
   g_lastUsedG[0] = 0;
   g_lastUsedG[1] = 0;
   g_setup[0].armed = false;
   g_setup[1].armed = false;
   LoadState();

   // reconcile with what is really open
   int pos, ord, pdir;
   double pl, ptp;
   CountBasket(pos, ord, pl, pdir, ptp);
   if(pos == 0 && ord == 0)
      g_basketActive = false;
   else if(!g_basketActive && pos > 0)
     {
      g_basketActive = true;
      g_basketDir    = pdir;
      g_basketTarget = ptp;
      g_basketG      = 0; // unknown after a restart without saved state
      g_basketBal    = AccountInfoDouble(ACCOUNT_BALANCE);
      g_mode         = pdir;
     }
   Log("INIT", "mode=" + DirName(g_mode) + " needFull=" + (g_needFull ? "yes" : "no") +
       " basket=" + (g_basketActive ? "open" : "none"));
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(hRsiM1 != INVALID_HANDLE)
      IndicatorRelease(hRsiM1);
   if(hRsiM5 != INVALID_HANDLE)
      IndicatorRelease(hRsiM5);
   if(reason == REASON_REMOVE)
      ObjectsDeleteAll(0, "SWP_");
   SaveState();
  }

void OnTick()
  {
   ManageBasket();

   datetime bt = iTime(_Symbol, PERIOD_M1, 0);
   if(bt != g_lastBar)
     {
      g_lastBar = bt;
      OnNewBar();
     }

   CheckTriggers();
  }
//+------------------------------------------------------------------+
