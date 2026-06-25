//+------------------------------------------------------------------+
//|                                                ScalpAdvance.mq5   |
//|                                                                  |
//|  ScalpSantai v2 + PYRAMIDING (tingkat ADVANCE, buat belajar).    |
//|                                                                  |
//|  Semua fitur v2: EMA50 + ADX (anti-sideways) + RSI cross, SL/TP  |
//|  ATR, break-even, trailing stop, exit-on-reversal, stop N rugi.  |
//|                                                                  |
//|  TAMBAHAN — PYRAMIDING (nambah ke posisi yang MENANG):           |
//|   - Pas posisi lagi PROFIT + ada sinyal SEARAH lagi -> nambah    |
//|     posisi (maks N), buat gedein cuan ngikut tren.               |
//|   - Lot TETAP tiap posisi (BUKAN martingale!). Nambah cuma pas   |
//|     UNTUNG, gak pernah pas rugi (itu jaring/averaging = bahaya). |
//|   - Tiap posisi punya SL+TP sendiri + ikut trailing.             |
//|   - Tren balik arah pas profit -> tutup SEMUA sekaligus.         |
//+------------------------------------------------------------------+
#property copyright "personal use - ADVANCE/belajar"
#property version   "1.00"
#property strict
#property description "ScalpSantai v2 + PYRAMIDING (nambah ke posisi MENANG, lot tetap, NO martingale). ADX+ATR+trailing+exit-reversal. Tes DEMO/EURUSDb. Buat belajar."

#include <Trade/Trade.mqh>

input group "=== Arah & Sinyal ==="
input int    InpEmaPeriod      = 50;   // EMA periode (filter ARAH tren)
input int    InpRsiPeriod      = 14;   // RSI periode
input double InpRsiBuy          = 50;  // BUY kalau RSI nyilang NAIK level ini (uptrend)
input double InpRsiSell         = 50;  // SELL kalau RSI nyilang TURUN level ini (downtrend)
input bool   InpUseADX          = true;// Pakai filter ADX (cuma trade pas tren kuat)?
input int    InpAdxPeriod       = 14;  // ADX periode
input double InpAdxMin          = 20;  // Tren "kuat" kalau ADX >= ini

input group "=== Order & Risiko ==="
input double InpLotSize         = 0.01; // Lot TETAP per posisi (NO martingale!)
input bool   InpUseATR          = true; // SL/TP otomatis pakai ATR?
input int    InpAtrPeriod       = 14;   // ATR periode
input double InpSL_ATR          = 1.5;  // SL = sekian x ATR
input double InpTP_ATR          = 2.5;  // TP = sekian x ATR
input double InpStopLossPrice   = 0.0020;// SL manual (kalau InpUseATR=false)
input double InpTakeProfitPrice = 0.0030;// TP manual (kalau InpUseATR=false)
input int    InpMaxSpreadPts   = 0;    // Spread maksimum (points, 0 = abaikan)
input int    InpMaxTradesDay   = 20;   // Maks transaksi per hari (termasuk pyramid)
input int    InpMaxConsecLosses = 3;   // STOP kalau KALAH sekian kali BERTURUT (menang=reset, 0=mati)

input group "=== Kelola Posisi ==="
input bool   InpUseBreakEven    = true; // Geser SL ke modal setelah profit?
input double InpBE_Trigger_ATR  = 1.0;  // Break-even setelah profit sekian x ATR
input bool   InpUseTrailing     = true; // Trailing stop (SL ikut geser pas harga jalan)?
input double InpTrailStart_ATR  = 1.5;  // Mulai trailing setelah profit sekian x ATR
input double InpTrail_ATR        = 1.0;  // Jarak SL trailing di belakang harga (x ATR)
input bool   InpExitOnReverse   = true; // Tutup SEMUA pas balik arah (kalau lagi profit)?

input group "=== PYRAMIDING (advance) ==="
input bool   InpUsePyramid      = true; // Nambah ke posisi yang MENANG?
input int    InpMaxPositions    = 3;    // Maks posisi searah (termasuk yang pertama)

input group "=== Lain ==="
input long   InpMagic          = 39570080; // Magic number (BEDA dari EA lain)
input int    InpSlippagePts    = 30;   // Deviasi/slippage maksimum (points)

//--- Internal ------------------------------------------------------
CTrade   trade;
int      g_emaHandle = INVALID_HANDLE;
int      g_rsiHandle = INVALID_HANDLE;
int      g_adxHandle = INVALID_HANDLE;
int      g_atrHandle = INVALID_HANDLE;
datetime g_lastBar   = 0;
datetime g_dayStart  = 0;
int      g_tradesToday = 0;
bool     g_lossStopLogged = false;

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);

   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, InpRsiPeriod, PRICE_CLOSE);
   g_adxHandle = iADX(_Symbol, PERIOD_CURRENT, InpAdxPeriod);
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpAtrPeriod);
   if(g_emaHandle==INVALID_HANDLE || g_rsiHandle==INVALID_HANDLE ||
      g_adxHandle==INVALID_HANDLE || g_atrHandle==INVALID_HANDLE)
   {
      Print("[ScalpAdvance] GAGAL bikin indikator. EA stop.");
      return(INIT_FAILED);
   }

   PrintFormat("[ScalpAdvance] AKTIF di %s | EMA%d+RSI cross %.0f/%.0f | ADX>=%.0f(%s) | SL/TP=%s | lot %.2f | PYRAMID %s maks %d posisi | stop %d kalah berturut",
               _Symbol, InpEmaPeriod, InpRsiBuy, InpRsiSell, InpAdxMin, (InpUseADX?"on":"off"),
               (InpUseATR?"ATR":"manual"), InpLotSize, (InpUsePyramid?"on":"off"), InpMaxPositions, InpMaxConsecLosses);
   Print("[ScalpAdvance] Pyramiding = nambah pas MENANG (lot tetap, NO martingale). Tes DEMO/EURUSDb dulu.");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(g_emaHandle!=INVALID_HANDLE) IndicatorRelease(g_emaHandle);
   if(g_rsiHandle!=INVALID_HANDLE) IndicatorRelease(g_rsiHandle);
   if(g_adxHandle!=INVALID_HANDLE) IndicatorRelease(g_adxHandle);
   if(g_atrHandle!=INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}

//+------------------------------------------------------------------+
double GetATR()
{
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_atrHandle, 0, 0, 2, atr) < 2) return 0.0;
   return atr[1];
}

int CountOurPositions()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic) n++;
   }
   return n;
}

long OurDirection() // POSITION_TYPE_BUY / SELL, atau -1 kalau gak ada
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return PositionGetInteger(POSITION_TYPE);
   }
   return -1;
}

double TotalOurProfit()
{
   double sum = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         sum += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return sum;
}

void CloseAllOurs(string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)  continue;
      if(trade.PositionClose(tk))
         PrintFormat("[ScalpAdvance] CLOSE %I64u: %s", tk, reason);
   }
}

//+------------------------------------------------------------------+
//| Kelola SEMUA posisi: break-even + trailing                       |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   if(!InpUseBreakEven && !InpUseTrailing) return;
   double atr = GetATR();
   if(atr <= 0) return;
   int    digits     = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double beTrig     = InpBE_Trigger_ATR  * atr;
   double trailStart = InpTrailStart_ATR * atr;
   double trailDist  = InpTrail_ATR       * atr;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)  continue;

      long   type  = PositionGetInteger(POSITION_TYPE);
      double openP = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL = PositionGetDouble(POSITION_SL);
      double curTP = PositionGetDouble(POSITION_TP);

      if(type == POSITION_TYPE_BUY)
      {
         double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double profit = bid - openP;
         double newSL  = curSL;
         if(InpUseBreakEven && profit >= beTrig && newSL < openP) newSL = openP;
         if(InpUseTrailing  && profit >= trailStart) { double t = bid - trailDist; if(t > newSL) newSL = t; }
         if(newSL > curSL) trade.PositionModify(tk, NormalizeDouble(newSL, digits), curTP);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit = openP - ask;
         double newSL  = curSL;
         if(InpUseBreakEven && profit >= beTrig && newSL > openP) newSL = openP;
         if(InpUseTrailing  && profit >= trailStart) { double t = ask + trailDist; if(t < newSL) newSL = t; }
         if(newSL < curSL && newSL > 0) trade.PositionModify(tk, NormalizeDouble(newSL, digits), curTP);
      }
   }
}

//+------------------------------------------------------------------+
int ConsecutiveLosses() // kalah BERTURUT (menang/BEP = reset 0)
{
   datetime dayStart = TimeCurrent() - (TimeCurrent() % 86400);
   if(!HistorySelect(dayStart, TimeCurrent())) return 0;
   int streak = 0;
   int total  = HistoryDealsTotal();
   for(int i = 0; i < total; i++) // urut waktu (lama -> baru)
   {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0) continue;
      if(HistoryDealGetString(tk, DEAL_SYMBOL) != _Symbol)  continue;
      if(HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic)  continue;
      if(HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      double pl = HistoryDealGetDouble(tk, DEAL_PROFIT)
                + HistoryDealGetDouble(tk, DEAL_SWAP)
                + HistoryDealGetDouble(tk, DEAL_COMMISSION);
      if(pl < 0) streak++; else streak = 0;
   }
   return streak;
}

//+------------------------------------------------------------------+
bool OpenTrade(bool isBuy, double slDist, double tpDist)
{
   string dirTxt = isBuy ? "BUY" : "SELL";

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && spread > InpMaxSpreadPts)
   {
      PrintFormat("[ScalpAdvance] Batal %s: spread %d > maks %d", dirTxt, (int)spread, InpMaxSpreadPts);
      return false;
   }

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double price  = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   ENUM_ORDER_TYPE otype = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   double marginReq = 0;
   if(OrderCalcMargin(otype, _Symbol, InpLotSize, price, marginReq))
   {
      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(marginReq > freeMargin)
      {
         PrintFormat("[ScalpAdvance] Batal %s: margin %.2f > free %.2f. TURUNKAN LOT!", dirTxt, marginReq, freeMargin);
         return false;
      }
   }

   double sl = 0.0, tp = 0.0;
   if(slDist > 0) sl = isBuy ? price - slDist : price + slDist;
   if(tpDist > 0) tp = isBuy ? price + tpDist : price - tpDist;

   long   stopsLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist    = stopsLevel * point;
   if(isBuy)
   {
      if(sl > 0 && (price - sl) < minDist) sl = price - minDist - point;
      if(tp > 0 && (tp - price) < minDist) tp = price + minDist + point;
   }
   else
   {
      if(sl > 0 && (sl - price) < minDist) sl = price + minDist + point;
      if(tp > 0 && (price - tp) < minDist) tp = price - minDist - point;
   }
   sl = (sl > 0) ? NormalizeDouble(sl, digits) : 0.0;
   tp = (tp > 0) ? NormalizeDouble(tp, digits) : 0.0;

   //--- coba beberapa filling mode kalau broker nolak (fix retcode 10030)
   ENUM_ORDER_TYPE_FILLING fills[3] = {ORDER_FILLING_IOC, ORDER_FILLING_FOK, ORDER_FILLING_RETURN};
   bool ok = false;
   for(int f = 0; f < 3 && !ok; f++)
   {
      trade.SetTypeFilling(fills[f]);
      ok = isBuy ? trade.Buy(InpLotSize, _Symbol, 0.0, sl, tp, "ScalpAdvance")
                 : trade.Sell(InpLotSize, _Symbol, 0.0, sl, tp, "ScalpAdvance");
      if(ok) break;
      if(trade.ResultRetcode() != TRADE_RETCODE_INVALID_FILL) break;
   }
   if(ok)
   {
      PrintFormat("[ScalpAdvance] %s %.2f lot @ %.*f | SL %.*f TP %.*f", dirTxt, InpLotSize, digits, price, digits, sl, digits, tp);
      return true;
   }
   PrintFormat("[ScalpAdvance] %s GAGAL: %s (retcode %d)", dirTxt, trade.ResultRetcodeDescription(), trade.ResultRetcode());
   return false;
}

//+------------------------------------------------------------------+
void OnTick()
{
   //--- kelola posisi terbuka (BE + trailing) tiap tick
   ManageOpenPositions();

   //--- sisanya tiap BAR baru
   datetime curBar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curBar == g_lastBar) return;
   g_lastBar = curBar;

   datetime dayStart = TimeCurrent() - (TimeCurrent() % 86400);
   if(dayStart != g_dayStart) { g_dayStart = dayStart; g_tradesToday = 0; g_lossStopLogged = false; }

   //--- indikator
   double ema[], rsi[], adx[];
   ArraySetAsSeries(ema, true);
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(adx, true);
   if(CopyBuffer(g_emaHandle, 0, 0, 3, ema) < 3) return;
   if(CopyBuffer(g_rsiHandle, 0, 0, 3, rsi) < 3) return;
   if(CopyBuffer(g_adxHandle, 0, 0, 3, adx) < 3) return;
   double atr = GetATR();
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(close1 <= 0) return;

   bool uptrend   = (close1 > ema[1]);
   bool downtrend = (close1 < ema[1]);
   bool adxOK     = (!InpUseADX) || (adx[1] >= InpAdxMin);
   bool buySignal  = uptrend   && adxOK && rsi[2] <  InpRsiBuy  && rsi[1] >= InpRsiBuy;
   bool sellSignal = downtrend && adxOK && rsi[2] >  InpRsiSell && rsi[1] <= InpRsiSell;
   bool revDown    = (rsi[2] > InpRsiSell && rsi[1] <= InpRsiSell); // momentum balik turun
   bool revUp      = (rsi[2] < InpRsiBuy  && rsi[1] >= InpRsiBuy);  // momentum balik naik

   double slDist, tpDist;
   if(InpUseATR && atr > 0) { slDist = atr * InpSL_ATR; tpDist = atr * InpTP_ATR; }
   else                     { slDist = InpStopLossPrice; tpDist = InpTakeProfitPrice; }

   int count = CountOurPositions();

   //=== SUDAH PUNYA POSISI ===
   if(count > 0)
   {
      long   dir = OurDirection();
      double tot = TotalOurProfit();

      //--- exit balik-arah: lagi profit + sinyal lawan -> tutup SEMUA (kunci cuan)
      if(InpExitOnReverse && tot > 0)
      {
         if((dir == POSITION_TYPE_BUY && revDown) || (dir == POSITION_TYPE_SELL && revUp))
         {
            CloseAllOurs("tanda balik arah pas profit (kunci cuan)");
            return;
         }
      }

      //--- PYRAMIDING: nambah searah HANYA kalau lagi PROFIT + ada sinyal searah + di bawah maks
      if(InpUsePyramid && count < InpMaxPositions && tot > 0
         && g_tradesToday < InpMaxTradesDay
         && !(InpMaxConsecLosses > 0 && ConsecutiveLosses() >= InpMaxConsecLosses))
      {
         if(dir == POSITION_TYPE_BUY && buySignal)
         {
            if(OpenTrade(true, slDist, tpDist)) { g_tradesToday++;
               PrintFormat("[ScalpAdvance] PYRAMID: nambah BUY (posisi ke-%d) pas lagi profit", count + 1); }
         }
         else if(dir == POSITION_TYPE_SELL && sellSignal)
         {
            if(OpenTrade(false, slDist, tpDist)) { g_tradesToday++;
               PrintFormat("[ScalpAdvance] PYRAMID: nambah SELL (posisi ke-%d) pas lagi profit", count + 1); }
         }
      }
      return;
   }

   //=== BELUM ADA POSISI: entry baru ===
   if(g_tradesToday >= InpMaxTradesDay) return;
   if(InpMaxConsecLosses > 0 && ConsecutiveLosses() >= InpMaxConsecLosses)
   {
      if(!g_lossStopLogged)
      {
         PrintFormat("[ScalpAdvance] STOP: kalah %d kali BERTURUT (batas %d). Gak buka baru sampai besok.",
                     ConsecutiveLosses(), InpMaxConsecLosses);
         g_lossStopLogged = true;
      }
      return;
   }

   if(buySignal)       { if(OpenTrade(true,  slDist, tpDist)) g_tradesToday++; }
   else if(sellSignal) { if(OpenTrade(false, slDist, tpDist)) g_tradesToday++; }
}
//+------------------------------------------------------------------+
