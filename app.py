import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import json
import os
import requests
import hashlib

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")

st.markdown("""
<style>
  body,.main{background:#0d1117;color:#e6edf3}
  .stMetric{background:#161b22;border-radius:10px;padding:12px}
  .stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}
  .tier-box{background:#161b22;border-radius:14px;padding:20px;text-align:center;border:2px solid #30363d}
  .tier-box.gold{border-color:#ffd200}
  .news-card{background:#161b22;border-radius:10px;padding:14px;margin-bottom:8px;border-left:4px solid #f78166}
  .strategy-card{background:#161b22;border-radius:10px;padding:14px;margin-bottom:8px;border-left:4px solid #3fb950;font-size:14px;line-height:1.8}
  .grade-a{background:#1a472a;border:1px solid #3fb950;border-radius:8px;padding:10px;text-align:center}
  .grade-b{background:#1a3a4a;border:1px solid #0072ff;border-radius:8px;padding:10px;text-align:center}
  .grade-c{background:#2d2a1a;border:1px solid #ffd200;border-radius:8px;padding:10px;text-align:center}
  .grade-d{background:#2d1a1a;border:1px solid #f85149;border-radius:8px;padding:10px;text-align:center}
  .strength-bar{height:20px;border-radius:4px;margin:2px 0}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# SUPABASE HELPERS
# ════════════════════════════════════════════════════════════
def get_supabase_headers():
    key = st.secrets.get("SUPABASE_KEY","")
    return {"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json"}

def supabase_url(path):
    return f"{st.secrets.get('SUPABASE_URL','')}/rest/v1/{path}"

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def get_user(email):
    try:
        r=requests.get(supabase_url(f"users?email=eq.{email}&select=*"),headers=get_supabase_headers(),timeout=8)
        d=r.json(); return d[0] if d else None
    except: return None

def create_user(email,password,tier="free"):
    try:
        headers=get_supabase_headers()
        headers["Prefer"]="return=representation"
        payload={"email":email,"password_hash":hash_password(password),"tier":tier,"is_active":True,"created_at":datetime.datetime.now().isoformat()}
        r=requests.post(supabase_url("users"),headers=headers,json=payload,timeout=8)
        return r.status_code in [200,201], r.text
    except Exception as e: return False, str(e)

def update_user_tier(email,tier):
    try:
        r=requests.patch(supabase_url(f"users?email=eq.{email}"),headers=get_supabase_headers(),
            json={"tier":tier},timeout=8)
        return r.status_code in [200,204]
    except: return False

def delete_user(email):
    try:
        r=requests.delete(supabase_url(f"users?email=eq.{email}"),headers=get_supabase_headers(),timeout=8)
        return r.status_code in [200,204]
    except: return False

def get_all_users():
    try:
        r=requests.get(supabase_url("users?select=*&order=created_at.desc"),headers=get_supabase_headers(),timeout=8)
        return r.json()
    except: return []

# ════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════
DEFAULTS={"logged_in":False,"user_email":"","user_tier":"free","is_admin":False,
          "trade_journal":[],"telegram_token":"","telegram_chat_id":"",
          "notification_threshold":75,"ai_strategy":"","uploaded_chart":None}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

# ════════════════════════════════════════════════════════════
# LOGIN SCREEN
# ════════════════════════════════════════════════════════════
def show_login():
    st.markdown("<div style='text-align:center;padding:40px 0 20px'><h1>🚀 Sparro FX AI</h1><p style='color:#8b949e'>AI-Powered Forex & Commodity Trading Signals</p></div>",unsafe_allow_html=True)
    tab1,tab2=st.tabs(["🔐 Login","📝 Register"])
    with tab1:
        st.subheader("Login")
        email=st.text_input("Email",key="li_email")
        password=st.text_input("Password",type="password",key="li_pass")
        if st.button("Login",type="primary",use_container_width=True):
            admin_u=st.secrets.get("ADMIN_USERNAME","admin")
            admin_p=st.secrets.get("ADMIN_PASSWORD","")
            if email==admin_u and password==admin_p:
                st.session_state.update({"logged_in":True,"is_admin":True,"user_email":email,"user_tier":"admin"})
                st.rerun()
            else:
                user=get_user(email)
                if user and user["password_hash"]==hash_password(password):
                    if not user.get("is_active",True): st.error("❌ Account deactivated.")
                    else:
                        st.session_state.update({"logged_in":True,"is_admin":False,"user_email":email,"user_tier":user.get("tier","free")})
                        st.rerun()
                else: st.error("❌ Invalid email or password.")
    with tab2:
        st.subheader("Create Free Account")
        re=st.text_input("Email",key="reg_e"); rp=st.text_input("Password",type="password",key="reg_p"); rp2=st.text_input("Confirm Password",type="password",key="reg_p2")
        if st.button("Register",type="primary",use_container_width=True):
            if not re or not rp: st.error("Fill all fields.")
            elif rp!=rp2: st.error("❌ Passwords don't match.")
            elif len(rp)<6: st.error("❌ Min 6 characters.")
            elif get_user(re): st.error("❌ Email already exists.")
            else:
                ok,err=create_user(re,rp,"free")
                if ok: st.success("✅ Account created! Please login.")
                else: st.error(f"❌ Failed: {err}")

if not st.session_state.logged_in:
    show_login(); st.stop()

# ════════════════════════════════════════════════════════════
# ASSETS & SPECIALIST WEIGHTINGS
# ════════════════════════════════════════════════════════════
ALL_PAIRS={
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS=dict(list(ALL_PAIRS.items())[:5])

# Specialist weighting — these pairs get bonus confidence when signals are strong
SPECIALIST_PAIRS={"Gold (XAU/USD)":1.15,"Bitcoin":1.10,"EUR/USD":1.08,"GBP/USD":1.05,"USD/JPY":1.05}

# Currency map for strength meter
CURRENCY_PAIRS={
    "USD":["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCHF=X","USDCAD=X"],
    "EUR":["EURUSD=X","EURGBP=X","EURJPY=X"],
    "GBP":["GBPUSD=X","EURGBP=X","GBPJPY=X"],
    "JPY":["USDJPY=X","EURJPY=X","GBPJPY=X"],
    "AUD":["AUDUSD=X","AUDCAD=X"],
    "CHF":["USDCHF=X","EURCHF=X"],
    "CAD":["USDCAD=X","AUDCAD=X"],
    "XAU":["GC=F"],
}

premium=st.session_state.user_tier in ["premium","admin"]
is_admin=st.session_state.is_admin
pairs=ALL_PAIRS if premium else FREE_PAIRS

# ════════════════════════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════════════════════════
def send_telegram(token,chat_id,message):
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id":chat_id,"text":message,"parse_mode":"Markdown"},timeout=5)
        return r.status_code==200
    except: return False

def notify_trade(asset,signal,confidence,grade,entry,sl,tp1,tp2,tp3):
    token=st.session_state.telegram_token; chat_id=st.session_state.telegram_chat_id
    if not token or not chat_id: return False
    grade_emoji={"A":"🏆","B":"✅","C":"⚠️","D":"❌"}.get(grade,"")
    direction="🚀 BUY" if "BUY" in signal else "📉 SELL"
    msg=f"""
🔔 *Sparro FX AI — Grade {grade} Signal* {grade_emoji}
{direction} *{asset}*
📊 {signal} | 🎯 {confidence}%
💰 Entry: `{round(entry,5)}`
🛑 SL: `{round(sl,5)}`
✅ TP1: `{round(tp1,5)}` | TP2: `{round(tp2,5)}` | TP3: `{round(tp3,5)}`
⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
_Sparro FX AI — Trade responsibly_
"""
    return send_telegram(token,chat_id,msg)

# ════════════════════════════════════════════════════════════
# DATA FETCH
# ════════════════════════════════════════════════════════════
def fetch_data(symbol,period="6mo",interval="1d"):
    try:
        df=yf.download(symbol,period=period,interval=interval,progress=False,auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return None

# ════════════════════════════════════════════════════════════
# SIGNAL GRADE SYSTEM (A/B/C/D)
# ════════════════════════════════════════════════════════════
def get_signal_grade(confidence, buys, sells, pair_name):
    """
    Grade A: 87%+ confidence, 7-8 strategies agree, specialist pair bonus
    Grade B: 75-86%, 6+ strategies agree
    Grade C: 62-74%, 5 strategies agree
    Grade D: Below 62% — avoid
    """
    agreement=max(buys,sells)
    specialist_bonus=SPECIALIST_PAIRS.get(pair_name,1.0)
    adj_conf=min(99,round(confidence*specialist_bonus))

    if adj_conf>=87 and agreement>=7: return "A", adj_conf, "🏆 Highest quality — take this trade"
    elif adj_conf>=75 and agreement>=6: return "B", adj_conf, "✅ Good setup — trade with standard size"
    elif adj_conf>=62 and agreement>=5: return "C", adj_conf, "⚠️ Moderate — trade with reduced size"
    else: return "D", adj_conf, "❌ Weak signal — avoid or wait"

# ════════════════════════════════════════════════════════════
# STRATEGY ENGINE (8 strategies)
# ════════════════════════════════════════════════════════════
def strategy_ema_trend(df):
    c=df["Close"]; e20=c.ewm(span=20).mean(); e50=c.ewm(span=50).mean(); e200=c.ewm(span=200).mean()
    v20=e20.iloc[-1]; v50=e50.iloc[-1]; v200=e200.iloc[-1]
    slope=e20.iloc[-1]-e20.iloc[-5]
    if v20>v50 and v50>v200: return "BUY",  f"EMA stack bullish. Slope: {'rising' if slope>0 else 'flat'}"
    if v20<v50 and v50<v200: return "SELL", f"EMA stack bearish. Slope: {'falling' if slope<0 else 'flat'}"
    return "NEUTRAL","EMA stack mixed — no clear trend"

def strategy_rsi(df):
    c=df["Close"]; d=c.diff()
    g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
    rsi=(100-(100/(1+(g/l)))).iloc[-1]
    if rsi>=70: return "BUY",  f"RSI={round(rsi,1)} — strongly overbought momentum"
    if rsi>=60: return "BUY",  f"RSI={round(rsi,1)} — bullish momentum"
    if rsi<=30: return "SELL", f"RSI={round(rsi,1)} — strongly oversold"
    if rsi<=40: return "SELL", f"RSI={round(rsi,1)} — bearish momentum"
    return "NEUTRAL",f"RSI={round(rsi,1)} — neutral zone (40-60)"

def strategy_macd(df):
    c=df["Close"]; m=c.ewm(span=12).mean()-c.ewm(span=26).mean()
    s=m.ewm(span=9).mean(); h=m-s
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>0 and h.iloc[-1]>h.iloc[-2]: return "BUY","MACD bullish crossover + positive histogram"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<0 and h.iloc[-1]<h.iloc[-2]: return "SELL","MACD bearish crossover + negative histogram"
    if m.iloc[-1]>s.iloc[-1]: return "BUY","MACD above signal line"
    if m.iloc[-1]<s.iloc[-1]: return "SELL","MACD below signal line"
    return "NEUTRAL","MACD no clear signal"

def strategy_bollinger(df):
    c=df["Close"]; mid=c.rolling(20).mean(); std=c.rolling(20).std()
    upper=mid+2*std; lower=mid-2*std; p=c.iloc[-1]; bw=((upper-lower)/mid).iloc[-1]
    prev_bw=((upper-lower)/mid).iloc[-5]; squeeze=prev_bw<bw*0.85
    if p>upper.iloc[-1]: return "BUY",f"Broke above BB upper — breakout (BW={round(bw,4)})"
    if p<lower.iloc[-1]: return "SELL",f"Broke below BB lower — breakdown (BW={round(bw,4)})"
    if squeeze and p>mid.iloc[-1]: return "BUY",f"BB squeeze expanding bullish (BW={round(bw,4)})"
    if squeeze and p<mid.iloc[-1]: return "SELL",f"BB squeeze expanding bearish (BW={round(bw,4)})"
    if p>mid.iloc[-1]: return "BUY",f"Above BB midline (BW={round(bw,4)})"
    return "SELL",f"Below BB midline (BW={round(bw,4)})"

def strategy_sr(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    res=float(h.rolling(10).max().iloc[-1]); sup=float(l.rolling(10).min().iloc[-1])
    zone=(res-sup)*0.15
    if p>=res-zone: return "SELL",f"At resistance {round(res,5)} — rejection zone"
    if p<=sup+zone: return "BUY", f"At support {round(sup,5)} — bounce zone"
    mid=(res+sup)/2
    if p>mid: return "BUY", f"Upper half of range — bullish bias. S={round(sup,5)} R={round(res,5)}"
    return "SELL",f"Lower half of range — bearish bias. S={round(sup,5)} R={round(res,5)}"

def strategy_candles(df):
    o=df["Open"].iloc[-1] if "Open" in df.columns else df["Close"].iloc[-2]
    h=df["High"].iloc[-1]; l=df["Low"].iloc[-1]; c=df["Close"].iloc[-1]
    po=df["Open"].iloc[-2] if "Open" in df.columns else df["Close"].iloc[-3]; pc=df["Close"].iloc[-2]
    body=abs(c-o); candle=h-l; uw=h-max(c,o); lw=min(c,o)-l
    if c>o and pc<po and c>po and o<pc: return "BUY","🕯️ Bullish Engulfing — strong reversal signal"
    if c<o and pc>po and c<po and o>pc: return "SELL","🕯️ Bearish Engulfing — strong reversal signal"
    if lw>body*2.5 and uw<body*0.3 and c>o: return "BUY","🕯️ Hammer — strong bullish rejection"
    if lw>body*2 and uw<body*0.5:           return "BUY","🕯️ Pin Bar — bullish rejection"
    if uw>body*2.5 and lw<body*0.3 and c<o: return "SELL","🕯️ Inverted Hammer / Shooting Star"
    if uw>body*2 and lw<body*0.5:           return "SELL","🕯️ Shooting Star — bearish rejection"
    if body<candle*0.1: return "NEUTRAL","🕯️ Doji — market indecision"
    if c>o: return "BUY","Bullish candle close"
    return "SELL","Bearish candle close"

def strategy_bos(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    sh=float(h.iloc[-20:-5].max()); sl_=float(l.iloc[-20:-5].min())
    prev_sh=float(h.iloc[-40:-20].max()) if len(h)>40 else sh
    prev_sl=float(l.iloc[-40:-20].min()) if len(l)>40 else sl_
    if p>sh and sh>prev_sh: return "BUY",f"🔺 Strong BOS — higher highs forming above {round(sh,5)}"
    if p>sh:                return "BUY",f"🔺 Break of Structure above {round(sh,5)}"
    if p<sl_ and sl_<prev_sl: return "SELL",f"🔻 Strong BOS — lower lows forming below {round(sl_,5)}"
    if p<sl_:               return "SELL",f"🔻 Break of Structure below {round(sl_,5)}"
    return "NEUTRAL",f"Inside range {round(sl_,5)}–{round(sh,5)}"

def strategy_volume(df):
    if "Volume" not in df.columns: return "NEUTRAL","No volume data"
    v=df["Volume"]; c=df["Close"]
    avg=v.rolling(20).mean().iloc[-1]; cur=v.iloc[-1]; up=c.iloc[-1]>c.iloc[-2]; r=cur/avg if avg>0 else 1
    if r>2.0 and up:     return "BUY", f"📊 Very high volume bullish ({round(r,1)}×avg) — strong conviction"
    if r>1.5 and up:     return "BUY", f"📊 High volume bullish ({round(r,1)}×avg)"
    if r>2.0 and not up: return "SELL",f"📊 Very high volume bearish ({round(r,1)}×avg) — strong conviction"
    if r>1.5 and not up: return "SELL",f"📊 High volume bearish ({round(r,1)}×avg)"
    return "NEUTRAL",f"Normal volume ({round(r,1)}×avg)"

STRATEGIES={
    "EMA Trend":strategy_ema_trend,"RSI Momentum":strategy_rsi,
    "MACD Crossover":strategy_macd,"Bollinger Breakout":strategy_bollinger,
    "Support/Resistance":strategy_sr,"Candlestick Pattern":strategy_candles,
    "Break of Structure":strategy_bos,"Volume Momentum":strategy_volume,
}

def run_all_strategies(symbol,period="6mo"):
    df=fetch_data(symbol,period)
    if df is None: return {},0,"ERROR",0,0
    results={}
    for name,fn in STRATEGIES.items():
        try:    results[name]=fn(df)
        except: results[name]=("NEUTRAL","Error")
    buys=sum(1 for s,_ in results.values() if s=="BUY")
    sells=sum(1 for s,_ in results.values() if s=="SELL")
    total=len(results)
    if buys>sells:   conf=round(buys/total*100);  sig="STRONG BUY" if buys>=6 else "BUY"
    elif sells>buys: conf=round(sells/total*100); sig="STRONG SELL" if sells>=6 else "SELL"
    else:            conf=50; sig="WAIT"
    return results,conf,sig,buys,sells

# ════════════════════════════════════════════════════════════
# MULTI-TIMEFRAME ANALYSIS
# ════════════════════════════════════════════════════════════
def multi_timeframe_analysis(symbol):
    timeframes=[
        ("1H","1h","5d"),("4H","1h","1mo"),
        ("Daily","1d","6mo"),("Weekly","1wk","1y"),("Monthly","1mo","2y")
    ]
    results=[]
    for label,interval,period in timeframes:
        try:
            df=fetch_data(symbol,period,interval)
            if df is None: results.append({"TF":label,"Signal":"N/A","RSI":"N/A","Trend":"N/A"}); continue
            c=df["Close"]
            e20=c.ewm(span=20).mean().iloc[-1]; e50=c.ewm(span=50).mean().iloc[-1]
            delta=c.diff(); g=delta.where(delta>0,0).rolling(14).mean(); l=(-delta.where(delta<0,0)).rolling(14).mean()
            rsi=round((100-(100/(1+(g/l)))).iloc[-1],1)
            if e20>e50 and rsi>55: sig="STRONG BUY"; trend="📈 Bullish"
            elif e20>e50:          sig="BUY";         trend="📈 Bullish"
            elif e20<e50 and rsi<45: sig="STRONG SELL"; trend="📉 Bearish"
            elif e20<e50:          sig="SELL";        trend="📉 Bearish"
            else:                  sig="WAIT";        trend="➡️ Neutral"
            results.append({"Timeframe":label,"Signal":sig,"RSI":rsi,"Trend":trend})
        except: results.append({"Timeframe":label,"Signal":"N/A","RSI":"N/A","Trend":"N/A"})
    return pd.DataFrame(results)

# ════════════════════════════════════════════════════════════
# PRECISION ENTRY TOOLS
# ════════════════════════════════════════════════════════════
def get_precision_entry(symbol, direction, account_size, risk_pct):
    try:
        df=fetch_data(symbol,"3mo","1d")
        c=df["Close"]; h=df["High"]; l=df["Low"]
        price=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1])

        # Multiple entry options
        entries={}
        if "BUY" in direction:
            entries["Aggressive (Market)"] ={"entry":price,          "sl":price-atr*1.0,"tp1":price+atr*1.0,"tp2":price+atr*2.0,"tp3":price+atr*3.0}
            entries["Standard (ATR SL)"]   ={"entry":price,          "sl":price-atr*1.5,"tp1":price+atr*1.5,"tp2":price+atr*3.0,"tp3":price+atr*4.5}
            entries["Conservative (EMA)"]  ={"entry":float(c.ewm(span=20).mean().iloc[-1]),"sl":price-atr*2.0,"tp1":price+atr*2.0,"tp2":price+atr*4.0,"tp3":price+atr*6.0}
        else:
            entries["Aggressive (Market)"] ={"entry":price,          "sl":price+atr*1.0,"tp1":price-atr*1.0,"tp2":price-atr*2.0,"tp3":price-atr*3.0}
            entries["Standard (ATR SL)"]   ={"entry":price,          "sl":price+atr*1.5,"tp1":price-atr*1.5,"tp2":price-atr*3.0,"tp3":price-atr*4.5}
            entries["Conservative (EMA)"]  ={"entry":float(c.ewm(span=20).mean().iloc[-1]),"sl":price+atr*2.0,"tp1":price-atr*2.0,"tp2":price-atr*4.0,"tp3":price-atr*6.0}

        # Position sizing
        risk_amount=account_size*risk_pct/100
        for k,v in entries.items():
            sl_dist=abs(v["entry"]-v["sl"])
            pip_val=0.10 if price<10 else 0.01
            lot=round(risk_amount/(sl_dist/pip_val*0.01),2) if sl_dist>0 else 0.01
            lot=max(0.01,min(lot,10.0))
            entries[k]["lot_size"]=lot
            entries[k]["risk_amount"]=risk_amount
            entries[k]["atr"]=round(atr,5)

        return entries, round(atr,5), price
    except Exception as e: return {}, 0, 0

def get_trade_setup(symbol,direction):
    try:
        df=fetch_data(symbol,"3mo"); c=df["Close"]; h=df["High"]; l=df["Low"]
        p=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); risk=atr*1.5
        if "BUY" in direction: return p,p-risk,p+risk,p+risk*2,p+risk*3,round(atr,5)
        else:                  return p,p+risk,p-risk,p-risk*2,p-risk*3,round(atr,5)
    except: return None,None,None,None,None,None

# ════════════════════════════════════════════════════════════
# CURRENCY STRENGTH METER
# ════════════════════════════════════════════════════════════
def calculate_currency_strength():
    strength={}
    for currency,syms in CURRENCY_PAIRS.items():
        scores=[]
        for sym in syms:
            try:
                df=fetch_data(sym,"1mo","1d")
                if df is None: continue
                c=df["Close"]
                change=(float(c.iloc[-1])-float(c.iloc[-5]))/float(c.iloc[-5])*100
                # If currency is quote in pair, invert
                if sym.startswith(currency.replace("XAU","GC")[:3]): scores.append(change)
                else: scores.append(-change)
            except: pass
        strength[currency]=round(np.mean(scores),3) if scores else 0
    # Normalize to 0-100
    vals=list(strength.values())
    mn,mx=min(vals),max(vals)
    rng=mx-mn if mx!=mn else 1
    return {k:round((v-mn)/rng*100,1) for k,v in strength.items()}

# ════════════════════════════════════════════════════════════
# PROP FIRM TOOLS
# ════════════════════════════════════════════════════════════
def prop_firm_calculator(account_size, firm_type, current_profit, current_loss):
    rules={
        "FTMO":        {"daily_loss":0.05,"max_loss":0.10,"profit_target":0.10},
        "MyForexFunds":{"daily_loss":0.05,"max_loss":0.10,"profit_target":0.08},
        "The5ers":     {"daily_loss":0.04,"max_loss":0.08,"profit_target":0.08},
        "FundedNext":  {"daily_loss":0.05,"max_loss":0.10,"profit_target":0.10},
    }
    rule=rules.get(firm_type,rules["FTMO"])
    daily_loss_limit =account_size*rule["daily_loss"]
    max_loss_limit   =account_size*rule["max_loss"]
    profit_target    =account_size*rule["profit_target"]
    remaining_daily  =daily_loss_limit-abs(current_loss)
    remaining_max    =max_loss_limit-abs(current_loss)
    profit_needed    =profit_target-current_profit
    safe_lot=round(remaining_daily*0.01/20,2)
    safe_lot=max(0.01,safe_lot)
    return {
        "daily_loss_limit":  daily_loss_limit,
        "max_loss_limit":    max_loss_limit,
        "profit_target":     profit_target,
        "remaining_daily":   max(0,remaining_daily),
        "remaining_max":     max(0,remaining_max),
        "profit_needed":     max(0,profit_needed),
        "safe_lot":          safe_lot,
        "daily_loss_pct":    rule["daily_loss"]*100,
        "max_loss_pct":      rule["max_loss"]*100,
        "profit_target_pct": rule["profit_target"]*100,
    }

# ════════════════════════════════════════════════════════════
# PRICE CHART
# ════════════════════════════════════════════════════════════
def show_price_chart(symbol,pair_name,signal,entry,sl,tp1,tp2,show_indicators=True):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    df=fetch_data(symbol,"3mo","1d")
    if df is None: st.warning("Chart unavailable."); return

    close=df["Close"]; dates=df.index
    ema20=close.ewm(span=20).mean(); ema50=close.ewm(span=50).mean(); ema200=close.ewm(span=200).mean()
    resistance=float(df["High"].rolling(10).max().iloc[-1]); support=float(df["Low"].rolling(10).min().iloc[-1])

    # RSI for subplot
    delta=close.diff(); g=delta.where(delta>0,0).rolling(14).mean(); l=(-delta.where(delta<0,0)).rolling(14).mean()
    rsi=100-(100/(1+(g/l)))

    # MACD for subplot
    macd=close.ewm(span=12).mean()-close.ewm(span=26).mean()
    macd_sig=macd.ewm(span=9).mean(); macd_hist=macd-macd_sig

    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,
        row_heights=[0.6,0.2,0.2],vertical_spacing=0.03,
        subplot_titles=[f"{pair_name} — Price","RSI","MACD"])

    # Candlestick
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],
            low=df["Low"],close=close,name="Price",
            increasing_line_color="#3fb950",decreasing_line_color="#f85149"),row=1,col=1)
    else:
        fig.add_trace(go.Scatter(x=dates,y=close,name="Price",line=dict(color="#58a6ff",width=2)),row=1,col=1)

    if show_indicators:
        fig.add_trace(go.Scatter(x=dates,y=ema20, name="EMA20", line=dict(color="#ffd700",width=1,dash="dot")),row=1,col=1)
        fig.add_trace(go.Scatter(x=dates,y=ema50, name="EMA50", line=dict(color="#ff7f50",width=1,dash="dot")),row=1,col=1)
        fig.add_trace(go.Scatter(x=dates,y=ema200,name="EMA200",line=dict(color="#da70d6",width=1,dash="dash")),row=1,col=1)

    # S/R lines
    fig.add_hline(y=resistance,line_color="#f85149",line_dash="dash",annotation_text=f"R {round(resistance,4)}",annotation_position="right",row=1,col=1)
    fig.add_hline(y=support,   line_color="#3fb950",line_dash="dash",annotation_text=f"S {round(support,4)}",  annotation_position="right",row=1,col=1)

    # Trade levels
    if entry:
        color="#3fb950" if "BUY" in signal else "#f85149"
        fig.add_hline(y=entry,line_color=color,   line_width=2,annotation_text=f"Entry {round(entry,5)}",annotation_position="left",row=1,col=1)
        fig.add_hline(y=sl,   line_color="#f85149",line_width=1,line_dash="dash",annotation_text=f"SL {round(sl,5)}",   annotation_position="left",row=1,col=1)
        fig.add_hline(y=tp1,  line_color="#3fb950",line_width=1,line_dash="dash",annotation_text=f"TP1 {round(tp1,5)}",annotation_position="left",row=1,col=1)
        fig.add_hline(y=tp2,  line_color="#3fb950",line_width=1,line_dash="dot", annotation_text=f"TP2 {round(tp2,5)}",annotation_position="left",row=1,col=1)

    # Signal arrow
    last_price=float(close.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[last_price],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in signal else "triangle-down",
        size=18,color="#3fb950" if "BUY" in signal else "#f85149"),name=f"{signal}"),row=1,col=1)

    # RSI subplot
    fig.add_trace(go.Scatter(x=dates,y=rsi,name="RSI",line=dict(color="#58a6ff",width=1)),row=2,col=1)
    fig.add_hline(y=70,line_color="#f85149",line_dash="dot",row=2,col=1)
    fig.add_hline(y=30,line_color="#3fb950",line_dash="dot",row=2,col=1)

    # MACD subplot
    colors=["#3fb950" if v>=0 else "#f85149" for v in macd_hist]
    fig.add_trace(go.Bar(x=dates,y=macd_hist,name="MACD Hist",marker_color=colors),row=3,col=1)
    fig.add_trace(go.Scatter(x=dates,y=macd,    name="MACD",   line=dict(color="#ffd700",width=1)),row=3,col=1)
    fig.add_trace(go.Scatter(x=dates,y=macd_sig,name="Signal", line=dict(color="#ff7f50",width=1)),row=3,col=1)

    fig.update_layout(
        plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",font=dict(color="#e6edf3"),
        xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),height=700,
        margin=dict(l=60,r=120,t=40,b=40),
        legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1))
    st.plotly_chart(fig,use_container_width=True)

    # Why take this trade
    st.subheader("💡 Why Take This Trade?")
    month_ago=float(close.iloc[-22]) if len(close)>22 else float(close.iloc[0])
    change_pct=round((last_price-month_ago)/month_ago*100,2)
    trend_dir="uptrend" if float(ema20.iloc[-1])>float(ema200.iloc[-1]) else "downtrend"
    ema_slope=float(ema20.iloc[-1])-float(ema20.iloc[-5])
    last_rsi=round(float(rsi.iloc[-1]),1)
    agree=("BUY" in signal and trend_dir=="uptrend") or ("SELL" in signal and trend_dir=="downtrend")
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
        <b>📈 Price Movement Analysis</b><br><br>
        • Price has moved <b>{"+" if change_pct>0 else ""}{change_pct}%</b> over 30 days<br>
        • EMA20 is <b>{"rising ↗" if ema_slope>0 else "falling ↘"}</b> — momentum {"building" if ema_slope>0 else "fading"}<br>
        • RSI at <b>{last_rsi}</b> — {"overbought" if last_rsi>70 else "oversold" if last_rsi<30 else "bullish" if last_rsi>55 else "bearish" if last_rsi<45 else "neutral"}<br>
        • Overall structure: <b>{trend_dir.upper()}</b><br>
        • Resistance: <b>{round(resistance,4)}</b> | Support: <b>{round(support,4)}</b>
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
        <b>🎯 Trade Reasoning</b><br><br>
        • Signal: <b>{signal}</b><br>
        • {"✅ Trading WITH the trend — HIGHER probability" if agree else "⚠️ Trading AGAINST trend — reduce position size"}<br>
        • EMA stack: <b>{"Fully aligned ✅" if float(ema20.iloc[-1])>float(ema50.iloc[-1])>float(ema200.iloc[-1]) or float(ema20.iloc[-1])<float(ema50.iloc[-1])<float(ema200.iloc[-1]) else "Partially aligned ⚠️"}</b><br>
        • Entry risk: <b>{"Low — price at key level" if abs(last_price-support)/last_price<0.005 or abs(last_price-resistance)/last_price<0.005 else "Moderate — mid-range entry"}</b>
        </div>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# NEWS
# ════════════════════════════════════════════════════════════
def fetch_forex_news():
    try:
        r=requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",timeout=8)
        if r.status_code==200:
            return pd.DataFrame([{"Time":e.get("date","")[:16].replace("T"," "),
                "Currency":e.get("currency",""),"Event":e.get("title",""),
                "Impact":e.get("impact",""),"Forecast":e.get("forecast","—"),
                "Previous":e.get("previous","—")} for e in r.json()[:30]])
    except: pass
    return pd.DataFrame([
        {"Time":"Today 08:30","Currency":"USD","Event":"Non-Farm Payrolls","Impact":"High","Forecast":"180K","Previous":"175K"},
        {"Time":"Today 10:00","Currency":"EUR","Event":"ECB Rate Decision","Impact":"High","Forecast":"4.5%","Previous":"4.5%"},
        {"Time":"Today 13:30","Currency":"GBP","Event":"CPI y/y","Impact":"Medium","Forecast":"3.1%","Previous":"3.4%"},
        {"Time":"Tomorrow 08:30","Currency":"USD","Event":"Jobless Claims","Impact":"Medium","Forecast":"220K","Previous":"215K"},
        {"Time":"Tomorrow 14:00","Currency":"USD","Event":"FOMC Minutes","Impact":"High","Forecast":"—","Previous":"—"},
    ])

def call_ai(prompt,max_tokens=1000):
    try:
        api_key=st.secrets.get("ANTHROPIC_API_KEY","")
        if not api_key: return "⚠️ Add ANTHROPIC_API_KEY to Streamlit secrets."
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        if r.status_code==200: return r.json()["content"][0]["text"]
        return f"AI error {r.status_code}"
    except Exception as e: return f"Error: {e}"

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🚀 Sparro FX AI")
    st.divider()
    tier_label="👑 Admin" if is_admin else ("⚡ Premium" if premium else "🆓 Free")
    st.markdown(f"**{tier_label}**")
    st.caption(f"📧 {st.session_state.user_email}")
    if not premium and not is_admin:
        st.warning("🔒 Free Plan")
        if st.button("⚡ Upgrade — $24/mo"): st.info("Pay via Whop/Gumroad then contact admin.")
    else: st.success("✅ Active")
    if st.button("🚪 Logout"):
        for k in ["logged_in","user_email","user_tier","is_admin"]: st.session_state[k]=DEFAULTS.get(k,"")
        st.session_state.logged_in=False; st.rerun()
    st.divider()
    pages=["📊 Scanner","🏆 Trade of the Day","🔬 Deep Analysis",
           "📐 Multi-Timeframe","💹 Currency Strength","🎯 Precision Entry",
           "🏢 Prop Firm Tools","🗞️ News Analysis","🤖 AI Strategy Builder",
           "📸 AI Chart Analysis","🔔 Notifications","📓 Trade Journal",
           "📈 Performance","💰 Risk Calculator","⚙️ Settings","💎 Pricing"]
    if is_admin: pages.insert(0,"👑 Admin Panel")
    page=st.radio("Navigate",pages)

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ════════════════════════════════════════════════════════════
if "Admin" in page:
    st.title("👑 Admin Panel")
    all_users=get_all_users()
    prem=[u for u in all_users if u.get("tier")=="premium"]
    free=[u for u in all_users if u.get("tier")=="free"]
    c1,c2,c3=st.columns(3)
    c1.metric("👥 Total Users",len(all_users)); c2.metric("⚡ Premium",len(prem)); c3.metric("🆓 Free",len(free))
    st.divider()
    if all_users:
        st.subheader("👥 All Users")
        df_u=pd.DataFrame(all_users)
        cols=[c for c in ["email","tier","is_active","created_at"] if c in df_u.columns]
        st.dataframe(df_u[cols],use_container_width=True)
    st.divider()
    st.subheader("⚡ Manage User")
    ug_email=st.text_input("User email")
    c1,c2=st.columns(2)
    if c1.button("⬆️ Upgrade to Premium"):
        st.success(f"✅ Done!") if update_user_tier(ug_email,"premium") else st.error("❌ Failed.")
    if c2.button("⬇️ Move to Free"):
        st.success(f"✅ Done!") if update_user_tier(ug_email,"free") else st.error("❌ Failed.")
    st.divider()
    st.subheader("➕ Create User")
    c1,c2,c3=st.columns(3)
    ne=c1.text_input("Email",key="ne"); np_=c2.text_input("Password",type="password",key="np"); nt=c3.selectbox("Tier",["free","premium"])
    if st.button("Create User"):
        ok,err=create_user(ne,np_,nt)
        if ok: st.success("✅ Created!")
        else: st.error(f"❌ Failed: {err}")
    st.divider()
    st.subheader("🗑️ Delete User")
    de=st.text_input("Email to delete")
    if st.button("Delete",type="primary"):
        st.success("✅ Deleted!") if delete_user(de) else st.error("❌ Failed.")

# ════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ════════════════════════════════════════════════════════════
elif "Scanner" in page:
    st.title("📊 Market Scanner")
    if not premium: st.warning("🔒 Free plan: 5 assets. Upgrade for all 10 + Grade system.")
    results=[]; prog=st.progress(0); items=list(pairs.items())
    for i,(name,sym) in enumerate(items):
        strats,conf,sig,buys,sells=run_all_strategies(sym)
        grade,adj_conf,grade_note=get_signal_grade(conf,buys,sells,name)
        results.append({"Asset":name,"Signal":sig,
            "Grade":f"Grade {grade}" if premium else "🔒",
            "Confidence":f"{adj_conf}%" if premium else "🔒",
            "Strategies":f"{max(buys,sells)}/8" if premium else "🔒"})
        prog.progress((i+1)/len(items))
    prog.empty()
    scanner=pd.DataFrame(results)
    c1,c2=st.columns(2)
    with c1:
        st.subheader("🚀 Top Buys")
        st.dataframe(scanner[scanner["Signal"].str.contains("BUY",na=False)].head(3),use_container_width=True)
    with c2:
        st.subheader("📉 Top Sells")
        st.dataframe(scanner[scanner["Signal"].str.contains("SELL",na=False)].head(3),use_container_width=True)
    st.subheader("📊 Full Scanner")
    st.dataframe(scanner,use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: TRADE OF THE DAY
# ════════════════════════════════════════════════════════════
elif "Trade of the Day" in page:
    st.title("🏆 Trade of the Day")
    if not premium: st.error("🔒 Premium only."); st.stop()
    best={"conf":0,"sig":"WAIT","name":"","sym":"","strats":{},"grade":"D","buys":0,"sells":0}
    with st.spinner("Scanning all assets..."):
        for name,sym in ALL_PAIRS.items():
            strats,conf,sig,buys,sells=run_all_strategies(sym)
            grade,adj_conf,_=get_signal_grade(conf,buys,sells,name)
            if sig!="WAIT" and adj_conf>best["conf"]:
                best={"conf":adj_conf,"sig":sig,"name":name,"sym":sym,"strats":strats,"grade":grade,"buys":buys,"sells":sells}
    grade_colors={"A":"#3fb950","B":"#0072ff","C":"#ffd200","D":"#f85149"}
    grade_color=grade_colors.get(best["grade"],"#8b949e")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("🏆 Asset",best["name"]); c2.metric("📡 Signal",best["sig"])
    c3.metric("🎯 Confidence",f"{best['conf']}%"); c4.metric("📊 Grade",f"Grade {best['grade']}")
    st.progress(best["conf"]/100)
    st.markdown(f"<div style='background:{grade_color}22;border:1px solid {grade_color};border-radius:10px;padding:12px;text-align:center'><b style='color:{grade_color}'>Grade {best['grade']} Signal</b> — {get_signal_grade(best['conf'],best['buys'],best['sells'],best['name'])[2]}</div>",unsafe_allow_html=True)
    entry,sl,tp1,tp2,tp3,atr=get_trade_setup(best["sym"],best["sig"])
    if entry:
        st.divider()
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        col1,col2=st.columns(2)
        if col1.button("🔔 Telegram Alert"):
            ok=notify_trade(best["name"],best["sig"],best["conf"],best["grade"],entry,sl,tp1,tp2,tp3)
            st.success("✅ Sent!") if ok else st.error("❌ Check Notifications.")
        if col2.button("➕ Add to Journal"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),"Asset":best["name"],
                "Signal":best["sig"],"Grade":best["grade"],"Entry":entry,"SL":sl,"TP1":tp1,
                "Confidence":best["conf"],"Result":"Open"})
            st.success("✅ Added!")
    st.divider()
    if best["sym"]: show_price_chart(best["sym"],best["name"],best["sig"],entry,sl,tp1,tp2)

# ════════════════════════════════════════════════════════════
# PAGE: DEEP ANALYSIS
# ════════════════════════════════════════════════════════════
elif "Deep Analysis" in page:
    st.title("🔬 Deep Strategy Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    selected=st.selectbox("Choose Asset",list(ALL_PAIRS.keys())); sym=ALL_PAIRS[selected]
    with st.spinner("Running 8 strategies..."):
        strats,conf,sig,buys,sells=run_all_strategies(sym)
    grade,adj_conf,grade_note=get_signal_grade(conf,buys,sells,selected)
    grade_colors={"A":"#3fb950","B":"#0072ff","C":"#ffd200","D":"#f85149"}
    gc=grade_colors.get(grade,"#8b949e")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Signal",sig); c2.metric("Confidence",f"{adj_conf}%"); c3.metric("Grade",f"Grade {grade}"); c4.metric("Strategies","8")
    st.progress(adj_conf/100)
    st.markdown(f"<div style='background:{gc}22;border:1px solid {gc};border-radius:10px;padding:10px;text-align:center'><b style='color:{gc}'>Grade {grade}</b> — {grade_note}</div>",unsafe_allow_html=True)
    st.divider()
    for name,(s,reason) in strats.items():
        color="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
        icon="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:12px;margin-bottom:8px;border-left:4px solid {color}'>
          <b>{icon} {name}</b> <span style='background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px'>{s}</span><br>
          <small style='color:#8b949e'>{reason}</small></div>""",unsafe_allow_html=True)
    c1,c2,c3=st.columns(3); c1.metric("🟢 Buys",buys); c2.metric("🔴 Sells",sells); c3.metric("🟡 Neutral",8-buys-sells)
    entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
    if entry and sig!="WAIT":
        st.divider()
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        if adj_conf>=87: st.success(f"✅ Grade A — HIGHEST quality setup")
        elif adj_conf>=75: st.info(f"✅ Grade B — Good setup")
        elif adj_conf>=62: st.warning(f"⚠️ Grade C — Moderate setup, reduce size")
        else: st.error(f"❌ Grade D — Weak signal, consider waiting")
        if st.button("🔔 Telegram Alert"):
            ok=notify_trade(selected,sig,adj_conf,grade,entry,sl,tp1,tp2,tp3)
            st.success("✅ Sent!") if ok else st.error("❌ Check Notifications.")
    st.divider()
    show_price_chart(sym,selected,sig,entry,sl,tp1,tp2)

# ════════════════════════════════════════════════════════════
# PAGE: MULTI-TIMEFRAME
# ════════════════════════════════════════════════════════════
elif "Multi-Timeframe" in page:
    st.title("📐 Multi-Timeframe Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    selected=st.selectbox("Choose Asset",list(ALL_PAIRS.keys())); sym=ALL_PAIRS[selected]
    with st.spinner("Analysing all timeframes..."):
        tf_df=multi_timeframe_analysis(sym)
    st.subheader(f"📊 {selected} — All Timeframes")
    st.dataframe(tf_df,use_container_width=True)
    st.divider()
    buys_tf=len(tf_df[tf_df["Signal"].str.contains("BUY",na=False)])
    sells_tf=len(tf_df[tf_df["Signal"].str.contains("SELL",na=False)])
    total_tf=len(tf_df)
    overall="STRONG BUY" if buys_tf>=4 else "BUY" if buys_tf>=3 else "STRONG SELL" if sells_tf>=4 else "SELL" if sells_tf>=3 else "WAIT"
    alignment=round(max(buys_tf,sells_tf)/total_tf*100)
    c1,c2,c3=st.columns(3)
    c1.metric("Overall Signal",overall); c2.metric("TF Alignment",f"{alignment}%"); c3.metric("Bullish TFs",f"{buys_tf}/{total_tf}")
    st.progress(alignment/100)
    if alignment>=80: st.success(f"✅ STRONG alignment — {alignment}% of timeframes agree")
    elif alignment>=60: st.warning(f"⚠️ MODERATE alignment — {alignment}%")
    else: st.error(f"❌ WEAK alignment — {alignment}%. Wait for more confluence.")
    st.divider()
    st.subheader("💡 Timeframe Trading Guide")
    st.markdown("""
    | Timeframe | Best For | Hold Time |
    |-----------|----------|-----------|
    | 1H | Day Trading entries | 4-24 hours |
    | 4H | Swing trade confirmation | 1-5 days |
    | Daily | Trend direction | 1-4 weeks |
    | Weekly | Big picture bias | Months |
    | Monthly | Long-term position | Months+ |
    
    **Rule:** Always trade in the direction of the Daily + Weekly trend. Use 1H/4H for entry timing.
    """)

# ════════════════════════════════════════════════════════════
# PAGE: CURRENCY STRENGTH
# ════════════════════════════════════════════════════════════
elif "Currency Strength" in page:
    st.title("💹 Currency Strength Meter")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.spinner("Calculating strength of 8 currencies..."):
        strength=calculate_currency_strength()
    sorted_strength=dict(sorted(strength.items(),key=lambda x:x[1],reverse=True))
    st.subheader("📊 Currency Rankings (Strongest → Weakest)")
    for currency,score in sorted_strength.items():
        color="#3fb950" if score>=60 else "#f85149" if score<=40 else "#ffd200"
        emoji="🟢" if score>=60 else "🔴" if score<=40 else "🟡"
        st.markdown(f"""
        <div style='background:#161b22;border-radius:8px;padding:10px;margin-bottom:6px'>
        {emoji} <b>{currency}</b> &nbsp;
        <div style='background:#21262d;border-radius:4px;height:20px;width:100%;margin-top:4px'>
          <div style='background:{color};width:{score}%;height:20px;border-radius:4px'></div>
        </div>
        <small style='color:#8b949e'>{score}/100</small>
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.subheader("💡 Best Pairs to Trade Right Now")
    currencies=list(sorted_strength.keys())
    if len(currencies)>=2:
        strongest=currencies[0]; weakest=currencies[-1]
        st.success(f"🚀 **BUY {strongest}** against **{weakest}** — biggest strength divergence")
        st.info(f"📊 Strongest currency: **{strongest}** ({sorted_strength[strongest]}/100)")
        st.info(f"📊 Weakest currency:   **{weakest}** ({sorted_strength[weakest]}/100)")

# ════════════════════════════════════════════════════════════
# PAGE: PRECISION ENTRY
# ════════════════════════════════════════════════════════════
elif "Precision Entry" in page:
    st.title("🎯 Precision Entry Tools")
    if not premium: st.error("🔒 Premium only."); st.stop()
    col1,col2=st.columns(2)
    with col1:
        selected=st.selectbox("Asset",list(ALL_PAIRS.keys())); sym=ALL_PAIRS[selected]
        _,conf,sig,buys,sells=run_all_strategies(sym)
        direction=st.selectbox("Direction",["BUY","SELL"],index=0 if "BUY" in sig else 1)
    with col2:
        account_size=st.number_input("Account Size ($)",min_value=100.0,value=1000.0)
        risk_pct=st.slider("Risk per trade (%)",0.5,5.0,2.0,step=0.5)

    if st.button("🎯 Calculate Precision Entries"):
        entries,atr,price=get_precision_entry(sym,direction,account_size,risk_pct)
        st.divider()
        st.subheader(f"🎯 {direction} Entry Options for {selected}")
        st.caption(f"Current Price: {round(price,5)} | ATR(14): {atr}")
        for entry_type,vals in entries.items():
            color="#1a472a" if direction=="BUY" else "#3d1f1f"
            st.markdown(f"""
            <div style='background:{color};border-radius:10px;padding:14px;margin-bottom:10px'>
            <b>📍 {entry_type}</b><br>
            Entry: <code>{round(vals['entry'],5)}</code> | 
            SL: <code>{round(vals['sl'],5)}</code> | 
            TP1: <code>{round(vals['tp1'],5)}</code> | 
            TP2: <code>{round(vals['tp2'],5)}</code> | 
            TP3: <code>{round(vals['tp3'],5)}</code><br>
            Lot Size: <b>{vals['lot_size']}</b> | Risk: <b>${round(vals['risk_amount'],2)}</b>
            </div>""",unsafe_allow_html=True)
        st.info("💡 **Aggressive**: Enter now at market. **Standard**: Best balance of risk/reward. **Conservative**: Wait for pullback to EMA20.")

# ════════════════════════════════════════════════════════════
# PAGE: PROP FIRM TOOLS
# ════════════════════════════════════════════════════════════
elif "Prop Firm" in page:
    st.title("🏢 Prop Firm Tools")
    if not premium: st.error("🔒 Premium only."); st.stop()
    st.info("Calculate safe position sizes and track your challenge progress for major prop firms.")
    col1,col2=st.columns(2)
    with col1:
        firm=st.selectbox("Prop Firm",["FTMO","MyForexFunds","The5ers","FundedNext"])
        account_size=st.number_input("Account Size ($)",min_value=1000.0,value=10000.0)
    with col2:
        current_profit=st.number_input("Current Profit ($)",value=0.0)
        current_loss=st.number_input("Current Loss ($)",value=0.0,min_value=0.0)

    result=prop_firm_calculator(account_size,firm,current_profit,current_loss)
    st.divider()
    st.subheader(f"📊 {firm} Challenge Rules — ${account_size:,.0f} Account")
    c1,c2,c3=st.columns(3)
    c1.metric("Daily Loss Limit",   f"${result['daily_loss_limit']:,.0f}",  f"{result['daily_loss_pct']}%")
    c2.metric("Max Loss Limit",     f"${result['max_loss_limit']:,.0f}",    f"{result['max_loss_pct']}%")
    c3.metric("Profit Target",      f"${result['profit_target']:,.0f}",     f"{result['profit_target_pct']}%")

    st.divider()
    st.subheader("📈 Your Current Status")
    c1,c2,c3=st.columns(3)
    c1.metric("Remaining Daily Limit",f"${result['remaining_daily']:,.0f}")
    c2.metric("Remaining Max Limit",  f"${result['remaining_max']:,.0f}")
    c3.metric("Profit Still Needed",  f"${result['profit_needed']:,.0f}")

    st.divider()
    daily_used=abs(current_loss)/result['daily_loss_limit'] if result['daily_loss_limit']>0 else 0
    if daily_used>=1: st.error("🚨 DAILY LOSS LIMIT REACHED — Stop trading today!")
    elif daily_used>=0.7: st.warning(f"⚠️ {round(daily_used*100)}% of daily loss limit used — be careful")
    else: st.success(f"✅ {round(daily_used*100)}% of daily limit used — safe to trade")
    st.progress(min(daily_used,1.0))

    st.subheader("💰 Safe Lot Size for Next Trade")
    st.metric("Recommended Lot Size",f"{result['safe_lot']} lots")
    st.caption("Based on remaining daily limit with conservative risk management")

    st.divider()
    st.subheader("📋 Prop Firm Trading Rules")
    st.markdown(f"""
    **{firm} Key Rules:**
    - ❌ Never lose more than **{result['daily_loss_pct']}%** in one day (${result['daily_loss_limit']:,.0f})
    - ❌ Never lose more than **{result['max_loss_pct']}%** total (${result['max_loss_limit']:,.0f})
    - ✅ Reach **{result['profit_target_pct']}%** profit target (${result['profit_target']:,.0f})
    - 📊 Always use the recommended lot size above
    - 🕐 Trade during high-liquidity sessions (London + NY)
    - 📰 Avoid trading during high-impact news events
    - 🎯 Only take Grade A and Grade B signals
    """)

# ════════════════════════════════════════════════════════════
# PAGE: NEWS ANALYSIS
# ════════════════════════════════════════════════════════════
elif "News" in page:
    st.title("🗞️ News Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.spinner("Fetching calendar..."): news_df=fetch_forex_news()
    st.subheader("📅 Economic Calendar — This Week")
    st.dataframe(news_df,use_container_width=True)
    st.divider()
    selected=st.selectbox("Asset for AI analysis",list(ALL_PAIRS.keys()))
    if st.button("🤖 AI News Analysis"):
        with st.spinner("Analysing news impact..."):
            analysis=call_ai(f"You are a professional forex news analyst. Analyse how this week's economic calendar affects {selected}.\nCalendar:\n{news_df.to_string()}\n\nProvide:\n1. Which events affect {selected} most\n2. Bullish/Bearish/Neutral bias\n3. Times to avoid trading\n4. Biggest move potential\nBe concise, use bullet points.",1000)
        st.markdown(f"<div class='news-card'>{analysis.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
    if "Impact" in news_df.columns:
        high=news_df[news_df["Impact"]=="High"]
        if not high.empty:
            st.subheader("⚠️ High-Impact Events")
            for _,row in high.iterrows():
                st.error(f"🔴 {row.get('Time','')} | {row.get('Currency','')} — {row.get('Event','')} | Forecast: {row.get('Forecast','—')}")

# ════════════════════════════════════════════════════════════
# PAGE: AI STRATEGY BUILDER
# ════════════════════════════════════════════════════════════
elif "AI Strategy" in page:
    st.title("🤖 AI Strategy Builder")
    if not premium: st.error("🔒 Premium only."); st.stop()
    col1,col2=st.columns(2)
    with col1:
        style     =st.selectbox("Style",["Day Trading","Scalping","Swing Trading"])
        risk_level=st.selectbox("Risk",["Conservative","Moderate","Aggressive"])
        fav_pairs =st.multiselect("Favourite Pairs",list(ALL_PAIRS.keys()),default=["EUR/USD","Gold (XAU/USD)"])
    with col2:
        session   =st.selectbox("Session",["London","New York","Asian","All Sessions"])
        experience=st.selectbox("Experience",["Beginner","Intermediate","Advanced"])
        custom    =st.text_area("Extra requirements",placeholder="e.g. only breakouts, trend following, specific indicators...")
    if st.button("🚀 Build My Strategy",type="primary"):
        prompt=f"""You are a professional forex trading strategy builder.
Build a complete, detailed {style} strategy.
Trader: {experience} level, {risk_level} risk, trades {session} session.
Favourite pairs: {', '.join(fav_pairs)}.
Extra requirements: {custom}

Include these sections:
1. 📋 Strategy Name & Summary
2. ✅ Exact Entry Rules (step by step)
3. 🛑 Stop Loss Placement (specific rules)
4. 🎯 Take Profit Targets (TP1=1R, TP2=2R, TP3=3R or specific levels)
5. ⏰ Best Timeframes to use
6. 💰 Position Sizing & Risk Rules
7. 📊 Best Assets for this strategy
8. 📰 News filter rules (when to avoid)
9. ❌ What NOT to do
10. 📈 Backtesting tips

Be very specific and practical. Real rules a trader can follow immediately."""
        with st.spinner("🤖 Building your strategy..."):
            strategy=call_ai(prompt,1500)
            st.session_state.ai_strategy=strategy
    if st.session_state.ai_strategy:
        st.divider()
        st.subheader("📋 Your Custom Strategy")
        st.markdown(f"<div class='strategy-card'>{st.session_state.ai_strategy.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
        if st.button("💾 Save to Journal"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),"Asset":"Strategy",
                "Signal":"AI BUILT","Grade":"A","Entry":0,"SL":0,"TP1":0,"Confidence":0,
                "Result":"Strategy","Notes":st.session_state.ai_strategy[:300]})
            st.success("✅ Saved!")

# ════════════════════════════════════════════════════════════
# PAGE: AI CHART ANALYSIS
# ════════════════════════════════════════════════════════════
elif "Chart Analysis" in page:
    st.title("📸 AI Chart Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    st.info("Upload a screenshot of any chart and AI will analyse it for you.")
    uploaded=st.file_uploader("Upload chart screenshot",type=["png","jpg","jpeg","webp"])
    pair_context=st.selectbox("Which pair is this?",["Not sure"]+list(ALL_PAIRS.keys()))
    tf_context=st.selectbox("Timeframe",["Not sure","1M","5M","15M","1H","4H","Daily","Weekly"])
    extra=st.text_area("Any specific questions?",placeholder="e.g. Is this a good entry? Where is support? What pattern is forming?")

    if uploaded and st.button("🔍 Analyse Chart",type="primary"):
        import base64
        img_bytes=uploaded.read()
        img_b64=base64.b64encode(img_bytes).decode()
        ext=uploaded.name.split(".")[-1].lower()
        media_type=f"image/{'jpeg' if ext in ['jpg','jpeg'] else ext}"
        prompt=f"""You are a professional forex technical analyst.
Analyse this trading chart screenshot.
Pair: {pair_context} | Timeframe: {tf_context}
Trader's question: {extra if extra else 'Give a complete technical analysis'}

Provide:
1. 📊 Overall trend direction
2. 🔑 Key support and resistance levels you can see
3. 📐 Any chart patterns (head & shoulders, triangles, flags, etc.)
4. 🕯️ Candlestick patterns visible
5. 📈 Indicator readings if visible (RSI, MACD, EMAs)
6. 🎯 Recommended trade direction (BUY/SELL/WAIT)
7. 💰 Suggested entry, stop loss and take profit
8. ⚠️ Key risks or things to watch

Be specific and actionable."""
        with st.spinner("🤖 Analysing your chart..."):
            try:
                api_key=st.secrets.get("ANTHROPIC_API_KEY","")
                if not api_key: st.error("⚠️ Add ANTHROPIC_API_KEY to secrets."); st.stop()
                r=requests.post("https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                    json={"model":"claude-sonnet-4-6","max_tokens":1200,
                        "messages":[{"role":"user","content":[
                            {"type":"image","source":{"type":"base64","media_type":media_type,"data":img_b64}},
                            {"type":"text","text":prompt}
                        ]}]},timeout=40)
                if r.status_code==200:
                    analysis=r.json()["content"][0]["text"]
                    st.subheader("🤖 AI Analysis")
                    st.markdown(f"<div class='strategy-card'>{analysis.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
                else: st.error(f"API error {r.status_code}")
            except Exception as e: st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════
# PAGE: NOTIFICATIONS
# ════════════════════════════════════════════════════════════
elif "Notifications" in page:
    st.title("🔔 Telegram Notifications")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("📖 Setup Guide"):
        st.markdown("""
1. Search `@BotFather` on Telegram → `/newbot` → copy **Bot Token**
2. Search `@userinfobot` → send message → copy **Chat ID**
3. Paste below and test!
        """)
    token  =st.text_input("Bot Token",  value=st.session_state.telegram_token,  type="password")
    chat_id=st.text_input("Chat ID",    value=st.session_state.telegram_chat_id)
    if st.button("💾 Save"):
        st.session_state.telegram_token=token; st.session_state.telegram_chat_id=chat_id; st.success("✅ Saved!")
    if st.button("🧪 Send Test"):
        ok=send_telegram(token,chat_id,"✅ *Sparro FX AI* — Telegram connected! Grade A signals will be sent here. 🚀")
        st.success("✅ Check Telegram!") if ok else st.error("❌ Failed — check token and chat ID.")
    st.divider()
    threshold=st.slider("Minimum confidence to alert (%)",60,95,st.session_state.notification_threshold)
    st.session_state.notification_threshold=threshold
    st.info(f"Alerts fire when confidence ≥ {threshold}% (Grade A/B signals only recommended)")

# ════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("➕ Log a Trade"):
        c1,c2,c3,c4=st.columns(4)
        j_asset=c1.selectbox("Asset",list(ALL_PAIRS.keys()))
        j_sig=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"])
        j_grade=c3.selectbox("Grade",["A","B","C","D"])
        j_result=c4.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c5,c6,c7=st.columns(3)
        j_entry=c5.number_input("Entry",format="%.5f")
        j_conf=c6.slider("Confidence",0,100,75)
        j_notes=c7.text_input("Notes")
        if st.button("Save Trade"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),
                "Asset":j_asset,"Signal":j_sig,"Grade":j_grade,"Entry":j_entry,
                "Confidence":j_conf,"Result":j_result,"Notes":j_notes})
            st.success("✅ Saved!")
    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal); st.dataframe(df,use_container_width=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); total=wins+loss
        wr=round(wins/total*100,1) if total>0 else 0
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total",len(df)); c2.metric("Win Rate",f"{wr}%")
        c3.metric("Open",len(df[df["Result"]=="Open"])); c4.metric("Wins",wins)
        if "Grade" in df.columns:
            st.subheader("Performance by Grade")
            grade_perf=df.groupby("Grade")["Result"].value_counts().unstack(fill_value=0)
            st.dataframe(grade_perf,use_container_width=True)
    else: st.info("No trades yet. Use Trade of the Day to auto-log setups.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.title("📈 Performance Dashboard")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"])
    be=len(df[df["Result"]=="Breakeven"]); total=wins+loss+be
    wr=round(wins/total*100,1) if total>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total Trades",total); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
    st.divider()
    if "Asset" in df.columns:
        st.subheader("By Asset")
        st.dataframe(df.groupby("Asset")["Result"].value_counts().unstack(fill_value=0),use_container_width=True)
    if "Grade" in df.columns:
        st.subheader("By Signal Grade")
        st.dataframe(df.groupby("Grade")["Result"].value_counts().unstack(fill_value=0),use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ════════════════════════════════════════════════════════════
elif "Risk" in page:
    st.title("💰 Risk Calculator")
    c1,c2=st.columns(2)
    with c1:
        balance=st.number_input("Balance ($)",min_value=10.0,value=1000.0)
        risk_pct=st.slider("Risk %",0.5,10.0,2.0,step=0.5)
        sl_pips=st.number_input("Stop Loss (pips)",min_value=1.0,value=20.0)
        pip_val=st.number_input("Pip value per 0.01 lot",value=0.10)
        rr=st.slider("Risk:Reward",1,5,2)
    risk_amt=balance*risk_pct/100; lot=round(risk_amt/(sl_pips*pip_val/0.01)*0.01,2)
    with c2:
        st.metric("Risk Amount",f"${risk_amt:.2f}"); st.metric("Lot Size",f"{lot} lots")
        st.metric("Potential Profit",f"${risk_amt*rr:.2f}"); st.metric("R:R",f"1:{rr}")
        st.metric("Account After Loss",f"${balance-risk_amt:.2f}")
        st.metric("Account After Win", f"${balance+(risk_amt*rr):.2f}")
    st.progress(risk_pct/10)
    if risk_pct<=1: st.success("✅ Ultra conservative — good for prop firms")
    elif risk_pct<=2: st.success("✅ Conservative — good for consistency")
    elif risk_pct<=5: st.warning("⚠️ Moderate — manage carefully")
    else: st.error("🚨 High risk — professionals only")

# ════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ════════════════════════════════════════════════════════════
elif "Settings" in page:
    st.title("⚙️ Settings")
    st.subheader("🔑 Change Password")
    old_pass=st.text_input("Current Password",type="password")
    new_pass=st.text_input("New Password",type="password")
    new_pass2=st.text_input("Confirm New Password",type="password")
    if st.button("Update Password"):
        user=get_user(st.session_state.user_email)
        if user and user["password_hash"]==hash_password(old_pass):
            if new_pass==new_pass2 and len(new_pass)>=6:
                try:
                    requests.patch(supabase_url(f"users?email=eq.{st.session_state.user_email}"),
                        headers=get_supabase_headers(),json={"password_hash":hash_password(new_pass)})
                    st.success("✅ Password updated!")
                except: st.error("❌ Failed.")
            else: st.error("❌ Passwords don't match or too short.")
        else: st.error("❌ Current password incorrect.")
    st.divider()
    st.subheader("🔔 Telegram")
    t=st.text_input("Bot Token",value=st.session_state.telegram_token,type="password")
    c=st.text_input("Chat ID",value=st.session_state.telegram_chat_id)
    if st.button("Save Telegram"):
        st.session_state.telegram_token=t; st.session_state.telegram_chat_id=c; st.success("✅ Saved!")
    st.divider()
    st.subheader("🔑 API Key Status")
    api_key=st.secrets.get("ANTHROPIC_API_KEY","")
    if api_key: st.success("✅ Anthropic API key configured — AI features active")
    else: st.error("❌ No Anthropic API key — add to Streamlit secrets")

# ════════════════════════════════════════════════════════════
# PAGE: PRICING
# ════════════════════════════════════════════════════════════
elif "Pricing" in page:
    st.title("💎 Upgrade to Premium")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'><h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        ✅ Account login<br><br>✅ 5 assets<br><br>✅ Basic signals<br><br>
        ❌ Grade A/B/C/D system<br><br>❌ 8-strategy engine<br><br>
        ❌ Price charts + indicators<br><br>❌ Multi-timeframe analysis<br><br>
        ❌ Currency strength meter<br><br>❌ Precision entry tools<br><br>
        ❌ Prop firm tools<br><br>❌ News + AI analysis<br><br>
        ❌ AI Strategy Builder<br><br>❌ AI Chart Analysis<br><br>
        ❌ Telegram alerts<br><br>❌ Trade Journal + Performance
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'><h3>⚡ Premium</h3><h2>$24/mo</h2><hr>
        ✅ All 10 assets<br><br>✅ 🏆 Grade A/B/C/D signal quality<br><br>
        ✅ 8-strategy engine<br><br>✅ 📈 Price charts (Candles+RSI+MACD)<br><br>
        ✅ 📐 Multi-timeframe analysis (1H to Monthly)<br><br>
        ✅ 💹 Currency strength meter<br><br>✅ 🎯 Precision entry tools<br><br>
        ✅ 🏢 Prop firm tools (FTMO, The5ers etc)<br><br>
        ✅ 🗞️ News + AI news analysis<br><br>✅ 🤖 AI Strategy Builder<br><br>
        ✅ 📸 AI Chart Analysis (upload any chart)<br><br>
        ✅ 🔔 Telegram alerts<br><br>
        ✅ 📓 Trade Journal + 📈 Performance Dashboard
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.markdown("""
    **💳 How to upgrade:**
    1. Pay \$24/mo on **[Whop](https://whop.com)** or **[Gumroad](https://gumroad.com)**
    2. Email your receipt to the admin
    3. Admin upgrades your account → login again → Premium unlocked ✅

    **Recommended: [Whop.com](https://whop.com)** — built for trading tools like this
    """)
