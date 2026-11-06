#property strict
#property version   "1.00"
#property description "Exports demo-only M5 quote snapshots to the MT5 common-files folder. Never trades."

input string          InpExpectedServer = "FinexBisnisSolusi-Demo";
input string          InpExpectedSymbol = "EURUSD";
input ENUM_TIMEFRAMES InpTimeframe      = PERIOD_M5;
input int             InpTimerSeconds   = 5;

const string SNAPSHOT_FILE = "forex_demo_snapshot.csv";
const string TEMP_FILE     = "forex_demo_snapshot.tmp";

string UtcTimestamp()
  {
   MqlDateTime value;
   TimeToStruct(TimeGMT(), value);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
                       value.year, value.mon, value.day,
                       value.hour, value.min, value.sec);
  }

int OnInit()
  {
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
     {
      Print("ShadowBridge refused: account is not demo.");
      return INIT_FAILED;
     }
   if(AccountInfoString(ACCOUNT_SERVER) != InpExpectedServer)
     {
      Print("ShadowBridge refused: server does not match configured demo server.");
      return INIT_FAILED;
     }
   if(_Symbol != InpExpectedSymbol || _Period != InpTimeframe)
     {
      Print("ShadowBridge refused: attach to the configured symbol and M5 chart.");
      return INIT_FAILED;
     }
   if(InpTimerSeconds < 1 || InpTimerSeconds > 60)
      return INIT_PARAMETERS_INCORRECT;
   if(!SymbolSelect(InpExpectedSymbol, true))
     {
      PrintFormat("ShadowBridge could not select symbol; error=%d", GetLastError());
      return INIT_FAILED;
     }
   EventSetTimer(InpTimerSeconds);
   Print("ShadowBridge initialized in demo read-only mode; order functions are not used.");
   PublishSnapshot();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTimer()
  {
   PublishSnapshot();
  }

void PublishSnapshot()
  {
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO ||
      AccountInfoString(ACCOUNT_SERVER) != InpExpectedServer ||
      _Symbol != InpExpectedSymbol || _Period != InpTimeframe)
      return;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(InpExpectedSymbol, InpTimeframe, 0, 6, rates) != 6)
      return;

   MqlTick tick;
   if(!SymbolInfoTick(InpExpectedSymbol, tick))
      return;
   double point = SymbolInfoDouble(InpExpectedSymbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(InpExpectedSymbol, SYMBOL_DIGITS);
   if(point <= 0 || tick.bid <= 0 || tick.ask < tick.bid)
      return;

   int file = FileOpen(TEMP_FILE,
                       FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ,
                       ',');
   if(file == INVALID_HANDLE)
     {
      PrintFormat("ShadowBridge file open failed; error=%d", GetLastError());
      return;
     }

   FileWrite(file, 1, UtcTimestamp(), "demo", InpExpectedServer, InpExpectedSymbol,
             "M5", DoubleToString(tick.bid, digits), DoubleToString(tick.ask, digits),
             DoubleToString((tick.ask - tick.bid) / point, 2),
             DoubleToString(point, digits), digits, 5,
             TimeToString(rates[1].time, TIME_DATE | TIME_MINUTES),
             DoubleToString(rates[1].open, digits), DoubleToString(rates[1].high, digits),
             DoubleToString(rates[1].low, digits), DoubleToString(rates[1].close, digits), rates[1].tick_volume,
             TimeToString(rates[2].time, TIME_DATE | TIME_MINUTES),
             DoubleToString(rates[2].open, digits), DoubleToString(rates[2].high, digits),
             DoubleToString(rates[2].low, digits), DoubleToString(rates[2].close, digits), rates[2].tick_volume,
             TimeToString(rates[3].time, TIME_DATE | TIME_MINUTES),
             DoubleToString(rates[3].open, digits), DoubleToString(rates[3].high, digits),
             DoubleToString(rates[3].low, digits), DoubleToString(rates[3].close, digits), rates[3].tick_volume,
             TimeToString(rates[4].time, TIME_DATE | TIME_MINUTES),
             DoubleToString(rates[4].open, digits), DoubleToString(rates[4].high, digits),
             DoubleToString(rates[4].low, digits), DoubleToString(rates[4].close, digits), rates[4].tick_volume,
             TimeToString(rates[5].time, TIME_DATE | TIME_MINUTES),
             DoubleToString(rates[5].open, digits), DoubleToString(rates[5].high, digits),
             DoubleToString(rates[5].low, digits), DoubleToString(rates[5].close, digits), rates[5].tick_volume);
   FileFlush(file);
   FileClose(file);

   ResetLastError();
   if(!FileMove(TEMP_FILE, FILE_COMMON, SNAPSHOT_FILE, FILE_COMMON | FILE_REWRITE))
      PrintFormat("ShadowBridge atomic publish failed; error=%d", GetLastError());
  }
