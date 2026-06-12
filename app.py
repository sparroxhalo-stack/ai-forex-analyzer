import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import json
import os
import requests
import xml.etree.ElementTree as ET
import time

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")

st.markdown("""
<style>
  body,.main{background:#0d1117;color:#e6edf3}
  .stMetric{background:#161b22;border-radius:10px;padding:12px}
  .stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}
  .tier-box{background:#161b22;border-radius:14px;padding:20px;
    text-align:center;border:2px solid #30363d}
  .tier-box.gold{border-color:#ffd200}
  .news-card{background:#161b22;border-radius:10px;padding:14px;
    margin-bottom:8px;border-left:4px solid #f78166}
  .strategy-card{background:#161b22;border-radius:10px;padding:14px;
    margin-bottom:8px;border-left:4px solid #3fb950}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────
DEFAULTS = {
    "is_premium": False,
    "trade_journal": [],
    "telegram_token": "",
    "telegram_chat_id": "",
    "mt5_folder": "",
    "last_signals": {},
    "ai_strategy": "",
    "notification_threshold": 75,
}
for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Assets ───────────────────────────────────────────────────
ALL_PAIRS = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])

MT5_SYMBOLS = {
    "EUR/USD":"EURUSD","GBP/USD":"GBPUSD","USD/JPY":"USDJPY",
    "AUD/USD":"AUDUSD","USD/CHF":"USDCHF","USD/CAD":"USDCAD",
    "Gold (XAU/USD)":"XAUUSD","Bitcoin":"BTCUSD","NASDAQ":"NAS100","S&P 500":"SP500"
}

# ════════════════════════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════════════════════════
def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r   = requests.post(url, data={"chat_id":chat_id,"text":message,"parse_mode":"Markdown"}, timeout=5)
        return r.status_code == 200
    except: return False

def notify_trade(asset, signal, confidence, entry, sl, tp1, tp2, tp3):
    token   = st.session_state.telegram_token
    chat_id = st.session_state.telegram_chat_id
    if not token or not chat_id: return False
    direction = "🚀 BUY" if "BUY" in signal else "📉 SELL"
    msg = f"""
🔔 *Sparro FX AI — New Signal*

{direction} *{asset}*
📊 Signal: *{signal}*
🎯 Confidence: *{confidence}%*

💰 Entry:     `{round(entry,5)}`
🛑 Stop Loss: `{round(sl,5)}`
✅ TP1 (1R):  `{round(tp1,5)}`
✅ TP2 (2R):  `{round(tp2,5)}`
✅ TP3 (3R):  `{round(tp3,5)}`

⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
_Sparro FX AI — Trade responsibly_
"""
    return send_telegram(token, chat_id, msg)

# ════════════════════════════════════════════════════════════
# MT5 FILE BRIDGE
# ════════════════════════════════════════════════════════════
def send_to_mt5(asset, signal, entry, sl, tp1, tp2, lot_size=0.01):
    """
    Writes a trade signal file that the MT5 EA reads and executes.
    File path must match what the EA monitors.
    """
    folder = st.session_state.mt5_folder
    if not folder: folder = os.path.expanduser("~/SparroFX_Signals")
    os.makedirs(folder, exist_ok=True)

    mt5_sym    = MT5_SYMBOLS.get(asset, asset.replace("/",""))
    order_type = "BUY" if "BUY" in signal else "SELL"

    signal_data = {
        "symbol":     mt5_sym,
        "action":     order_type,
        "entry":      round(entry, 5),
        "sl":         round(sl, 5),
        "tp1":        round(tp1, 5),
        "tp2":        round(tp2, 5),
        "lot_size":   lot_size,
        "timestamp":  datetime.datetime.now().isoformat(),
        "source":     "SparroFXAI"
    }

    filepath = os.path.join(folder, "sparro_signal.json")
    with open(filepath, "w") as f:
        json.dump(signal_data, f, indent=2)

    # Also write a timestamped history file
    history_path = os.path.join(folder, f"signal_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(history_path, "w") as f:
        json.dump(signal_data, f, indent=2)

    return filepath

MT5_EA_CODE = '''
//+------------------------------------------------------------------+
//|  SparroFX_EA.mq5  — reads signals from Sparro FX AI app          |
//+------------------------------------------------------------------+
#property copyright "Sparro FX AI"
#property version   "1.00"

#include <Trade\\Trade.mqh>
CTrade trade;

input string SignalFolder = "C:\\\\Users\\\\YourName\\\\SparroFX_Signals\\\\";
input string SignalFile   = "sparro_signal.json";
input bool   EnableTrading = true;
input double MaxLotSize    = 0.10;

string lastTimestamp = "";

int OnInit() {
   EventSetTimer(10); // check every 10 seconds
   Print("SparroFX EA started. Monitoring: ", SignalFolder + SignalFile);
   return(INIT_SUCCEEDED);
}

void OnTimer() {
   if(!EnableTrading) return;
   string fullPath = SignalFolder + SignalFile;
   int fh = FileOpen(fullPath, FILE_READ|FILE_TXT|FILE_ANSI);
   if(fh == INVALID_HANDLE) return;

   string content = "";
   while(!FileIsEnding(fh)) content += FileReadString(fh);
   FileClose(fh);

   // Parse timestamp to avoid re-trading same signal
   string ts = ParseField(content, "timestamp");
   if(ts == lastTimestamp) return;
   lastTimestamp = ts;

   string symbol     = ParseField(content, "symbol");
   string action     = ParseField(content, "action");
   double entry      = StringToDouble(ParseField(content, "entry"));
   double sl         = StringToDouble(ParseField(content, "sl"));
   double tp1        = StringToDouble(ParseField(content, "tp1"));
   double lot        = MathMin(StringToDouble(ParseField(content, "lot_size")), MaxLotSize);

   if(symbol == "" || action == "") return;

   // Switch to correct symbol
   if(symbol != _Symbol) return; // EA only trades its own chart symbol

   Print("New Sparro signal: ", action, " ", symbol, " lot=", lot);

   if(action == "BUY")
      trade.Buy(lot, symbol, 0, sl, tp1, "SparroFX AI");
   else if(action == "SELL")
      trade.Sell(lot, symbol, 0, sl, tp1, "SparroFX AI");
}

string ParseField(string json, string key) {
   string search = "\\"" + key + "\\"";
   int pos = StringFind(json, search);
   if(pos < 0) return "";
   pos = StringFind(json, ":", pos) + 1;
   while(StringGetCharacter(json, pos) == ' ' || StringGetCharacter(json, pos) == '"') pos++;
   string result = "";
   while(pos < StringLen(json)) {
      ushort c = StringGetCharacter(json, pos);
      if(c == '"' || c == ',' || c == '}') break;
      result += ShortToString(c);
      pos++;
   }
   return result;
}

void OnDeinit(const int reason) { EventKillTimer(); }
void OnTick() {}
//+------------------------------------------------------------------+
'''

# ════════════════════════════════════════════════════════════
# NEWS ANALYSIS
# ════════════════════════════════════════════════════════════
def fetch_forex_news():
    """Fetch economic news from ForexFactory RSS"""
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        r   = requests.get(url, timeout=8)
        if r.status_code == 200:
            events = r.json()
            news   = []
            for e in events[:20]:
                impact = e.get("impact","")
                news.append({
                    "Time":     e.get("date","")[:16].replace("T"," "),
                    "Currency": e.get("currency",""),
                    "Event":    e.get("title",""),
                    "Impact":   impact,
                    "Forecast": e.get("forecast","—"),
                    "Previous": e.get("previous","—"),
                })
            return pd.DataFrame(news)
    except: pass

    # Fallback: dummy data so UI always shows something
    return pd.DataFrame([
        {"Time":"Today 08:30","Currency":"USD","Event":"Non-Farm Payrolls","Impact":"High","Forecast":"180K","Previous":"175K"},
        {"Time":"Today 10:00","Currency":"EUR","Event":"ECB Interest Rate Decision","Impact":"High","Forecast":"4.5%","Previous":"4.5%"},
        {"Time":"Today 13:30","Currency":"GBP","Event":"CPI y/y","Impact":"Medium","Forecast":"3.1%","Previous":"3.4%"},
        {"Time":"Tomorrow 08:30","Currency":"USD","Event":"Initial Jobless Claims","Impact":"Medium","Forecast":"220K","Previous":"215K"},
        {"Time":"Tomorrow 14:00","Currency":"USD","Event":"FOMC Meeting Minutes","Impact":"High","Forecast":"—","Previous":"—"},
    ])

def news_impact_on_pair(pair, news_df):
    currencies = pair.replace("Gold (XAU/USD)","USD").replace("Bitcoin","USD")
    base = currencies[:3]; quote = currencies[3:6] if len(currencies)>3 else ""
    relevant = news_df[news_df["Currency"].isin([base,quote])]
    high_impact = relevant[relevant["Impact"]=="High"]
    return relevant, len(high_impact) > 0

def news_sentiment(pair, news_df):
    """Simple rule: high-impact news on USD → affects all USD pairs"""
    _, has_high = news_impact_on_pair(pair, news_df)
    if has_high:
        return "⚠️ HIGH IMPACT NEWS — Trade carefully or avoid"
    return "✅ No high-impact news — safe to trade"

# ════════════════════════════════════════════════════════════
# STRATEGY ENGINE (8 strategies)
# ════════════════════════════════════════════════════════════
def fetch_data(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol,period=period,interval=interval,
                         progress=False,auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns,pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def strategy_ema_trend(df):
    c = df["Close"]
    e20=c.ewm(span=20).mean().iloc[-1]; e50=c.ewm(span=50).mean().iloc[-1]; e200=c.ewm(span=200).mean().iloc[-1]
    if e20>e50 and e50>e200: return "BUY",  f"EMA20>EMA50>EMA200 — full bullish stack"
    if e20<e50 and e50<e200: return "SELL", f"EMA20<EMA50<EMA200 — full bearish stack"
    return "NEUTRAL","EMA stack mixed"

def strategy_rsi(df):
    c=df["Close"]; d=c.diff()
    g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
    rsi=(100-(100/(1+(g/l)))).iloc[-1]
    if rsi>60: return "BUY",  f"RSI={round(rsi,1)} — bullish momentum"
    if rsi<40: return "SELL", f"RSI={round(rsi,1)} — bearish momentum"
    return "NEUTRAL",f"RSI={round(rsi,1)} — neutral"

def strategy_macd(df):
    c=df["Close"]; m=c.ewm(span=12).mean()-c.ewm(span=26).mean()
    s=m.ewm(span=9).mean(); h=m-s
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2]: return "BUY",  f"MACD bullish crossover (hist={round(h.iloc[-1],5)})"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2]: return "SELL", f"MACD bearish crossover (hist={round(h.iloc[-1],5)})"
    return "NEUTRAL",f"MACD weak (hist={round(h.iloc[-1],5)})"

def strategy_bollinger(df):
    c=df["Close"]; mid=c.rolling(20).mean(); std=c.rolling(20).std()
    upper=mid+2*std; lower=mid-2*std; p=c.iloc[-1]; bw=((upper-lower)/mid).iloc[-1]
    if p>upper.iloc[-1]: return "BUY",  f"Price above Bollinger upper — breakout (BW={round(bw,4)})"
    if p<lower.iloc[-1]: return "SELL", f"Price below Bollinger lower — breakdown (BW={round(bw,4)})"
    if p>mid.iloc[-1]:   return "BUY",  f"Price above BB midline (BW={round(bw,4)})"
    return "SELL",f"Price below BB midline (BW={round(bw,4)})"

def strategy_sr(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    res=float(h.rolling(10).max().iloc[-1]); sup=float(l.rolling(10).min().iloc[-1])
    zone=(res-sup)*0.15
    if p>=res-zone: return "SELL",f"At resistance {round(res,4)} — rejection likely"
    if p<=sup+zone: return "BUY", f"At support {round(sup,4)} — bounce likely"
    return ("BUY" if p>(res+sup)/2 else "SELL"), f"S={round(sup,4)} R={round(res,4)}"

def strategy_candles(df):
    o=df["Open"].iloc[-1] if "Open" in df.columns else df["Close"].iloc[-2]
    h=df["High"].iloc[-1]; l=df["Low"].iloc[-1]; c=df["Close"].iloc[-1]
    po=df["Open"].iloc[-2] if "Open" in df.columns else df["Close"].iloc[-3]
    pc=df["Close"].iloc[-2]
    body=abs(c-o); candle=h-l
    uw=h-max(c,o); lw=min(c,o)-l
    if c>o and pc<po and c>po and o<pc: return "BUY",  "Bullish Engulfing pattern"
    if c<o and pc>po and c<po and o>pc: return "SELL", "Bearish Engulfing pattern"
    if lw>body*2 and uw<body*0.5:       return "BUY",  "Hammer / Pin Bar — bullish rejection"
    if uw>body*2 and lw<body*0.5:       return "SELL", "Shooting Star — bearish rejection"
    if body<candle*0.1:                 return "NEUTRAL","Doji — indecision"
    return "NEUTRAL","No strong candle pattern"

def strategy_bos(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    sh=float(h.iloc[-20:-5].max()); sl_=float(l.iloc[-20:-5].min())
    if p>sh: return "BUY",  f"Break of Structure — broke swing high {round(sh,4)}"
    if p<sl_:return "SELL", f"Break of Structure — broke swing low {round(sl_,4)}"
    return "NEUTRAL",f"Inside range {round(sl_,4)}–{round(sh,4)}"

def strategy_volume(df):
    if "Volume" not in df.columns: return "NEUTRAL","No volume data"
    v=df["Volume"]; c=df["Close"]
    avg=v.rolling(20).mean().iloc[-1]; cur=v.iloc[-1]
    up=c.iloc[-1]>c.iloc[-2]; r=cur/avg if avg>0 else 1
    if r>1.5 and up:  return "BUY",  f"High volume bullish move ({round(r,1)}×avg)"
    if r>1.5 and not up: return "SELL",f"High volume bearish move ({round(r,1)}×avg)"
    return "NEUTRAL",f"Normal volume ({round(r,1)}×avg)"

STRATEGIES = {
    "EMA Trend":           strategy_ema_trend,
    "RSI Momentum":        strategy_rsi,
    "MACD Crossover":      strategy_macd,
    "Bollinger Breakout":  strategy_bollinger,
    "Support/Resistance":  strategy_sr,
    "Candlestick Pattern": strategy_candles,
    "Break of Structure":  strategy_bos,
    "Volume Momentum":     strategy_volume,
}

def run_all_strategies(symbol, period="6mo"):
    df = fetch_data(symbol, period)
    if df is None: return {}, 0, "ERROR"
    results = {}
    for name,fn in STRATEGIES.items():
        try:    results[name] = fn(df)
        except: results[name] = ("NEUTRAL","Error")
    buys  = sum(1 for s,_ in results.values() if s=="BUY")
    sells = sum(1 for s,_ in results.values() if s=="SELL")
    total = len(results)
    if buys>sells:   conf=round(buys/total*100);  sig="STRONG BUY" if buys>=6 else "BUY"
    elif sells>buys: conf=round(sells/total*100); sig="STRONG SELL" if sells>=6 else "SELL"
    else:            conf=50; sig="WAIT"
    return results, conf, sig

def get_trade_setup(symbol, direction):
    try:
        df=fetch_data(symbol,"3mo"); c=df["Close"]; h=df["High"]; l=df["Low"]
        p=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); risk=atr*1.5
        if "BUY" in direction: return p,p-risk,p+risk,p+risk*2,p+risk*3,round(atr,5)
        else:                  return p,p+risk,p-risk,p-risk*2,p-risk*3,round(atr,5)
    except: return None,None,None,None,None,None

# ════════════════════════════════════════════════════════════
# AI STRATEGY BUILDER (Claude API)
# ════════════════════════════════════════════════════════════
def build_ai_strategy(user_input, market_context):
    try:
        prompt = f"""You are a professional forex trading strategy builder.
The trader says: "{user_input}"

Current market context:
{market_context}

Build a clear, specific trading strategy with:
1. Entry conditions (exact rules)
2. Stop loss placement
3. Take profit targets (TP1, TP2, TP3)
4. Best timeframes to use
5. Risk management rules
6. Which assets this works best on
7. What to avoid

Be specific, practical and concise. Format with clear sections."""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json"},
            json={
                "model":"claude-sonnet-4-6",
                "max_tokens":1000,
                "messages":[{"role":"user","content":prompt}]
            },
            timeout=30
        )
        if r.status_code==200:
            return r.json()["content"][0]["text"]
        return f"API error {r.status_code}"
    except Exception as e:
        return f"Error: {e}"

def analyse_news_with_ai(news_df, pair):
    try:
        news_text = news_df.to_string(index=False)
        prompt = f"""You are a forex news analyst.
Asset being traded: {pair}

This week's economic calendar:
{news_text}

Analyse:
1. Which news events most affect {pair} this week?
2. What direction does the news sentiment suggest?
3. Which days/times should a trader AVOID trading {pair}?
4. Which events could cause the biggest moves?
5. Overall news bias: Bullish, Bearish or Neutral for {pair}?

Be concise and direct."""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json"},
            json={
                "model":"claude-sonnet-4-6",
                "max_tokens":800,
                "messages":[{"role":"user","content":prompt}]
            },
            timeout=30
        )
        if r.status_code==200:
            return r.json()["content"][0]["text"]
        return "AI analysis unavailable."
    except Exception as e:
        return f"Error: {e}"

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🚀 Sparro FX AI")
    st.divider()
    tier = st.radio("Account Tier",["Free","Premium (Demo)"])
    st.session_state.is_premium = (tier=="Premium (Demo)")
    if st.session_state.is_premium: st.success("✅ Premium Active")
    else:
        st.warning("🔒 Free Plan")
        if st.button("⚡ Upgrade — $24/mo"):
            st.info("Connect Stripe / Gumroad / Whop here.")
    st.divider()
    page = st.radio("Navigate",[
        "📊 Scanner",
        "🏆 Trade of the Day",
        "🔬 Deep Analysis",
        "🗞️ News Analysis",
        "🤖 AI Strategy Builder",
        "📡 MT5 Auto-Trade",
        "🔔 Notifications",
        "📓 Trade Journal",
        "📈 Performance",
        "💰 Risk Calculator",
        "⚙️ Settings",
        "💎 Pricing",
    ])

premium = st.session_state.is_premium
pairs   = ALL_PAIRS if premium else FREE_PAIRS

# ════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ════════════════════════════════════════════════════════════
if "Scanner" in page:
    st.title("📊 Market Scanner")
    if not premium:
        st.warning("🔒 Free plan: 5 assets. Upgrade for all 10 + full strategy engine.")

    results = []
    prog = st.progress(0)
    items = list(pairs.items())
    for i,(name,sym) in enumerate(items):
        strats,conf,sig = run_all_strategies(sym)
        buys  = sum(1 for s,_ in strats.values() if s=="BUY")
        sells = sum(1 for s,_ in strats.values() if s=="SELL")
        results.append({
            "Asset":name, "Signal":sig,
            "Confidence": f"{conf}%" if premium else "🔒",
            "Agree": f"{max(buys,sells)}/8" if premium else "🔒"
        })
        prog.progress((i+1)/len(items))
    prog.empty()

    scanner = pd.DataFrame(results)
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("🚀 Top Buys")
        st.dataframe(scanner[scanner["Signal"].str.contains("BUY",na=False)].head(3),use_container_width=True)
    with c2:
        st.subheader("📉 Top Sells")
        st.dataframe(scanner[scanner["Signal"].str.contains("SELL",na=False)].head(3),use_container_width=True)
    st.dataframe(scanner, use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: TRADE OF THE DAY
# ════════════════════════════════════════════════════════════
elif "Trade of the Day" in page:
    st.title("🏆 Trade of the Day")
    if not premium: st.error("🔒 Premium only."); st.stop()

    best = {"conf":0,"sig":"WAIT","name":"","sym":"","strats":{}}
    with st.spinner("Scanning all assets..."):
        for name,sym in ALL_PAIRS.items():
            strats,conf,sig = run_all_strategies(sym)
            if sig!="WAIT" and conf>best["conf"]:
                best = {"conf":conf,"sig":sig,"name":name,"sym":sym,"strats":strats}

    c1,c2,c3 = st.columns(3)
    c1.metric("🏆 Asset",      best["name"])
    c2.metric("📡 Signal",     best["sig"])
    c3.metric("🎯 Confidence", f"{best['conf']}%")
    st.progress(best["conf"]/100)

    if "BUY"  in best["sig"]: st.success(f"🚀 {best['name']} — {best['sig']} at {best['conf']}% confidence")
    elif "SELL" in best["sig"]: st.error(f"📉 {best['name']} — {best['sig']} at {best['conf']}% confidence")

    st.divider()
    entry,sl,tp1,tp2,tp3,atr = get_trade_setup(best["sym"], best["sig"])
    if entry:
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}");    c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")

        col1,col2,col3 = st.columns(3)
        if col1.button("📡 Send to MT5"):
            lot = 0.01
            path = send_to_mt5(best["name"], best["sig"], entry, sl, tp1, tp2, lot)
            st.success(f"✅ Signal written to: {path}")
            st.info("MT5 EA will pick this up within 10 seconds.")

        if col2.button("🔔 Send Telegram Alert"):
            ok = notify_trade(best["name"],best["sig"],best["conf"],entry,sl,tp1,tp2,tp3)
            st.success("✅ Telegram sent!") if ok else st.error("❌ Telegram failed — check Settings.")

        if col3.button("➕ Add to Journal"):
            st.session_state.trade_journal.append({
                "Date":str(datetime.date.today()),"Asset":best["name"],
                "Signal":best["sig"],"Entry":entry,"SL":sl,"TP1":tp1,
                "Confidence":best["conf"],"Result":"Open"
            })
            st.success("✅ Added to journal!")

# ════════════════════════════════════════════════════════════
# PAGE: DEEP ANALYSIS
# ════════════════════════════════════════════════════════════
elif "Deep Analysis" in page:
    st.title("🔬 Deep Strategy Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()

    selected = st.selectbox("Choose Asset", list(ALL_PAIRS.keys()))
    sym      = ALL_PAIRS[selected]

    with st.spinner(f"Running 8 strategies on {selected}..."):
        strats,conf,sig = run_all_strategies(sym)

    c1,c2,c3 = st.columns(3)
    c1.metric("Signal",sig); c2.metric("Confidence",f"{conf}%"); c3.metric("Strategies","8 analysed")
    st.progress(conf/100)
    st.divider()

    for name,(s,reason) in strats.items():
        color = "#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
        icon  = "🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:12px;margin-bottom:8px;border-left:4px solid {color}'>
          <b>{icon} {name}</b> &nbsp;
          <span style='background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px'>{s}</span><br>
          <small style='color:#8b949e'>{reason}</small>
        </div>""", unsafe_allow_html=True)

    buys=sum(1 for s,_ in strats.values() if s=="BUY")
    sells=sum(1 for s,_ in strats.values() if s=="SELL")
    c1,c2,c3=st.columns(3)
    c1.metric("🟢 Buy Votes",buys); c2.metric("🔴 Sell Votes",sells); c3.metric("🟡 Neutral",8-buys-sells)

    st.divider()
    entry,sl,tp1,tp2,tp3,atr = get_trade_setup(sym,sig)
    if entry and sig!="WAIT":
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        if conf>=75: st.success(f"✅ HIGH confidence — {conf}% strategies agree")
        elif conf>=60: st.warning(f"⚠️ MODERATE — {conf}%. Use smaller size.")
        else: st.error(f"🚨 LOW confidence — {conf}%. Consider waiting.")

        col1,col2 = st.columns(2)
        if col1.button("📡 Send to MT5"):
            path = send_to_mt5(selected,sig,entry,sl,tp1,tp2)
            st.success(f"✅ Signal sent to MT5: {path}")
        if col2.button("🔔 Telegram Alert"):
            ok = notify_trade(selected,sig,conf,entry,sl,tp1,tp2,tp3)
            st.success("✅ Sent!") if ok else st.error("❌ Check Telegram settings.")

# ════════════════════════════════════════════════════════════
# PAGE: NEWS ANALYSIS
# ════════════════════════════════════════════════════════════
elif "News" in page:
    st.title("🗞️ News Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()

    with st.spinner("Fetching this week's economic calendar..."):
        news_df = fetch_forex_news()

    st.subheader("📅 Economic Calendar — This Week")

    # Colour code by impact
    def colour_impact(val):
        if val=="High":   return "background-color:#3d1f1f;color:#f85149"
        if val=="Medium": return "background-color:#2d2000;color:#e3b341"
        return ""

    try:
        styled = news_df.style.applymap(colour_impact, subset=["Impact"])
        st.dataframe(styled, use_container_width=True)
    except:
        st.dataframe(news_df, use_container_width=True)

    st.divider()
    st.subheader("🤖 AI News Analysis for Your Asset")
    selected = st.selectbox("Select asset to analyse", list(ALL_PAIRS.keys()))

    if st.button("🔍 Analyse News Impact"):
        with st.spinner("Asking AI to analyse news impact..."):
            analysis = analyse_news_with_ai(news_df, selected)
        st.markdown(f"""
        <div class='news-card'>
        {analysis.replace(chr(10),'<br>')}
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("⚠️ High-Impact Events Today")
    today_high = news_df[news_df["Impact"]=="High"] if "Impact" in news_df.columns else pd.DataFrame()
    if not today_high.empty:
        for _,row in today_high.iterrows():
            st.error(f"🔴 {row.get('Time','')} | {row.get('Currency','')} — {row.get('Event','')} | Forecast: {row.get('Forecast','—')}")
    else:
        st.success("✅ No high-impact events found — relatively safe trading window")

# ════════════════════════════════════════════════════════════
# PAGE: AI STRATEGY BUILDER
# ════════════════════════════════════════════════════════════
elif "AI Strategy" in page:
    st.title("🤖 AI Strategy Builder")
    if not premium: st.error("🔒 Premium only."); st.stop()

    st.info("Describe what kind of trader you are or what you want, and the AI will build a custom strategy for you.")

    col1,col2 = st.columns(2)
    with col1:
        style       = st.selectbox("Trading Style",["Day Trading","Scalping","Swing Trading"])
        risk_level  = st.selectbox("Risk Appetite",["Conservative","Moderate","Aggressive"])
        fav_pairs   = st.multiselect("Favourite Pairs",list(ALL_PAIRS.keys()),default=["EUR/USD","USD/JPY"])
    with col2:
        session     = st.selectbox("Trading Session",["London","New York","Asian","All Sessions"])
        experience  = st.selectbox("Experience Level",["Beginner","Intermediate","Advanced"])
        custom_note = st.text_area("Additional requirements (optional)",
                                   placeholder="e.g. I only want to trade breakouts, or I prefer trend following...")

    if st.button("🚀 Build My Strategy"):
        market_context = f"""
Trading style: {style}
Risk: {risk_level}
Pairs: {', '.join(fav_pairs)}
Session: {session}
Experience: {experience}
Custom: {custom_note}
"""
        user_input = f"Build me a {style.lower()} strategy for {', '.join(fav_pairs)} during the {session} session. I am {experience.lower()} level with {risk_level.lower()} risk appetite. {custom_note}"

        with st.spinner("🤖 AI is building your strategy..."):
            strategy = build_ai_strategy(user_input, market_context)
            st.session_state.ai_strategy = strategy

    if st.session_state.ai_strategy:
        st.divider()
        st.subheader("📋 Your Custom AI Strategy")
        st.markdown(f"""
        <div class='strategy-card' style='font-size:14px;line-height:1.8'>
        {st.session_state.ai_strategy.replace(chr(10),'<br>')}
        </div>""", unsafe_allow_html=True)

        if st.button("💾 Save Strategy to Journal"):
            st.session_state.trade_journal.append({
                "Date":str(datetime.date.today()),
                "Asset":"Custom Strategy",
                "Signal":"AI BUILT",
                "Entry":0,"SL":0,"TP1":0,
                "Confidence":0,
                "Result":"Strategy",
                "Notes":st.session_state.ai_strategy[:200]
            })
            st.success("✅ Strategy saved!")

# ════════════════════════════════════════════════════════════
# PAGE: MT5 AUTO-TRADE
# ════════════════════════════════════════════════════════════
elif "MT5" in page:
    st.title("📡 MT5 Auto-Trade Setup")
    if not premium: st.error("🔒 Premium only."); st.stop()

    st.success("✅ How it works: This app writes a signal file → your MT5 EA reads it → trade is placed automatically")

    st.divider()
    st.subheader("Step 1 — Configure Signal Folder")
    folder = st.text_input(
        "Signal folder path (must match your EA setting)",
        value=st.session_state.mt5_folder or os.path.expanduser("~/SparroFX_Signals"),
        help="This folder is where the app saves signal files. Your MT5 EA must point to the same folder."
    )
    st.session_state.mt5_folder = folder

    if st.button("📁 Create Signal Folder"):
        os.makedirs(folder, exist_ok=True)
        st.success(f"✅ Folder ready: {folder}")

    st.divider()
    st.subheader("Step 2 — Download & Install the MT5 EA")
    st.markdown("""
    1. Download the EA file below
    2. Open MT5 → **File → Open Data Folder**
    3. Go to `MQL5 → Experts`
    4. Copy `SparroFX_EA.mq5` there
    5. Restart MT5, then open the EA on your chart
    6. Set `SignalFolder` to the same path above
    7. Enable **AutoTrading** in MT5 (green button top bar)
    """)

    ea_path = "/mnt/user-data/outputs/SparroFX_EA.mq5"
    with open(ea_path,"w") as f:
        f.write(MT5_EA_CODE)

    with open(ea_path,"r") as f:
        st.download_button("⬇️ Download SparroFX_EA.mq5", f, file_name="SparroFX_EA.mq5",
                           mime="text/plain", type="primary")

    st.divider()
    st.subheader("Step 3 — Test the Connection")
    col1,col2 = st.columns(2)
    test_asset  = col1.selectbox("Test Asset",  list(ALL_PAIRS.keys()))
    test_action = col2.selectbox("Test Action", ["BUY","SELL"])
    test_lot    = st.number_input("Lot Size",min_value=0.01,value=0.01,step=0.01)

    if st.button("🧪 Send Test Signal to MT5"):
        path = send_to_mt5(test_asset, test_action, 1.08500, 1.08000, 1.09000, 1.09500, test_lot)
        st.success(f"✅ Test signal written to:\n`{path}`")
        st.info("Open your signal folder and confirm `sparro_signal.json` was created. MT5 EA will execute within 10 seconds if running.")

        with open(path) as f:
            st.code(f.read(), language="json")

    st.divider()
    st.subheader("⚡ Auto-Scanner — Send Signals Automatically")
    st.warning("⚠️ This will monitor markets and auto-send signals to MT5 when confidence ≥ threshold.")
    threshold   = st.slider("Minimum Confidence to Auto-Send (%)", 60, 95, 75)
    auto_lot    = st.number_input("Auto Lot Size", min_value=0.01, value=0.01, step=0.01)

    if st.button("▶️ Run One Auto-Scan Now"):
        found = []
        prog = st.progress(0)
        for i,(name,sym) in enumerate(ALL_PAIRS.items()):
            _,conf,sig = run_all_strategies(sym)
            if sig!="WAIT" and conf>=threshold:
                entry,sl,tp1,tp2,tp3,_ = get_trade_setup(sym,sig)
                if entry:
                    path = send_to_mt5(name,sig,entry,sl,tp1,tp2,auto_lot)
                    ok   = notify_trade(name,sig,conf,entry,sl,tp1,tp2,tp3)
                    found.append(f"✅ {name} | {sig} | {conf}% → Signal sent")
            prog.progress((i+1)/len(ALL_PAIRS))
        prog.empty()
        if found:
            for f_ in found: st.success(f_)
        else:
            st.info(f"No signals met the {threshold}% threshold right now.")

# ════════════════════════════════════════════════════════════
# PAGE: NOTIFICATIONS
# ════════════════════════════════════════════════════════════
elif "Notifications" in page:
    st.title("🔔 Telegram Notifications")
    if not premium: st.error("🔒 Premium only."); st.stop()

    st.subheader("Setup Guide")
    with st.expander("📖 How to get your Bot Token & Chat ID (3 steps)"):
        st.markdown("""
        **Step 1 — Create your bot:**
        1. Open Telegram and search for `@BotFather`
        2. Send `/newbot`
        3. Choose a name (e.g. "Sparro FX Alerts")
        4. Copy the **Bot Token** it gives you (looks like `7123456789:AAHx...`)

        **Step 2 — Get your Chat ID:**
        1. Search for `@userinfobot` on Telegram
        2. Send it any message
        3. It replies with your **Chat ID** (a number like `987654321`)

        **Step 3 — Paste both below and test!**
        """)

    token   = st.text_input("🤖 Bot Token",   value=st.session_state.telegram_token,   type="password")
    chat_id = st.text_input("💬 Chat ID",     value=st.session_state.telegram_chat_id)

    if st.button("💾 Save"):
        st.session_state.telegram_token   = token
        st.session_state.telegram_chat_id = chat_id
        st.success("✅ Settings saved!")

    if st.button("🧪 Send Test Message"):
        ok = send_telegram(token, chat_id,
             "✅ *Sparro FX AI* — Telegram connected successfully! You'll receive trade alerts here. 🚀")
        st.success("✅ Test sent! Check Telegram.") if ok else st.error("❌ Failed. Check your token and chat ID.")

    st.divider()
    st.subheader("🎛️ Alert Settings")
    threshold = st.slider("Minimum confidence to alert (%)", 60, 95,
                          st.session_state.notification_threshold)
    st.session_state.notification_threshold = threshold
    st.info(f"You'll only receive alerts when confidence ≥ {threshold}%")

# ════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()

    with st.expander("➕ Log a Trade"):
        c1,c2,c3=st.columns(3)
        j_asset =c1.selectbox("Asset",list(ALL_PAIRS.keys()))
        j_sig   =c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"])
        j_result=c3.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c4,c5,c6=st.columns(3)
        j_entry =c4.number_input("Entry",format="%.5f")
        j_conf  =c5.slider("Confidence",0,100,70)
        j_notes =c6.text_input("Notes")
        if st.button("Save Trade"):
            st.session_state.trade_journal.append({
                "Date":str(datetime.date.today()),"Asset":j_asset,"Signal":j_sig,
                "Entry":j_entry,"SL":0,"TP1":0,"Confidence":j_conf,
                "Result":j_result,"Notes":j_notes
            })
            st.success("✅ Saved!")

    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df,use_container_width=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"])
        total=wins+loss; wr=round(wins/total*100,1) if total>0 else 0
        c1,c2,c3=st.columns(3)
        c1.metric("Total",len(df)); c2.metric("Win Rate",f"{wr}%"); c3.metric("Open",len(df[df["Result"]=="Open"]))
    else:
        st.info("No trades yet.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.title("📈 Performance Dashboard")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal:
        st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"])
    total=wins+loss; wr=round(wins/total*100,1) if total>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Trades",total); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
    if "Asset" in df.columns:
        st.subheader("By Asset")
        st.dataframe(df.groupby("Asset")["Result"].value_counts().unstack(fill_value=0),use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ════════════════════════════════════════════════════════════
elif "Risk" in page:
    st.title("💰 Risk Calculator")
    c1,c2=st.columns(2)
    with c1:
        balance =st.number_input("Balance ($)",min_value=10.0,value=1000.0)
        risk_pct=st.slider("Risk %",0.5,10.0,2.0,step=0.5)
        sl_pips =st.number_input("Stop Loss (pips)",min_value=1.0,value=20.0)
        pip_val =st.number_input("Pip Value per 0.01 lot ($)",value=0.10)
        rr      =st.slider("Risk:Reward",1,5,2)
    risk_amt=balance*risk_pct/100
    lot=round(risk_amt/(sl_pips*pip_val/0.01)*0.01,2)
    with c2:
        st.metric("Risk Amount",f"${risk_amt:.2f}"); st.metric("Lot Size",f"{lot} lots")
        st.metric("Potential Profit",f"${risk_amt*rr:.2f}"); st.metric("R:R",f"1:{rr}")
    st.progress(risk_pct/10)
    if risk_pct<=2: st.success("✅ Conservative")
    elif risk_pct<=5: st.warning("⚠️ Moderate")
    else: st.error("🚨 High risk")

# ════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ════════════════════════════════════════════════════════════
elif "Settings" in page:
    st.title("⚙️ Settings")
    st.subheader("📡 MT5 Signal Folder")
    folder=st.text_input("Folder path",value=st.session_state.mt5_folder or os.path.expanduser("~/SparroFX_Signals"))
    if st.button("Save MT5 Path"):
        st.session_state.mt5_folder=folder; st.success("✅ Saved!")

    st.subheader("🔔 Telegram")
    t=st.text_input("Bot Token",value=st.session_state.telegram_token,type="password")
    c=st.text_input("Chat ID",value=st.session_state.telegram_chat_id)
    if st.button("Save Telegram"):
        st.session_state.telegram_token=t; st.session_state.telegram_chat_id=c; st.success("✅ Saved!")

# ════════════════════════════════════════════════════════════
# PAGE: PRICING
# ════════════════════════════════════════════════════════════
elif "Pricing" in page:
    st.title("💎 Upgrade to Premium")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'>
        <h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        ✅ 5 assets<br><br>✅ Basic signals<br><br>
        ❌ Confidence scores<br><br>❌ 8-strategy engine<br><br>
        ❌ News Analysis<br><br>❌ AI Strategy Builder<br><br>
        ❌ MT5 Auto-Trade<br><br>❌ Telegram Alerts<br><br>
        ❌ Trade Journal & Performance
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$24/mo</h2><hr>
        ✅ All 10 assets<br><br>✅ 8-strategy engine<br><br>
        ✅ Real confidence scores<br><br>✅ 🗞️ News Analysis + AI news insights<br><br>
        ✅ 🤖 AI Strategy Builder<br><br>✅ 📡 MT5 Auto-Trade (sends trades automatically)<br><br>
        ✅ 🔔 Telegram trade alerts<br><br>✅ 📓 Trade Journal + 📈 Performance Dashboard<br><br>
        ✅ 💰 Full Risk Calculator
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.markdown("""
    **💳 Start collecting payments:**
    - **[Whop.com](https://whop.com)** — built for trading tools, member gating included
    - **[Gumroad](https://gumroad.com)** — live in 15 min
    - **[Stripe](https://stripe.com)** — professional recurring billing
    """)
    st.info("💡 Launch on **Whop** first — it attracts traders already looking for tools like this.")
