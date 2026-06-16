//+------------------------------------------------------------------+
//|                                                  ScalpSantai.mq5  |
//|                                                      versi 2.00   |
//|                                                                  |
//|  Scalper "santai" buat MetaTrader 5 — versi disempurnakan.       |
//|  Inti: IKUT TREN (EMA50) + ada KEKUATAN tren (ADX) + entry pas   |
//|  RSI nyilang level searah tren.                                  |
//|  Upgrade v2:                                                     |
//|   - Filter ADX  : cuma trade pas tren KUAT (anti sideways/whipsaw)|
//|   - SL/TP ATR   : otomatis nyesuain volatilitas (gak set manual) |
//|   - Break-even  : SL geser ke modal setelah profit (kunci cuan)  |
//|  Tetap: lot TETAP, SELALU SL+TP, 1 posisi, TANPA martingale,     |
//|         maks N trade/hari, STOP kalau udah rugi N kali.          |
//+------------------------------------------------------------------+
#property copyright "personal use"
#property version   "2.00"
#property strict
#property description "Scalp santai v2: EMA50 + ADX (anti-sideways) + RSI cross. SL/TP otomatis (ATR) + break-even. NO martingale. Tes DEMO dulu."

#include <Trade/Trade.mqh>

input group "=== Arah & Sinyal ==="
input int    InpEmaPeriod      = 50;   // EMA periode (filter ARAH tren)
input int    InpRsiPeriod      = 14;   // RSI periode
input double InpRsiBuy          = 50;  // BUY kalau RSI nyilang NAIK level ini (saat uptrend)
input double InpRsiSell         = 50;  // SELL kalau RSI nyilang TURUN level ini (saat downtrend)
input bool   InpUseADX          = true;// Pakai filter ADX? (cuma trade pas tren kuat)
input int    InpAdxPeriod       = 14;  // ADX periode
input double InpAdxMin          = 20;  // Tren dianggap "kuat" kalau ADX >= ini (di bawah = sideways, skip)

input group "=== Order & Risiko ==="
input double InpLotSize         = 0.01; // Lot TETAP (NO martingale!)
input bool   InpUseATR          = true; // SL/TP otomatis pakai ATR? (adaptif volatilitas)
input int    InpAtrPeriod       = 14;   // ATR periode
input double InpSL_ATR          = 1.5;  // SL = sekian x ATR
input double InpTP_ATR          = 2.25; // TP = sekian x ATR (default R:R 1:1.5)
input double InpStopLossPrice   = 0.0020;// SL manual (dipakai kalau InpUseATR=false)
input double InpTakeProfitPrice = 0.0030;// TP manual (dipakai kalau InpUseATR=false)
input bool   InpUseBreakEven    = true; // Geser SL ke modal setelah profit?
input double InpBE_Trigger_ATR  = 1.0;  // Geser ke break-even setelah profit sekian x ATR
input bool   InpUseTrailing     = true; // Trailing stop: SL ikut geser pas harga jalan (kunci cuan)?
input double InpTrailStart_ATR  = 1.5;  // Mulai trailing setelah profit sekian x ATR
input double InpTrail_ATR        = 1.0;  // Jarak SL trailing di belakang harga (x ATR)
input bool   InpExitOnReverse   = true; // Tutup posisi pas ada sinyal BALIK ARAH (cuma kalau lagi profit)?
input int    InpMaxSpreadPts   = 0;    // Spread maksimum (points, 0 = abaikan)
input int    InpMaxTradesDay   = 10;   // Maks transaksi per hari
input int    InpMaxLossesDay   = 5;    // STOP hari ini kalau udah RUGI sekian kali (0 = mati)

input group "=== Lain ==="
input long   InpMagic          = 39570060; // Magic number (identitas EA ini)
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
   trade.SetTypeFillingBySymbol(_Symbol);

   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, InpRsiPeriod, PRICE_CLOSE);
   g_adxHandle = iADX(_Symbol, PERIOD_CURRENT, InpAdxPeriod);
   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpAtrPeriod);
   if(g_emaHandle==INVALID_HANDLE || g_rsiHandle==INVALID_HANDLE ||
      g_adxHandle==INVALID_HANDLE || g_atrHandle==INVALID_HANDLE)
   {
      Print("[ScalpSantai] GAGAL bikin indikator. EA stop.");
      return(INIT_FAILED);
   }

   PrintFormat("[ScalpSantai v2] AKTIF di %s | EMA%d + RSI%d cross %.0f/%.0f | ADX>=%.0f(%s) | SL/TP=%s | lot %.2f | maks %d trade & %d rugi/hari",
               _Symbol, InpEmaPeriod, InpRsiPeriod, InpRsiBuy, InpRsiSell, InpAdxMin,
               (InpUseADX?"on":"off"), (InpUseATR?"ATR-auto":"manual"), InpLotSize,
               InpMaxTradesDay, InpMaxLossesDay);
   Print("[ScalpSantai v2] TANPA martingale. Tiap trade pakai SL+TP + break-even. TES DI DEMO dulu ya.");
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

bool HasOurPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Kelola posisi terbuka: BREAK-EVEN + TRAILING STOP                |
//|  - Break-even: cuan >= trigger -> SL ke harga masuk (gak rugi)   |
//|  - Trailing  : harga makin jalan -> SL ikut di belakang (kunci   |
//|    cuan). Balik arah mendadak = keluar cuan/BEP, bukan rugi.     |
//+------------------------------------------------------------------+
void ManageOpenPosition()
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
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
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
         if(InpUseBreakEven && profit >= beTrig && newSL < openP) newSL = openP;      // BE
         if(InpUseTrailing  && profit >= trailStart)                                  // trailing
         {
            double t = bid - trailDist;
            if(t > newSL) newSL = t;
         }
         if(newSL > curSL)
            trade.PositionModify(ticket, NormalizeDouble(newSL, digits), curTP);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit = openP - ask;
         double newSL  = curSL;
         if(InpUseBreakEven && profit >= beTrig && newSL > openP) newSL = openP;      // BE
         if(InpUseTrailing  && profit >= trailStart)                                  // trailing
         {
            double t = ask + trailDist;
            if(t < newSL) newSL = t;
         }
         if(newSL < curSL && newSL > 0)
            trade.PositionModify(ticket, NormalizeDouble(newSL, digits), curTP);
      }
   }
}

//+------------------------------------------------------------------+
//| Hitung berapa kali RUGI hari ini                                 |
//+------------------------------------------------------------------+
int LossesToday()
{
   datetime dayStart = TimeCurrent() - (TimeCurrent() % 86400);
   if(!HistorySelect(dayStart, TimeCurrent())) return 0;

   int losses = 0;
   int total  = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0) continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL)  != _Symbol)  continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC)  != InpMagic) continue;
      if(HistoryDealGetInteger(ticket, DEAL_ENTRY)  != DEAL_ENTRY_OUT) continue;
      double pl = HistoryDealGetDouble(ticket, DEAL_PROFIT)
                + HistoryDealGetDouble(ticket, DEAL_SWAP)
                + HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      if(pl < 0) losses++;
   }
   return losses;
}

//+------------------------------------------------------------------+
//| Buka posisi dengan jarak SL/TP yang dikasih (dalam satuan harga) |
//+------------------------------------------------------------------+
bool OpenTrade(bool isBuy, double slDist, double tpDist)
{
   string dirTxt = isBuy ? "BUY" : "SELL";

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && spread > InpMaxSpreadPts)
   {
      PrintFormat("[ScalpSantai] Batal %s: spread %d > maks %d", dirTxt, (int)spread, InpMaxSpreadPts);
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
         PrintFormat("[ScalpSantai] Batal %s: margin %.2f > free %.2f. TURUNKAN LOT!", dirTxt, marginReq, freeMargin);
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

   //--- kirim order; coba beberapa filling mode kalau broker nolak (fix retcode 10030 "invalid fill")
   ENUM_ORDER_TYPE_FILLING fills[3] = {ORDER_FILLING_IOC, ORDER_FILLING_FOK, ORDER_FILLING_RETURN};
   bool ok = false;
   for(int f = 0; f < 3 && !ok; f++)
   {
      trade.SetTypeFilling(fills[f]);
      ok = isBuy ? trade.Buy(InpLotSize, _Symbol, 0.0, sl, tp, "ScalpSantai")
                 : trade.Sell(InpLotSize, _Symbol, 0.0, sl, tp, "ScalpSantai");
      if(ok) break;
      if(trade.ResultRetcode() != TRADE_RETCODE_INVALID_FILL) break; // error lain -> stop nyoba
   }
   if(ok)
   {
      PrintFormat("[ScalpSantai] %s %.2f lot @ %.*f | SL %.*f TP %.*f", dirTxt, InpLotSize, digits, price, digits, sl, digits, tp);
      return true;
   }
   PrintFormat("[ScalpSantai] %s GAGAL: %s (retcode %d)", dirTxt, trade.ResultRetcodeDescription(), trade.ResultRetcode());
   return false;
}

//+------------------------------------------------------------------+
void OnTick()
{
   //--- kelola posisi terbuka (break-even + trailing) tiap tick
   ManageOpenPosition();

   //--- entry cuma dicek tiap BAR baru (santai)
   datetime curBar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curBar == g_lastBar) return;
   g_lastBar = curBar;

   //--- reset hitungan tiap ganti hari
   datetime dayStart = TimeCurrent() - (TimeCurrent() % 86400);
   if(dayStart != g_dayStart) { g_dayStart = dayStart; g_tradesToday = 0; g_lossStopLogged = false; }

   //--- ambil indikator (dipake buat exit-balik-arah DAN entry)
   double ema[], rsi[], adx[];
   ArraySetAsSeries(ema, true);
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(adx, true);
   if(CopyBuffer(g_emaHandle, 0, 0, 3, ema) < 3) return;
   if(CopyBuffer(g_rsiHandle, 0, 0, 3, rsi) < 3) return;
   if(CopyBuffer(g_adxHandle, 0, 0, 3, adx) < 3) return; // buffer 0 = garis ADX
   double atr = GetATR();

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(close1 <= 0) return;

   //--- PUNYA POSISI: cek tutup-pas-BALIK-ARAH (cuma saat profit), terus stop (gak entry baru)
   if(HasOurPosition())
   {
      if(InpExitOnReverse)
      {
         for(int i = PositionsTotal() - 1; i >= 0; i--)
         {
            ulong tk = PositionGetTicket(i);
            if(tk == 0) continue;
            if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;
            if(PositionGetInteger(POSITION_MAGIC) != InpMagic)  continue;
            if(PositionGetDouble(POSITION_PROFIT) <= 0) continue; // cuma tutup kalau LAGI PROFIT
            long ptype = PositionGetInteger(POSITION_TYPE);
            bool rev = false;
            if(ptype == POSITION_TYPE_BUY)       rev = (rsi[2] > InpRsiSell && rsi[1] <= InpRsiSell); // momentum balik TURUN
            else if(ptype == POSITION_TYPE_SELL) rev = (rsi[2] < InpRsiBuy  && rsi[1] >= InpRsiBuy);  // momentum balik NAIK
            if(rev && trade.PositionClose(tk))
               PrintFormat("[ScalpSantai] %s %I64u DITUTUP: tanda balik arah pas profit (kunci cuan di puncak)",
                           (ptype==POSITION_TYPE_BUY?"BUY":"SELL"), tk);
         }
      }
      return;
   }

   //--- batas trade harian
   if(g_tradesToday >= InpMaxTradesDay) return;
   //--- STOP kalau udah kebanyakan RUGI hari ini
   if(InpMaxLossesDay > 0 && LossesToday() >= InpMaxLossesDay)
   {
      if(!g_lossStopLogged)
      {
         PrintFormat("[ScalpSantai] STOP hari ini: udah %d kali rugi (batas %d). Gak buka trade baru sampai besok.",
                     LossesToday(), InpMaxLossesDay);
         g_lossStopLogged = true;
      }
      return;
   }

   bool uptrend   = (close1 > ema[1]);
   bool downtrend = (close1 < ema[1]);

   //--- filter ADX: cuma trade pas tren KUAT (anti sideways)
   bool adxOK = (!InpUseADX) || (adx[1] >= InpAdxMin);
   if(!adxOK) return;

   //--- sinyal: RSI nyilang level searah tren
   bool buySignal  = uptrend   && rsi[2] <  InpRsiBuy  && rsi[1] >= InpRsiBuy;
   bool sellSignal = downtrend && rsi[2] >  InpRsiSell && rsi[1] <= InpRsiSell;

   //--- jarak SL/TP: otomatis (ATR) atau manual
   double slDist, tpDist;
   if(InpUseATR && atr > 0) { slDist = atr * InpSL_ATR; tpDist = atr * InpTP_ATR; }
   else                     { slDist = InpStopLossPrice; tpDist = InpTakeProfitPrice; }

   if(buySignal)       { if(OpenTrade(true,  slDist, tpDist)) g_tradesToday++; }
   else if(sellSignal) { if(OpenTrade(false, slDist, tpDist)) g_tradesToday++; }
}
//+------------------------------------------------------------------+
