//+------------------------------------------------------------------+
//|                                            TimedDailyTrade.mq5    |
//|                                                                  |
//|  Expert Advisor untuk MetaTrader 5.                              |
//|  Tiap hari OTOMATIS:                                             |
//|    - BUY (market) pada jam tertentu                              |
//|    - CLOSE / jual pada jam tertentu                              |
//|  Jam diisi pakai WIB (GMT+7) lalu dikonversi ke waktu server.    |
//+------------------------------------------------------------------+
#property copyright "personal use"
#property version   "1.00"
#property strict
#property description "Setiap hari: BUY pada jam BUY (WIB), CLOSE pada jam CLOSE (WIB). Symbol = chart tempat EA dipasang."

#include <Trade/Trade.mqh>

//--- Arah trading ---
enum ENUM_TRADE_DIR
{
   DIR_BUY  = 0, // BUY long (taruhan gap NAIK / continuation naik)
   DIR_SELL = 1  // SELL short (taruhan gap TURUN)
};

//--- Waktu (SEMUA pakai WIB / waktu Indonesia Barat) ---------------
input group "=== Waktu (pakai WIB / waktu HP kamu) ==="
input int    InpBuyHour       = 3;     // Jam BUY (WIB, 0-23)
input int    InpBuyMinute     = 57;    // Menit BUY (WIB, 0-59)
input int    InpCloseHour     = 5;     // Jam CLOSE/jual (WIB, 0-23)
input int    InpCloseMinute   = 2;     // Menit CLOSE/jual (WIB, 0-59)
input int    InpWIBOffset     = 7;     // WIB = GMT+7 (JANGAN diubah)
input int    InpBrokerGMTOff  = 3;     // Offset GMT server broker (cek Market Watch). Umum GMT+2 atau +3

//--- Order ---------------------------------------------------------
input group "=== Order ==="
input ENUM_TRADE_DIR InpDirection = DIR_BUY; // Arah: BUY (taruhan gap naik) / SELL (taruhan gap turun)
input double InpLotSize         = 0.10; // Ukuran lot (PERINGATAN: 0.10 emas di akun kecil = sangat berisiko)
input bool   InpUseStopLoss     = true; // Pakai Stop Loss?
input double InpStopLossPrice   = 3.0;  // Jarak SL dari harga masuk, dalam satuan HARGA (emas: dollar). 3.0 = SL $3 di bawah
input bool   InpUseTakeProfit   = false;// Pakai Take Profit?
input double InpTakeProfitPrice = 3.0;  // Jarak TP dari harga masuk, dalam satuan HARGA (emas: dollar)
input int    InpMaxSpreadPts   = 0;    // Spread maksimum (points, 0 = abaikan)
input bool   InpTradeMonToFri  = true; // Hanya Senin-Jumat (skip Sabtu/Minggu)
input long   InpMagic          = 39570050; // Magic number (identitas posisi EA ini)
input int    InpSlippagePts    = 30;   // Deviasi/slippage maksimum (points)

//--- Trailing / tahan-kalau-cuan ----------------------------------
input group "=== Trailing (tahan posisi kalau masih CUAN di jam CLOSE) ==="
input bool   InpHoldIfProfit    = true; // Jam CLOSE: kalau masih CUAN -> JANGAN tutup, tahan pakai trailing
input bool   InpUseTrailing     = true; // Pakai break-even + trailing stop?
input double InpBE_TriggerPrice = 0.8;  // Geser SL ke MODAL setelah profit sekian (harga; emas=$)
input double InpTrailStartPrice = 1.5;  // Mulai TRAILING setelah profit sekian (harga; emas=$)
input double InpTrailDistPrice  = 1.0;  // Jarak SL trailing di belakang harga (harga; emas=$)

//--- Internal ------------------------------------------------------
CTrade   trade;
datetime g_lastBuyDay = 0;   // penanda WIB-day-start terakhir yang sudah BUY (anti dobel)

//+------------------------------------------------------------------+
//| Konversi waktu server -> waktu WIB                               |
//+------------------------------------------------------------------+
datetime ServerToWIB(datetime serverTime)
{
   return serverTime + (datetime)((InpWIBOffset - InpBrokerGMTOff) * 3600);
}

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetTypeFillingBySymbol(_Symbol);

   EventSetTimer(1); // cek tiap 1 detik (anti ketinggalan jam walau tick jarang)

   datetime srv = TimeTradeServer();
   PrintFormat("[TimedDailyTrade] AKTIF di %s", _Symbol);
   PrintFormat("[TimedDailyTrade] Waktu server: %s  |  Waktu WIB: %s",
               TimeToString(srv, TIME_DATE|TIME_MINUTES),
               TimeToString(ServerToWIB(srv), TIME_DATE|TIME_MINUTES));
   PrintFormat("[TimedDailyTrade] Rencana harian: %s %02d:%02d WIB, CLOSE %02d:%02d WIB, lot %.2f",
               (InpDirection == DIR_BUY ? "BUY" : "SELL"),
               InpBuyHour, InpBuyMinute, InpCloseHour, InpCloseMinute, InpLotSize);
   Print( "[TimedDailyTrade] CEK: pastikan 'Waktu WIB' di atas = jam asli di HP kamu. Kalau meleset, ubah InpBrokerGMTOff.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
}

//+------------------------------------------------------------------+
//| Apakah ada posisi milik EA ini di symbol ini?                    |
//+------------------------------------------------------------------+
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
//| Tutup semua posisi milik EA ini di symbol ini                    |
//+------------------------------------------------------------------+
void CloseOurPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
      {
         //--- catat data GAP sebelum nutup (buat analisa harian)
         int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
         double openP  = PositionGetDouble(POSITION_PRICE_OPEN);
         double curP   = PositionGetDouble(POSITION_PRICE_CURRENT);
         double gap    = curP - openP;
         double pl     = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

         if(trade.PositionClose(ticket))
            PrintFormat("[TimedDailyTrade] CLOSE ticket %I64u | OPEN %.*f -> CLOSE %.*f | GAP %+.2f | P/L+swap %.2f %s",
                        ticket, digits, openP, digits, curP, gap, pl,
                        AccountInfoString(ACCOUNT_CURRENCY));
         else
            PrintFormat("[TimedDailyTrade] CLOSE GAGAL ticket %I64u: %s (retcode %d)",
                        ticket, trade.ResultRetcodeDescription(), trade.ResultRetcode());
      }
   }
}

//+------------------------------------------------------------------+
//| Total profit floating posisi kita (P/L + swap)                   |
//+------------------------------------------------------------------+
double OurPositionProfit()
{
   double sum = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         sum += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return sum;
}

//+------------------------------------------------------------------+
//| Kunci SL ke harga masuk (break-even) -> posisi gak bisa rugi     |
//+------------------------------------------------------------------+
void ForceBreakEven()
{
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
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
      double be    = NormalizeDouble(openP, digits);
      if(type == POSITION_TYPE_BUY  && (curSL < openP || curSL == 0.0))
         trade.PositionModify(ticket, be, curTP);
      else if(type == POSITION_TYPE_SELL && (curSL > openP || curSL == 0.0))
         trade.PositionModify(ticket, be, curTP);
   }
}

//+------------------------------------------------------------------+
//| Break-even + trailing stop untuk posisi terbuka                  |
//+------------------------------------------------------------------+
void ManageTrailing()
{
   if(!InpUseTrailing) return;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
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
         if(profit >= InpBE_TriggerPrice && (newSL < openP || newSL == 0.0)) newSL = openP;
         if(profit >= InpTrailStartPrice) { double tr = bid - InpTrailDistPrice; if(tr > newSL) newSL = tr; }
         if(newSL > 0 && (curSL == 0.0 || newSL > curSL))
            trade.PositionModify(ticket, NormalizeDouble(newSL, digits), curTP);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit = openP - ask;
         double newSL  = curSL;
         if(profit >= InpBE_TriggerPrice && (newSL > openP || newSL == 0.0)) newSL = openP;
         if(profit >= InpTrailStartPrice) { double tr = ask + InpTrailDistPrice; if(newSL == 0.0 || tr < newSL) newSL = tr; }
         if(newSL > 0 && (curSL == 0.0 || newSL < curSL))
            trade.PositionModify(ticket, NormalizeDouble(newSL, digits), curTP);
      }
   }
}

//+------------------------------------------------------------------+
//| Buka posisi (BUY atau SELL sesuai InpDirection) + pengecekan     |
//+------------------------------------------------------------------+
bool OpenTrade()
{
   bool   isBuy  = (InpDirection == DIR_BUY);
   string dirTxt = isBuy ? "BUY" : "SELL";

   //--- guard spread
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && spread > InpMaxSpreadPts)
   {
      PrintFormat("[TimedDailyTrade] Batal %s: spread %d > maks %d", dirTxt, (int)spread, InpMaxSpreadPts);
      return false;
   }

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double price  = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   ENUM_ORDER_TYPE otype = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   //--- guard margin (biar gak error kalau saldo gak cukup)
   double marginReq = 0;
   if(OrderCalcMargin(otype, _Symbol, InpLotSize, price, marginReq))
   {
      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(marginReq > freeMargin)
      {
         PrintFormat("[TimedDailyTrade] Batal %s: butuh margin %.2f tapi free margin cuma %.2f. TURUNKAN LOT!",
                     dirTxt, marginReq, freeMargin);
         return false;
      }
   }

   //--- SL / TP opsional (jarak dalam satuan harga, mis. emas = dollar). Arah disesuaikan.
   double sl = 0.0, tp = 0.0;
   if(InpUseStopLoss && InpStopLossPrice > 0)
      sl = isBuy ? price - InpStopLossPrice : price + InpStopLossPrice;
   if(InpUseTakeProfit && InpTakeProfitPrice > 0)
      tp = isBuy ? price + InpTakeProfitPrice : price - InpTakeProfitPrice;

   //--- hormati jarak minimum stop dari broker (stops level)
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

   //--- info estimasi rugi maks dari SL (dalam mata uang akun, mis. IDR)
   if(sl > 0)
   {
      double estLoss = 0;
      if(OrderCalcProfit(otype, _Symbol, InpLotSize, price, sl, estLoss))
         PrintFormat("[TimedDailyTrade] SL @ %.*f -> estimasi rugi maks ~%.2f %s",
                     digits, sl, estLoss, AccountInfoString(ACCOUNT_CURRENCY));
   }

   bool ok = isBuy ? trade.Buy(InpLotSize, _Symbol, 0.0, sl, tp, "TimedDailyTrade")
                   : trade.Sell(InpLotSize, _Symbol, 0.0, sl, tp, "TimedDailyTrade");
   if(ok)
   {
      PrintFormat("[TimedDailyTrade] %s sukses %.2f lot %s @ %.*f", dirTxt, InpLotSize, _Symbol, digits, price);
      return true;
   }

   PrintFormat("[TimedDailyTrade] %s GAGAL: %s (retcode %d)",
               dirTxt, trade.ResultRetcodeDescription(), trade.ResultRetcode());
   return false;
}

//+------------------------------------------------------------------+
//| Logika utama. Dipanggil dari OnTimer (live) & OnTick (backtest)   |
//| supaya hasil akurat baik saat live maupun di Strategy Tester.    |
//+------------------------------------------------------------------+
void ProcessTrading()
{
   datetime srv = TimeTradeServer();
   datetime wib = ServerToWIB(srv);

   MqlDateTime t;
   TimeToStruct(wib, t);

   //--- skip weekend kalau diaktifkan (0=Minggu, 6=Sabtu)
   if(InpTradeMonToFri && (t.day_of_week == 0 || t.day_of_week == 6))
      return;

   //--- kelola posisi terbuka: break-even + trailing (jalan terus tiap cek)
   ManageTrailing();

   int curMin   = t.hour * 60 + t.min;
   int buyMin   = InpBuyHour   * 60 + InpBuyMinute;
   int closeMin = InpCloseHour * 60 + InpCloseMinute;

   //--- apakah sekarang dalam periode "tahan posisi" (antara jam BUY dan jam CLOSE)?
   bool holding;
   if(buyMin <= closeMin) holding = (curMin >= buyMin && curMin < closeMin);
   else                   holding = (curMin >= buyMin || curMin < closeMin); // window lewat tengah malam

   //--- DI LUAR periode tahan (jam CLOSE):
   if(!holding)
   {
      if(HasOurPosition())
      {
         //--- kalau InpHoldIfProfit & masih CUAN -> JANGAN tutup, kunci modal + biarin trailing ride
         if(InpHoldIfProfit && OurPositionProfit() > 0.0)
            ForceBreakEven();
         //--- kalau rugi/BEP (atau fitur mati) -> tutup seperti biasa (tahan banting)
         else
            CloseOurPositions();
      }
      return;
   }

   //--- DI DALAM periode tahan: buka posisi sekali, di 3 menit pertama jam BUY (toleransi tester).
   if(curMin >= buyMin && curMin <= buyMin + 2)
   {
      datetime dayStart = wib - (wib % 86400); // awal hari (WIB)
      if(g_lastBuyDay == dayStart) return;     // sudah buka hari ini
      if(HasOurPosition()) { g_lastBuyDay = dayStart; return; }

      if(OpenTrade())
         g_lastBuyDay = dayStart;
   }
}

//+------------------------------------------------------------------+
void OnTimer() { ProcessTrading(); } // dipakai saat LIVE (cek tiap 1 detik)
void OnTick()  { ProcessTrading(); } // dipakai saat BACKTEST (tiap tick)
//+------------------------------------------------------------------+
