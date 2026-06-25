//+------------------------------------------------------------------+
//|                                            WeekendGapTrade.mq5    |
//|                                                                  |
//|  Expert Advisor MetaTrader 5 — strategi GAP AKHIR PEKAN.         |
//|  - Buka posisi (BUY/SELL) menjelang market tutup Jum'at.         |
//|  - Tahan posisi lewat akhir pekan.                               |
//|  - Tutup posisi setelah market buka Senin.                       |
//|  Jam pakai WIB (GMT+7), dikonversi ke waktu server broker.       |
//+------------------------------------------------------------------+
#property copyright "personal use"
#property version   "1.00"
#property strict
#property description "Gap akhir pekan: buka menjelang tutup Jum'at, tutup setelah buka Senin. Pilih BUY/SELL."

#include <Trade/Trade.mqh>

//--- Arah trading ---
enum ENUM_TRADE_DIR
{
   DIR_BUY  = 0, // BUY long (taruhan gap Senin NAIK)
   DIR_SELL = 1  // SELL short (taruhan gap Senin TURUN)
};

//--- Hari (sesuai MqlDateTime: 0=Minggu .. 6=Sabtu) ---
enum ENUM_DOW
{
   DOW_SUN = 0, // Minggu
   DOW_MON = 1, // Senin
   DOW_TUE = 2, // Selasa
   DOW_WED = 3, // Rabu
   DOW_THU = 4, // Kamis
   DOW_FRI = 5, // Jumat
   DOW_SAT = 6  // Sabtu
};

input group "=== Waktu (pakai WIB / waktu HP kamu) ==="
input ENUM_DOW InpEntryDOW   = DOW_FRI; // Hari BUKA posisi (WIB) — menjelang tutup Jum'at
input int    InpEntryHour     = 23;    // Jam BUKA (WIB)
input int    InpEntryMinute   = 55;    // Menit BUKA (WIB)
input ENUM_DOW InpExitDOW     = DOW_MON;// Hari TUTUP posisi (WIB) — setelah buka Senin
input int    InpExitHour      = 4;     // Jam TUTUP (WIB)
input int    InpExitMinute    = 10;    // Menit TUTUP (WIB)
input int    InpWIBOffset     = 7;     // WIB = GMT+7 (JANGAN diubah)
input int    InpBrokerGMTOff  = 3;     // Offset GMT server broker (cek Market Watch). Umum GMT+2 atau +3

input group "=== Order ==="
input ENUM_TRADE_DIR InpDirection = DIR_BUY; // Arah: BUY (gap naik) / SELL (gap turun)
input double InpLotSize         = 0.10; // Ukuran lot (PERINGATAN: 0.10 emas di akun kecil = sangat berisiko)
input bool   InpUseStopLoss     = true; // Pakai Stop Loss?
input double InpStopLossPrice   = 5.0;  // Jarak SL dari harga masuk, dalam satuan HARGA (emas: dollar)
input bool   InpUseTakeProfit   = false;// Pakai Take Profit?
input double InpTakeProfitPrice = 5.0;  // Jarak TP dari harga masuk, dalam satuan HARGA (emas: dollar)
input int    InpMaxSpreadPts   = 0;    // Spread maksimum (points, 0 = abaikan)
input long   InpMagic          = 39570051; // Magic number (beda dari EA harian!)
input int    InpSlippagePts    = 50;   // Deviasi/slippage maksimum (points)

//--- Internal ------------------------------------------------------
CTrade   trade;
int      g_lastEntryWeek = -1;   // ISO-ish week penanda sudah buka pekan ini (anti dobel)

//+------------------------------------------------------------------+
datetime ServerToWIB(datetime serverTime)
{
   return serverTime + (datetime)((InpWIBOffset - InpBrokerGMTOff) * 3600);
}

//--- "menit dalam pekan": 0 = Minggu 00:00 .. 10079 = Sabtu 23:59
int WeekMinute(const MqlDateTime &t)
{
   return t.day_of_week * 1440 + t.hour * 60 + t.min;
}

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetTypeFillingBySymbol(_Symbol);
   EventSetTimer(1);

   datetime srv = TimeTradeServer();
   PrintFormat("[WeekendGap] AKTIF di %s | %s", _Symbol, (InpDirection==DIR_BUY?"BUY":"SELL"));
   PrintFormat("[WeekendGap] Waktu server: %s | Waktu WIB: %s",
               TimeToString(srv, TIME_DATE|TIME_MINUTES),
               TimeToString(ServerToWIB(srv), TIME_DATE|TIME_MINUTES));
   Print("[WeekendGap] CEK: cocokkan 'Waktu WIB' dgn jam HP kamu; sesuaikan jam BUKA/TUTUP dgn jam tutup/buka broker. Kalau meleset, ubah InpBrokerGMTOff.");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { EventKillTimer(); }

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

void CloseOurPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
      {
         int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
         double openP  = PositionGetDouble(POSITION_PRICE_OPEN);
         double curP   = PositionGetDouble(POSITION_PRICE_CURRENT);
         double gap    = curP - openP;
         double pl     = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

         if(trade.PositionClose(ticket))
            PrintFormat("[WeekendGap] CLOSE %I64u | OPEN %.*f -> CLOSE %.*f | GAP %+.2f | P/L+swap %.2f %s",
                        ticket, digits, openP, digits, curP, gap, pl, AccountInfoString(ACCOUNT_CURRENCY));
         else
            PrintFormat("[WeekendGap] CLOSE GAGAL %I64u: %s (retcode %d)",
                        ticket, trade.ResultRetcodeDescription(), trade.ResultRetcode());
      }
   }
}

//+------------------------------------------------------------------+
bool OpenTrade()
{
   bool   isBuy  = (InpDirection == DIR_BUY);
   string dirTxt = isBuy ? "BUY" : "SELL";

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPts > 0 && spread > InpMaxSpreadPts)
   {
      PrintFormat("[WeekendGap] Batal %s: spread %d > maks %d", dirTxt, (int)spread, InpMaxSpreadPts);
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
         PrintFormat("[WeekendGap] Batal %s: butuh margin %.2f tapi free margin cuma %.2f. TURUNKAN LOT!",
                     dirTxt, marginReq, freeMargin);
         return false;
      }
   }

   double sl = 0.0, tp = 0.0;
   if(InpUseStopLoss && InpStopLossPrice > 0)
      sl = isBuy ? price - InpStopLossPrice : price + InpStopLossPrice;
   if(InpUseTakeProfit && InpTakeProfitPrice > 0)
      tp = isBuy ? price + InpTakeProfitPrice : price - InpTakeProfitPrice;

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

   if(sl > 0)
   {
      double estLoss = 0;
      if(OrderCalcProfit(otype, _Symbol, InpLotSize, price, sl, estLoss))
         PrintFormat("[WeekendGap] SL @ %.*f -> estimasi rugi maks ~%.2f %s",
                     digits, sl, estLoss, AccountInfoString(ACCOUNT_CURRENCY));
   }

   bool ok = isBuy ? trade.Buy(InpLotSize, _Symbol, 0.0, sl, tp, "WeekendGap")
                   : trade.Sell(InpLotSize, _Symbol, 0.0, sl, tp, "WeekendGap");
   if(ok)
   {
      PrintFormat("[WeekendGap] %s sukses %.2f lot %s @ %.*f", dirTxt, InpLotSize, _Symbol, digits, price);
      return true;
   }
   PrintFormat("[WeekendGap] %s GAGAL: %s (retcode %d)", dirTxt, trade.ResultRetcodeDescription(), trade.ResultRetcode());
   return false;
}

//+------------------------------------------------------------------+
//| Logika utama (week-based). Dipanggil dari OnTimer & OnTick.       |
//+------------------------------------------------------------------+
void ProcessTrading()
{
   datetime wib = ServerToWIB(TimeTradeServer());
   MqlDateTime t;
   TimeToStruct(wib, t);

   int curWM   = WeekMinute(t);
   int entryWM = InpEntryDOW * 1440 + InpEntryHour * 60 + InpEntryMinute;
   int exitWM  = InpExitDOW  * 1440 + InpExitHour  * 60 + InpExitMinute;

   //--- periode "tahan" dari jam BUKA (Jum'at) sampai jam TUTUP (Senin) — lewat akhir pekan.
   bool holding;
   if(entryWM <= exitWM) holding = (curWM >= entryWM && curWM < exitWM);
   else                  holding = (curWM >= entryWM || curWM < exitWM); // wrap lewat akhir pekan

   //--- DI LUAR periode tahan: pastikan flat (tutup kalau masih ada).
   if(!holding)
   {
      if(HasOurPosition())
         CloseOurPositions();
      return;
   }

   //--- DI DALAM periode tahan: buka sekali, di 3 menit pertama jam BUKA (toleransi tester).
   if(curWM >= entryWM && curWM <= entryWM + 2)
   {
      int weekId = (int)(wib / (7 * 86400)); // penanda pekan, anti buka dobel
      if(g_lastEntryWeek == weekId) return;
      if(HasOurPosition()) { g_lastEntryWeek = weekId; return; }
      if(OpenTrade())
         g_lastEntryWeek = weekId;
   }
}

//+------------------------------------------------------------------+
void OnTimer() { ProcessTrading(); } // LIVE
void OnTick()  { ProcessTrading(); } // BACKTEST
//+------------------------------------------------------------------+
