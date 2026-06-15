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
input double InpLotSize         = 0.10; // Ukuran lot (PERINGATAN: 0.10 emas di akun kecil = sangat berisiko)
input bool   InpUseStopLoss     = true; // Pakai Stop Loss?
input double InpStopLossPrice   = 3.0;  // Jarak SL dari harga masuk, dalam satuan HARGA (emas: dollar). 3.0 = SL $3 di bawah
input bool   InpUseTakeProfit   = false;// Pakai Take Profit?
input double InpTakeProfitPrice = 3.0;  // Jarak TP dari harga masuk, dalam satuan HARGA (emas: dollar)
input int    InpMaxSpreadPts   = 0;    // Spread maksimum (points, 0 = abaikan)
input bool   InpTradeMonToFri  = true; // Hanya Senin-Jumat (skip Sabtu/Minggu)
input long   InpMagic          = 39570050; // Magic number (identitas posisi EA ini)
input int    InpSlippagePts    = 30;   // Deviasi/slippage maksimum (points)

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
   PrintFormat("[TimedDailyTrade] Rencana harian: BUY %02d:%02d WIB, CLOSE %02d:%02d WIB, lot %.2f",
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
            PrintFormat("[TimedDailyTrade] CLOSE ticket %I64u | BUY %.*f -> CLOSE %.*f | GAP %+.2f | P/L+swap %.2f %s",
                        ticket, digits, openP, digits, curP, gap, pl,
                        AccountInfoString(ACCOUNT_CURRENCY));
         else
            PrintFormat("[TimedDailyTrade] CLOSE GAGAL ticket %I64u: %s (retcode %d)",
                        ticket, trade.ResultRetcodeDescription(), trade.ResultRetcode());
      }
   }
}

//+------------------------------------------------------------------+
//| Buka posisi BUY (market) dengan pengecekan keamanan              |
//+------------------------------------------------------------------+
bool OpenBuy()
{
   //--- guard spread
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && spread > InpMaxSpreadPts)
   {
      PrintFormat("[TimedDailyTrade] Batal BUY: spread %d > maks %d", (int)spread, InpMaxSpreadPts);
      return false;
   }

   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   //--- guard margin (biar gak error kalau saldo gak cukup)
   double marginReq = 0;
   if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, InpLotSize, ask, marginReq))
   {
      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(marginReq > freeMargin)
      {
         PrintFormat("[TimedDailyTrade] Batal BUY: butuh margin %.2f tapi free margin cuma %.2f. TURUNKAN LOT!",
                     marginReq, freeMargin);
         return false;
      }
   }

   //--- SL / TP opsional (jarak dalam satuan harga, mis. emas = dollar)
   double sl = 0.0, tp = 0.0;
   if(InpUseStopLoss   && InpStopLossPrice   > 0) sl = ask - InpStopLossPrice;
   if(InpUseTakeProfit && InpTakeProfitPrice > 0) tp = ask + InpTakeProfitPrice;

   //--- hormati jarak minimum stop dari broker (stops level)
   long   stopsLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist    = stopsLevel * point;
   if(sl > 0 && (ask - sl) < minDist)
   {
      sl = ask - minDist - point;
      PrintFormat("[TimedDailyTrade] SL terlalu dekat, didorong ke jarak minimum broker (%d points).", (int)stopsLevel);
   }
   if(tp > 0 && (tp - ask) < minDist)
      tp = ask + minDist + point;

   sl = (sl > 0) ? NormalizeDouble(sl, digits) : 0.0;
   tp = (tp > 0) ? NormalizeDouble(tp, digits) : 0.0;

   //--- info estimasi rugi maks dari SL (dalam mata uang akun, mis. IDR)
   if(sl > 0)
   {
      double estLoss = 0;
      if(OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, InpLotSize, ask, sl, estLoss))
         PrintFormat("[TimedDailyTrade] SL @ %.*f -> estimasi rugi maks ~%.2f %s",
                     digits, sl, estLoss, AccountInfoString(ACCOUNT_CURRENCY));
   }

   if(trade.Buy(InpLotSize, _Symbol, 0.0, sl, tp, "TimedDailyTrade"))
   {
      PrintFormat("[TimedDailyTrade] BUY sukses %.2f lot %s @ %.*f", InpLotSize, _Symbol, digits, ask);
      return true;
   }

   PrintFormat("[TimedDailyTrade] BUY GAGAL: %s (retcode %d)",
               trade.ResultRetcodeDescription(), trade.ResultRetcode());
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

   int curMin   = t.hour * 60 + t.min;
   int buyMin   = InpBuyHour   * 60 + InpBuyMinute;
   int closeMin = InpCloseHour * 60 + InpCloseMinute;

   //--- apakah sekarang dalam periode "tahan posisi" (antara jam BUY dan jam CLOSE)?
   bool holding;
   if(buyMin <= closeMin) holding = (curMin >= buyMin && curMin < closeMin);
   else                   holding = (curMin >= buyMin || curMin < closeMin); // window lewat tengah malam

   //--- DI LUAR periode tahan: pastikan gak ada posisi (tutup kalau masih ada).
   //    Dicek terus => CLOSE tahan banting walau market baru buka / sempat requote di jam CLOSE.
   if(!holding)
   {
      if(HasOurPosition())
         CloseOurPositions();
      return;
   }

   //--- DI DALAM periode tahan: BUY sekali, di 3 menit pertama jam BUY (toleransi tester).
   if(curMin >= buyMin && curMin <= buyMin + 2)
   {
      datetime dayStart = wib - (wib % 86400); // awal hari (WIB)
      if(g_lastBuyDay == dayStart) return;     // sudah BUY hari ini
      if(HasOurPosition()) { g_lastBuyDay = dayStart; return; }

      if(OpenBuy())
         g_lastBuyDay = dayStart;
   }
}

//+------------------------------------------------------------------+
void OnTimer() { ProcessTrading(); } // dipakai saat LIVE (cek tiap 1 detik)
void OnTick()  { ProcessTrading(); } // dipakai saat BACKTEST (tiap tick)
//+------------------------------------------------------------------+
