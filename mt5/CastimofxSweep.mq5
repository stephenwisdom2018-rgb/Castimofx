//+------------------------------------------------------------------+
//|                                             CastimofxSweep.mq5   |
//|  Castimofx gold sweep strategy - chosen version "C+3m+MZ+FE"     |
//|  (backtest: research/SWEEP_RESULTS.md, Python: castimofx/,       |
//|   research/micro3_reentry.py, research/micro3_zone.py)           |
//|                                                                  |
//|  All logic runs on closed M1 bars of the chart symbol, whatever  |
//|  the chart timeframe. At start the EA replays the last           |
//|  InpWarmDays of M1 history (no trading) to rebuild structures,   |
//|  zones and open setups, then trades live.                        |
//|                                                                  |
//|  Parts:                                                          |
//|   MAIN  A-F staircase (RSI 14, 68/32 swings, takeout structure), |
//|         G sweeps E (or the last 5-candle low before F), H, then  |
//|         buy the wick break of H. Stop $30, target $20 (or the    |
//|         F-G size if smaller, min $5). RSI re-entries after a     |
//|         stop: target = first target + $15, up to 5.              |
//|   ZONE  every completed structure (A, E, F): 3-candle G inside   |
//|         E-A (and F-E), small H, I, buy the break of H.           |
//|         Stop $1 beyond G (min $5), target 2x risk, up to 40 per  |
//|         structure for 20 days; 1 re-entry after a zone stop.     |
//|   3M    after a taken losing trade: 3 rising candles closing     |
//|         above SMA 10 -> enter, stop beyond the low, 2x risk.     |
//|   MZ    G in the E-A zone at RSI 32 -> 3 micro -> enter early.   |
//|   FLIP  a main/zone trade hits its stop -> trade the other way:   |
//|         stop = half its risk, target = 1.5x that stop.           |
//|  Filters: RSI side of 50, no new trades at 15:00 / 23:00 server, |
//|  no trades when the last hour is tight (< 0.6x normal) or when   |
//|  ADX(14) on M15 is 25-35.                                        |
//|  Sells mirror everything.                                        |
//|                                                                  |
//|  (c) Castimofx.com                                               |
//+------------------------------------------------------------------+
#property copyright "Castimofx.com"
#property link      "https://castimofx.com"
#property version   "1.14"
#property description "Castimofx gold sweep bot (C+3m+MZ+FE). Logic on M1, any chart timeframe."

#include <Trade/Trade.mqh>

//--- inputs
enum ENUM_CFX_ACCOUNT
  {
   CFX_NORMAL = 0,   // Normal account
   CFX_PROP   = 1    // Prop firm account
  };
input group "Account (the only choice you make)"
input ENUM_CFX_ACCOUNT InpAccount        = CFX_NORMAL;   // Account type: Normal or Prop

input group "Prop firm protection"
input double           InpPropStart      = 100000;       // Prop: starting balance (lot = 0.07 per $100,000, automatic)
input double           InpPropDailyStop  = 3.0;          // Prop: stop for the day at this % loss
input double           InpPropMaxStop    = 8.0;          // Prop: stop trading at this % drawdown

input group "General"
input long             InpMagic          = 26112601;     // Magic number
input int              InpWarmDays       = 31;           // History replayed at start (days)
input bool             InpTrade          = true;         // Trading on (false = only log signals)
input bool             InpLog            = true;         // Log signals in the Experts tab
input double           InpFixedLot       = 0;            // Test only: fixed lot (0 = automatic lot plan)

//--- lot settings (automatic, not inputs)
// The lot grows with the balance, but more slowly as the account gets bigger (less risk on big money):
//   up to $10,000      : 0.01 per $2,000             ($2k 0.01, $4k 0.02, $10k 0.05)
//   $10,000 - $50,000  : 0.05 + 0.01 per $4,000      ($30k 0.10, $50k 0.15)
//   above $50,000      : 0.15 + 0.01 per $8,000      ($100k 0.21, $250k 0.40, $500k 0.71)
const bool   FLIPS_ON        = false;   // flips switched off in v1.13 (lost in both EA tests)
const int    LOT_HALF_AFTER  = 3;       // half lot after 3 losses in a row
const double PROP_LOT_PER_1K = 0.0007;  // prop: 0.07 lot per $100,000
const double FLIP_STOP       = 0.5;     // flip: stop = half the stopped trade's risk
const double FLIP_TARGET     = 1.5;     // flip: target = 1.5x the flip stop
const double MKT_MAX_SLIP    = 0.5;     // v1.14: price already past the level -> buy at market if within 0.5x risk

//--- strategy constants (from the backtest)
#define CAP          65536
#define IX(i)        ((i) & (CAP - 1))
const double TOL        = 1.0;     // $ a wick must come within to take out a level
const int    MINOR_K    = 5;       // small pivot size for the level G must sweep
const double HI_LV      = 68.0;
const double LO_LV      = 32.0;
const int    SETUP_BARS = 600;     // a main setup dies after 600 bars without a new swing
const double MAIN_SL    = 30.0;
const double MAIN_TP    = 20.0;
const double MAIN_EXTRA = 15.0;
const int    MAIN_MAXRE = 5;
const int    ZONE_PER   = 40;
const int    ZONE_BARS  = 20 * 1440;
const int    ZRE_BARS   = 4320;
const double RISK_MIN   = 5.0;
const int    M3_BARS    = 1440;
const int    MZ_PER     = 3;
const int    MZ_WAIT    = 240;
const double MZ_RSI     = 32.0;

//--- trade types (bit mask for account modes)
#define T_MAIN    1
#define T_MAINRE  2
#define T_ZEA     4
#define T_ZEARE   8
#define T_ZFE     16
#define T_ZFERE   32
#define T_M3C     64
#define T_M3FE    128
#define T_MZ      256
#define T_FLIP    512
#define T_ALL     1023
#define T_C       (T_MAIN | T_MAINRE | T_ZEA | T_ZEARE)

//--- bar ring buffer (closed M1 bars), absolute index t = 0..N-1
datetime BT[CAP];
double   BO[CAP], BH[CAP], BL[CAP], BC[CAP], BS[CAP], RS[CAP], MA[CAP], RG[CAP];
int      N = 0;
double Hh(int i) { return BH[IX(i)]; }
double Ll(int i) { return BL[IX(i)]; }
double Cc(int i) { return BC[IX(i)]; }
double Oo(int i) { return BO[IX(i)]; }
double Sp(int i) { return BS[IX(i)]; }
double Rr(int i) { return RS[IX(i)]; }
double Mm(int i) { return MA[IX(i)]; }
datetime Tt(int i) { return BT[IX(i)]; }

bool   g_live = false;
CTrade trade;

//+------------------------------------------------------------------+
//| indicators: Wilder RSI 14, SMA 10, 60-bar range, ADX M15         |
//+------------------------------------------------------------------+
double rsi_au = 0, rsi_ad = 0, sma_sum = 0;
// ADX on M15 built from M1 (EWM alpha 1/14), value of the last finished M15 block
datetime adx_block = 0;
bool     adx_have = false;
double   blkH, blkL, blkC, prevH, prevL, prevC;
int      adx_n = 0;
double   eTR, ePDM, eNDM, eDX;
bool     dx_init = false;
double   adx_prev = EMPTY_VALUE;
double   ADXB[CAP];   // ADX value valid for bar t (previous finished block)

void UpdIndicators(int t)
  {
   int k = IX(t);
   // RSI (same seeding as the backtest)
   if(t == 0) RS[k] = 50;
   else
     {
      double d = Cc(t) - Cc(t - 1);
      double up = d > 0 ? d : 0, dn = d < 0 ? -d : 0;
      if(t <= 14)
        {
         rsi_au += up; rsi_ad += dn; RS[k] = 50;
         if(t == 14) { rsi_au /= 14.0; rsi_ad /= 14.0; }
        }
      else
        {
         rsi_au = (rsi_au * 13.0 + up) / 14.0;
         rsi_ad = (rsi_ad * 13.0 + dn) / 14.0;
         RS[k] = (rsi_ad == 0) ? 100.0 : 100.0 - 100.0 / (1.0 + rsi_au / rsi_ad);
        }
     }
   // SMA 10
   sma_sum += Cc(t);
   if(t >= 10) sma_sum -= Cc(t - 10);
   MA[k] = (t >= 9) ? sma_sum / 10.0 : EMPTY_VALUE;
   // 60-bar range
   if(t >= 59)
     {
      double mx = Hh(t), mn = Ll(t);
      for(int i = t - 59; i < t; i++) { mx = MathMax(mx, Hh(i)); mn = MathMin(mn, Ll(i)); }
      RG[k] = mx - mn;
     }
   else RG[k] = EMPTY_VALUE;
   // ADX M15
   datetime blk = (datetime)(((long)Tt(t) / 900) * 900);
   if(!adx_have) { adx_have = true; adx_block = blk; blkH = Hh(t); blkL = Ll(t); blkC = Cc(t); }
   else if(blk != adx_block)
     {
      FinalizeAdxBlock();
      adx_block = blk; blkH = Hh(t); blkL = Ll(t); blkC = Cc(t);
     }
   else { blkH = MathMax(blkH, Hh(t)); blkL = MathMin(blkL, Ll(t)); blkC = Cc(t); }
   ADXB[k] = adx_prev;
  }

void FinalizeAdxBlock()
  {
   const double a = 1.0 / 14.0;
   double tr, pdm = 0, ndm = 0;
   if(adx_n == 0) tr = blkH - blkL;
   else
     {
      double up = blkH - prevH, dn = prevL - blkL;
      pdm = (up > dn && up > 0) ? up : 0;
      ndm = (dn > up && dn > 0) ? dn : 0;
      tr = MathMax(blkH - blkL, MathMax(MathAbs(blkH - prevC), MathAbs(blkL - prevC)));
     }
   if(adx_n == 0) { eTR = tr; ePDM = pdm; eNDM = ndm; }
   else { eTR += a * (tr - eTR); ePDM += a * (pdm - ePDM); eNDM += a * (ndm - eNDM); }
   if(eTR > 0)
     {
      double pdi = 100.0 * ePDM / eTR, ndi = 100.0 * eNDM / eTR;
      if(pdi + ndi > 0)
        {
         double dx = 100.0 * MathAbs(pdi - ndi) / (pdi + ndi);
         if(!dx_init) { eDX = dx; dx_init = true; }
         else eDX += a * (dx - eDX);
        }
     }
   adx_prev = dx_init ? eDX : EMPTY_VALUE;
   prevH = blkH; prevL = blkL; prevC = blkC; adx_n++;
  }

// last-hour range compared with its 5-day median (7200 bars, needs 1440)
double RangeRatio(int t)
  {
   if(RG[IX(t)] == EMPTY_VALUE) return EMPTY_VALUE;
   static double v[];
   ArrayResize(v, 7200);
   int n = 0;
   int from = MathMax(0, t - 7199);
   for(int i = from; i <= t; i++)
     {
      double r = RG[IX(i)];
      if(r != EMPTY_VALUE) v[n++] = r;
     }
   if(n < 1440) return EMPTY_VALUE;
   ArrayResize(v, n);
   ArraySort(v);
   double med = (n % 2 == 1) ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
   return med > 0 ? RG[IX(t)] / med : EMPTY_VALUE;
  }

// the backtest filters, as known at bar t
bool Keep(int t, int d)
  {
   double r = Rr(t);
   if(d == 1 && r < 50) return false;
   if(d == -1 && r > 50) return false;
   MqlDateTime dt; TimeToStruct(Tt(t), dt);
   if(dt.hour == 15 || dt.hour == 23) return false;
   double rr = RangeRatio(t);
   if(rr != EMPTY_VALUE && rr < 0.6) return false;
   double ad = ADXB[IX(t)];
   if(ad != EMPTY_VALUE && ad > 25 && ad <= 35) return false;
   return true;
  }

// 3 micro inside SMA 10 at bar t (buy: 3 rising bullish candles, all closes above the SMA)
bool Micro3(int t, int d)
  {
   if(t < 12) return false;
   int a = t - 2, b = t - 1, e = t;
   if(Mm(a) == EMPTY_VALUE) return false;
   double mxma = MathMax(Mm(a), MathMax(Mm(b), Mm(e)));
   double mnma = MathMin(Mm(a), MathMin(Mm(b), Mm(e)));
   if(d == 1)
      return Cc(a) > Oo(a) && Cc(b) > Oo(b) && Cc(e) > Oo(e) && Cc(b) > Cc(a) && Cc(e) > Cc(b) &&
             MathMin(Cc(a), MathMin(Cc(b), Cc(e))) > mxma;
   return Cc(a) < Oo(a) && Cc(b) < Oo(b) && Cc(e) < Oo(e) && Cc(b) < Cc(a) && Cc(e) < Cc(b) &&
          MathMax(Cc(a), MathMax(Cc(b), Cc(e))) < mnma;
  }

//+------------------------------------------------------------------+
//| swings                                                           |
//+------------------------------------------------------------------+
struct Swing { int kind; double price; int index; int conf; };   // kind +1 high, -1 low

class CRsiSwings
  {
public:
   bool   takeout;
   int    state;          // 0 none, 1 looking for a high, -1 looking for a low
   double extp;
   int    exti;
   bool   seen;
   Swing  last;
   bool   has_last;
   Swing  out[4];
   int    nout;
   void   Init(bool to) { takeout = to; state = 0; has_last = false; nout = 0; seen = false; }
   void   Push(int kind, double p, int idx, int conf)
     {
      last.kind = kind; last.price = p; last.index = idx; last.conf = conf; has_last = true;
      out[nout] = last; nout++;
     }
   void   Step(int t)
     {
      nout = 0;
      double h = Hh(t), l = Ll(t), r = Rr(t);
      if(state == 0)
        {
         if(r >= HI_LV) { state = 1; extp = h; exti = t; seen = true; }
         else if(r <= LO_LV) { state = -1; extp = l; exti = t; seen = true; }
         return;
        }
      if(state == 1)
        {
         if(takeout && has_last && last.kind == -1 && l < last.price && exti < t)
           {
            int a = last.index + 1, hi_i = a; double mx = Hh(a);
            for(int i = a + 1; i <= t; i++) if(Hh(i) > mx) { mx = Hh(i); hi_i = i; }
            if(hi_i < t) { Push(1, mx, hi_i, t); state = -1; extp = l; exti = t; seen = true; return; }
           }
         if(h > extp) { extp = h; exti = t; }
         if(r >= HI_LV) seen = true;
         if(r <= LO_LV && seen)
           {
            Push(1, extp, exti, t);
            int k = exti; double mn = Ll(exti);
            for(int i = exti + 1; i <= t; i++) if(Ll(i) < mn) { mn = Ll(i); k = i; }
            state = -1; extp = mn; exti = k; seen = true;
           }
        }
      else
        {
         if(takeout && has_last && last.kind == 1 && h > last.price && exti < t)
           {
            int a = last.index + 1, lo_i = a; double mn = Ll(a);
            for(int i = a + 1; i <= t; i++) if(Ll(i) < mn) { mn = Ll(i); lo_i = i; }
            if(lo_i < t) { Push(-1, mn, lo_i, t); state = 1; extp = h; exti = t; seen = true; return; }
           }
         if(l < extp) { extp = l; exti = t; }
         if(r <= LO_LV) seen = true;
         if(r >= HI_LV && seen)
           {
            Push(-1, extp, exti, t);
            int k = exti; double mx = Hh(exti);
            for(int i = exti + 1; i <= t; i++) if(Hh(i) > mx) { mx = Hh(i); k = i; }
            state = 1; extp = mx; exti = k; seen = true;
           }
        }
     }
  };

CRsiSwings engA;   // structure swings (takeout exception on)
CRsiSwings engB;   // main re-entry swings (plain)

// small pivots (5 each side) for the level G must sweep
int    pv5_lo_i[], pv5_hi_i[];
double pv5_lo_p[], pv5_hi_p[];
void AddPivot5(int t)
  {
   int i = t - MINOR_K;
   if(i < MINOR_K) return;
   double mx = Hh(i), mn = Ll(i);
   bool isH = true, isL = true;
   for(int j = i - MINOR_K; j <= i + MINOR_K; j++) { if(Hh(j) > mx) isH = false; if(Ll(j) < mn) isL = false; }
   if(isL) { int n = ArraySize(pv5_lo_i); ArrayResize(pv5_lo_i, n + 1, 1000); ArrayResize(pv5_lo_p, n + 1, 1000); pv5_lo_i[n] = i; pv5_lo_p[n] = mn; }
   if(isH) { int n = ArraySize(pv5_hi_i); ArrayResize(pv5_hi_i, n + 1, 1000); ArrayResize(pv5_hi_p, n + 1, 1000); pv5_hi_i[n] = i; pv5_hi_p[n] = mx; }
  }

// 3-candle pivots confirmed at bar t (pivot at t-3): high first, then low (as in the backtest)
Swing x3[2]; int nx3 = 0;
void Pivots3(int t)
  {
   nx3 = 0;
   int i = t - 3;
   if(i < 3) return;
   double mx = Hh(i), mn = Ll(i);
   bool isH = true, isL = true;
   for(int j = i - 3; j <= i + 3; j++) { if(Hh(j) > mx) isH = false; if(Ll(j) < mn) isL = false; }
   if(isH) { x3[nx3].kind = 1;  x3[nx3].price = mx; x3[nx3].index = i; x3[nx3].conf = t; nx3++; }
   if(isL) { x3[nx3].kind = -1; x3[nx3].price = mn; x3[nx3].index = i; x3[nx3].conf = t; nx3++; }
  }

//+------------------------------------------------------------------+
//| main setups (find_signals with the takeout structure)            |
//+------------------------------------------------------------------+
struct MainSetup
  {
   bool   active;
   int    d;
   bool   hasE, hasF, hasG, hasH, hasEp;
   double e, f, g, h, e_pending;
   int    start, h_conf, f_idx, g_idx;
   bool   cont;
  };
MainSetup setup_[2];   // [0] buy, [1] sell
int SI(int d) { return d == 1 ? 0 : 1; }

struct Track
  {
   bool   hasLvl, hasBase, hasPull, hasA;
   double lvl, base, pull, a;
   int    cnt;
  };
Track trk[2];
Swing known[];   // last swings of engine A
int   boss = 0;

struct MainSignal { bool ok; int d; int bar; double entry, g, f; bool with_boss; };

void NewSetup(int d, bool hasE, double e, bool hasF, double f, int start, int f_idx, bool cont)
  {
   MainSetup s; ZeroMemory(s);
   s.active = true; s.d = d; s.hasE = hasE; s.e = e; s.hasF = hasF; s.f = f; s.start = start; s.f_idx = f_idx; s.cont = cont;
   s.h_conf = -1; s.g_idx = -1;
   setup_[SI(d)] = s;
  }

double LevelToSweep(MainSetup &st)
  {
   if(st.f_idx < 0) return st.e;
   if(st.d == 1)
     {
      double lv = 0; bool got = false;
      for(int j = ArraySize(pv5_lo_i) - 1; j >= 0; j--) if(pv5_lo_i[j] < st.f_idx) { lv = pv5_lo_p[j]; got = true; break; }
      return got ? MathMax(lv, st.e) : st.e;
     }
   double lv = 0; bool got = false;
   for(int j = ArraySize(pv5_hi_i) - 1; j >= 0; j--) if(pv5_hi_i[j] < st.f_idx) { lv = pv5_hi_p[j]; got = true; break; }
   return got ? MathMin(lv, st.e) : st.e;
  }

// step 1: wick triggers on bar t, levels known before this bar
void MainTriggers(int t, MainSignal &sig)
  {
   sig.ok = false;
   for(int k = 0; k < 2; k++)
     {
      int d = k == 0 ? 1 : -1;
      if(!setup_[k].active) continue;
      if(t - setup_[k].start > SETUP_BARS) { setup_[k].active = false; continue; }
      if(setup_[k].hasG && setup_[k].hasH && t > setup_[k].h_conf)
        {
         bool beyond_g = d == 1 ? Ll(t) < setup_[k].g + TOL : Hh(t) > setup_[k].g - TOL;
         bool broke_h  = d == 1 ? Hh(t) > setup_[k].h : Ll(t) < setup_[k].h;
         if(beyond_g && !broke_h) { setup_[k].active = false; continue; }   // G swept before H broke: invalid
         if(broke_h)
           {
            sig.ok = true; sig.d = d; sig.bar = t; sig.entry = setup_[k].h; sig.g = setup_[k].g; sig.f = setup_[k].f;
            sig.with_boss = (boss == d);
            setup_[k].active = false;
            if(boss == d) NewSetup(d, false, 0, false, 0, t, -1, true);
           }
        }
     }
  }

// new completed structures (A, E, F) for the zones
struct ALevel { int d; double A, E, F; int t0; };
ALevel newA[4]; int nNewA = 0;

// step 2: swings of engine A confirmed at bar t
void MainSwing(int t, Swing &s)
  {
   int n = ArraySize(known);
   if(n >= 50) { ArrayRemove(known, 0, 1); n--; }
   ArrayResize(known, n + 1); known[n] = s; n++;
   for(int k = 0; k < 2; k++)
     {
      if(!setup_[k].active) continue;
      int d = k == 0 ? 1 : -1;
      int g_kind = d == 1 ? -1 : 1, h_kind = -g_kind;
      if(!setup_[k].hasF)
        {
         if(s.kind == h_kind && n >= 2)
           { setup_[k].f = s.price; setup_[k].hasF = true; setup_[k].e = known[n - 2].price; setup_[k].hasE = true; setup_[k].start = t; setup_[k].f_idx = s.index; }
         continue;
        }
      setup_[k].start = t;
      if(s.kind == g_kind)
        {
         if(!setup_[k].hasG)
           {
            double lv = LevelToSweep(setup_[k]);
            bool swept = d == 1 ? s.price < lv + TOL : s.price > lv - TOL;
            if(swept) { setup_[k].g = s.price; setup_[k].hasG = true; setup_[k].g_idx = s.index; }
            else { setup_[k].e_pending = s.price; setup_[k].hasEp = true; }
           }
        }
      else if(s.kind == h_kind && setup_[k].hasG) { setup_[k].h = s.price; setup_[k].hasH = true; setup_[k].h_conf = t; }
      else if(s.kind == h_kind && setup_[k].hasEp)
        {
         bool higher = d == 1 ? s.price > setup_[k].f : s.price < setup_[k].f;
         if(higher)
           { setup_[k].e = setup_[k].e_pending; setup_[k].f = s.price; setup_[k].hasEp = false; setup_[k].start = t; setup_[k].f_idx = s.index; }
        }
     }
   // takeout structure
   for(int k = 0; k < 2; k++)
     {
      int d = k == 0 ? 1 : -1;
      int ext_kind = d == 1 ? 1 : -1;
      if(s.kind == ext_kind)
        {
         if(!trk[k].hasLvl)
           {
            trk[k].lvl = s.price; trk[k].hasLvl = true; trk[k].hasPull = false;
            trk[k].hasA = (n >= 2 && known[n - 2].kind != s.kind);
            if(trk[k].hasA) trk[k].a = known[n - 2].price;
           }
         else if(d == 1 ? s.price > trk[k].lvl : s.price < trk[k].lvl)
           {
            trk[k].cnt++;
            if(trk[k].hasPull) { trk[k].base = trk[k].pull; trk[k].hasBase = true; }
            trk[k].lvl = s.price; trk[k].hasPull = false;
            if(trk[k].cnt == 2 && trk[k].hasA && trk[k].hasBase && nNewA < 4)
              { newA[nNewA].d = d; newA[nNewA].A = trk[k].a; newA[nNewA].E = trk[k].base; newA[nNewA].F = s.price; newA[nNewA].t0 = t; nNewA++; }
            if(trk[k].cnt >= 2 && trk[k].hasBase)
              {
               bool new_boss = boss != d;
               boss = d;
               if(!setup_[k].active || !setup_[k].hasG || new_boss)
                  NewSetup(d, true, trk[k].base, true, s.price, t, s.index, false);
              }
           }
        }
      else
        {
         if(!trk[k].hasPull) { trk[k].pull = s.price; trk[k].hasPull = true; }
         else trk[k].pull = d == 1 ? MathMin(trk[k].pull, s.price) : MathMax(trk[k].pull, s.price);
         if(trk[k].hasBase && (d == 1 ? s.price < trk[k].base : s.price > trk[k].base))
           { trk[k].cnt = 0; trk[k].base = s.price; trk[k].hasPull = false; trk[k].hasLvl = false; }
        }
     }
  }

//+------------------------------------------------------------------+
//| 3-micro re-entry waits (after a taken losing trade)              |
//+------------------------------------------------------------------+
struct M3Wait { int d; int from; int until; int type; };
M3Wait m3w[];
void AddM3(int d, int exitBar, int type)
  {
   int n = ArraySize(m3w); ArrayResize(m3w, n + 1, 100);
   m3w[n].d = d; m3w[n].from = exitBar; m3w[n].until = exitBar + M3_BARS; m3w[n].type = type;
  }

//+------------------------------------------------------------------+
//| market entries decided at a bar close (3 micro, MZ)              |
//+------------------------------------------------------------------+
struct MktOrder { int d; int type; double risk; int bar; string tag; };
MktOrder mkt[];
void QueueMarket(int d, int type, double risk, int bar, string tag)
  {
   int n = ArraySize(mkt); ArrayResize(mkt, n + 1, 50);
   mkt[n].d = d; mkt[n].type = type; mkt[n].risk = risk; mkt[n].bar = bar; mkt[n].tag = tag;
  }

//+------------------------------------------------------------------+
//| main trade track (virtual, as in the backtest) + RSI re-entries  |
//+------------------------------------------------------------------+
struct MainPos { bool open; int d; double entry, sl, tp, tp0; int t; int n; bool taken; };
struct MainWait { bool on; int d; double target; int n; bool hasLvl; double lvl; bool seen; };
MainPos  mpos;
MainWait mwait;
datetime mwait_armed = 0;
double   MainTargetSize(double f, double g)
  {
   double size = MathAbs(f - g);
   return size < MAIN_TP ? MathMax(5.0, MathFloor(size)) : MAIN_TP;
  }

void MainStep(int t, MainSignal &sig, Swing &bsw[], int nb)
  {
   bool use = sig.ok && sig.with_boss && t >= 600;
   // manage the open trade
   if(mpos.open)
     {
      int d = mpos.d;
      bool hit_sl = d == 1 ? Ll(t) <= mpos.sl : Hh(t) + Sp(t) >= mpos.sl;
      bool hit_tp = (d == 1 ? Hh(t) >= mpos.tp : Ll(t) + Sp(t) <= mpos.tp) && t > mpos.t;
      double px = 0; int why = 0;
      if(hit_sl) { bool gap = d == 1 ? Oo(t) < mpos.sl : Oo(t) + Sp(t) > mpos.sl; px = gap ? Oo(t) : mpos.sl; why = 1; }
      else if(hit_tp) { px = mpos.tp; why = 2; }
      else if(use && sig.d != d) { px = sig.entry; why = 3; }
      if(why != 0)
        {
         double pnl = (px - mpos.entry) * d;
         if(pnl < 0 && mpos.taken) AddM3(d, t, T_M3C);
         if(why == 1 && mpos.n < MAIN_MAXRE)
           { mwait.on = true; mwait.d = d; mwait.target = mpos.tp0; mwait.n = mpos.n + 1; mwait.hasLvl = false; mwait.seen = false; }
         mpos.open = false;
        }
     }
   // a new signal opens a trade
   if(!mpos.open && use)
     {
      int d = sig.d;
      double entry = d == 1 ? MathMax(Oo(t), sig.entry) + Sp(t) : MathMin(Oo(t), sig.entry);
      double tp = MainTargetSize(sig.f, sig.g);
      mpos.open = true; mpos.d = d; mpos.entry = entry; mpos.sl = entry - d * MAIN_SL; mpos.tp = entry + d * tp;
      mpos.tp0 = mpos.tp; mpos.t = t; mpos.n = 0; mpos.taken = Keep(t, d);
      mwait.on = false;
      if(InpLog && g_live) PrintFormat("CFX main %s signal at %.2f (target $%.0f)%s", d == 1 ? "BUY" : "SELL", sig.entry, tp, mpos.taken ? "" : " - filtered");
      return;
     }
   // waiting to re-enter: a high then a low, then price takes out that high
   if(mwait.on && !mpos.open)
     {
      int d = mwait.d;
      if(mwait.hasLvl && mwait.seen)
        {
         bool broke = d == 1 ? Hh(t) >= mwait.lvl : Ll(t) <= mwait.lvl;
         if(broke)
           {
            double entry = d == 1 ? MathMax(Oo(t), mwait.lvl) + Sp(t) : MathMin(Oo(t), mwait.lvl);
            double target = mwait.target + d * MAIN_EXTRA;
            if((target - entry) * d > 0)
              {
               mpos.open = true; mpos.d = d; mpos.entry = entry; mpos.sl = entry - d * MAIN_SL; mpos.tp = target;
               mpos.tp0 = mwait.target; mpos.t = t; mpos.n = mwait.n; mpos.taken = Keep(t, d);
              }
            mwait.on = false;
           }
        }
      if(mwait.on)
         for(int i = 0; i < nb; i++)
           {
            if(bsw[i].kind == (d == 1 ? 1 : -1)) { mwait.lvl = bsw[i].price; mwait.hasLvl = true; mwait.seen = false; }
            else if(mwait.hasLvl) { mwait.seen = true; mwait_armed = Tt(t); }
           }
     }
  }

//+------------------------------------------------------------------+
//| zone structures (E-A and F-E), zone re-entries, MZ               |
//+------------------------------------------------------------------+
struct VTrade { bool open; double entry, stop, target, risk; int t; bool taken; };

struct MZCand { double G; int from; int until; bool on; };

class CZone
  {
public:
   int    id;
   int    d;
   int    region;          // 0 E-A, 1 F-E
   double A, E, F, depth;
   int    t0, endBar;
   bool   searching;
   int    taken;
   int    searchFrom;
   bool   hasG, hasH, iok, armed;
   double G, Hl;
   int    armConf;
   VTrade tr;
   // zone re-entry
   bool   reOn;
   int    reFrom, reStop, reV0;
   bool   reHasLvl, reSeen, reArmed;
   double reLvl;
   int    reArmConf;
   VTrade rt;
   // MZ (E-A only)
   int    mzTaken;
   MZCand mz[];

   bool InZone(double p)
     {
      if(region == 0) return (E - p) * d > 0 && (E - p) * d < depth;
      return (F - p) * d > 0 && (F - p) * d < (F - E) * d;
     }
   bool Beyond(double p, double lvl) { return d == 1 ? p < lvl : p > lvl; }
  };

CZone *zones[];
int    zone_seq = 0;
datetime mz_seen_t[]; int mz_seen_d[];

bool MZSeen(datetime t, int d)
  {
   for(int i = ArraySize(mz_seen_t) - 1; i >= 0 && i >= ArraySize(mz_seen_t) - 200; i--)
      if(mz_seen_t[i] == t && mz_seen_d[i] == d) return true;
   return false;
  }
void MZMark(datetime t, int d)
  {
   int n = ArraySize(mz_seen_t); ArrayResize(mz_seen_t, n + 1, 500); ArrayResize(mz_seen_d, n + 1, 500);
   mz_seen_t[n] = t; mz_seen_d[n] = d;
  }

void AddZones(ALevel &a)
  {
   if((a.E - a.A) * a.d <= 0) return;
   for(int region = 0; region < 2; region++)
     {
      if(region == 1 && (a.F - a.E) * a.d <= 0) continue;
      CZone *z = new CZone;
      z.id = ++zone_seq; z.d = a.d; z.region = region; z.A = a.A; z.E = a.E; z.F = a.F; z.depth = (a.E - a.A) * a.d;
      z.t0 = a.t0; z.endBar = a.t0 + ZONE_BARS; z.searching = true; z.taken = 0; z.searchFrom = a.t0;
      z.hasG = false; z.hasH = false; z.iok = false; z.armed = false; z.tr.open = false;
      z.reOn = false; z.rt.open = false; z.mzTaken = 0;
      int n = ArraySize(zones); ArrayResize(zones, n + 1, 100); zones[n] = z;
     }
  }

// virtual exit check for a zone-type trade on bar t (stop includes the entry bar, target from the next bar)
int VExit(VTrade &v, int d, int t)
  {
   if(!v.open) return 0;
   if(d == 1 ? Ll(t) <= v.stop : Hh(t) + Sp(t) >= v.stop) return -1;
   if(t > v.t && (d == 1 ? Hh(t) >= v.target : Ll(t) + Sp(t) <= v.target)) return 1;
   return 0;
  }

void ZoneOpen(CZone *z, VTrade &v, int t, double level, double ext)
  {
   int d = z.d;
   double entry = level + (d == 1 ? Sp(t) : 0);
   double risk = MathMax(MathAbs(entry - ext) + 1.0, RISK_MIN);
   v.open = true; v.entry = entry; v.risk = risk; v.stop = entry - d * risk; v.target = entry + d * 2 * risk; v.t = t;
   v.taken = Keep(t, d);
  }

void ZoneStep(CZone *z, int t)
  {
   int d = z.d;
   // 1) open zone trade
   if(z.tr.open)
     {
      int r = (t > z.tr.t) ? VExit(z.tr, d, t) : 0;
      if(r != 0)
        {
         z.tr.open = false; z.taken++; z.searchFrom = t;
         if(r < 0)
           {
            if(z.tr.taken) AddM3(d, t, z.region == 0 ? T_M3C : T_M3FE);
            z.reOn = true; z.reFrom = t; z.reV0 = t; z.reStop = MathMax(z.endBar, t + ZRE_BARS);
            z.reHasLvl = false; z.reSeen = false; z.reArmed = false;
           }
         if(z.taken >= ZONE_PER) z.searching = false;
        }
     }
   else if(z.searching)
     {
      if(nx3 > 0)
        {
         z.armed = false;   // the break window ends before a new swing's bar
         if(t >= z.endBar) z.searching = false;
         else if(t > z.searchFrom)
            for(int i = 0; i < nx3 && z.searching; i++)
              {
               Swing x = x3[i];
               int lo = d == 1 ? -1 : 1;
               if(!z.hasG) { if(x.kind == lo && z.InZone(x.price)) { z.hasG = true; z.G = x.price; } continue; }
               if(x.kind == lo)
                 {
                  if(z.Beyond(x.price, z.G))
                    {
                     if(z.InZone(x.price)) { z.G = x.price; z.hasH = false; z.iok = false; }
                     else { z.searching = false; break; }   // left the zone: this structure is done
                    }
                  else if(z.hasH) z.iok = true;
                 }
               else { z.hasH = true; z.Hl = x.price; z.iok = false; }
               if(z.hasH && z.iok) { z.armed = true; z.armConf = t; }
               else z.armed = false;
              }
        }
      else if(z.armed && t > z.armConf)
        {
         if(t >= z.endBar) { z.armed = false; z.searching = false; }
         else if(d == 1 ? Ll(t) < z.G : Hh(t) > z.G) z.armed = false;
         else if(d == 1 ? Hh(t) > z.Hl : Ll(t) < z.Hl)
           {
            ZoneOpen(z, z.tr, t, z.Hl, z.G);
            z.armed = false; z.hasG = false; z.hasH = false; z.iok = false;
            if(InpLog && g_live) PrintFormat("CFX zone %s #%d %s at %.2f risk $%.1f%s", z.region == 0 ? "E-A" : "F-E", z.id, d == 1 ? "BUY" : "SELL", z.tr.entry, z.tr.risk, z.tr.taken ? "" : " - filtered");
            int r = VExit(z.tr, d, t);   // stop on the entry bar
            if(r < 0)
              {
               z.tr.open = false; z.taken++; z.searchFrom = t;
               if(z.tr.taken) AddM3(d, t, z.region == 0 ? T_M3C : T_M3FE);
               z.reOn = true; z.reFrom = t; z.reV0 = t; z.reStop = MathMax(z.endBar, t + ZRE_BARS);
               z.reHasLvl = false; z.reSeen = false; z.reArmed = false;
               if(z.taken >= ZONE_PER) z.searching = false;
              }
           }
        }
     }
   // 2) zone re-entry (one, after a zone stop)
   if(z.rt.open)
     {
      int r = (t > z.rt.t) ? VExit(z.rt, d, t) : 0;
      if(r != 0)
        {
         z.rt.open = false;
         if(r < 0 && z.rt.taken) AddM3(d, t, z.region == 0 ? T_M3C : T_M3FE);
        }
     }
   else if(z.reOn)
     {
      if(t >= z.reStop) z.reOn = false;
      else if(nx3 > 0)
        {
         z.reArmed = false;
         if(t > z.reFrom)
            for(int i = 0; i < nx3; i++)
              {
               if(x3[i].kind == (d == 1 ? 1 : -1)) { z.reLvl = x3[i].price; z.reHasLvl = true; z.reSeen = false; }
               else if(z.reHasLvl) z.reSeen = true;
               z.reArmed = z.reHasLvl && z.reSeen; z.reArmConf = t;
              }
        }
      else if(z.reArmed && t > z.reArmConf)
        {
         if(d == 1 ? Hh(t) > z.reLvl : Ll(t) < z.reLvl)
           {
            double ext = d == 1 ? Ll(z.reV0) : Hh(z.reV0);
            for(int i = z.reV0; i <= t; i++) ext = d == 1 ? MathMin(ext, Ll(i)) : MathMax(ext, Hh(i));
            ZoneOpen(z, z.rt, t, z.reLvl, ext);
            z.reOn = false;
            int r = VExit(z.rt, d, t);
            if(r < 0) { z.rt.open = false; if(z.rt.taken) AddM3(d, t, z.region == 0 ? T_M3C : T_M3FE); }
           }
        }
     }
   // 3) MZ: G in the E-A zone at RSI 32, then 3 micro
   if(z.region == 0)
     {
      for(int i = 0; i < nx3; i++)
        {
         Swing x = x3[i];
         if(x.kind != (d == 1 ? -1 : 1) || x.conf <= z.t0 || x.conf >= z.t0 + ZONE_BARS || !z.InZone(x.price)) continue;
         double rx = Rr(x.index);
         for(int j = x.index - 3; j <= x.index + 3; j++) rx = d == 1 ? MathMin(rx, Rr(j)) : MathMax(rx, Rr(j));
         if(d == 1 ? rx > MZ_RSI : rx < 100 - MZ_RSI) continue;
         int n = ArraySize(z.mz); ArrayResize(z.mz, n + 1, 20);
         z.mz[n].G = x.price; z.mz[n].from = t; z.mz[n].until = t + MZ_WAIT; z.mz[n].on = true;
        }
      for(int i = 0; i < ArraySize(z.mz); i++)
        {
         if(!z.mz[i].on) continue;
         if(z.mzTaken >= MZ_PER || t >= z.mz[i].until) { z.mz[i].on = false; continue; }
         if(d == 1 ? Ll(t) < z.mz[i].G : Hh(t) > z.mz[i].G) { z.mz[i].on = false; continue; }
         if(Micro3(t, d))
           {
            z.mz[i].on = false;
            if(MZSeen(Tt(t), d) || !Keep(t, d)) continue;
            MZMark(Tt(t), d); z.mzTaken++;
            double entry = Cc(t) + (d == 1 ? Sp(t) : 0);
            double risk = MathMax(MathAbs(entry - z.mz[i].G) + 1.0, RISK_MIN);
            if(g_live) QueueMarket(d, T_MZ, risk, t, "CFX ZM");
           }
        }
      // drop finished candidates
      int w = 0;
      for(int i = 0; i < ArraySize(z.mz); i++) if(z.mz[i].on) z.mz[w++] = z.mz[i];
      ArrayResize(z.mz, w, 20);
     }
  }

int Last();
bool ZoneDead(CZone *z)
  {
   bool mzOn = (z.region == 0 && ArraySize(z.mz) > 0) || (z.region == 0 && z.mzTaken < MZ_PER && Last() < z.t0 + ZONE_BARS);
   return !z.searching && !z.tr.open && !z.reOn && !z.rt.open && !mzOn;
  }
int Last() { return N - 1; }

//+------------------------------------------------------------------+
//| the bar engine                                                    |
//+------------------------------------------------------------------+
void ProcessBar(int t)
  {
   UpdIndicators(t);
   engA.Step(t);
   engB.Step(t);
   AddPivot5(t);
   Pivots3(t);
   // main
   MainSignal sig; MainTriggers(t, sig);
   nNewA = 0;
   for(int i = 0; i < engA.nout; i++) MainSwing(t, engA.out[i]);
   Swing bsw[]; ArrayResize(bsw, engB.nout);
   for(int i = 0; i < engB.nout; i++) bsw[i] = engB.out[i];
   MainStep(t, sig, bsw, engB.nout);
   // zones
   for(int i = 0; i < ArraySize(zones); i++) ZoneStep(zones[i], t);
   // 3-micro waits (checked before new waits from this bar are added... they need a later bar anyway)
   int w = 0;
   for(int i = 0; i < ArraySize(m3w); i++)
     {
      bool keepw = true;
      if(t > m3w[i].from && t < m3w[i].until)
        {
         int d = m3w[i].d;
         if(Micro3(t, d))
           {
            keepw = false;
            if(Keep(t, d))
              {
               double entry = Cc(t) + (d == 1 ? Sp(t) : 0);
               double ext = d == 1 ? Ll(m3w[i].from) : Hh(m3w[i].from);
               for(int j = m3w[i].from; j <= t; j++) ext = d == 1 ? MathMin(ext, Ll(j)) : MathMax(ext, Hh(j));
               double risk = MathMax(MathAbs(entry - ext) + 1.0, RISK_MIN);
               if(g_live) QueueMarket(d, m3w[i].type, risk, t, "CFX 3M");
              }
           }
        }
      else if(t >= m3w[i].until) keepw = false;
      if(keepw) m3w[w++] = m3w[i];
     }
   ArrayResize(m3w, w, 100);
   // new structures from this bar
   for(int i = 0; i < nNewA; i++) AddZones(newA[i]);
   // drop finished zones
   int zw = 0;
   for(int i = 0; i < ArraySize(zones); i++)
     {
      if(ZoneDead(zones[i])) { delete zones[i]; continue; }
      zones[zw++] = zones[i];
     }
   ArrayResize(zones, zw, 100);
  }

//+------------------------------------------------------------------+
//| account modes, lots, protection                                  |
//+------------------------------------------------------------------+
int    g_mask = T_ALL;
int    g_maxOpen = 999;
double g_cap = 1e9;
bool   g_dedupe = false;
string g_modeName = "";
bool   g_dayStop = false, g_hardStop = false;
int    g_day = -1;
double g_dayStartEquity = 0;

void SetMode()
  {
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_mask = T_ALL; g_maxOpen = 999; g_cap = 1e9; g_dedupe = false; g_modeName = "full";
   if(InpAccount == CFX_PROP) return;
   if(bal < 200)       { g_mask = T_C | T_M3C | T_MZ; g_maxOpen = 1; g_cap = 10; g_modeName = "$100 mode"; }
   else if(bal < 400)  { g_mask = T_C | T_M3C | T_MZ | T_FLIP; g_maxOpen = 1; g_cap = 15; g_modeName = "$200 mode"; }
   else if(bal < 1000) { g_mask = T_C | T_FLIP; g_dedupe = true; g_modeName = "$400 mode"; }
  }

int LossesInARow()
  {
   if(!HistorySelect(TimeCurrent() - 90 * 86400, TimeCurrent())) return 0;
   int n = 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(tk, DEAL_SYMBOL) != _Symbol) continue;
      if(HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      double p = HistoryDealGetDouble(tk, DEAL_PROFIT) + HistoryDealGetDouble(tk, DEAL_SWAP) + HistoryDealGetDouble(tk, DEAL_COMMISSION);
      if(p < 0) n++; else break;
     }
   return n;
  }

double NormLot(double lot)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lot = MathFloor(lot / step + 1e-9) * step;
   lot = MathMax(mn, MathMin(mx, lot));
   return NormalizeDouble(lot, 2);
  }

double LotUnits(double bal)
  {
   double u;
   if(bal <= 10000) u = MathFloor(bal / 2000.0);
   else if(bal <= 50000) u = 5 + MathFloor((bal - 10000) / 4000.0);
   else u = 15 + MathFloor((bal - 50000) / 8000.0);
   return MathMax(1.0, u);
  }

double LotNow()
  {
   if(InpFixedLot > 0) return NormLot(InpFixedLot);
   if(InpAccount == CFX_PROP) return NormLot(InpPropStart / 1000.0 * PROP_LOT_PER_1K);
   double units = LotUnits(AccountInfoDouble(ACCOUNT_BALANCE));
   if(LOT_HALF_AFTER > 0 && LossesInARow() >= LOT_HALF_AFTER) units = MathMax(1.0, MathFloor(units / 2));
   return NormLot(units * 0.01);
  }

int CountOpen()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol) n++;
     }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(OrderGetInteger(ORDER_MAGIC) == InpMagic && OrderGetString(ORDER_SYMBOL) == _Symbol) n++;
     }
   return n;
  }

bool MarginOk(int d, double lot, double price)
  {
   double m = 0;
   if(!OrderCalcMargin(d == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, lot, price, m)) return false;
   return m <= AccountInfoDouble(ACCOUNT_MARGIN_FREE);
  }

void CloseAll(string why)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol) trade.PositionClose(tk);
     }
   DeletePendings("");
   Print("CFX: closed everything - ", why);
  }

void Protect()
  {
   if(InpAccount != CFX_PROP) return;
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(dt.day_of_year != g_day) { g_day = dt.day_of_year; g_dayStartEquity = MathMax(eq, AccountInfoDouble(ACCOUNT_BALANCE)); g_dayStop = false; }
   if(!g_hardStop && eq <= InpPropStart * (1.0 - InpPropMaxStop / 100.0))
     { g_hardStop = true; CloseAll("prop max drawdown stop reached"); }
   if(!g_dayStop && eq <= g_dayStartEquity - InpPropStart * InpPropDailyStop / 100.0)
     { g_dayStop = true; CloseAll("prop daily loss stop reached"); }
  }

bool CanTrade() { return InpTrade && g_live && !g_dayStop && !g_hardStop; }

//+------------------------------------------------------------------+
//| orders                                                            |
//+------------------------------------------------------------------+
struct Want { string key; int d; int type; double price, sl, tp, risk; datetime armed; };
string   fill_key[];
datetime fill_time[];
void RegisterFill(string key, datetime t)
  {
   int n = ArraySize(fill_key);
   for(int i = 0; i < n; i++) if(fill_key[i] == key) { fill_time[i] = t; return; }
   ArrayResize(fill_key, n + 1, 100); ArrayResize(fill_time, n + 1, 100); fill_key[n] = key; fill_time[n] = t;
  }
// a setup that already got a real fill since it was armed must not be placed again
bool FilledSince(string key, datetime armed)
  {
   for(int i = 0; i < ArraySize(fill_key); i++) if(fill_key[i] == key) return fill_time[i] >= armed;
   return false;
  }
Want want[];
void AddWant(string key, int d, int type, double price, double sl, double tp, double risk, datetime armed)
  {
   if(FilledSince(key, armed)) return;
   int n = ArraySize(want); ArrayResize(want, n + 1, 50);
   want[n].armed = armed; want[n].key = key; want[n].d = d; want[n].type = type; want[n].price = price; want[n].sl = sl; want[n].tp = tp; want[n].risk = risk;
  }

void DeletePendings(string keepPrefix)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic || OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      trade.OrderDelete(tk);
     }
  }

// pending stop orders for every armed setup (filters checked at the last closed bar, next bar's hour)
void BuildWants(int t)
  {
   ArrayResize(want, 0);
   double sp = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   // main first entry
   for(int k = 0; k < 2; k++)
     {
      int d = k == 0 ? 1 : -1;
      if(!setup_[k].active || !setup_[k].hasG || !setup_[k].hasH || boss != d) continue;
      if(mpos.open && mpos.d == d) continue;
      double entry = setup_[k].h + (d == 1 ? sp : 0);
      double tp = MainTargetSize(setup_[k].f, setup_[k].g);
      AddWant(StringFormat("CFX M%d", d), d, T_MAIN, entry, entry - d * MAIN_SL, entry + d * tp, MAIN_SL, Tt(setup_[k].h_conf));
     }
   // main RSI re-entry
   if(mwait.on && !mpos.open && mwait.hasLvl && mwait.seen)
     {
      int d = mwait.d;
      double entry = mwait.lvl + (d == 1 ? sp : 0);
      double target = mwait.target + d * MAIN_EXTRA;
      if((target - entry) * d > 0) AddWant("CFX R", d, T_MAINRE, entry, entry - d * MAIN_SL, target, MAIN_SL, mwait_armed);
     }
   // zones
   for(int i = 0; i < ArraySize(zones); i++)
     {
      CZone *z = zones[i];
      int d = z.d;
      if(z.armed && !z.tr.open)
        {
         double entry = z.Hl + (d == 1 ? sp : 0);
         double risk = MathMax(MathAbs(entry - z.G) + 1.0, RISK_MIN);
         AddWant(StringFormat("CFX %s%d", z.region == 0 ? "Z" : "F", z.id), d, z.region == 0 ? T_ZEA : T_ZFE, entry, entry - d * risk, entry + d * 2 * risk, risk, Tt(z.armConf));
        }
      if(z.reOn && z.reArmed && !z.rt.open)
        {
         double ext = d == 1 ? Ll(z.reV0) : Hh(z.reV0);
         for(int j = z.reV0; j <= t; j++) ext = d == 1 ? MathMin(ext, Ll(j)) : MathMax(ext, Hh(j));
         double entry = z.reLvl + (d == 1 ? sp : 0);
         double risk = MathMax(MathAbs(entry - ext) + 1.0, RISK_MIN);
         AddWant(StringFormat("CFX %sR%d", z.region == 0 ? "Z" : "F", z.id), d, z.region == 0 ? T_ZEARE : T_ZFERE, entry, entry - d * risk, entry + d * 2 * risk, risk, Tt(z.reArmConf));
        }
     }
  }

bool AllowedNow(int t, int d, int type, double risk)
  {
   if((g_mask & type) == 0) return false;
   if(risk > g_cap) return false;
   // filters as at the next bar (hour of the next minute)
   double r = Rr(t);
   if(d == 1 && r < 50) return false;
   if(d == -1 && r > 50) return false;
   MqlDateTime dt; TimeToStruct(Tt(t) + 60, dt);
   if(dt.hour == 15 || dt.hour == 23) return false;
   double rr = RangeRatio(t);
   if(rr != EMPTY_VALUE && rr < 0.6) return false;
   double ad = ADXB[IX(t)];
   if(ad != EMPTY_VALUE && ad > 25 && ad <= 35) return false;
   return true;
  }

void SyncOrders(int t)
  {
   if(!CanTrade()) { DeletePendings(""); return; }
   SetMode();
   BuildWants(t);
   // filter, dedupe, max open
   int open = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol) open++;
     }
   int slots = g_maxOpen - open;
   Want ok[]; int nok = 0;
   double lot = LotNow();
   for(int i = 0; i < ArraySize(want); i++)
     {
      if(nok >= slots) break;
      if(!AllowedNow(t, want[i].d, want[i].type, want[i].risk)) continue;
      bool dup = false;
      if(g_dedupe) for(int j = 0; j < nok; j++) if(ok[j].d == want[i].d && MathAbs(ok[j].price - want[i].price) < 0.02) dup = true;
      if(dup) continue;
      ArrayResize(ok, nok + 1); ok[nok++] = want[i];
     }
   // delete pendings that are no longer wanted, keep matching ones
   bool have[]; ArrayResize(have, nok); ArrayInitialize(have, false);
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic || OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      string c = OrderGetString(ORDER_COMMENT);
      double p = OrderGetDouble(ORDER_PRICE_OPEN);
      int found = -1;
      for(int j = 0; j < nok; j++) if(ok[j].key == c) { found = j; break; }
      if(found < 0 || MathAbs(p - ok[found].price) > 0.05) { trade.OrderDelete(tk); continue; }
      have[found] = true;
     }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double stopsLvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   for(int j = 0; j < nok; j++)
     {
      if(have[j]) continue;
      Want w = ok[j];
      double price = NormalizeDouble(w.price, digits), sl = NormalizeDouble(w.sl, digits), tp = NormalizeDouble(w.tp, digits);
      bool through = (w.d == 1 && price <= ask + stopsLvl) || (w.d == -1 && price >= bid - stopsLvl);
      if(through)
        {
         // v1.14: price is already past the level -> enter at market with the same stop and target,
         // unless price moved too far (more than half the risk) or is already at the stop/target
         double now = w.d == 1 ? ask : bid;
         double slip = (now - price) * w.d;
         if(slip > MKT_MAX_SLIP * w.risk) continue;
         if((now - sl) * w.d <= stopsLvl || (tp - now) * w.d <= stopsLvl) continue;
         if(!MarginOk(w.d, lot, now)) { if(InpLog) Print("CFX: not enough margin for ", w.key); continue; }
         bool rm = w.d == 1 ? trade.Buy(lot, _Symbol, 0, sl, tp, w.key) : trade.Sell(lot, _Symbol, 0, sl, tp, w.key);
         if(InpLog) PrintFormat("CFX %s market (price past level by $%.2f) %s", w.key, slip, rm ? "sent" : "FAILED");
         continue;
        }
      if(!MarginOk(w.d, lot, price)) { if(InpLog) Print("CFX: not enough margin for ", w.key); continue; }
      bool r = w.d == 1 ? trade.BuyStop(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, w.key)
                        : trade.SellStop(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, w.key);
      if(!r && InpLog) PrintFormat("CFX: pending %s failed (%d)", w.key, trade.ResultRetcode());
     }
  }

void SendMarkets()
  {
   if(!CanTrade()) { ArrayResize(mkt, 0); return; }
   SetMode();
   double lot = LotNow();
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   for(int i = 0; i < ArraySize(mkt); i++)
     {
      MktOrder m = mkt[i];
      if((g_mask & m.type) == 0 || m.risk > g_cap) continue;
      if(CountOpen() >= g_maxOpen) continue;
      double price = m.d == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(!MarginOk(m.d, lot, price)) { if(InpLog) Print("CFX: not enough margin for ", m.tag); continue; }
      double sl = NormalizeDouble(price - m.d * m.risk, digits), tp = NormalizeDouble(price + m.d * 2 * m.risk, digits);
      bool r = m.d == 1 ? trade.Buy(lot, _Symbol, 0, sl, tp, m.tag) : trade.Sell(lot, _Symbol, 0, sl, tp, m.tag);
      if(InpLog) PrintFormat("CFX %s %s lot %.2f risk $%.1f %s", m.tag, m.d == 1 ? "BUY" : "SELL", lot, m.risk, r ? "sent" : "FAILED");
     }
   ArrayResize(mkt, 0);
  }

// a new main trade closes the opposite main trade (the new trend leads)
void MainOpposite()
  {
   datetime newest = 0; int nd = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      string c = PositionGetString(POSITION_COMMENT);
      if(StringFind(c, "CFX M") != 0 && c != "CFX R") continue;
      datetime tm = (datetime)PositionGetInteger(POSITION_TIME);
      if(tm > newest) { newest = tm; nd = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1; }
     }
   if(nd == 0) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      string c = PositionGetString(POSITION_COMMENT);
      if(StringFind(c, "CFX M") != 0 && c != "CFX R") continue;
      int d = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      if(d != nd) trade.PositionClose(tk);
     }
  }

//+------------------------------------------------------------------+
//| flip: when a main / zone trade hits its stop, trade the other way |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || !g_live) return;
   ulong deal = trans.deal;
   if(!HistoryDealSelect(deal)) return;
   if(HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic || HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) return;
   if(HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_IN)
     { RegisterFill(HistoryDealGetString(deal, DEAL_COMMENT), (datetime)HistoryDealGetInteger(deal, DEAL_TIME)); return; }
   if(HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_OUT) return;
   if(HistoryDealGetInteger(deal, DEAL_REASON) != DEAL_REASON_SL) return;
   double outPrice = HistoryDealGetDouble(deal, DEAL_PRICE);
   long posId = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   if(!HistorySelectByPosition(posId)) return;
   double openPrice = 0, sl = 0; string cmt = ""; int dOld = 0;
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      openPrice = HistoryDealGetDouble(tk, DEAL_PRICE);
      sl = HistoryDealGetDouble(tk, DEAL_SL);
      cmt = HistoryDealGetString(tk, DEAL_COMMENT);
      dOld = HistoryDealGetInteger(tk, DEAL_TYPE) == DEAL_TYPE_BUY ? 1 : -1;
     }
   if(dOld == 0) return;
   // flips only follow main and zone trades (not 3-micro, MZ or other flips), as in the backtest
   if(StringFind(cmt, "CFX 3M") == 0 || StringFind(cmt, "CFX ZM") == 0 || StringFind(cmt, "CFX FL") == 0) return;
   double risk = sl > 0 ? MathAbs(openPrice - sl) : MathAbs(openPrice - outPrice);
   if(risk <= 0) return;
   if(!CanTrade()) return;
   SetMode();
   int d = -dOld;
   double fr = risk * FLIP_STOP;
   if(!FLIPS_ON || (g_mask & T_FLIP) == 0 || fr > g_cap || CountOpen() >= g_maxOpen) return;   // flips: $200 mode and up, prop
   double lot = LotNow();
   double price = d == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(!MarginOk(d, lot, price)) { if(InpLog) Print("CFX: not enough margin for a flip"); return; }
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double fsl = NormalizeDouble(price - d * fr, digits), ftp = NormalizeDouble(price + d * FLIP_TARGET * fr, digits);
   bool r = d == 1 ? trade.Buy(lot, _Symbol, 0, fsl, ftp, "CFX FL") : trade.Sell(lot, _Symbol, 0, fsl, ftp, "CFX FL");
   if(InpLog) PrintFormat("CFX flip %s after a stop: lot %.2f stop $%.1f target $%.1f %s", d == 1 ? "BUY" : "SELL", lot, fr, FLIP_TARGET * fr, r ? "sent" : "FAILED");
  }

//+------------------------------------------------------------------+
//| feeding bars                                                      |
//+------------------------------------------------------------------+
datetime g_lastBar = 0;

void AddBar(const MqlRates &r)
  {
   int k = IX(N);
   BT[k] = r.time; BO[k] = r.open; BH[k] = r.high; BL[k] = r.low; BC[k] = r.close; BS[k] = r.spread * _Point;
   int t = N; N++;
   ProcessBar(t);
   g_lastBar = r.time;
  }

bool Warm()
  {
   engA.Init(true); engB.Init(false);
   ZeroMemory(setup_[0]); ZeroMemory(setup_[1]); ZeroMemory(trk[0]); ZeroMemory(trk[1]);
   mpos.open = false; mwait.on = false;
   int need = InpWarmDays * 1440;
   if(need > CAP - 2000) need = CAP - 2000;
   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int got = CopyRates(_Symbol, PERIOD_M1, 1, need, rates);
   if(got < 2000) { Print("CFX: waiting for M1 history (open an M1 chart once to download it)"); return false; }
   for(int i = 0; i < got; i++) AddBar(rates[i]);
   g_live = true;
   DeletePendings("");
   PrintFormat("CFX: replayed %d M1 bars (%s to %s), %d zones active, trend %s. Live.", got,
               TimeToString(rates[0].time), TimeToString(rates[got - 1].time), ArraySize(zones),
               boss == 1 ? "BUY" : boss == -1 ? "SELL" : "none");
   return true;
  }

int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("CFX: warning - this bot was built and tested on gold (XAUUSD)");
   Warm();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   for(int i = 0; i < ArraySize(zones); i++) delete zones[i];
   ArrayResize(zones, 0);
   Comment("");
  }

void OnTick()
  {
   if(!g_live) { if(N == 0) Warm(); return; }
   Protect();
   MainOpposite();
   datetime last_closed = iTime(_Symbol, PERIOD_M1, 1);
   if(last_closed <= g_lastBar) return;
   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int got = CopyRates(_Symbol, PERIOD_M1, g_lastBar + 1, last_closed, rates);
   if(got <= 0) return;
   for(int i = 0; i < got; i++) if(rates[i].time > g_lastBar) AddBar(rates[i]);
   SendMarkets();
   SyncOrders(N - 1);
   Comment(StringFormat("Castimofx Sweep | %s | mode: %s | lot %.2f | zones %d | trend %s%s",
                        InpAccount == CFX_PROP ? "PROP" : "NORMAL", g_modeName, LotNow(), ArraySize(zones),
                        boss == 1 ? "BUY" : boss == -1 ? "SELL" : "-", g_dayStop ? " | DAY STOP" : g_hardStop ? " | STOPPED" : ""));
  }
//+------------------------------------------------------------------+
