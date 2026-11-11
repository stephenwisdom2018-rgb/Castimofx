//+------------------------------------------------------------------+
//|  APOSTLE - A to I - v3.3 LOW VOLATILITY FILTER                   |
//|  1 instant + 19 pending limits, $2 apart, NOT 20 instant        |
//|  BUY: 1 Buy market + 19 BuyLimit below                           |
//|  SELL: 1 Sell market + 19 SellLimit above                        |
//|  NEW: Basket only opens when ATR shows LOW volatility            |
//+------------------------------------------------------------------+
#property copyright "Apostle - A to I v3.3"
#property version   "3.30"
#property strict
#include <Trade\Trade.mqh>
CTrade trade;

input double InpLot          = 0.01;
input int    InpPendCount    = 19;
input double InpPendStepUSD = 2.0; // $2 profit spacing
input double InpTPBasketUSD = 20.0;
input int    InpRSIPeriod    = 14;
input double InpRSIHigh     = 70.0;
input double InpRSILow      = 30.0;
input int    InpSwingLeft   = 5;
input int    InpSwingRight  = 2;
input double InpMinMove     = 3.0;
input bool   InpDebug       = true;
input ulong  InpMagic       = 20261108;

//--- LOW VOLATILITY FILTER
input bool            InpUseLowVol  = true;      // Trade only in low volatility
input ENUM_TIMEFRAMES InpATRTF      = PERIOD_M5; // ATR timeframe
input int             InpATRPeriod  = 14;        // ATR period
input double          InpMaxATR     = 3.0;       // Max ATR in $ price (low vol if ATR <= this)

int hRSI_M1, hRSI_M5, hATR;
bool g_locked=false; bool g_isBuy=true;
double g_Hprice=0, g_Gprice=0, g_Iprice=0;
datetime g_Itime=0, g_lastTradedI=0;
datetime g_lastVolLog=0;

struct Swing { datetime time; double price; bool isHigh; double rsiM1; };
void Log(string s){ if(InpDebug) Print(s); }

int OnInit()
{
   hRSI_M1=iRSI(_Symbol,PERIOD_M1,InpRSIPeriod,PRICE_CLOSE);
   hRSI_M5=iRSI(_Symbol,PERIOD_M5,InpRSIPeriod,PRICE_CLOSE);
   hATR=iATR(_Symbol,InpATRTF,InpATRPeriod);
   if(hRSI_M1==INVALID_HANDLE||hRSI_M5==INVALID_HANDLE||hATR==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagic);
   Print("v3.3 started. 1 instant + 19 pendings $2 apart. Low-vol filter=",(InpUseLowVol?"ON":"OFF"),
         " MaxATR=$",DoubleToString(InpMaxATR,2));
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ IndicatorRelease(hRSI_M1); IndicatorRelease(hRSI_M5); IndicatorRelease(hATR); Comment(""); }

//--- ATR of the last CLOSED bar
double CurrentATR()
{
   double buf[1];
   if(CopyBuffer(hATR,0,1,1,buf)!=1) return -1;
   return buf[0];
}

//--- true when market is calm enough to trade
bool IsLowVolatility()
{
   if(!InpUseLowVol) return true;
   double atr=CurrentATR();
   if(atr<0) return false;
   return (atr<=InpMaxATR);
}

void ShowStatus()
{
   double atr=CurrentATR();
   string vol = !InpUseLowVol ? "FILTER OFF" : (atr<0 ? "NO DATA" : (atr<=InpMaxATR ? "LOW - TRADING ALLOWED" : "HIGH - WAITING"));
   Comment("APOSTLE A-I v3.3\n",
           "ATR(",InpATRPeriod,"): $",DoubleToString(atr,2)," / Max $",DoubleToString(InpMaxATR,2),"\n",
           "Volatility: ",vol,"\n",
           "Setup: ",(g_locked?(g_isBuy?"BUY LOCKED - wait H break":"SELL LOCKED - wait H break"):"SCANNING"));
}

double RSI_M5_Closed(datetime t)
{
   int shift=iBarShift(_Symbol,PERIOD_M5,t,true);
   if(shift<0) return -1;
   if(shift==0) return -1;
   double buf[1];
   if(CopyBuffer(hRSI_M5,0,shift,1,buf)!=1) return -1;
   return buf[0];
}

int GetSwings(Swing &sw[])
{
   MqlRates rt[]; ArraySetAsSeries(rt,true);
   int need=600;
   if(CopyRates(_Symbol,PERIOD_M1,0,need,rt)<100) return 0;
   double rsiBuf[]; ArraySetAsSeries(rsiBuf,true);
   if(CopyBuffer(hRSI_M1,0,0,need,rsiBuf)<100) return 0;
   int cnt=0; ArrayResize(sw,need);
   for(int i=InpSwingRight;i<need-InpSwingLeft;i++)
   {
      bool isHigh=true,isLow=true;
      for(int k=1;k<=InpSwingLeft;k++){ if(rt[i].high<=rt[i+k].high) isHigh=false; if(rt[i].low>=rt[i+k].low) isLow=false; }
      for(int k=1;k<=InpSwingRight;k++){ if(rt[i].high<=rt[i-k].high) isHigh=false; if(rt[i].low>=rt[i-k].low) isLow=false; }
      if(!isHigh && !isLow) continue;
      if(isHigh && isLow) continue;
      double p = isHigh ? rt[i].high : rt[i].low;
      if(cnt>0 && MathAbs(p - sw[cnt-1].price) < InpMinMove) continue;
      sw[cnt].time=rt[i].time; sw[cnt].price=p; sw[cnt].isHigh=isHigh; sw[cnt].rsiM1=rsiBuf[i]; cnt++;
      if(cnt>=need-5) break;
   }
   for(int a=0;a<cnt/2;a++){ Swing tmp=sw[a]; sw[a]=sw[cnt-1-a]; sw[cnt-1-a]=tmp; }
   return cnt;
}

int NextHigh(Swing &sw[],int cnt,int start,double minPrice)
{
   for(int i=start;i<cnt;i++){ if(sw[i].isHigh && sw[i].price>minPrice) return i; }
   return -1;
}
int NextLow(Swing &sw[],int cnt,int start,double maxPrice)
{
   for(int i=start;i<cnt;i++){ if(!sw[i].isHigh && sw[i].price<maxPrice) return i; }
   return -1;
}

bool FindBuy(Swing &sw[],int cnt,double &Hprice,double &Gprice,double &Iprice,datetime &Itime)
{
   for(int a=0;a<cnt-8;a++)
   {
      if(sw[a].isHigh) continue;
      Swing A=sw[a];
      int b=NextHigh(sw,cnt,a+1,A.price+InpMinMove); if(b<0) continue;
      Swing B=sw[b];
      int c=NextLow(sw,cnt,b+1,B.price); if(c<0) continue;
      Swing C=sw[c]; if(!(C.price>A.price)) continue;
      int d=NextHigh(sw,cnt,c+1,C.price); if(d<0) continue;
      Swing D=sw[d]; if(!(D.price>B.price)) continue;
      int e=NextLow(sw,cnt,d+1,D.price); if(e<0) continue;
      Swing E=sw[e]; if(!(E.price>C.price)) continue;
      int f=NextHigh(sw,cnt,e+1,E.price); if(f<0) continue;
      Swing F=sw[f]; if(!(F.price>E.price)) continue;
      int g=-1; Swing G; double gM5=-1;
      for(int i=f+1;i<cnt;i++)
      {
         if(sw[i].isHigh) continue;
         if(!(sw[i].price<E.price)) continue;
         if(!(sw[i].rsiM1<=InpRSILow)) continue;
         gM5=RSI_M5_Closed(sw[i].time);
         if(gM5<0) continue;
         if(!(gM5<=InpRSILow)) continue;
         g=i; G=sw[i]; break;
      }
      if(g<0) continue;
      int h=NextHigh(sw,cnt,g+1,G.price); if(h<0) continue;
      Swing H=sw[h]; if(!(H.price<F.price)) continue;
      int ii=-1; Swing I;
      for(int i=h+1;i<cnt;i++)
      {
         if(sw[i].isHigh) continue;
         if(!(sw[i].price>G.price)) continue;
         if(!(sw[i].rsiM1<=InpRSILow)) continue;
         ii=i; I=sw[i]; break;
      }
      if(ii<0) continue;
      Hprice=H.price; Gprice=G.price; Iprice=I.price; Itime=I.time;
      Log("BUY A-I LOCKED G="+DoubleToString(G.price,1)+" H="+DoubleToString(H.price,1)+" I="+DoubleToString(I.price,1));
      return true;
   }
   return false;
}

bool FindSell(Swing &sw[],int cnt,double &Hprice,double &Gprice,double &Iprice,datetime &Itime)
{
   for(int a=0;a<cnt-8;a++)
   {
      if(!sw[a].isHigh) continue;
      Swing A=sw[a];
      int b=-1; for(int i=a+1;i<cnt;i++){ if(!sw[i].isHigh && sw[i].price<A.price-InpMinMove){ b=i; break; } } if(b<0) continue;
      Swing B=sw[b];
      int c=-1; for(int i=b+1;i<cnt;i++){ if(sw[i].isHigh && sw[i].price>B.price){ c=i; break; } } if(c<0) continue;
      Swing C=sw[c]; if(!(C.price<A.price)) continue;
      int d=-1; for(int i=c+1;i<cnt;i++){ if(!sw[i].isHigh && sw[i].price<C.price){ d=i; break; } } if(d<0) continue;
      Swing D=sw[d]; if(!(D.price<B.price)) continue;
      int e=-1; for(int i=d+1;i<cnt;i++){ if(sw[i].isHigh && sw[i].price>D.price){ e=i; break; } } if(e<0) continue;
      Swing E=sw[e]; if(!(E.price<C.price)) continue;
      int f=-1; for(int i=e+1;i<cnt;i++){ if(!sw[i].isHigh && sw[i].price<E.price){ f=i; break; } } if(f<0) continue;
      Swing F=sw[f]; if(!(F.price<E.price)) continue;
      int g=-1; Swing G; double gM5=-1;
      for(int i=f+1;i<cnt;i++)
      {
         if(!sw[i].isHigh) continue;
         if(!(sw[i].price>E.price)) continue;
         if(!(sw[i].rsiM1>=InpRSIHigh)) continue;
         gM5=RSI_M5_Closed(sw[i].time);
         if(gM5<0) continue;
         if(!(gM5>=InpRSIHigh)) continue;
         g=i; G=sw[i]; break;
      }
      if(g<0) continue;
      int h=-1; for(int i=g+1;i<cnt;i++){ if(!sw[i].isHigh && sw[i].price<G.price){ h=i; break; } } if(h<0) continue;
      Swing H=sw[h]; if(!(H.price>F.price)) continue;
      int ii=-1; Swing I;
      for(int i=h+1;i<cnt;i++)
      {
         if(!sw[i].isHigh) continue;
         if(!(sw[i].price<G.price)) continue;
         if(!(sw[i].rsiM1>=InpRSIHigh)) continue;
         ii=i; I=sw[i]; break;
      }
      if(ii<0) continue;
      Hprice=H.price; Gprice=G.price; Iprice=I.price; Itime=I.time;
      Log("SELL A-I LOCKED G="+DoubleToString(G.price,1)+" H="+DoubleToString(H.price,1)+" I="+DoubleToString(I.price,1));
      return true;
   }
   return false;
}

bool HasOpenOrPending()
{
   for(int i=PositionsTotal()-1;i>=0;i--){ ulong t=PositionGetTicket(i); if(t==0) continue; if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==(long)InpMagic) return true; }
   for(int i=OrdersTotal()-1;i>=0;i--){ ulong t=OrderGetTicket(i); if(t==0) continue; if(OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==(long)InpMagic) return true; }
   return false;
}

void OpenBasket(bool isBuy)
{
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double price=isBuy?ask:bid;

   // 1 - INSTANT ONLY
   bool ok=false;
   if(isBuy) ok=trade.Buy(InpLot,_Symbol,price,0,0,"A-I H-BREAK BUY instant");
   else      ok=trade.Sell(InpLot,_Symbol,price,0,0,"A-I H-BREAK SELL instant");
   if(!ok){ Print("Instant failed: ",trade.ResultRetcodeDescription()); return; }
   Print(isBuy?"1 INSTANT BUY @ ":"1 INSTANT SELL @ ",DoubleToString(price,2));

   // 2 - CORRECT $2 PRICE STEP
   // Profit = priceMove * Lot * ContractSize
   // So priceMove = $2 / (Lot * ContractSize)
   // XAUUSD: Contract=100, Lot=0.01 => 0.01*100=1 => $2 / 1 = $2.00 price move
   double contract = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0) contract=100;
   double stepPrice = InpPendStepUSD / (InpLot * contract);
   Print("Pend stepPrice = $",DoubleToString(stepPrice,2)," for $",DoubleToString(InpPendStepUSD,2)," spacing. Contract=",contract," Lot=",InpLot);

   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   int stopsLevel=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minDist = stopsLevel*point + 0.05; // keep pendings away from price so they do NOT fill instantly

   for(int j=1;j<=InpPendCount;j++)
   {
      double p = isBuy ? price - stepPrice*j : price + stepPrice*j;
      p = NormalizeDouble(p, digits);
      // Safety: if too close to market, push it further
      if(isBuy && p > ask - minDist) p = NormalizeDouble(ask - minDist - stepPrice*(j-1), digits);
      if(!isBuy && p < bid + minDist) p = NormalizeDouble(bid + minDist + stepPrice*(j-1), digits);

      bool rok=false;
      if(isBuy) rok=trade.BuyLimit(InpLot,p,_Symbol,0,0,0,0,"pend BuyLimit "+IntegerToString(j));
      else      rok=trade.SellLimit(InpLot,p,_Symbol,0,0,0,0,"pend SellLimit "+IntegerToString(j));
      if(!rok) Print("Pending ",j," failed at ",DoubleToString(p,2)," : ",trade.ResultRetcodeDescription());
      else if(InpDebug) Print("Pending ",j," placed: ",(isBuy?"BuyLimit @ ":"SellLimit @ "),DoubleToString(p,2));
   }
   Print(isBuy?"BUY BASKET DONE: 1 instant + 19 BuyLimit":"SELL BASKET DONE: 1 instant + 19 SellLimit");
   g_locked=false;
}

void ManageTP()
{
   double profit=0;
   for(int i=PositionsTotal()-1;i>=0;i--){ ulong t=PositionGetTicket(i); if(t==0) continue; if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue; if(PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic) continue; profit+=PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP); }
   if(profit>=InpTPBasketUSD && profit>0)
   {
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong t=PositionGetTicket(i); if(t==0) continue; if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue; if(PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic) continue; trade.PositionClose(t); }
      for(int i=OrdersTotal()-1;i>=0;i--){ ulong t=OrderGetTicket(i); if(t==0) continue; if(OrderGetString(ORDER_SYMBOL)!=_Symbol) continue; if(OrderGetInteger(ORDER_MAGIC)!=(long)InpMagic) continue; trade.OrderDelete(t); }
      Print("Basket TP +$20 closed Profit=",profit); g_locked=false;
   }
}

//--- open basket only if volatility is low; otherwise keep waiting
void TryOpenBasket(bool isBuy)
{
   if(!IsLowVolatility())
   {
      datetime bar=iTime(_Symbol,PERIOD_M1,0);
      if(bar!=g_lastVolLog)
      {
         g_lastVolLog=bar;
         Log((isBuy?"BUY":"SELL")+string(" H-BREAK but volatility HIGH (ATR=$")+DoubleToString(CurrentATR(),2)+
             " > $"+DoubleToString(InpMaxATR,2)+"). Waiting for calm market.");
      }
      return; // stay locked, retry next tick
   }
   g_lastTradedI=g_Itime;
   OpenBasket(isBuy);
}

void OnTick()
{
   ShowStatus();
   ManageTP(); if(HasOpenOrPending()) return;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(g_locked)
   {
      if(g_isBuy){ if(bid<g_Gprice){ Log("BUY VOID cut G"); g_locked=false; return; } if(ask>g_Hprice){ Log(">>> BUY H-BREAK Ask="+DoubleToString(ask,2)+" H="+DoubleToString(g_Hprice,2)); TryOpenBasket(true); return; } }
      else { if(ask>g_Gprice){ Log("SELL VOID cut G"); g_locked=false; return; } if(bid<g_Hprice){ Log(">>> SELL H-BREAK Bid="+DoubleToString(bid,2)+" H="+DoubleToString(g_Hprice,2)); TryOpenBasket(false); return; } }
      return;
   }
   Swing sw[]; int cnt=GetSwings(sw); if(cnt<9) return;
   double Hp=0,Gp=0,Ip=0; datetime It=0;
   if(FindBuy(sw,cnt,Hp,Gp,Ip,It)){ if(It==g_lastTradedI) return; g_locked=true; g_isBuy=true; g_Hprice=Hp; g_Gprice=Gp; g_Iprice=Ip; g_Itime=It; Log("BUY LOCKED wait H break "+DoubleToString(Hp,2)); return; }
   if(FindSell(sw,cnt,Hp,Gp,Ip,It)){ if(It==g_lastTradedI) return; g_locked=true; g_isBuy=false; g_Hprice=Hp; g_Gprice=Gp; g_Iprice=Ip; g_Itime=It; Log("SELL LOCKED wait H break "+DoubleToString(Hp,2)); return; }
}
