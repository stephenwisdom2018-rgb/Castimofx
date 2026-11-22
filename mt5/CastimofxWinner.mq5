//+------------------------------------------------------------------+
//|  Castimofx Winner v1.10                                          |
//|  Buy stop + sell stop around price, one-cancels-other,           |
//|  fixed SL/TP, breakeven + trailing. Lot steps up with balance.   |
//|                                                                  |
//|  v1.10 changes vs SHEGEE COPY 1.02 C:                            |
//|  - All distances are in gold PRICE ($), so they mean the same    |
//|    on 2-digit (HFM) and 3-digit (Exness) brokers.                |
//|    Defaults = 10x the old point values on a 3-digit broker.      |
//|  - No new orders 23:00-01:00 server time (rollover spread).      |
//|  - Breakeven/trailing and cancel-opposite ALWAYS run, even when  |
//|    cooldown / spread / daily-limit block new orders.             |
//|  - A trade is never opened without a stop loss.                  |
//|  - Removed dead MaxLossPerSideUSD (it could never trigger).      |
//|  - Fixed spread limit (was auto-raised at startup).              |
//|  - Trailing only modifies when SL improves by TrailStep.         |
//|  - Fewer order re-placements (cooldown 60s), margin check,       |
//|    no one-sided straddles, lot rounding fix.                     |
//+------------------------------------------------------------------+
#property copyright "Castimofx"
#property version   "1.10"

#include <Trade\Trade.mqh>
CTrade trade;

input group "Distances in gold price ($) - same on every broker"
input double EntryDistance    = 1.50;  // Pending order distance from price
input double StopLoss         = 2.50;  // Stop loss
input double TakeProfit       = 15.00; // Take profit
input double BreakevenAt      = 5.00;  // Move SL to breakeven at this profit
input double BreakevenLock    = 0.10;  // Profit locked at breakeven
input double TrailDistance    = 3.00;  // Trail distance (starts at BreakevenAt + TrailDistance)
input double TrailStep        = 0.20;  // Minimum SL improvement per modify
input double MaxOrderDistance = 6.00;  // Delete pending order if price is this far away
input double MaxSpread        = 0.60;  // No new orders when spread is above this

input group "Lots"
input double StartLot     = 0.01;  // Lot below $2,000 balance
input bool   LotByBalance = true;  // 0.02 from $2k, 0.04 from $4k, 0.08 from $8k

input group "Timing"
input int CooldownSeconds  = 60;   // Seconds between new straddles
input int MaxTradesPerDay  = 200;  // Max straddles per day
input int NoTradeStartHour = 23;   // No new orders from this hour (server time)
input int NoTradeEndHour   = 1;    // ...until this hour. Same value = off

input group "Other"
input long   Magic        = 123456;
input string TradeComment = "CASTIMOFX_WINNER";
input bool   ShowDebug    = false;  // Print every order action

int      buyCount = 0, sellCount = 0;
datetime lastTradeTime = 0;
int      tradesToday = 0, lastDay = -1;
datetime lastWaitPrint = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   if(EntryDistance <= 0 || StopLoss <= 0 || TakeProfit <= 0 || TrailDistance <= 0)
   {
      Print("Distances must be above 0");
      return INIT_PARAMETERS_INCORRECT;
   }
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   PrintFormat("Castimofx Winner on %s | Digits=%d Point=%g StopsLevel=%d Contract=%g",
               _Symbol, _Digits, _Point,
               (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
               SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE));
   return INIT_SUCCEEDED;
}
//+------------------------------------------------------------------+
void OnTick()
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;

   // 1. Always manage open trades first
   CountPositions();
   ManageBreakevenTrail(bid, ask);
   if(buyCount  > 0) DeletePendings(ORDER_TYPE_SELL_STOP);
   if(sellCount > 0) DeletePendings(ORDER_TYPE_BUY_STOP);
   if(buyCount > 0 || sellCount > 0) return;

   // 2. Bad conditions: remove pending orders so they can't fill on a spike
   double spread = ask - bid;
   if(InNoTradeHours())
   {
      DeleteAllPendings();
      return;
   }
   if(spread > MaxSpread)
   {
      DeleteAllPendings();
      if(TimeCurrent() - lastWaitPrint >= 600)
      {
         PrintFormat("Waiting: spread %.3f > MaxSpread %.3f", spread, MaxSpread);
         lastWaitPrint = TimeCurrent();
      }
      return;
   }
   DeleteFarPendings(bid, ask);

   // 3. Filters for NEW orders only
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day != lastDay) { lastDay = dt.day; tradesToday = 0; }
   if(tradesToday >= MaxTradesPerDay) return;
   if(TimeCurrent() - lastTradeTime < CooldownSeconds) return;

   int pend = CountPendings();
   if(pend >= 2) return;
   if(pend == 1) DeleteAllPendings();   // never leave a one-sided straddle

   double lot = GetLot();
   if(!EnoughMargin(lot, ask))
   {
      if(TimeCurrent() - lastWaitPrint >= 600)
      {
         Print("Waiting: not enough free margin for ", lot, " lot");
         lastWaitPrint = TimeCurrent();
      }
      return;
   }

   bool okBuy  = PlacePending(ORDER_TYPE_BUY_STOP,  ask + EntryDistance, lot);
   bool okSell = PlacePending(ORDER_TYPE_SELL_STOP, bid - EntryDistance, lot);
   if(okBuy != okSell) DeleteAllPendings();
   lastTradeTime = TimeCurrent();
   if(okBuy && okSell) tradesToday++;
}
//+------------------------------------------------------------------+
bool InNoTradeHours()
{
   if(NoTradeStartHour == NoTradeEndHour) return false;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(NoTradeStartHour < NoTradeEndHour)
      return dt.hour >= NoTradeStartHour && dt.hour < NoTradeEndHour;
   return dt.hour >= NoTradeStartHour || dt.hour < NoTradeEndHour;
}
//+------------------------------------------------------------------+
double MinStopDistance()
{
   long stops  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   return (double)(MathMax(stops, freeze) + 5) * _Point;
}
//+------------------------------------------------------------------+
double NormPrice(double p)
{
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick > 0) p = MathRound(p / tick) * tick;
   return NormalizeDouble(p, _Digits);
}
//+------------------------------------------------------------------+
double GetLot()
{
   double lot = StartLot;
   if(LotByBalance)
   {
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal >= 8000)      lot = 0.08;
      else if(bal >= 4000) lot = 0.04;
      else if(bal >= 2000) lot = 0.02;
   }
   return NormalizeLot(lot);
}
//+------------------------------------------------------------------+
double NormalizeLot(double lot)
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minV = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxV = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step > 0) lot = MathFloor(lot / step + 1e-9) * step;
   if(lot < minV) lot = minV;
   if(lot > maxV) lot = maxV;
   int lotDigits = (step > 0) ? (int)MathMax(0, MathCeil(-MathLog10(step) - 1e-9)) : 2;
   return NormalizeDouble(lot, lotDigits);
}
//+------------------------------------------------------------------+
bool EnoughMargin(double lot, double price)
{
   double margin = 0;
   if(!OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, lot, price, margin)) return true;
   return AccountInfoDouble(ACCOUNT_MARGIN_FREE) > margin * 1.5;
}
//+------------------------------------------------------------------+
bool PlacePending(ENUM_ORDER_TYPE type, double price, double lot)
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double minDist = MinStopDistance();

   if(StopLoss < minDist || TakeProfit < minDist)
   {
      PrintFormat("Skipped: SL/TP closer than broker minimum %.3f", minDist);
      return false;   // never trade without a stop loss
   }
   if(type == ORDER_TYPE_BUY_STOP  && price - ask < minDist) price = ask + minDist;
   if(type == ORDER_TYPE_SELL_STOP && bid - price < minDist) price = bid - minDist;
   price = NormPrice(price);

   double sl, tp;
   if(type == ORDER_TYPE_BUY_STOP) { sl = price - StopLoss; tp = price + TakeProfit; }
   else                            { sl = price + StopLoss; tp = price - TakeProfit; }
   sl = NormPrice(sl);
   tp = NormPrice(tp);

   if(!trade.OrderOpen(_Symbol, type, lot, 0, price, sl, tp, ORDER_TIME_GTC, 0, TradeComment))
   {
      PrintFormat("PlacePending FAILED type=%d price=%.3f lot=%.2f retcode=%d %s",
                  (int)type, price, lot, trade.ResultRetcode(), trade.ResultRetcodeDescription());
      return false;
   }
   if(ShowDebug) PrintFormat("PlacePending OK type=%d price=%.3f lot=%.2f", (int)type, price, lot);
   return true;
}
//+------------------------------------------------------------------+
void ManageBreakevenTrail(double bid, double ask)
{
   double minDist = MinStopDistance();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;

      long   type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);

      if(type == POSITION_TYPE_BUY)
      {
         double profit = bid - open;
         double newSL  = sl;
         if(profit >= BreakevenAt && newSL < open + BreakevenLock) newSL = open + BreakevenLock;
         if(profit > BreakevenAt + TrailDistance && bid - TrailDistance > newSL) newSL = bid - TrailDistance;
         newSL = NormPrice(newSL);
         if(newSL - sl >= TrailStep && bid - newSL >= minDist)
         {
            if(!trade.PositionModify(ticket, newSL, tp) && ShowDebug)
               Print("Modify BUY failed: ", trade.ResultRetcodeDescription());
         }
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double cur    = (sl == 0) ? DBL_MAX : sl;
         double profit = open - ask;
         double newSL  = cur;
         if(profit >= BreakevenAt && newSL > open - BreakevenLock) newSL = open - BreakevenLock;
         if(profit > BreakevenAt + TrailDistance && ask + TrailDistance < newSL) newSL = ask + TrailDistance;
         if(newSL == DBL_MAX) continue;
         newSL = NormPrice(newSL);
         if(cur - newSL >= TrailStep && newSL - ask >= minDist)
         {
            if(!trade.PositionModify(ticket, newSL, tp) && ShowDebug)
               Print("Modify SELL failed: ", trade.ResultRetcodeDescription());
         }
      }
   }
}
//+------------------------------------------------------------------+
bool IsMyOrder(ulong ticket)
{
   return ticket != 0
          && OrderGetString(ORDER_SYMBOL) == _Symbol
          && OrderGetInteger(ORDER_MAGIC) == Magic;
}
//+------------------------------------------------------------------+
void DeletePendings(long typeToDelete)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(!IsMyOrder(ticket)) continue;
      if(OrderGetInteger(ORDER_TYPE) == typeToDelete) trade.OrderDelete(ticket);
   }
}
//+------------------------------------------------------------------+
void DeleteAllPendings()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(IsMyOrder(ticket)) trade.OrderDelete(ticket);
   }
}
//+------------------------------------------------------------------+
void DeleteFarPendings(double bid, double ask)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(!IsMyOrder(ticket)) continue;
      long   type  = OrderGetInteger(ORDER_TYPE);
      double price = OrderGetDouble(ORDER_PRICE_OPEN);
      if(type == ORDER_TYPE_SELL_STOP && MathAbs(price - bid) > MaxOrderDistance) trade.OrderDelete(ticket);
      if(type == ORDER_TYPE_BUY_STOP  && MathAbs(price - ask) > MaxOrderDistance) trade.OrderDelete(ticket);
   }
}
//+------------------------------------------------------------------+
int CountPendings()
{
   int c = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
      if(IsMyOrder(OrderGetTicket(i))) c++;
   return c;
}
//+------------------------------------------------------------------+
void CountPositions()
{
   buyCount = 0;
   sellCount = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      if(type == POSITION_TYPE_BUY)  buyCount++;
      if(type == POSITION_TYPE_SELL) sellCount++;
   }
}
//+------------------------------------------------------------------+
