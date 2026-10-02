//+------------------------------------------------------------------+
//| SOYUZ GAGARIN -> MT5 DEMO BRIDGE                                |
//| Receives PAPER signals from the Gagarin Render endpoint.         |
//| Default: DISPLAY ONLY. No orders are sent unless the user        |
//| explicitly enables demo execution AND the account is DEMO.      |
//+------------------------------------------------------------------+
#property strict
#property version "1.1"

#include <Trade/Trade.mqh>

input string BridgeURL = "https://soyuz-gagarin-telegram-v2.onrender.com/mt5/paper";
input string BridgeKey = "";
input int PollSeconds = 60;
input bool EnableDemoExecution = false;
input double Lots = 0.01;

CTrade Trade;
string LastSignalId = "";

bool IsDemoAccount()
{
   long mode = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   return mode == ACCOUNT_TRADE_MODE_DEMO;
}

string JsonString(string json, string key)
{
   string needle = "\"" + key + "\":\"";
   int p = StringFind(json, needle);
   if(p < 0) return "";
   p += StringLen(needle);
   int e = StringFind(json, "\"", p);
   if(e < 0) return "";
   return StringSubstr(json, p, e-p);
}

bool JsonTrue(string json, string key)
{
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return false;
   p += StringLen(needle);
   string tail = StringSubstr(json, p, 6);
   return StringFind(tail, "true") == 0 || StringFind(tail, "\"true\"") == 0;
}

double JsonNumber(string json, string key)
{
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return 0.0;
   p += StringLen(needle);
   int e = p;
   while(e < StringLen(json))
   {
      ushort c = StringGetCharacter(json, e);
      if(c == ',' || c == '}' || c == '\n') break;
      e++;
   }
   return StringToDouble(StringSubstr(json, p, e-p));
}

bool FetchSignal(string &body)
{
   string headers = "";
   if(BridgeKey != "")
      headers = "X-MT5-Bridge-Key: " + BridgeKey + "\r\n";

   char post[];
   char result[];
   string result_headers;
   ResetLastError();

   int status = WebRequest(
      "GET",
      BridgeURL,
      headers,
      10000,
      post,
      result,
      result_headers
   );

   if(status != 200)
   {
      Print("GAGARIN BRIDGE HTTP ERROR: ", status,
            " last_error=", GetLastError());
      return false;
   }

   body = CharArrayToString(result);
   return true;
}

void ProcessSignal(string json)
{
   bool paper = JsonTrue(json, "paper_only");
   string execution = JsonString(json, "execution");

   if(!paper || execution != "DISABLED")
   {
      Print("GAGARIN SAFETY BLOCK: payload is not PAPER_ONLY/DISABLED.");
      return;
   }

   string symbol = JsonString(json, "symbol");
   string side = JsonString(json, "side");
   string timestamp = JsonString(json, "timestamp_utc");

   if(symbol == "" || side == "" || timestamp == "")
      return;

   string signal_id = symbol + "|" + side + "|" + timestamp;
   if(signal_id == LastSignalId)
      return;

   double entry = JsonNumber(json, "entry");
   double sl = JsonNumber(json, "stop_loss");
   double tp3 = JsonNumber(json, "take_profit_3");

   Print("GAGARIN PAPER SIGNAL | ", symbol,
         " | ", side,
         " | ENTRY=", DoubleToString(entry, _Digits),
         " | SL=", DoubleToString(sl, _Digits),
         " | TP3=", DoubleToString(tp3, _Digits));

   LastSignalId = signal_id;

   if(!EnableDemoExecution)
   {
      Comment("SOYUZ GAGARIN PAPER SIGNAL\n",
              symbol, " ", side, "\n",
              "ENTRY ", DoubleToString(entry, _Digits),
              " SL ", DoubleToString(sl, _Digits),
              " TP3 ", DoubleToString(tp3, _Digits),
              "\nEXECUTION DISABLED");
      return;
   }

   if(!IsDemoAccount())
   {
      Print("GAGARIN SAFETY BLOCK: account is not DEMO.");
      return;
   }

   bool ok = false;
   if(side == "LONG")
      ok = Trade.Buy(Lots, symbol, 0.0, sl, tp3, "SOYUZ GAGARIN DEMO");
   else if(side == "SHORT")
      ok = Trade.Sell(Lots, symbol, 0.0, sl, tp3, "SOYUZ GAGARIN DEMO");

   if(!ok)
      Print("GAGARIN DEMO ORDER FAILED: ", Trade.ResultRetcodeDescription());
   else
      Print("GAGARIN DEMO ORDER SENT: ", symbol, " ", side);
}

int OnInit()
{
   EventSetTimer(MathMax(10, PollSeconds));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   string body;
   if(FetchSignal(body))
      ProcessSignal(body);
}
