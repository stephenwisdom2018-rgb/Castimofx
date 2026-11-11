//+------------------------------------------------------------------+
//| CASTIMOFX MA+RSI WONDER EA V5.18                                 |
//| GOLD ONLY - ALL BROKERS / ALL GOLD SYMBOL NAMES                  |
//| FIXED LOT 0.02                                                   |
//| EQUITY-BASED EXPOSURE - MAX 10 OPEN + PENDING                    |
//| DYNAMIC GRID SPACING BASED ON MAX TRADES                         |
//| INDIVIDUAL TP = $20 PRICE MOVEMENT                               |
//| TP RE-ENTRY = ORIGINAL ENTRY PRICE LIMIT ORDER                   |
//| ACCOUNT STOP OUT = TIERED 50% -> 10% OF ACCOUNT BALANCE          |
//+------------------------------------------------------------------+
#property strict
#property version "5.18"

#include <Trade/Trade.mqh>
CTrade trade;

//==================================================================
// INPUTS
//==================================================================
input string InpSymbol              = "XAUUSD";
input int    InpRSIPeriod            = 14;
input double InpRSIHigh              = 70.0;
input double InpRSILow               = 30.0;
input int    InpMAPeriod             = 10;

input int    InpHistoryDays          = 30;
input int    InpMinHistoryDays       = 14;

input int    InpMaxPositions         = 10;
input double InpIndividualTPUSD      = 20.0;

input int    InpSwingLookback        = 2;
input int    InpSwingMaxBars         = 300;
input double InpSwingGapUSD          = 1.0;

input int    InpSoldierMaxBars       = 60;

input bool   InpNewsFilter           = true;
input int    InpNewsBeforeMin        = 15;
input int    InpNewsAfterMin         = 15;

input int    InpDeviationPoints      = 100;
input bool   InpVerbose              = true;

input ulong  InpMagic                = 20251015;

//==================================================================
// FIXED SETTINGS
//==================================================================
#define FIXED_LOT 0.02
#define MAX_TOTAL_TRADES 10

// Dynamic grid spacing:
//   1 trade   -> no grid
//   2 trades  -> $10.00
//   3+ trades -> $20.00 / (max trades - 1)
#define GRID_RANGE_USD     20.0
#define GRID_TWO_TRADE_USD 10.0

//==================================================================
// INDICATOR HANDLES
//==================================================================
int g_rsiM1 = INVALID_HANDLE;
int g_rsiM5 = INVALID_HANDLE;
int g_maM5  = INVALID_HANDLE;

datetime g_lastM1Bar = 0;
datetime g_lastM5Bar = 0;

//==================================================================
// DIRECTION
//==================================================================
enum DIRECTION_STATE
{
   DIRECTION_NONE  = 0,
   DIRECTION_BUY   = 1,
   DIRECTION_SELL  = -1
};

DIRECTION_STATE g_direction = DIRECTION_NONE;

//==================================================================
// M1 STRUCTURE
//==================================================================
enum M1_STATE
{
   M1_NONE = 0,
   M1_TWO_SWINGS_READY,
   M1_THIRD_SWING_LOCKED,
   M1_READY
};

M1_STATE g_m1BuyState  = M1_NONE;
M1_STATE g_m1SellState = M1_NONE;

double g_buySwing1 = 0.0;
double g_buySwing2 = 0.0;
double g_buySwing3 = 0.0;

double g_sellSwing1 = 0.0;
double g_sellSwing2 = 0.0;
double g_sellSwing3 = 0.0;

datetime g_buySwingTime1  = 0;
datetime g_buySwingTime2  = 0;
datetime g_buySwingTime3  = 0;

datetime g_sellSwingTime1 = 0;
datetime g_sellSwingTime2 = 0;
datetime g_sellSwingTime3 = 0;

//==================================================================
// M5 SETUP
//==================================================================
enum M5_STATE
{
   M5_WAIT_SOLDIERS = 0,
   M5_WAIT_SWEEP,
   M5_WAIT_CUT,
   M5_WAIT_CONFIRM
};

M5_STATE g_buyM5State  = M5_WAIT_SOLDIERS;
M5_STATE g_sellM5State = M5_WAIT_SOLDIERS;

double g_buySoldierLow   = 0.0;
double g_sellSoldierHigh = 0.0;

double g_buySweepLow     = 0.0;
double g_sellSweepHigh   = 0.0;

int g_buyM5Age  = 0;
int g_sellM5Age = 0;

//==================================================================
// RSI DIRECTION MEMORY
//==================================================================
bool g_buyRSIActive  = false;
bool g_sellRSIActive = false;

bool g_buyExtremeArmed  = false;
bool g_sellExtremeArmed = false;

//==================================================================
// ZONE MEMORY
//==================================================================
double g_buyZonePrice   = 0.0;
double g_sellZonePrice  = 0.0;

bool g_buyZoneValid  = false;
bool g_sellZoneValid = false;

//==================================================================
// POST STOP-OUT STATE
// After a stop out the EA must get a NEW full confirmation
// (M1 structure + M5 setup) before trading again.
//==================================================================
bool g_waitConfirmAfterStopout = false;

//==================================================================
// GOLD CHECK - BROKER SUFFIX/PREFIX SUPPORT
//==================================================================
bool IsGold()
{
   // Symbol name: XAUUSD, XAUUSDm, XAUUSD.r, XAU/USD, #XAUUSD,
   // GOLD, GOLD#, GOLDmicro, etc.
   string s = _Symbol;
   StringToUpper(s);

   if(StringFind(s,"XAU") >= 0)
      return true;

   if(StringFind(s,"GOLD") >= 0)
      return true;

   // Broker base currency = XAU (renamed gold symbols).
   string base = SymbolInfoString(_Symbol,SYMBOL_CURRENCY_BASE);
   StringToUpper(base);

   if(base == "XAU")
      return true;

   return false;
}

//==================================================================
// PRICE
//==================================================================
int PriceDigits()
{
   return (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
}

double NormalizePrice(double price)
{
   return NormalizeDouble(price,PriceDigits());
}

double PointValue()
{
   return SymbolInfoDouble(_Symbol,SYMBOL_POINT);
}

//==================================================================
// RATES
//==================================================================
bool GetRates(ENUM_TIMEFRAMES tf,int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates,true);

   int copied = CopyRates(_Symbol,tf,0,count,rates);

   return (copied >= count);
}

//==================================================================
// RSI
//==================================================================
bool GetRSI(int handle,int shift,double &value)
{
   double buffer[];
   ArraySetAsSeries(buffer,true);

   if(CopyBuffer(handle,0,shift,1,buffer) != 1)
      return false;

   value = buffer[0];
   return true;
}

//==================================================================
// MA
//==================================================================
bool GetMA(int shift,double &value)
{
   double buffer[];
   ArraySetAsSeries(buffer,true);

   if(CopyBuffer(g_maM5,0,shift,1,buffer) != 1)
      return false;

   value = buffer[0];
   return true;
}

//==================================================================
// CANDLE FUNCTIONS
//==================================================================
bool IsBull(const MqlRates &c)
{
   return (c.close > c.open);
}

bool IsBear(const MqlRates &c)
{
   return (c.close < c.open);
}

bool IsDoji(const MqlRates &c)
{
   double range = c.high-c.low;

   if(range <= 0.0)
      return true;

   double body = MathAbs(c.close-c.open);

   return (body < range*0.15);
}

bool CandleTouchesMA(
   const MqlRates &c,
   double ma,
   bool bullish)
{
   bool touch = (c.low <= ma && c.high >= ma);

   if(!touch)
      return false;

   if(bullish)
      return (c.close >= ma);

   return (c.close <= ma);
}

//==================================================================
// FIXED LOT - ALWAYS 0.02
//==================================================================
double GetDynamicLot()
{
   return FIXED_LOT;
}

//==================================================================
// EQUITY-BASED MAXIMUM EXPOSURE
//==================================================================
int GetMaxPositions()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   if(equity < 100.0)
      return 0;

   if(equity < 200.0)
      return 1;

   if(equity < 600.0)
      return 2;

   if(equity < 800.0)
      return 3;

   if(equity < 1000.0)
      return 4;

   if(equity < 2400.0)
      return 5;

   if(equity < 2800.0)
      return 6;

   if(equity < 3200.0)
      return 7;

   if(equity < 3600.0)
      return 8;

   if(equity < 4000.0)
      return 9;

   return 10;
}

//==================================================================
// DYNAMIC GRID SPACING
// Max trades | Spacing
//     1      | No grid (returns 0)
//     2      | $10.00
//     3      | $10.00
//     4      | $6.67
//     5      | $5.00
//     6      | $4.00
//     7      | $3.33
//     8      | $2.86
//     9      | $2.50
//    10      | $2.22
//==================================================================
double GetGridSpacing(int maxTrades)
{
   if(maxTrades <= 1)
      return 0.0;

   if(maxTrades == 2)
      return GRID_TWO_TRADE_USD;

   return GRID_RANGE_USD/(double)(maxTrades-1);
}

//==================================================================
// COUNT OPEN POSITIONS
//==================================================================
int CountMyPositions(int direction)
{
   int count = 0;

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);

      if(direction == 1 && type == POSITION_TYPE_BUY)
         count++;

      if(direction == -1 && type == POSITION_TYPE_SELL)
         count++;
   }

   return count;
}

//==================================================================
// COUNT PENDING BY DIRECTION
//==================================================================
int CountMyPending(int direction)
{
   int count = 0;

   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket = OrderGetTicket(i);

      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;

      ENUM_ORDER_TYPE type =
         (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);

      if(direction == 1 && type == ORDER_TYPE_BUY_LIMIT)
         count++;

      if(direction == -1 && type == ORDER_TYPE_SELL_LIMIT)
         count++;
   }

   return count;
}

//==================================================================
// TOTAL OPEN + PENDING COUNT
//==================================================================
int CountMyTotalExposure()
{
   int count = 0;

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      count++;
   }

   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket = OrderGetTicket(i);

      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;

      count++;
   }

   return count;
}

//==================================================================
// PENDING EXISTS
//==================================================================
bool PendingExists(ENUM_ORDER_TYPE type,double price)
{
   double tolerance = PointValue()*3.0;

   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket = OrderGetTicket(i);

      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;

      ENUM_ORDER_TYPE existing =
         (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);

      if(existing != type)
         continue;

      double existingPrice =
         OrderGetDouble(ORDER_PRICE_OPEN);

      if(MathAbs(existingPrice-price) <= tolerance)
         return true;
   }

   return false;
}

//==================================================================
// DELETE ALL EA PENDING ORDERS
//==================================================================
void DeleteAllMyPending()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket = OrderGetTicket(i);

      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;

      if(!trade.OrderDelete(ticket))
      {
         Print("Pending delete failed ticket ",ticket,
               ": ",trade.ResultRetcodeDescription());
      }
   }
}

//==================================================================
// DELETE PENDING BY DIRECTION
//==================================================================
void DeletePendingType(int direction)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket = OrderGetTicket(i);

      if(ticket == 0 || !OrderSelect(ticket))
         continue;

      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;

      ENUM_ORDER_TYPE type =
         (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);

      if(direction == 1 && type == ORDER_TYPE_BUY_LIMIT)
      {
         if(!trade.OrderDelete(ticket))
            Print("BUY pending delete failed: ",
                  trade.ResultRetcodeDescription());
      }

      if(direction == -1 && type == ORDER_TYPE_SELL_LIMIT)
      {
         if(!trade.OrderDelete(ticket))
            Print("SELL pending delete failed: ",
                  trade.ResultRetcodeDescription());
      }
   }
}

//==================================================================
// CLOSE ALL EA POSITIONS
//==================================================================
void CloseAllMyPositions()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      if(!trade.PositionClose(ticket,InpDeviationPoints))
      {
         Print("Position close failed ticket ",ticket,
               ": ",trade.ResultRetcodeDescription());
      }
   }
}

//==================================================================
// CLOSE ALL BUYS
//==================================================================
void CloseAllBuys()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      if(PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_BUY)
         continue;

      if(!trade.PositionClose(ticket,InpDeviationPoints))
      {
         Print("BUY close failed ticket ",ticket,
               ": ",trade.ResultRetcodeDescription());
      }
   }
}

//==================================================================
// CLOSE ALL SELLS
//==================================================================
void CloseAllSells()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      if(PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_SELL)
         continue;

      if(!trade.PositionClose(ticket,InpDeviationPoints))
      {
         Print("SELL close failed ticket ",ticket,
               ": ",trade.ResultRetcodeDescription());
      }
   }
}

//==================================================================
// RESET SETUPS AFTER STOP OUT
//==================================================================
void ResetSetupsAfterStopout()
{
   // M1 swings and M1 state are KEPT after a stop out.
   // The swing structure is still valid; only a new
   // M5 confirmation is required before trading again.

   g_buyM5State = M5_WAIT_SOLDIERS;
   g_sellM5State = M5_WAIT_SOLDIERS;

   g_buyM5Age = 0;
   g_sellM5Age = 0;

   g_buySoldierLow = 0.0;
   g_sellSoldierHigh = 0.0;

   g_buySweepLow = 0.0;
   g_sellSweepHigh = 0.0;

   g_buyZonePrice = 0.0;
   g_sellZonePrice = 0.0;

   g_buyZoneValid = false;
   g_sellZoneValid = false;

   // Clear armed RSI cycles so the refill path cannot
   // re-enter straight away.
   g_buyExtremeArmed = false;
   g_sellExtremeArmed = false;

   // Require a fresh full confirmation before trading again.
   g_waitConfirmAfterStopout = true;

   // Keep the current RSI direction.
   // No cooldown is imposed after a stopout.
}

//==================================================================
// TIERED STOP OUT PERCENT
// Balance below $2000      -> 50%
// $2000 - $2999.99         -> 40%
// $3000 - $3999.99         -> 30%
// $4000 - $4999.99         -> 20%
// $5000 and above          -> 10% (locked)
//==================================================================
double GetStopoutPercent(double balance)
{
   if(balance < 2000.0)
      return 50.0;

   if(balance < 3000.0)
      return 40.0;

   if(balance < 4000.0)
      return 30.0;

   if(balance < 5000.0)
      return 20.0;

   return 10.0;
}

//==================================================================
// TIERED BALANCE-BASED ACCOUNT STOP OUT
//==================================================================
bool CheckAccountStopout()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);

   if(balance <= 0.0)
      return false;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   double stopoutEquity =
      balance*(1.0-GetStopoutPercent(balance)/100.0);

   if(equity > stopoutEquity)
      return false;

   if(CountMyTotalExposure() <= 0)
      return false;

   if(InpVerbose)
   {
      Print("V5.18 ACCOUNT STOP OUT TRIGGERED. ",
            "Balance=",DoubleToString(balance,2),
            " Equity=",DoubleToString(equity,2),
            " Stopout level=",
            DoubleToString(stopoutEquity,2));
   }

   CloseAllMyPositions();
   DeleteAllMyPending();

   ResetSetupsAfterStopout();

   if(InpVerbose)
      Print("V5.18: All EA Gold trades closed. ",
            "Scanning resumes immediately. ",
            "Waiting for NEW full confirmation before trading.");

   return true;
}

//==================================================================
// PLACE TP RE-ENTRY AT ORIGINAL ENTRY PRICE
// BUY TP -> BUY LIMIT AT ORIGINAL BUY ENTRY
// SELL TP -> SELL LIMIT AT ORIGINAL SELL ENTRY
//==================================================================
void PlaceTPReplacement(int direction,double originalEntry)
{
   if(direction == 1)
   {
      if(g_direction != DIRECTION_BUY || !g_buyRSIActive)
         return;
   }
   else if(direction == -1)
   {
      if(g_direction != DIRECTION_SELL || !g_sellRSIActive)
         return;
   }
   else
   {
      return;
   }

   int maxExposure = GetMaxPositions();

   if(maxExposure <= 0)
      return;

   if(CountMyTotalExposure() >= maxExposure)
   {
      if(InpVerbose)
         Print("V5.18 TP replacement skipped: exposure limit reached.");

      return;
   }

   double price = NormalizePrice(originalEntry);
   double lot = GetDynamicLot();

   if(price <= 0.0 || lot <= 0.0)
      return;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   if(direction == 1)
   {
      double ask = SymbolInfoDouble(_Symbol,SYMBOL_ASK);

      // A BUY LIMIT must be below the current Ask.
      if(price >= ask)
      {
         if(InpVerbose)
            Print("V5.18 BUY TP replacement skipped: original entry ",
                  price," is not below current Ask ",ask);

         return;
      }

      if(PendingExists(ORDER_TYPE_BUY_LIMIT,price))
         return;

      if(CountMyTotalExposure() >= GetMaxPositions())
         return;

      if(trade.BuyLimit(
            lot,price,_Symbol,0,0,
            ORDER_TIME_GTC,0,"V5.18 BUY TP REENTRY"))
      {
         if(InpVerbose)
            Print("V5.18 BUY TP replacement placed at original entry: ",
                  DoubleToString(price,PriceDigits()));
      }
      else
      {
         Print("V5.18 BUY TP replacement failed at ",
               price," : ",trade.ResultRetcodeDescription());
      }
   }

   if(direction == -1)
   {
      double bid = SymbolInfoDouble(_Symbol,SYMBOL_BID);

      // A SELL LIMIT must be above the current Bid.
      if(price <= bid)
      {
         if(InpVerbose)
            Print("V5.18 SELL TP replacement skipped: original entry ",
                  price," is not above current Bid ",bid);

         return;
      }

      if(PendingExists(ORDER_TYPE_SELL_LIMIT,price))
         return;

      if(CountMyTotalExposure() >= GetMaxPositions())
         return;

      if(trade.SellLimit(
            lot,price,_Symbol,0,0,
            ORDER_TIME_GTC,0,"V5.18 SELL TP REENTRY"))
      {
         if(InpVerbose)
            Print("V5.18 SELL TP replacement placed at original entry: ",
                  DoubleToString(price,PriceDigits()));
      }
      else
      {
         Print("V5.18 SELL TP replacement failed at ",
               price," : ",trade.ResultRetcodeDescription());
      }
   }
}

//==================================================================
// INDIVIDUAL TAKE PROFIT - $20 PRICE MOVEMENT PER TRADE
// BUY: entry price + $20
// SELL: entry price - $20
// AFTER SUCCESSFUL CLOSE, PLACE LIMIT AT ORIGINAL ENTRY
//==================================================================
void CheckIndividualTakeProfit()
{
   double bid = SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol,SYMBOL_ASK);

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);

      if(type == POSITION_TYPE_BUY)
      {
         double target = entry+InpIndividualTPUSD;

         if(bid >= target)
         {
            if(InpVerbose)
               Print("V5.18: Individual BUY TP reached. Ticket=",
                     ticket," Entry=",entry," Target=",target);

            bool closeSent =
               trade.PositionClose(ticket,InpDeviationPoints);

            uint retcode = trade.ResultRetcode();

            bool closeAccepted =
               (closeSent &&
                (retcode == TRADE_RETCODE_DONE ||
                 retcode == TRADE_RETCODE_DONE_PARTIAL));

            if(!closeAccepted)
            {
               Print("Individual BUY TP close failed: ",
                     trade.ResultRetcodeDescription());
            }
            else
            {
               // Only replace after the original position is fully closed.
               if(!PositionSelectByTicket(ticket))
                  PlaceTPReplacement(1,entry);
            }
         }
      }

      if(type == POSITION_TYPE_SELL)
      {
         double target = entry-InpIndividualTPUSD;

         if(ask <= target)
         {
            if(InpVerbose)
               Print("V5.18: Individual SELL TP reached. Ticket=",
                     ticket," Entry=",entry," Target=",target);

            bool closeSent =
               trade.PositionClose(ticket,InpDeviationPoints);

            uint retcode = trade.ResultRetcode();

            bool closeAccepted =
               (closeSent &&
                (retcode == TRADE_RETCODE_DONE ||
                 retcode == TRADE_RETCODE_DONE_PARTIAL));

            if(!closeAccepted)
            {
               Print("Individual SELL TP close failed: ",
                     trade.ResultRetcodeDescription());
            }
            else
            {
               // Only replace after the original position is fully closed.
               if(!PositionSelectByTicket(ticket))
                  PlaceTPReplacement(-1,entry);
            }
         }
      }
   }
}

//==================================================================
// NEWS
//==================================================================
bool HighImpactNewsNow()
{
   if(!InpNewsFilter)
      return false;

   datetime now = TimeTradeServer();

   MqlCalendarValue values[];

   datetime from = now-InpNewsAfterMin*60;
   datetime to   = now+InpNewsBeforeMin*60;

   int count = CalendarValueHistory(values,from,to,NULL,NULL);

   if(count <= 0)
      return false;

   for(int i=0;i<count;i++)
   {
      MqlCalendarEvent event;

      if(!CalendarEventById(values[i].event_id,event))
         continue;

      if(event.importance == CALENDAR_IMPORTANCE_HIGH)
         return true;
   }

   return false;
}

//==================================================================
// BULL SOLDIERS
//==================================================================
bool BullSoldiers(double &sweepLow)
{
   MqlRates r[];

   if(!GetRates(PERIOD_M5,6,r))
      return false;

   double ma1,ma2,ma3;

   if(!GetMA(1,ma1) || !GetMA(2,ma2) || !GetMA(3,ma3))
      return false;

   if(!IsBull(r[1]) || !IsBull(r[2]) || !IsBull(r[3]))
      return false;

   if(IsDoji(r[1]) || IsDoji(r[2]) || IsDoji(r[3]))
      return false;

   if(!CandleTouchesMA(r[1],ma1,true) ||
      !CandleTouchesMA(r[2],ma2,true) ||
      !CandleTouchesMA(r[3],ma3,true))
      return false;

   sweepLow = MathMin(r[1].low,MathMin(r[2].low,r[3].low));

   return true;
}

//==================================================================
// BEAR SOLDIERS
//==================================================================
bool BearSoldiers(double &sweepHigh)
{
   MqlRates r[];

   if(!GetRates(PERIOD_M5,6,r))
      return false;

   double ma1,ma2,ma3;

   if(!GetMA(1,ma1) || !GetMA(2,ma2) || !GetMA(3,ma3))
      return false;

   if(!IsBear(r[1]) || !IsBear(r[2]) || !IsBear(r[3]))
      return false;

   if(IsDoji(r[1]) || IsDoji(r[2]) || IsDoji(r[3]))
      return false;

   if(!CandleTouchesMA(r[1],ma1,false) ||
      !CandleTouchesMA(r[2],ma2,false) ||
      !CandleTouchesMA(r[3],ma3,false))
      return false;

   sweepHigh = MathMax(r[1].high,MathMax(r[2].high,r[3].high));

   return true;
}

//==================================================================
// M1 PIVOT LOW
//==================================================================
bool IsPivotLow(int shift)
{
   MqlRates r[];

   int need = shift+InpSwingLookback*2+3;

   if(!GetRates(PERIOD_M1,need,r))
      return false;

   double low = r[shift].low;

   for(int i=1;i<=InpSwingLookback;i++)
   {
      if(low >= r[shift-i].low)
         return false;

      if(low >= r[shift+i].low)
         return false;
   }

   return true;
}

//==================================================================
// M1 PIVOT HIGH
//==================================================================
bool IsPivotHigh(int shift)
{
   MqlRates r[];

   int need = shift+InpSwingLookback*2+3;

   if(!GetRates(PERIOD_M1,need,r))
      return false;

   double high = r[shift].high;

   for(int i=1;i<=InpSwingLookback;i++)
   {
      if(high <= r[shift-i].high)
         return false;

      if(high <= r[shift+i].high)
         return false;
   }

   return true;
}

//==================================================================
// RESET M1 BUY
//==================================================================
void ResetM1Buy()
{
   g_m1BuyState = M1_NONE;

   g_buySwing1 = 0.0;
   g_buySwing2 = 0.0;
   g_buySwing3 = 0.0;

   g_buySwingTime1 = 0;
   g_buySwingTime2 = 0;
   g_buySwingTime3 = 0;
}

//==================================================================
// RESET M1 SELL
//==================================================================
void ResetM1Sell()
{
   g_m1SellState = M1_NONE;

   g_sellSwing1 = 0.0;
   g_sellSwing2 = 0.0;
   g_sellSwing3 = 0.0;

   g_sellSwingTime1 = 0;
   g_sellSwingTime2 = 0;
   g_sellSwingTime3 = 0;
}

//==================================================================
// UPDATE M1 STRUCTURE
//==================================================================
void UpdateM1Structure()
{
   MqlRates r[];

   if(!GetRates(PERIOD_M1,20,r))
      return;

   int shift = InpSwingLookback+1;

   if(g_direction == DIRECTION_BUY)
   {
      if(IsPivotLow(shift))
      {
         double low = r[shift].low;
         datetime tm = r[shift].time;

         if(g_buySwing1 == 0.0)
         {
            g_buySwing1 = low;
            g_buySwingTime1 = tm;
         }
         else if(g_buySwing2 == 0.0)
         {
            if(low > g_buySwing1 &&
               MathAbs(low-g_buySwing1) >= InpSwingGapUSD)
            {
               g_buySwing2 = low;
               g_buySwingTime2 = tm;
               g_m1BuyState = M1_TWO_SWINGS_READY;
            }
         }
         else if(g_buySwing3 == 0.0)
         {
            if(low > g_buySwing2 &&
               MathAbs(low-g_buySwing2) >= InpSwingGapUSD)
            {
               g_buySwing3 = low;
               g_buySwingTime3 = tm;
               g_m1BuyState = M1_THIRD_SWING_LOCKED;
            }
         }
      }
   }

   if(g_direction == DIRECTION_SELL)
   {
      if(IsPivotHigh(shift))
      {
         double high = r[shift].high;
         datetime tm = r[shift].time;

         if(g_sellSwing1 == 0.0)
         {
            g_sellSwing1 = high;
            g_sellSwingTime1 = tm;
         }
         else if(g_sellSwing2 == 0.0)
         {
            if(high < g_sellSwing1 &&
               MathAbs(high-g_sellSwing1) >= InpSwingGapUSD)
            {
               g_sellSwing2 = high;
               g_sellSwingTime2 = tm;
               g_m1SellState = M1_TWO_SWINGS_READY;
            }
         }
         else if(g_sellSwing3 == 0.0)
         {
            if(high < g_sellSwing2 &&
               MathAbs(high-g_sellSwing2) >= InpSwingGapUSD)
            {
               g_sellSwing3 = high;
               g_sellSwingTime3 = tm;
               g_m1SellState = M1_THIRD_SWING_LOCKED;
            }
         }
      }
   }
}

//==================================================================
// CHECK M1 SWEEP
//==================================================================
void CheckM1Sweep()
{
   MqlRates r[];

   if(!GetRates(PERIOD_M1,5,r))
      return;

   if(g_direction == DIRECTION_BUY)
   {
      if(g_m1BuyState == M1_TWO_SWINGS_READY)
      {
         if(r[1].low < g_buySwing2)
            g_m1BuyState = M1_READY;
      }

      if(g_m1BuyState == M1_THIRD_SWING_LOCKED)
      {
         if(r[1].low < g_buySwing3)
            g_m1BuyState = M1_READY;
      }
   }

   if(g_direction == DIRECTION_SELL)
   {
      if(g_m1SellState == M1_TWO_SWINGS_READY)
      {
         if(r[1].high > g_sellSwing2)
            g_m1SellState = M1_READY;
      }

      if(g_m1SellState == M1_THIRD_SWING_LOCKED)
      {
         if(r[1].high > g_sellSwing3)
            g_m1SellState = M1_READY;
      }
   }
}

//==================================================================
// FORCE CLOSE OPPOSITE BASKET
//==================================================================
void CloseOppositeBasket(int newDirection)
{
   if(newDirection == 1)
   {
      if(InpVerbose)
         Print("V5.18: BUY CONFIRMED - CLOSING SELL BASKET.");

      CloseAllSells();
      DeletePendingType(-1);

      g_sellZonePrice = 0.0;
      g_sellZoneValid = false;

      g_sellRSIActive = false;
      g_sellExtremeArmed = false;

      ResetM1Sell();

      g_sellM5State = M5_WAIT_SOLDIERS;
      g_sellM5Age = 0;
   }

   if(newDirection == -1)
   {
      if(InpVerbose)
         Print("V5.18: SELL CONFIRMED - CLOSING BUY BASKET.");

      CloseAllBuys();
      DeletePendingType(1);

      g_buyZonePrice = 0.0;
      g_buyZoneValid = false;

      g_buyRSIActive = false;
      g_buyExtremeArmed = false;

      ResetM1Buy();

      g_buyM5State = M5_WAIT_SOLDIERS;
      g_buyM5Age = 0;
   }
}

//==================================================================
// M5 RSI DIRECTION
//==================================================================
void ProcessDirectionRSI()
{
   double rsi1;
   double rsi2;

   if(!GetRSI(g_rsiM5,1,rsi1))
      return;

   if(!GetRSI(g_rsiM5,2,rsi2))
      return;

   if(rsi1 <= InpRSILow)
   {
      if(g_direction != DIRECTION_BUY)
      {
         if(InpVerbose)
            Print("V5.18: M5 RSI <= 30. BUY direction confirmed.");

         CloseOppositeBasket(1);

         g_direction = DIRECTION_BUY;

         g_buyRSIActive = true;
         g_sellRSIActive = false;

         g_buyExtremeArmed = true;

         ResetM1Buy();

         g_buyM5State = M5_WAIT_SOLDIERS;
         g_buyM5Age = 0;

         return;
      }

      if(rsi2 > InpRSILow)
      {
         g_buyExtremeArmed = true;

         if(InpVerbose)
            Print("V5.18: Fresh BUY RSI-30 cycle armed.");
      }

      g_buyRSIActive = true;
      return;
   }

   if(rsi1 >= InpRSIHigh)
   {
      if(g_direction != DIRECTION_SELL)
      {
         if(InpVerbose)
            Print("V5.18: M5 RSI >= 70. SELL direction confirmed.");

         CloseOppositeBasket(-1);

         g_direction = DIRECTION_SELL;

         g_sellRSIActive = true;
         g_buyRSIActive = false;

         g_sellExtremeArmed = true;

         ResetM1Sell();

         g_sellM5State = M5_WAIT_SOLDIERS;
         g_sellM5Age = 0;

         return;
      }

      if(rsi2 < InpRSIHigh)
      {
         g_sellExtremeArmed = true;

         if(InpVerbose)
            Print("V5.18: Fresh SELL RSI-70 cycle armed.");
      }

      g_sellRSIActive = true;
      return;
   }

   // Middle RSI does not cancel direction.
}

//==================================================================
// BUY M5 CONFIRMATION
//==================================================================
bool BuyM5Confirmation()
{
   MqlRates r[];

   if(!GetRates(PERIOD_M5,8,r))
      return false;

   double sweepLow = 0.0;

   if(g_buyM5State == M5_WAIT_SOLDIERS)
   {
      if(BullSoldiers(sweepLow))
      {
         g_buySoldierLow = sweepLow;
         g_buyM5State = M5_WAIT_SWEEP;
         g_buyM5Age = 0;

         if(InpVerbose)
            Print("V5.18: BUY 3 Soldiers detected.");
      }

      return false;
   }

   g_buyM5Age++;

   if(g_buyM5Age > InpSoldierMaxBars)
   {
      g_buyM5State = M5_WAIT_SOLDIERS;
      g_buyM5Age = 0;
      return false;
   }

   if(g_buyM5State == M5_WAIT_SWEEP)
   {
      if(r[1].low < g_buySoldierLow)
      {
         g_buySweepLow = r[1].low;
         g_buyM5State = M5_WAIT_CUT;

         if(InpVerbose)
            Print("V5.18: BUY liquidity sweep.");
      }

      return false;
   }

   if(g_buyM5State == M5_WAIT_CUT)
   {
      if(r[1].close > g_buySweepLow)
      {
         g_buyM5State = M5_WAIT_CONFIRM;

         if(InpVerbose)
            Print("V5.18: BUY sweep CUT/CLOSE confirmed.");
      }

      return false;
   }

   if(g_buyM5State == M5_WAIT_CONFIRM)
   {
      if(IsBull(r[1]) && !IsDoji(r[1]))
      {
         g_buyM5State = M5_WAIT_SOLDIERS;
         g_buyM5Age = 0;
         return true;
      }
   }

   return false;
}

//==================================================================
// SELL M5 CONFIRMATION
//==================================================================
bool SellM5Confirmation()
{
   MqlRates r[];

   if(!GetRates(PERIOD_M5,8,r))
      return false;

   double sweepHigh = 0.0;

   if(g_sellM5State == M5_WAIT_SOLDIERS)
   {
      if(BearSoldiers(sweepHigh))
      {
         g_sellSoldierHigh = sweepHigh;
         g_sellM5State = M5_WAIT_SWEEP;
         g_sellM5Age = 0;

         if(InpVerbose)
            Print("V5.18: SELL 3 Soldiers detected.");
      }

      return false;
   }

   g_sellM5Age++;

   if(g_sellM5Age > InpSoldierMaxBars)
   {
      g_sellM5State = M5_WAIT_SOLDIERS;
      g_sellM5Age = 0;
      return false;
   }

   if(g_sellM5State == M5_WAIT_SWEEP)
   {
      if(r[1].high > g_sellSoldierHigh)
      {
         g_sellSweepHigh = r[1].high;
         g_sellM5State = M5_WAIT_CUT;

         if(InpVerbose)
            Print("V5.18: SELL liquidity sweep.");
      }

      return false;
   }

   if(g_sellM5State == M5_WAIT_CUT)
   {
      if(r[1].close < g_sellSweepHigh)
      {
         g_sellM5State = M5_WAIT_CONFIRM;

         if(InpVerbose)
            Print("V5.18: SELL sweep CUT/CLOSE confirmed.");
      }

      return false;
   }

   if(g_sellM5State == M5_WAIT_CONFIRM)
   {
      if(IsBear(r[1]) && !IsDoji(r[1]))
      {
         g_sellM5State = M5_WAIT_SOLDIERS;
         g_sellM5Age = 0;
         return true;
      }
   }

   return false;
}

//==================================================================
// OPEN BUY BASKET - EQUITY EXPOSURE LIMIT
//==================================================================
bool OpenBuyBasket(double base)
{
   if(HighImpactNewsNow())
      return false;

   int maxExposure = GetMaxPositions();

   if(maxExposure <= 0)
      return false;

   CloseAllSells();
   DeletePendingType(-1);

   if(CountMyPositions(-1) > 0 || CountMyPending(-1) > 0)
      return false;

   if(CountMyTotalExposure() >= maxExposure)
      return false;

   double lot = GetDynamicLot();

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   if(CountMyPositions(1) == 0)
   {
      if(CountMyTotalExposure() >= maxExposure)
         return false;

      if(!trade.Buy(lot,_Symbol,0,0,0,"V5.18 BUY"))
      {
         Print("BUY market failed: ",
               trade.ResultRetcodeDescription());
         return false;
      }
   }

   g_buyZonePrice = NormalizePrice(base);
   g_buyZoneValid = true;

   // Dynamic grid spacing, locked in when the basket is built.
   double spacing = GetGridSpacing(maxExposure);

   if(spacing <= 0.0)
   {
      if(InpVerbose)
         Print("V5.18: Max trades = ",maxExposure,
               ". No BUY grid placed.");

      return true;
   }

   if(InpVerbose)
      Print("V5.18: BUY grid spacing = $",
            DoubleToString(spacing,2),
            " (max trades ",maxExposure,")");

   for(int i=1;i<MAX_TOTAL_TRADES;i++)
   {
      maxExposure = GetMaxPositions();

      if(maxExposure <= 0 ||
         CountMyTotalExposure() >= maxExposure)
         break;

      double price = NormalizePrice(base-spacing*i);

      if(price <= 0.0)
         continue;

      if(PendingExists(ORDER_TYPE_BUY_LIMIT,price))
         continue;

      if(trade.BuyLimit(
            lot,price,_Symbol,0,0,
            ORDER_TIME_GTC,0,"V5.18 BUY GRID"))
      {
         if(InpVerbose)
            Print("BUY LIMIT placed: ",price);
      }
      else if(InpVerbose)
      {
         Print("BUY LIMIT failed at ",price,
               " : ",trade.ResultRetcodeDescription());
      }
   }

   return true;
}

//==================================================================
// OPEN SELL BASKET - EQUITY EXPOSURE LIMIT
//==================================================================
bool OpenSellBasket(double base)
{
   if(HighImpactNewsNow())
      return false;

   int maxExposure = GetMaxPositions();

   if(maxExposure <= 0)
      return false;

   CloseAllBuys();
   DeletePendingType(1);

   if(CountMyPositions(1) > 0 || CountMyPending(1) > 0)
      return false;

   if(CountMyTotalExposure() >= maxExposure)
      return false;

   double lot = GetDynamicLot();

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   if(CountMyPositions(-1) == 0)
   {
      if(CountMyTotalExposure() >= maxExposure)
         return false;

      if(!trade.Sell(lot,_Symbol,0,0,0,"V5.18 SELL"))
      {
         Print("SELL market failed: ",
               trade.ResultRetcodeDescription());
         return false;
      }
   }

   g_sellZonePrice = NormalizePrice(base);
   g_sellZoneValid = true;

   // Dynamic grid spacing, locked in when the basket is built.
   double spacing = GetGridSpacing(maxExposure);

   if(spacing <= 0.0)
   {
      if(InpVerbose)
         Print("V5.18: Max trades = ",maxExposure,
               ". No SELL grid placed.");

      return true;
   }

   if(InpVerbose)
      Print("V5.18: SELL grid spacing = $",
            DoubleToString(spacing,2),
            " (max trades ",maxExposure,")");

   for(int i=1;i<MAX_TOTAL_TRADES;i++)
   {
      maxExposure = GetMaxPositions();

      if(maxExposure <= 0 ||
         CountMyTotalExposure() >= maxExposure)
         break;

      double price = NormalizePrice(base+spacing*i);

      if(price <= 0.0)
         continue;

      if(PendingExists(ORDER_TYPE_SELL_LIMIT,price))
         continue;

      if(trade.SellLimit(
            lot,price,_Symbol,0,0,
            ORDER_TIME_GTC,0,"V5.18 SELL GRID"))
      {
         if(InpVerbose)
            Print("SELL LIMIT placed: ",price);
      }
      else if(InpVerbose)
      {
         Print("SELL LIMIT failed at ",price,
               " : ",trade.ResultRetcodeDescription());
      }
   }

   return true;
}

//==================================================================
// REFILL SAME DIRECTION
//==================================================================
void RefillSameDirection()
{
   // After a stop out, only a new full confirmation may enter.
   if(g_waitConfirmAfterStopout)
      return;

   int maxExposure = GetMaxPositions();

   if(maxExposure <= 0)
      return;

   if(g_direction == DIRECTION_BUY &&
      g_buyRSIActive &&
      g_buyExtremeArmed)
   {
      if(CountMyPositions(1) == 0 &&
         CountMyPending(1) == 0)
      {
         double base = g_buyZonePrice;

         if(base <= 0.0)
         {
            base = NormalizePrice(
               SymbolInfoDouble(_Symbol,SYMBOL_ASK));

            g_buyZonePrice = base;
            g_buyZoneValid = true;
         }

         if(OpenBuyBasket(base))
         {
            g_buyExtremeArmed = false;

            if(InpVerbose)
               Print("V5.18: BUY basket rebuilt from remembered zone.");
         }
      }
   }

   if(g_direction == DIRECTION_SELL &&
      g_sellRSIActive &&
      g_sellExtremeArmed)
   {
      if(CountMyPositions(-1) == 0 &&
         CountMyPending(-1) == 0)
      {
         double base = g_sellZonePrice;

         if(base <= 0.0)
         {
            base = NormalizePrice(
               SymbolInfoDouble(_Symbol,SYMBOL_BID));

            g_sellZonePrice = base;
            g_sellZoneValid = true;
         }

         if(OpenSellBasket(base))
         {
            g_sellExtremeArmed = false;

            if(InpVerbose)
               Print("V5.18: SELL basket rebuilt from remembered zone.");
         }
      }
   }
}

//==================================================================
// HISTORY SCAN
//==================================================================
void ScanHistoryDirection()
{
   int bars = InpHistoryDays*24*12;
   int minimum = InpMinHistoryDays*24*12;

   if(bars < minimum)
      bars = minimum;

   if(bars > 20000)
      bars = 20000;

   double rsi[];
   ArraySetAsSeries(rsi,true);

   int copied = CopyBuffer(g_rsiM5,0,1,bars,rsi);

   if(copied <= 0)
      return;

   g_direction = DIRECTION_NONE;

   for(int i=0;i<copied;i++)
   {
      if(rsi[i] >= InpRSIHigh)
      {
         g_direction = DIRECTION_SELL;

         g_sellRSIActive = true;
         g_buyRSIActive = false;

         if(InpVerbose)
            Print("V5.18 history: most recent extreme = SELL.");

         return;
      }

      if(rsi[i] <= InpRSILow)
      {
         g_direction = DIRECTION_BUY;

         g_buyRSIActive = true;
         g_sellRSIActive = false;

         if(InpVerbose)
            Print("V5.18 history: most recent extreme = BUY.");

         return;
      }
   }
}

//==================================================================
// NEW BAR
//==================================================================
bool IsNewBar(ENUM_TIMEFRAMES tf,datetime &lastBar)
{
   datetime current = iTime(_Symbol,tf,0);

   if(current == 0)
      return false;

   if(current != lastBar)
   {
      lastBar = current;
      return true;
   }

   return false;
}

//==================================================================
// CHART STATUS
//==================================================================
void UpdateComment()
{
   string directionText = "NONE";

   if(g_direction == DIRECTION_BUY)
      directionText = "BUY";

   if(g_direction == DIRECTION_SELL)
      directionText = "SELL";

   string buyState = "NONE";
   string sellState = "NONE";

   if(g_m1BuyState == M1_TWO_SWINGS_READY)
      buyState = "2 SWINGS";

   if(g_m1BuyState == M1_THIRD_SWING_LOCKED)
      buyState = "3RD LOCKED";

   if(g_m1BuyState == M1_READY)
      buyState = "READY";

   if(g_m1SellState == M1_TWO_SWINGS_READY)
      sellState = "2 SWINGS";

   if(g_m1SellState == M1_THIRD_SWING_LOCKED)
      sellState = "3RD LOCKED";

   if(g_m1SellState == M1_READY)
      sellState = "READY";

   double rsiM5 = 0.0;
   GetRSI(g_rsiM5,1,rsiM5);

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double stopoutPct = GetStopoutPercent(balance);
   double stopoutLevel = balance*(1.0-stopoutPct/100.0);

   int maxTrades = GetMaxPositions();
   double spacing = GetGridSpacing(maxTrades);

   string spacingText = "NO GRID";

   if(spacing > 0.0)
      spacingText = "$"+DoubleToString(spacing,2);

   Comment(
      "CASTIMOFX MA+RSI WONDER V5.18\n",
      "Symbol: ",_Symbol,"\n",
      "M5 Direction: ",directionText,"\n",
      "M5 RSI: ",DoubleToString(rsiM5,2),"\n",
      "BUY RSI Active: ",(g_buyRSIActive?"YES":"NO"),"\n",
      "SELL RSI Active: ",(g_sellRSIActive?"YES":"NO"),"\n",
      "BUY Next 30 Cycle: ",(g_buyExtremeArmed?"ARMED":"WAIT"),"\n",
      "SELL Next 70 Cycle: ",(g_sellExtremeArmed?"ARMED":"WAIT"),"\n",
      "M1 BUY: ",buyState,"\n",
      "M1 SELL: ",sellState,"\n",
      "BUY Zone: ",DoubleToString(g_buyZonePrice,PriceDigits()),"\n",
      "SELL Zone: ",DoubleToString(g_sellZonePrice,PriceDigits()),"\n",
      "BUY Open: ",CountMyPositions(1),"\n",
      "BUY Pending: ",CountMyPending(1),"\n",
      "SELL Open: ",CountMyPositions(-1),"\n",
      "SELL Pending: ",CountMyPending(-1),"\n",
      "TOTAL OPEN + PENDING: ",
      CountMyTotalExposure(),"/",maxTrades,"\n",
      "GRID SPACING: ",spacingText,"\n",
      "AFTER STOP OUT: ",
      (g_waitConfirmAfterStopout?"WAITING NEW CONFIRMATION":"NORMAL"),"\n",
      "EQUITY: ",DoubleToString(equity,2),"\n",
      "BALANCE: ",DoubleToString(balance,2),"\n",
      "STOP OUT EQUITY LEVEL: ",
      DoubleToString(stopoutLevel,2),"\n",
      "FIXED LOT: 0.02\n",
      "INDIVIDUAL TP: $20 PRICE MOVEMENT\n",
      "TP RE-ENTRY: ORIGINAL ENTRY LIMIT\n",
      "ACCOUNT STOP OUT: ",DoubleToString(stopoutPct,0),"% BALANCE"
   );
}

//==================================================================
// INITIALIZATION
//==================================================================
int OnInit()
{
   if(!IsGold())
   {
      Print("V5.18 ERROR: Gold only. Current symbol = ",_Symbol);
      return INIT_FAILED;
   }

   // Validate fixed 0.02 lot against broker volume rules.
   double minLot = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);

   if(FIXED_LOT < minLot || FIXED_LOT > maxLot)
   {
      Print("V5.18 ERROR: Broker does not support fixed 0.02 lot.");
      return INIT_FAILED;
   }

   if(step > 0.0)
   {
      double steps = (FIXED_LOT-minLot)/step;

      if(MathAbs(steps-MathRound(steps)) > 0.000001)
      {
         Print("V5.18 ERROR: Broker volume step does not support exactly 0.02 lot.");
         return INIT_FAILED;
      }
   }

   g_rsiM1 = iRSI(_Symbol,PERIOD_M1,InpRSIPeriod,PRICE_CLOSE);
   g_rsiM5 = iRSI(_Symbol,PERIOD_M5,InpRSIPeriod,PRICE_CLOSE);

   g_maM5 = iMA(
      _Symbol,
      PERIOD_M5,
      InpMAPeriod,
      0,
      MODE_SMA,
      PRICE_CLOSE);

   if(g_rsiM1 == INVALID_HANDLE ||
      g_rsiM5 == INVALID_HANDLE ||
      g_maM5 == INVALID_HANDLE)
   {
      Print("V5.18 ERROR: Indicator handle creation failed.");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   ScanHistoryDirection();

   g_lastM1Bar = iTime(_Symbol,PERIOD_M1,0);
   g_lastM5Bar = iTime(_Symbol,PERIOD_M5,0);

   Print(
      "CASTIMOFX MA+RSI WONDER V5.18 started. ",
      "Symbol=",_Symbol,
      " Direction=",g_direction,
      " FixedLot=0.02",
      " EquityMaxExposure=",GetMaxPositions(),
      " GridSpacing=",DoubleToString(GetGridSpacing(GetMaxPositions()),2),
      " IndividualTP=$20",
      " TPReplacement=OriginalEntryLimit",
      " Stopout=",DoubleToString(GetStopoutPercent(AccountInfoDouble(ACCOUNT_BALANCE)),0),"% balance",
      " HistoryDays=",InpHistoryDays
   );

   return INIT_SUCCEEDED;
}

//==================================================================
// DEINITIALIZATION
//==================================================================
void OnDeinit(const int reason)
{
   if(g_rsiM1 != INVALID_HANDLE)
      IndicatorRelease(g_rsiM1);

   if(g_rsiM5 != INVALID_HANDLE)
      IndicatorRelease(g_rsiM5);

   if(g_maM5 != INVALID_HANDLE)
      IndicatorRelease(g_maM5);

   Comment("");
}

//==================================================================
// MAIN TICK
//==================================================================
void OnTick()
{
   if(!IsGold())
      return;

   //---------------------------------------------------------------
   // ACCOUNT STOP OUT - CHECK FIRST
   //---------------------------------------------------------------
   if(CheckAccountStopout())
   {
      UpdateComment();
      return;
   }

   //---------------------------------------------------------------
   // INDIVIDUAL PROFIT EXIT
   //---------------------------------------------------------------
   CheckIndividualTakeProfit();

   //---------------------------------------------------------------
   // DETECT NEW BARS
   //---------------------------------------------------------------
   bool newM1 = IsNewBar(PERIOD_M1,g_lastM1Bar);
   bool newM5 = IsNewBar(PERIOD_M5,g_lastM5Bar);

   //---------------------------------------------------------------
   // M5 DIRECTION
   //---------------------------------------------------------------
   if(newM5)
      ProcessDirectionRSI();

   //---------------------------------------------------------------
   // M1 STRUCTURE
   //---------------------------------------------------------------
   if(newM1)
   {
      UpdateM1Structure();
      CheckM1Sweep();
   }

   //---------------------------------------------------------------
   // M5 CONFIRMATION + ENTRY
   //---------------------------------------------------------------
   if(newM5)
   {
      // BUY
      if(g_direction == DIRECTION_BUY)
      {
         if(g_m1BuyState == M1_READY)
         {
            if(BuyM5Confirmation())
            {
               CloseAllSells();
               DeletePendingType(-1);

               if(CountMyPositions(-1) == 0 &&
                  CountMyPending(-1) == 0)
               {
                  if(CountMyPositions(1) == 0 &&
                     CountMyPending(1) == 0)
                  {
                     double base = NormalizePrice(
                        SymbolInfoDouble(_Symbol,SYMBOL_ASK));

                     g_buyZonePrice = base;
                     g_buyZoneValid = true;

                     if(OpenBuyBasket(base))
                     {
                        g_buyExtremeArmed = false;
                        g_waitConfirmAfterStopout = false;

                        if(InpVerbose)
                           Print("V5.18: BUY entry setup confirmed.");
                     }
                  }
               }
            }
         }
      }

      // SELL
      if(g_direction == DIRECTION_SELL)
      {
         if(g_m1SellState == M1_READY)
         {
            if(SellM5Confirmation())
            {
               CloseAllBuys();
               DeletePendingType(1);

               if(CountMyPositions(1) == 0 &&
                  CountMyPending(1) == 0)
               {
                  if(CountMyPositions(-1) == 0 &&
                     CountMyPending(-1) == 0)
                  {
                     double base = NormalizePrice(
                        SymbolInfoDouble(_Symbol,SYMBOL_BID));

                     g_sellZonePrice = base;
                     g_sellZoneValid = true;

                     if(OpenSellBasket(base))
                     {
                        g_sellExtremeArmed = false;
                        g_waitConfirmAfterStopout = false;

                        if(InpVerbose)
                           Print("V5.18: SELL entry setup confirmed.");
                     }
                  }
               }
            }
         }
      }
   }

   //---------------------------------------------------------------
   // SAME-DIRECTION NEW RSI CYCLE
   //---------------------------------------------------------------
   if(newM5)
      RefillSameDirection();

   //---------------------------------------------------------------
   // DISPLAY
   //---------------------------------------------------------------
   UpdateComment();
}
//+------------------------------------------------------------------+
