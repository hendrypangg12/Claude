//+------------------------------------------------------------------+
//|                                                  ScalpSantai.mq5  |
//|                                                                  |
//|  EA scalping "santai" buat MetaTrader 5.                         |
//|  Strategi: IKUT TREN (EMA) + masuk pas PULLBACK (RSI mantul).     |
//|    - Uptrend (harga > EMA) + RSI balik naik dari oversold -> BUY  |
//|    - Downtrend (harga < EMA) + RSI balik turun dari overbought -> SELL
//|  Tiap trade SELALU pakai SL + TP. Lot TETAP. TANPA martingale.    |
//+------------------------------------------------------------------+
#property copyright "personal use"
#property version   "1.00"
#property strict
#property description "Scalp santai: ikut tren (EMA50) + entry pullback (RSI). SELALU SL+TP, lot tetap, 1 posisi, NO martingale. Tes di DEMO dulu."

#include <Trade/Trade.mqh>

input group "=== Strategi ==="
input int    InpEmaPeriod      = 50;   // EMA periode (filter arah tren)
input int    InpRsiPeriod      = 14;   // RSI periode
input double InpRsiBuy          = 35;  // RSI di bawah ini = oversold (zona BUY saat uptrend)
input double InpRsiSell         = 65;  // RSI di atas ini = overbought (zona SELL saat downtrend)

input group "=== Order ==="
input double InpLotSize         = 0.01; // Lot TETAP (NO martingale!)
input double InpStopLossPrice   = 3.0;  // Jarak SL (satuan harga; emas = dollar)
input double InpTakeProfitPrice = 4.5;  // Jarak TP (satuan harga; R:R ~1:1.5)
input int    InpMaxSpreadPts   = 0;    // Spread maksimum (points, 0 = abaikan)
input int    InpMaxTradesDay   = 5;    // Maks transaksi per hari (biar santai)

input group "=== Lain ==="
input long   InpMagic          = 39570060; // Magic number (identitas EA ini)
input int    InpSlippagePts    = 30;   // Deviasi/slippage maksimum (points)

//--- Internal ------------------------------------------------------
CTrade   trade;
int      g_emaHandle = INVALID_HANDLE;
int      g_rsiHandle = INVALID_HANDLE;
datetime g_lastBar   = 0;   // anti dobel: 1 cek per bar baru
datetime g_dayStart  = 0;   // penanda hari (reset hitungan trade)
int      g_tradesToday = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   trade.SetTypeFillingBySymbol(_Symbol);

   g_emaHandle = iMA(_Symbol, PERIOD_CURRENT, InpEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, InpRsiPeriod, PRICE_CLOSE);
   if(g_emaHandle == INVALID_HANDLE || g_rsiHandle == INVALID_HANDLE)
   {
      Print("[ScalpSantai] GAGAL bikin indikator. EA stop.");
      return(INIT_FAILED);
   }

   PrintFormat("[ScalpSantai] AKTIF di %s | EMA%d + RSI%d | lot %.2f | SL %.1f / TP %.1f | maks %d trade/hari",
               _Symbol, InpEmaPeriod, InpRsiPeriod, InpLotSize,
               InpStopLossPrice, InpTakeProfitPrice, InpMaxTradesDay);
   Print("[ScalpSantai] TANPA martingale. Tiap trade pakai SL+TP. TES DI DEMO dulu ya.");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(g_emaHandle != INVALID_HANDLE) IndicatorRelease(g_emaHandle);
   if(g_rsiHandle != INVALID_HANDLE) IndicatorRelease(g_rsiHandle);
}

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
//| Buka posisi (BUY/SELL) + SL/TP + pengecekan keamanan             |
//+------------------------------------------------------------------+
bool OpenTrade(bool isBuy)
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
   if(InpStopLossPrice > 0)   sl = isBuy ? price - InpStopLossPrice : price + InpStopLossPrice;
   if(InpTakeProfitPrice > 0) tp = isBuy ? price + InpTakeProfitPrice : price - InpTakeProfitPrice;

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

   bool ok = isBuy ? trade.Buy(InpLotSize, _Symbol, 0.0, sl, tp, "ScalpSantai")
                   : trade.Sell(InpLotSize, _Symbol, 0.0, sl, tp, "ScalpSantai");
   if(ok)
   {
      PrintFormat("[ScalpSantai] %s %.2f lot @ %.*f | SL %.*f TP %.*f",
                  dirTxt, InpLotSize, digits, price, digits, sl, digits, tp);
      return true;
   }
   PrintFormat("[ScalpSantai] %s GAGAL: %s (retcode %d)", dirTxt, trade.ResultRetcodeDescription(), trade.ResultRetcode());
   return false;
}

//+------------------------------------------------------------------+
void OnTick()
{
   //--- cuma proses sekali tiap BAR baru (santai, gak tiap tick)
   datetime curBar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curBar == g_lastBar) return;
   g_lastBar = curBar;

   //--- reset hitungan trade tiap ganti hari
   datetime dayStart = TimeCurrent() - (TimeCurrent() % 86400);
   if(dayStart != g_dayStart) { g_dayStart = dayStart; g_tradesToday = 0; }

   //--- 1 posisi aja; biarin SL/TP yang nutup
   if(HasOurPosition()) return;
   //--- batas trade harian
   if(g_tradesToday >= InpMaxTradesDay) return;

   //--- ambil nilai indikator (as-series: [1] = bar baru ditutup, [2] = sebelumnya)
   double ema[], rsi[];
   ArraySetAsSeries(ema, true);
   ArraySetAsSeries(rsi, true);
   if(CopyBuffer(g_emaHandle, 0, 0, 3, ema) < 3) return;
   if(CopyBuffer(g_rsiHandle, 0, 0, 3, rsi) < 3) return;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(close1 <= 0) return;

   bool uptrend   = (close1 > ema[1]);
   bool downtrend = (close1 < ema[1]);

   //--- BUY: uptrend + RSI balik NAIK nembus level oversold (pullback selesai)
   bool buySignal  = uptrend   && rsi[2] <  InpRsiBuy  && rsi[1] >= InpRsiBuy;
   //--- SELL: downtrend + RSI balik TURUN nembus level overbought
   bool sellSignal = downtrend && rsi[2] >  InpRsiSell && rsi[1] <= InpRsiSell;

   if(buySignal)       { if(OpenTrade(true))  g_tradesToday++; }
   else if(sellSignal) { if(OpenTrade(false)) g_tradesToday++; }
}
//+------------------------------------------------------------------+
