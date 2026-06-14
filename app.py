import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib

st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")
st.markdown("""
<style>
  body,.main{background:#0d1117;color:#e6edf3}
  .block-container{padding-top:1.5rem}
  .stTabs [data-baseweb="tab-list"]{gap:6px;background:#161b22;border-radius:12px;padding:6px}
  .stTabs [data-baseweb="tab"]{border-radius:8px;padding:8px 16px;color:#8b949e;font-weight:600;font-size:13px}
  .stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0072ff,#00c6ff) !important;color:#fff !important}
  .stMetric{background:#161b22;border-radius:10px;padding:12px}
  .stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}
  .tier-box{background:#161b22;border-radius:14px;padding:20px;text-align:center;border:2px solid #30363d}
  .tier-box.gold{border-color:#ffd200}
  .card{background:#161b22;border-radius:12px;padding:16px;margin-bottom:10px;border:1px solid #30363d}
  .login-box{background:#161b22;border-radius:16px;padding:30px 26px;border:1px solid #30363d}
  .pulse-live{display:inline-block;width:10px;height:10px;background:#3fb950;
    border-radius:50%;margin-right:6px;animation:blink 1.2s infinite}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
  .news-trade-card{background:#161b22;border-radius:12px;padding:16px;
    margin-bottom:10px;border-left:4px solid #ffd200}
  .smc-tag{background:#7c3aed;color:#fff;border-radius:6px;
    padding:2px 8px;font-size:11px;font-weight:700;margin-left:4px}
  .ticket-card{background:#161b22;border-radius:12px;padding:16px;
    margin-bottom:10px;border:2px solid #0072ff}
  .history-row{background:#161b22;border-radius:8px;padding:10px 14px;
    margin-bottom:6px;border-left:3px solid #30363d;font-size:13px}
</style>
""", unsafe_allow_html=True)

# ════════ PERSISTENT LOGIN ════════
def make_token(at, email, ts):
    return hashlib.sha256(f"{at}|{email}|{ts}|sparro_salt_2024".encode()).hexdigest()[:16]

def save_login(at, email, trial_start=None):
    ts = trial_start.isoformat() if trial_start else ""
    st.query_params["session"] = f"{at}|{email}|{ts}|{make_token(at,email,ts)}"

def load_login():
    try:
        raw = st.query_params.get("session","")
        if not raw: return None
        p = raw.split("|")
        if len(p)!=4: return None
        at,email,ts,token = p
        if token != make_token(at,email,ts): return None
        return {"account_type":at,"email":email,
                "trial_start":datetime.datetime.fromisoformat(ts) if ts else None}
    except: return None

def clear_login(): st.query_params.clear()

# ════════ SESSION STATE ════════
DEFAULTS = {
    "logged_in":False,"account_type":None,"trial_start":None,
    "user_email":"","trade_journal":[],"subscribers":[],
    "signal_history":[],"session_loaded":False,"active_page":"Dashboard",
    "last_main_nav":"Dashboard",
}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.session_loaded:
    saved=load_login()
    if saved: st.session_state.update(logged_in=True,**saved)
    st.session_state.session_loaded=True

def _secret(k,fb):
    try: return st.secrets.get(k,fb)
    except: return fb

ADMIN_PASSWORD   = _secret("ADMIN_PASSWORD","sparro_admin_2024")
PREMIUM_PASSWORD = _secret("PREMIUM_PASSWORD","sparro_pro_2024")
FREE_PASSWORD    = _secret("FREE_PASSWORD","sparro_free")
TRIAL_HOURS      = 48

def trial_hours_left():
    if not st.session_state.trial_start: return 0
    return max(0,TRIAL_HOURS-int((datetime.datetime.now()-st.session_state.trial_start).total_seconds()/3600))

def is_premium():
    if st.session_state.account_type in ("premium","admin"): return True
    if st.session_state.account_type=="trial" and trial_hours_left()>0: return True
    return False

# ════════ LOGIN PAGE ════════
def show_login():
    st.markdown("""<div style='max-width:480px;margin:50px auto 0 auto;text-align:center'>
      <div style='font-size:64px'>🚀</div>
      <div style='font-size:38px;font-weight:900;background:linear-gradient(90deg,#00c6ff,#0072ff);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent'>Sparro FX AI</div>
      <div style='color:#8b949e;font-size:15px;margin-bottom:28px'>Professional AI-Powered Forex Signal Platform</div>
    </div>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,2,1])
    with col:
        t1,t2,t3=st.tabs(["🔑 Login","🎁 Free 48hr Trial","ℹ️ About"])
        with t1:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            st.markdown("#### Welcome back 👋")
            email=st.text_input("Email",placeholder="you@email.com",key="li_e")
            pw=st.text_input("Password",type="password",placeholder="Your password",key="li_p")
            rem=st.checkbox("Keep me logged in",value=True)
            if st.button("🔓 Login",use_container_width=True,type="primary"):
                at=("admin" if pw.strip()==ADMIN_PASSWORD else
                    "premium" if pw.strip()==PREMIUM_PASSWORD else
                    "free" if pw.strip()==FREE_PASSWORD else None)
                if at:
                    st.session_state.update(logged_in=True,account_type=at,user_email=email)
                    if rem: save_login(at,email)
                    st.rerun()
                else: st.error("❌ Incorrect password.")
            st.markdown("</div>",unsafe_allow_html=True)
        with t2:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;margin-bottom:14px'>
              <span style='background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;
              border-radius:20px;padding:6px 18px;font-weight:700'>🎁 48 Hours FREE — Full Premium</span>
            </div>""",unsafe_allow_html=True)
            st.markdown("""Full access for 48 hours — no card needed:
- ✅ All 10 assets · 8 pro strategies + SMC
- ✅ Multi-timeframe confirmation
- ✅ ⚡ Pulse Signal + Signal History
- ✅ Auto Trade Ticket Panel
- ✅ News Trading + AI Analysis""")
            te=st.text_input("Email",placeholder="you@email.com",key="tr_e")
            tn=st.text_input("Name",placeholder="First name",key="tr_n")
            if st.button("🚀 Start Free Trial",use_container_width=True,type="primary"):
                if not te or "@" not in te: st.error("❌ Valid email required.")
                elif not tn.strip(): st.error("❌ Name required.")
                else:
                    ts=datetime.datetime.now()
                    st.session_state.update(logged_in=True,account_type="trial",
                                            trial_start=ts,user_email=te)
                    save_login("trial",te,ts); st.rerun()
            st.markdown("</div>",unsafe_allow_html=True)
        with t3:
            st.markdown("""<div class='login-box'>
            <h4 style='margin-top:0'>What is Sparro FX AI?</h4>
            <p style='color:#8b949e'>8 institutional strategies including SMC, multi-timeframe analysis,
            live Pulse Signal, auto trade tickets, signal history and news trading.</p>
            <b>🆓 Free</b> — 5 assets, basic signals<br><br>
            <b>🎁 Trial (48h)</b> — full premium, no card<br><br>
            <b>⚡ Premium $15/mo</b> — everything<br><br>
            <hr style='border-color:#30363d'>
            <span style='color:#8b949e;font-size:12px'>Trade responsibly. Past signals do not guarantee future results.</span>
            </div>""",unsafe_allow_html=True)

if not st.session_state.logged_in: show_login(); st.stop()
if st.session_state.account_type=="trial" and trial_hours_left()==0:
    st.error("⏰ Your 48-hour free trial has ended.")
    st.markdown("### Upgrade to Premium — $15/mo\nContact us to get your premium password.")
    if st.button("🔓 Login with premium password"):
        clear_login(); st.session_state.logged_in=False; st.rerun()
    st.stop()

premium=is_premium()
atype=st.session_state.account_type

# ════════ ASSETS ════════
ALL_PAIRS={
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS=dict(list(ALL_PAIRS.items())[:5])
pairs=ALL_PAIRS if premium else FREE_PAIRS

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
# STRATEGIES
# ════════════════════════════════════════════════════════════
def strategy_ema_trend(df):
    c=df["Close"]
    e20=c.ewm(span=20).mean().iloc[-1]; e50=c.ewm(span=50).mean().iloc[-1]; e200=c.ewm(span=200).mean().iloc[-1]
    if e20>e50 and e50>e200: return "BUY","EMA20 > EMA50 > EMA200 — full bullish stack"
    if e20<e50 and e50<e200: return "SELL","EMA20 < EMA50 < EMA200 — full bearish stack"
    if e20>e200: return "BUY","Price above EMA200 — long-term bullish bias"
    if e20<e200: return "SELL","Price below EMA200 — long-term bearish bias"
    return "NEUTRAL","EMA stack mixed"

def strategy_rsi(df):
    c=df["Close"]; d=c.diff()
    g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
    rsi=(100-(100/(1+(g/l)))).iloc[-1]
    if rsi>65: return "BUY",f"RSI={round(rsi,1)} — strong bullish momentum"
    if rsi>55: return "BUY",f"RSI={round(rsi,1)} — moderate bullish momentum"
    if rsi<35: return "SELL",f"RSI={round(rsi,1)} — strong bearish momentum"
    if rsi<45: return "SELL",f"RSI={round(rsi,1)} — moderate bearish momentum"
    return "NEUTRAL",f"RSI={round(rsi,1)} — neutral"

def strategy_macd(df):
    c=df["Close"]; m=c.ewm(span=12).mean()-c.ewm(span=26).mean()
    s=m.ewm(span=9).mean(); h=m-s
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2] and m.iloc[-1]>0: return "BUY","MACD bullish crossover above zero"
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2]: return "BUY","MACD bullish crossover"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2] and m.iloc[-1]<0: return "SELL","MACD bearish crossover below zero"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2]: return "SELL","MACD bearish crossover"
    return "NEUTRAL","MACD no clear crossover"

def strategy_sr(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    res=float(h.rolling(20).max().iloc[-1]); sup=float(l.rolling(20).min().iloc[-1]); zone=(res-sup)*0.12
    if p>=res-zone: return "SELL",f"At resistance {round(res,4)} — rejection likely"
    if p<=sup+zone: return "BUY",f"At support {round(sup,4)} — bounce likely"
    if p>(res+sup)/2+zone: return "BUY",f"Above midrange — bullish bias"
    if p<(res+sup)/2-zone: return "SELL",f"Below midrange — bearish bias"
    return "NEUTRAL",f"S={round(sup,4)} R={round(res,4)}"

def strategy_adx(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        up=h.diff(); dn=-l.diff()
        pdm=up.where((up>dn)&(up>0),0); ndm=dn.where((dn>up)&(dn>0),0)
        p=14; atr=tr.ewm(span=p).mean()
        pdi=100*(pdm.ewm(span=p).mean()/atr); ndi=100*(ndm.ewm(span=p).mean()/atr)
        adx=((100*(pdi-ndi).abs()/(pdi+ndi)).ewm(span=p).mean()).iloc[-1]
        pv=pdi.iloc[-1]; nv=ndi.iloc[-1]
        if adx>=30 and pv>nv: return "BUY",f"ADX={round(adx,1)} — strong uptrend confirmed"
        if adx>=30 and nv>pv: return "SELL",f"ADX={round(adx,1)} — strong downtrend confirmed"
        if adx>=20 and pv>nv: return "BUY",f"ADX={round(adx,1)} — moderate uptrend"
        if adx>=20 and nv>pv: return "SELL",f"ADX={round(adx,1)} — moderate downtrend"
        return "NEUTRAL",f"ADX={round(adx,1)} — weak/ranging market"
    except: return "NEUTRAL","ADX error"

def strategy_stochastic(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        lm=l.rolling(14).min(); hm=h.rolling(14).max()
        k=100*(c-lm)/(hm-lm); d=k.rolling(3).mean()
        kv=k.iloc[-1]; dv=d.iloc[-1]; kp=k.iloc[-2]
        if kv<20 and dv<20: return "BUY",f"Stoch K={round(kv,1)} — oversold, strong BUY zone"
        if kv<35 and kv>kp and kv>dv: return "BUY",f"Stoch K={round(kv,1)} — bullish crossover"
        if kv>80 and dv>80: return "SELL",f"Stoch K={round(kv,1)} — overbought, strong SELL zone"
        if kv>65 and kv<kp and kv<dv: return "SELL",f"Stoch K={round(kv,1)} — bearish crossover"
        return "NEUTRAL",f"Stoch K={round(kv,1)} — neutral"
    except: return "NEUTRAL","Stochastic error"

def strategy_smc_orderblock(df):
    try:
        o=df["Open"]; h=df["High"]; l=df["Low"]; c=df["Close"]
        cp=float(c.iloc[-1]); bobs=[]; sobs=[]
        for i in range(2,min(50,len(df)-3)):
            idx=-i
            if c.iloc[idx]<o.iloc[idx]:
                if c.iloc[idx+1]>o.iloc[idx+1] and c.iloc[idx+2]>o.iloc[idx+2] and c.iloc[idx+2]>h.iloc[idx]:
                    bobs.append((float(l.iloc[idx]),float(h.iloc[idx])))
            if c.iloc[idx]>o.iloc[idx]:
                if c.iloc[idx+1]<o.iloc[idx+1] and c.iloc[idx+2]<o.iloc[idx+2] and c.iloc[idx+2]<l.iloc[idx]:
                    sobs.append((float(l.iloc[idx]),float(h.iloc[idx])))
        for lo,hi in bobs[:3]:
            if lo<=cp<=hi*1.002: return "BUY",f"SMC Bullish Order Block {round(lo,4)}-{round(hi,4)} — institutional buy zone"
        for lo,hi in sobs[:3]:
            if lo*0.998<=cp<=hi: return "SELL",f"SMC Bearish Order Block {round(lo,4)}-{round(hi,4)} — institutional sell zone"
        for lo,hi in bobs[:3]:
            if cp<=hi*1.01 and cp>hi: return "BUY",f"SMC Approaching Bullish OB {round(lo,4)}-{round(hi,4)}"
        for lo,hi in sobs[:3]:
            if cp>=lo*0.99 and cp<lo: return "SELL",f"SMC Approaching Bearish OB {round(lo,4)}-{round(hi,4)}"
        return "NEUTRAL","SMC No active order blocks near price"
    except: return "NEUTRAL","SMC Order Block — insufficient data"

def strategy_smc_fvg(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        cp=float(c.iloc[-1]); bfvgs=[]; sfvgs=[]
        for i in range(2,min(40,len(df)-3)):
            idx=-i
            ph=float(h.iloc[idx-1]); nl=float(l.iloc[idx+1])
            if nl>ph and (nl-ph)/ph>0.001: bfvgs.append((ph,nl))
            pl=float(l.iloc[idx-1]); nh=float(h.iloc[idx+1])
            if pl>nh and (pl-nh)/pl>0.001: sfvgs.append((nh,pl))
        for lo,hi in bfvgs[:4]:
            if lo<=cp<=hi: return "BUY",f"SMC Bullish FVG {round(lo,4)}-{round(hi,4)} — filling imbalance"
            if cp<=lo*1.005: return "BUY",f"SMC Bullish FVG magnet at {round(lo,4)}-{round(hi,4)}"
        for lo,hi in sfvgs[:4]:
            if lo<=cp<=hi: return "SELL",f"SMC Bearish FVG {round(lo,4)}-{round(hi,4)} — filling imbalance"
            if cp>=hi*0.995: return "SELL",f"SMC Bearish FVG magnet at {round(lo,4)}-{round(hi,4)}"
        return "NEUTRAL","SMC No active Fair Value Gaps near price"
    except: return "NEUTRAL","SMC FVG — insufficient data"

# NEW: RSI DIVERGENCE ──────────────────────────────────────
def strategy_divergence(df):
    """Detects RSI divergence — one of the most powerful reversal signals."""
    try:
        c=df["Close"]; d=c.diff()
        g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
        rsi=100-(100/(1+(g/l)))
        # Look at last 20 candles for divergence
        lookback=20
        prices=c.iloc[-lookback:].values
        rsis=rsi.iloc[-lookback:].values
        # Find recent swing highs and lows in price
        p_highs=[i for i in range(1,len(prices)-1) if prices[i]>prices[i-1] and prices[i]>prices[i+1]]
        p_lows =[i for i in range(1,len(prices)-1) if prices[i]<prices[i-1] and prices[i]<prices[i+1]]
        # Bearish divergence: price makes higher high but RSI makes lower high
        if len(p_highs)>=2:
            h1,h2=p_highs[-2],p_highs[-1]
            if prices[h2]>prices[h1] and rsis[h2]<rsis[h1]:
                return "SELL",f"Bearish RSI Divergence — price higher high but RSI lower high (reversal signal)"
        # Bullish divergence: price makes lower low but RSI makes higher low
        if len(p_lows)>=2:
            l1,l2=p_lows[-2],p_lows[-1]
            if prices[l2]<prices[l1] and rsis[l2]>rsis[l1]:
                return "BUY",f"Bullish RSI Divergence — price lower low but RSI higher low (reversal signal)"
        return "NEUTRAL","No RSI divergence detected"
    except: return "NEUTRAL","Divergence — insufficient data"

# NEW: LIQUIDITY ZONES (SMC) ───────────────────────────────
def strategy_liquidity_zones(df):
    """
    Identifies liquidity pools — areas where stop losses cluster.
    Smart money hunts these before reversing direction.
    """
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        cp=float(c.iloc[-1])
        # Equal highs/lows = liquidity pools (stop hunts target these)
        recent_h=h.iloc[-30:]; recent_l=l.iloc[-30:]
        # Find clusters of highs within 0.1% of each other
        h_vals=recent_h.values; l_vals=recent_l.values
        liq_highs=[]; liq_lows=[]
        for i in range(len(h_vals)):
            cluster_h=[v for v in h_vals if abs(v-h_vals[i])/h_vals[i]<0.001]
            if len(cluster_h)>=2: liq_highs.append(float(np.mean(cluster_h)))
        for i in range(len(l_vals)):
            cluster_l=[v for v in l_vals if abs(v-l_vals[i])/l_vals[i]<0.001]
            if len(cluster_l)>=2: liq_lows.append(float(np.mean(cluster_l)))
        liq_highs=sorted(set([round(x,4) for x in liq_highs]),reverse=True)
        liq_lows =sorted(set([round(x,4) for x in liq_lows]))
        # Price just swept liquidity high (bearish — smart money sold into stops)
        if liq_highs:
            nearest_h=liq_highs[0]
            if cp>=nearest_h*0.999 and cp<=nearest_h*1.003:
                return "SELL",f"SMC Liquidity Sweep — price at buy-side liquidity {round(nearest_h,4)} (stop hunt likely)"
            if cp>nearest_h*1.003:
                return "SELL",f"SMC Buy-side liquidity swept at {round(nearest_h,4)} — reversal expected"
        # Price just swept liquidity low (bullish — smart money bought into stops)
        if liq_lows:
            nearest_l=liq_lows[0]
            if cp>=nearest_l*0.997 and cp<=nearest_l*1.001:
                return "BUY",f"SMC Liquidity Sweep — price at sell-side liquidity {round(nearest_l,4)} (stop hunt likely)"
            if cp<nearest_l*0.997:
                return "BUY",f"SMC Sell-side liquidity swept at {round(nearest_l,4)} — reversal expected"
        return "NEUTRAL",f"No active liquidity sweeps near price"
    except: return "NEUTRAL","Liquidity zones — insufficient data"

STRATEGIES={
    "EMA Trend":strategy_ema_trend,
    "RSI Momentum":strategy_rsi,
    "MACD Crossover":strategy_macd,
    "Support / Resistance":strategy_sr,
    "ADX Trend Strength":strategy_adx,
    "Stochastic Oscillator":strategy_stochastic,
    "SMC Order Blocks":strategy_smc_orderblock,
    "SMC Fair Value Gap":strategy_smc_fvg,
    "RSI Divergence":strategy_divergence,
    "SMC Liquidity Zones":strategy_liquidity_zones,
}
SMC_STRATS={"SMC Order Blocks","SMC Fair Value Gap","SMC Liquidity Zones"}

def run_all_strategies(symbol,period="6mo"):
    df=fetch_data(symbol,period)
    if df is None: return {},0,"ERROR"
    results={}
    for name,fn in STRATEGIES.items():
        try: results[name]=fn(df)
        except: results[name]=("NEUTRAL","Error")
    buys=sum(1 for s,_ in results.values() if s=="BUY")
    sells=sum(1 for s,_ in results.values() if s=="SELL")
    total=len(results)
    if buys>sells:   conf=round(buys/total*100); sig="STRONG BUY"  if buys>=7  else "BUY"
    elif sells>buys: conf=round(sells/total*100);sig="STRONG SELL" if sells>=7 else "SELL"
    else:            conf=50; sig="WAIT"
    return results,conf,sig

# ════════ MULTI-TIMEFRAME ════════
def run_mtf(symbol):
    """Run strategies on 3 timeframes and return consensus."""
    tf_results={}
    configs=[("Daily","6mo","1d"),("4H","1mo","4h"),("1H","5d","1h")]
    for label,period,interval in configs:
        df=fetch_data(symbol,period,interval)
        if df is None or len(df)<30:
            tf_results[label]=("WAIT",0)
            continue
        results={}
        for name,fn in STRATEGIES.items():
            try: results[name]=fn(df)
            except: results[name]=("NEUTRAL","Error")
        buys=sum(1 for s,_ in results.values() if s=="BUY")
        sells=sum(1 for s,_ in results.values() if s=="SELL")
        total=len(results)
        if buys>sells:   conf=round(buys/total*100); sig="BUY"  if buys>=5 else "BUY"
        elif sells>buys: conf=round(sells/total*100);sig="SELL" if sells>=5 else "SELL"
        else:            conf=50; sig="WAIT"
        tf_results[label]=(sig,conf)
    # MTF consensus
    sigs=[s for s,_ in tf_results.values() if s!="WAIT"]
    buy_tfs=sum(1 for s in sigs if s=="BUY")
    sell_tfs=sum(1 for s in sigs if s=="SELL")
    if buy_tfs==3:   mtf_sig="STRONG BUY";  mtf_note="All 3 timeframes agree — very high probability"
    elif buy_tfs==2: mtf_sig="BUY";         mtf_note="2/3 timeframes agree — good setup"
    elif sell_tfs==3:mtf_sig="STRONG SELL"; mtf_note="All 3 timeframes agree — very high probability"
    elif sell_tfs==2:mtf_sig="SELL";        mtf_note="2/3 timeframes agree — good setup"
    else:            mtf_sig="WAIT";        mtf_note="Timeframes conflicting — stand aside"
    return tf_results,mtf_sig,mtf_note

def get_trade_setup(symbol,direction):
    try:
        df=fetch_data(symbol,"3mo"); c=df["Close"]; h=df["High"]; l=df["Low"]; p=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); risk=atr*1.5
        if "BUY" in direction: return p,p-risk,p+risk,p+risk*2,p+risk*3,round(atr,5)
        else:                  return p,p+risk,p-risk,p-risk*2,p-risk*3,round(atr,5)
    except: return None,None,None,None,None,None

# ════════ FIBONACCI + PIVOT POINTS ════════
def get_fib_levels(symbol):
    try:
        df=fetch_data(symbol,"3mo")
        h=float(df["High"].iloc[-20:].max()); l=float(df["Low"].iloc[-20:].min())
        diff=h-l
        return {
            "High":h,"0.786":h-diff*0.214,"0.618":h-diff*0.382,
            "0.5":h-diff*0.5,"0.382":h-diff*0.618,
            "0.236":h-diff*0.764,"Low":l
        }
    except: return {}

def get_pivot_points(symbol):
    try:
        df=fetch_data(symbol,"5d")
        prev=df.iloc[-2]
        h=float(prev["High"]); l=float(prev["Low"]); c=float(prev["Close"])
        pp=(h+l+c)/3
        return {
            "R3":pp+2*(h-l),"R2":pp+(h-l),"R1":2*pp-l,
            "PP":pp,
            "S1":2*pp-h,"S2":pp-(h-l),"S3":pp-2*(h-l)
        }
    except: return {}

# ════════ SIGNAL BANNER ════════
def show_signal_banner(sig,asset,conf):
    if sig=="STRONG BUY":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#0d5c2e,#1a7a3e);
        border:2px solid #3fb950;border-radius:14px;padding:20px;text-align:center;
        margin-bottom:14px;box-shadow:0 0 24px rgba(63,185,80,0.4)'>
        <div style='font-size:26px;font-weight:900;color:#3fb950'>🚀 STRONG BUY — BUY NOW</div>
        <div style='font-size:16px;color:#e6edf3;margin-top:6px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="BUY":
        st.markdown(f"""<div style='background:#0d2b1a;border:2px solid #3fb950;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:14px'>
        <div style='font-size:20px;font-weight:800;color:#3fb950'>🟢 BUY SIGNAL</div>
        <div style='font-size:15px;color:#e6edf3;margin-top:4px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="STRONG SELL":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#5c0d0d,#7a1a1a);
        border:2px solid #f85149;border-radius:14px;padding:20px;text-align:center;
        margin-bottom:14px;box-shadow:0 0 24px rgba(248,81,73,0.4)'>
        <div style='font-size:26px;font-weight:900;color:#f85149'>📉 STRONG SELL — SELL NOW</div>
        <div style='font-size:16px;color:#e6edf3;margin-top:6px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="SELL":
        st.markdown(f"""<div style='background:#2b0d0d;border:2px solid #f85149;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:14px'>
        <div style='font-size:20px;font-weight:800;color:#f85149'>🔴 SELL SIGNAL</div>
        <div style='font-size:15px;color:#e6edf3;margin-top:4px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#1c1c1c;border:1px solid #30363d;
        border-radius:14px;padding:14px;text-align:center;margin-bottom:14px'>
        <div style='font-size:18px;color:#8b949e'>⏳ WAIT — No Clear Signal &nbsp;|&nbsp; {asset}</div>
        </div>""",unsafe_allow_html=True)

# ════════ AUTO TICKET ════════
def auto_add_to_journal(asset,sig,conf,entry,sl,tp1,tp2,tp3,source="Auto Ticket"):
    """Automatically adds a signal to the trade journal."""
    # Avoid duplicates — don't add same asset+signal within same day
    today=str(datetime.date.today())
    existing=[t for t in st.session_state.trade_journal
              if t.get("Asset")==asset and t.get("Date")==today and t.get("Signal")==sig]
    if existing: return False,"Already in journal today"
    st.session_state.trade_journal.append({
        "Date":today,"Time":datetime.datetime.now().strftime("%H:%M"),
        "Asset":asset,"Signal":sig,"Entry":round(entry,5),
        "SL":round(sl,5),"TP1":round(tp1,5),"TP2":round(tp2,5),"TP3":round(tp3,5),
        "Confidence":conf,"Result":"Open","Notes":source,"Source":source
    })
    return True,"Added"

def log_signal_history(asset,sig,conf,entry,sl,tp1):
    """Log every signal that fires to history."""
    st.session_state.signal_history.append({
        "DateTime":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Asset":asset,"Signal":sig,"Confidence":conf,
        "Entry":round(entry,5),"SL":round(sl,5),"TP1":round(tp1,5),
        "Result":"Pending"
    })

# ════════ PRICE CHART WITH FIBS + PIVOTS ════════
def show_price_chart(symbol,pair_name,signal,entry,sl,tp1,tp2,show_fibs=True,show_pivots=True,chart_key=None):
    df=fetch_data(symbol,"3mo","1d")
    if df is None: st.warning("Chart unavailable."); return
    close=df["Close"]; ema20=close.ewm(span=20).mean()
    ema50=close.ewm(span=50).mean(); ema200=close.ewm(span=200).mean()
    res=float(df["High"].rolling(20).max().iloc[-1]); sup=float(df["Low"].rolling(20).min().iloc[-1])
    dates=df.index; fig=go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],
            low=df["Low"],close=close,name="Price",
            increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates,y=close,name="Price",line=dict(color="#58a6ff",width=2)))
    fig.add_trace(go.Scatter(x=dates,y=ema20,name="EMA20",line=dict(color="#ffd700",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema50,name="EMA50",line=dict(color="#ff7f50",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema200,name="EMA200",line=dict(color="#da70d6",width=1,dash="dash")))
    fig.add_hline(y=res,line_color="#f85149",line_dash="dash",
        annotation_text=f"Res {round(res,4)}",annotation_position="right")
    fig.add_hline(y=sup,line_color="#3fb950",line_dash="dash",
        annotation_text=f"Sup {round(sup,4)}",annotation_position="right")
    if entry:
        color="#3fb950" if "BUY" in signal else "#f85149"
        fig.add_hline(y=entry,line_color=color,line_width=2,
            annotation_text=f"Entry {round(entry,5)}",annotation_position="left")
        fig.add_hline(y=sl,line_color="#f85149",line_width=1,line_dash="dash",
            annotation_text=f"SL {round(sl,5)}",annotation_position="left")
        fig.add_hline(y=tp1,line_color="#3fb950",line_width=1,line_dash="dash",
            annotation_text=f"TP1 {round(tp1,5)}",annotation_position="left")
        fig.add_hline(y=tp2,line_color="#3fb950",line_width=1,line_dash="dot",
            annotation_text=f"TP2 {round(tp2,5)}",annotation_position="left")
    # Fibonacci levels
    if show_fibs:
        fibs=get_fib_levels(symbol)
        fib_colors={"0.382":"#9b59b6","0.5":"#3498db","0.618":"#e67e22","0.786":"#e74c3c"}
        for level,price in fibs.items():
            if level in fib_colors:
                fig.add_hline(y=price,line_color=fib_colors[level],line_width=1,
                    line_dash="dot",annotation_text=f"Fib {level}",
                    annotation_position="right",annotation_font_size=9)
    # Pivot points
    if show_pivots:
        pivots=get_pivot_points(symbol)
        pivot_colors={"PP":"#ffffff","R1":"#ff6b6b","R2":"#ff4444","S1":"#51cf66","S2":"#37b24d"}
        for level,price in pivots.items():
            if level in pivot_colors:
                fig.add_hline(y=price,line_color=pivot_colors[level],line_width=1,
                    line_dash="longdash",annotation_text=level,
                    annotation_position="left",annotation_font_size=9)
    lp=float(close.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[lp],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in signal else "triangle-down",
                    size=14,color="#3fb950" if "BUY" in signal else "#f85149"),name="Signal"))
    fig.update_layout(title=f"{pair_name}",plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),
        legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1,font=dict(size=10)),
        height=450,margin=dict(l=50,r=130,t=40,b=30))
    _ckey = chart_key or f"chart_{symbol}_{signal}_{id(fig)}"
    st.plotly_chart(fig,use_container_width=True,key=_ckey)
    # Context box
    pve20="above" if lp>float(ema20.iloc[-1]) else "below"
    pve200="above" if lp>float(ema200.iloc[-1]) else "below"
    trend="uptrend" if float(ema20.iloc[-1])>float(ema200.iloc[-1]) else "downtrend"
    ma=float(close.iloc[-22]) if len(close)>22 else float(close.iloc[0])
    cp=round((lp-ma)/ma*100,2); cs=f"up {cp}%" if cp>0 else f"down {abs(cp)}%"
    ta=(("BUY" in signal and trend=="uptrend") or ("SELL" in signal and trend=="downtrend"))
    nr=abs(lp-res)/lp<0.005; ns=abs(lp-sup)/lp<0.005
    zn="⚠️ Near resistance" if nr else "✅ Near support" if ns else "📊 Mid range"
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
        <b>📈 Price Context</b><br><br>
        Moved <b>{cs}</b> past 30 days<br>
        Short-term: <b>{"bullish" if pve20=="above" else "bearish"}</b> vs EMA20<br>
        Long-term: <b>{"bullish" if pve200=="above" else "bearish"}</b> vs EMA200<br>
        Overall: <b>{trend.upper()}</b></div>""",unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
        <b>🎯 Trade Reasoning</b><br><br>
        Signal: <b>{signal}</b><br>
        Position: {zn}<br>
        Fib + Pivot levels shown on chart<br>
        {"✅ Trend + signal AGREE" if ta else "⚠️ Counter-trend — reduce size"}</div>""",unsafe_allow_html=True)

# ════════ NEWS ════════
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
        {"Time":"Tomorrow 14:00","Currency":"USD","Event":"FOMC Minutes","Impact":"High","Forecast":"—","Previous":"—"},
    ])

NEWS_PAIRS={"USD":["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CHF","USD/CAD","Gold (XAU/USD)"],
    "EUR":["EUR/USD"],"GBP":["GBP/USD"],"JPY":["USD/JPY"],
    "AUD":["AUD/USD"],"CHF":["USD/CHF"],"CAD":["USD/CAD"],"XAU":["Gold (XAU/USD)"]}

def get_daily_briefing(news_df):
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":_secret("ANTHROPIC_API_KEY",""),"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":400,"messages":[{"role":"user","content":
                f"You are a forex market analyst. Write a concise daily market briefing (3-4 sentences max) "
                f"covering: today's key themes, risk sentiment, and top 2 pairs to watch. "
                f"Today's calendar: {news_df.to_string(index=False)}. Be direct and actionable."}]},timeout=20)
        if r.status_code==200: return r.json()["content"][0]["text"]
    except: pass
    return "Market briefing unavailable. Add ANTHROPIC_API_KEY to Streamlit secrets to enable AI briefings."

def analyse_news_with_ai(news_df,pair):
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":_secret("ANTHROPIC_API_KEY",""),"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":600,"messages":[{"role":"user","content":
                f"Forex news trader. Asset: {pair}\nCalendar:\n{news_df.to_string(index=False)}\n\n"
                "Give: 1) Events affecting this pair 2) Expected direction 3) Best entry timing "
                "4) Risk level 5) Quick trade plan. Bullet points only."}]},timeout=25)
        if r.status_code==200: return r.json()["content"][0]["text"]
        return "AI unavailable — add ANTHROPIC_API_KEY in Streamlit secrets."
    except Exception as e: return f"Error: {e}"

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""<div style='text-align:center;font-size:24px;font-weight:900;
    background:linear-gradient(90deg,#00c6ff,#0072ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent'>🚀 Sparro FX AI</div>""",
    unsafe_allow_html=True)
    st.divider()

    if atype=="admin":       st.success("👑 Admin")
    elif atype=="premium":   st.success("⚡ Premium Active")
    elif atype=="trial":
        h=trial_hours_left()
        st.warning(f"🎁 Trial — {h}h left")
        if h<=12: st.error("⏰ Upgrade now!")
    elif atype=="free":
        st.info("🆓 Free Plan")
        if st.button("⚡ Upgrade — $15/mo",use_container_width=True):
            st.info("Contact us for your premium password.")
    if st.session_state.user_email: st.caption(f"👤 {st.session_state.user_email}")
    st.divider()

    nav_items=[("🏠 Dashboard","Dashboard"),("🎫 Trade Tickets","Tickets"),
               ("📓 Journal","Journal"),("📈 Performance","Performance"),
               ("💰 Risk Calc","Risk")]
    for label,key in nav_items:
        active=st.session_state.get("active_page","Dashboard")==key
        if st.button(label,use_container_width=True,
                     type="primary" if active else "secondary",key=f"nav_{key}"):
            st.session_state["active_page"]=key; st.rerun()

    st.markdown("<br>",unsafe_allow_html=True)
    with st.expander("≫ More"):
        more=[("💎 Pricing","Pricing"),("📚 Learn SMC","LearnSMC"),
              ("ℹ️ About","About")]
        if atype=="admin": more.append(("👑 Admin","Admin"))
        for label,key in more:
            if st.button(label,use_container_width=True,key=f"nav_{key}"):
                st.session_state["active_page"]=key; st.rerun()

    if "active_page" not in st.session_state: st.session_state["active_page"]="Dashboard"
    page=st.session_state["active_page"]
    st.divider()
    if st.button("🚪 Logout",use_container_width=True):
        clear_login()
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
if page=="Dashboard":
    now=datetime.datetime.utcnow().strftime("%A %d %b %Y  •  %H:%M UTC")
    st.markdown(f"""<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:16px'>
      <div style='font-size:24px;font-weight:900'>📊 Sparro FX AI — Dashboard</div>
      <div style='color:#8b949e;font-size:13px'>🕐 {now}</div>
    </div>""",unsafe_allow_html=True)

    if not premium: st.warning("🔒 Free plan — 5 assets only. Upgrade for full access.")

    # Daily briefing strip
    if premium:
        with st.expander("📰 Today's Market Briefing — click to expand",expanded=False):
            with st.spinner("Generating AI briefing..."):
                ndf=fetch_forex_news()
                briefing=get_daily_briefing(ndf)
            # News risk warning
            high_ev=ndf[ndf["Impact"]=="High"] if "Impact" in ndf.columns else pd.DataFrame()
            if not high_ev.empty:
                events_str=" · ".join([f"{r.get('Time','')} {r.get('Currency','')} {r.get('Event','')}" for _,r in high_ev.head(3).iterrows()])
                st.error(f"⚠️ HIGH IMPACT NEWS TODAY: {events_str}")
            st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:16px;
            border-left:4px solid #00c6ff;font-size:14px;line-height:1.8'>
            {briefing.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)

    tabs=st.tabs(["⚡ Pulse","📊 Scanner","🏆 Trade of Day","🔬 Deep Analysis","🗞️ News Trading"])

    # ══ PULSE ══════════════════════════════════════════════
    with tabs[0]:
        st.markdown("""<div style='display:flex;align-items:center;margin-bottom:6px'>
          <span class='pulse-live'></span>
          <span style='font-size:20px;font-weight:800'>Live Pulse Signal</span>
        </div>
        <div style='color:#8b949e;font-size:13px;margin-bottom:16px'>
        STRONG signals with 70%+ confidence only. Auto-scans all 10 strategies including SMC + Divergence.</div>""",
        unsafe_allow_html=True)
        if not premium: st.error("🔒 Upgrade to see Pulse Signals.")
        else:
            cr,cb=st.columns([3,1])
            with cb:
                if st.button("🔄 Refresh",use_container_width=True): st.rerun()
            with cr: st.caption(f"Scan: {datetime.datetime.now().strftime('%H:%M:%S')}")

            with st.spinner("Scanning all markets..."):
                pulse=[]
                for name,sym in ALL_PAIRS.items():
                    strats,conf,sig=run_all_strategies(sym)
                    if sig in ("STRONG BUY","STRONG SELL") and conf>=70:
                        entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
                        if entry:
                            # MTF check
                            tf_res,mtf_sig,mtf_note=run_mtf(sym)
                            mtf_agrees=(mtf_sig in ("BUY","STRONG BUY") and "BUY" in sig) or \
                                       (mtf_sig in ("SELL","STRONG SELL") and "SELL" in sig)
                            pulse.append({"name":name,"sym":sym,"sig":sig,"conf":conf,
                                "entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,
                                "strats":strats,"tf_res":tf_res,"mtf_sig":mtf_sig,
                                "mtf_note":mtf_note,"mtf_agrees":mtf_agrees})
                            log_signal_history(name,sig,conf,entry,sl,tp1)
                pulse.sort(key=lambda x:(x["mtf_agrees"],x["conf"]),reverse=True)

            if not pulse:
                st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
                border-radius:14px;padding:50px;text-align:center'>
                <div style='font-size:40px'>😴</div>
                <div style='font-size:18px;color:#8b949e;margin-top:12px'>No strong signals right now</div>
                <div style='color:#8b949e;font-size:13px;margin-top:6px'>Market is quiet. Check back soon.</div>
                </div>""",unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#3fb950;font-weight:700;margin-bottom:12px'>✅ {len(pulse)} strong signal(s) active</div>",unsafe_allow_html=True)
                for p in pulse:
                    is_buy="BUY" in p["sig"]
                    border="#3fb950" if is_buy else "#f85149"
                    bg="linear-gradient(135deg,#0d3b20,#0d1f14)" if is_buy else "linear-gradient(135deg,#3b0d0d,#1f0d0d)"
                    icon="🚀" if is_buy else "📉"
                    cf_col="#3fb950" if p["conf"]>=80 else "#ffd700" if p["conf"]>=65 else "#f85149"
                    direction="BUY" if is_buy else "SELL"
                    agreeing=[n for n,(s,_) in p["strats"].items() if s==direction]
                    smc_on=any(n in SMC_STRATS for n in agreeing)
                    div_on="RSI Divergence" in agreeing
                    mtf_badge=("🟢 MTF CONFIRM" if p["mtf_agrees"] else "🟡 MTF MIXED")
                    mtf_col=("#3fb950" if p["mtf_agrees"] else "#ffd700")

                    # Build MTF timeframe HTML safely (avoids nested quote issues)
                    tf_parts=[]
                    for tf,(s,c) in p["tf_res"].items():
                        col=("#3fb950" if s=="BUY" else "#f85149" if s=="SELL" else "#8b949e")
                        tf_parts.append(f"<div style='background:#00000044;border-radius:6px;padding:6px;text-align:center;color:{col}'>{tf}: {s}</div>")
                    p["_tf_html"]="".join(tf_parts)

                    st.markdown(f"""<div style='background:{bg};border:2px solid {border};
                    border-radius:14px;padding:18px;margin-bottom:14px;box-shadow:0 0 16px {border}44'>
                      <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px'>
                        <div>
                          <div style='font-size:20px;font-weight:900;color:{border}'>{icon} {p["sig"]}
                            {"&nbsp;<span class='smc-tag'>SMC ✓</span>" if smc_on else ""}
                            {"&nbsp;<span style='background:#e67e22;color:#fff;border-radius:6px;padding:2px 7px;font-size:11px'>DIV</span>" if div_on else ""}
                          </div>
                          <div style='font-size:22px;font-weight:700;color:#e6edf3'>{p["name"]}</div>
                          <div style='font-size:12px;color:{mtf_col};margin-top:4px'>{mtf_badge} &nbsp;|&nbsp; {p["mtf_note"]}</div>
                        </div>
                        <div style='text-align:right'>
                          <div style='font-size:32px;font-weight:900;color:{cf_col}'>{p["conf"]}%</div>
                          <div style='font-size:11px;color:#8b949e'>CONFIDENCE</div>
                        </div>
                      </div>
                      <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px'>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e'>ENTRY</div>
                          <div style='font-size:13px;font-weight:700;color:#e6edf3'>{round(p["entry"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e'>STOP</div>
                          <div style='font-size:13px;font-weight:700;color:#f85149'>{round(p["sl"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e'>TP1</div>
                          <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp1"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e'>TP2</div>
                          <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp2"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e'>TP3</div>
                          <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp3"],5)}</div>
                        </div>
                      </div>
                      <div style='display:flex;justify-content:space-between;align-items:center'>
                        <div style='font-size:12px;color:#8b949e'>✅ {" · ".join(agreeing[:5])}</div>
                      </div>
                      <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px;font-size:12px'>
                        {p["_tf_html"]}
                      </div>
                    </div>""",unsafe_allow_html=True)

                    col1,col2=st.columns(2)
                    with col1:
                        if st.button(f"🎫 Auto Ticket — {p['name']}",key=f"ticket_{p['name']}",use_container_width=True):
                            ok,msg=auto_add_to_journal(p["name"],p["sig"],p["conf"],
                                p["entry"],p["sl"],p["tp1"],p["tp2"],p["tp3"],"Pulse Auto Ticket")
                            st.success(f"✅ Trade ticket created! Go to Journal to manage it.") if ok else st.warning(f"⚠️ {msg}")
                    with col2:
                        with st.expander(f"📊 Chart"):
                            show_price_chart(p["sym"],p["name"],p["sig"],p["entry"],p["sl"],p["tp1"],p["tp2"],chart_key="pulse_"+p["name"])

    # ══ SCANNER ═══════════════════════════════════════════
    with tabs[1]:
        st.markdown("### 📊 Market Scanner")
        results=[]; prog=st.progress(0); items=list(pairs.items())
        for i,(name,sym) in enumerate(items):
            strats,conf,sig=run_all_strategies(sym)
            buys=sum(1 for s,_ in strats.values() if s=="BUY")
            sells=sum(1 for s,_ in strats.values() if s=="SELL")
            smc_v=sum(1 for n,(s,_) in strats.items() if s in ("BUY","SELL") and n in SMC_STRATS)
            results.append({"Asset":name,"Signal":sig,
                "Confidence":f"{conf}%" if premium else "🔒",
                "Buy":buys if premium else "🔒",
                "Sell":sells if premium else "🔒",
                "SMC":f"{smc_v}/3" if premium else "🔒"})
            prog.progress((i+1)/len(items))
        prog.empty()
        scanner=pd.DataFrame(results)
        strong=[r for r in results if r["Signal"] in ("STRONG BUY","STRONG SELL")]
        if strong:
            st.markdown("**⚡ Urgent:**")
            for r in strong:
                cv=int(r["Confidence"].replace("%","")) if "%" in str(r["Confidence"]) else 0
                show_signal_banner(r["Signal"],r["Asset"],cv)
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**🚀 Buys**")
            st.dataframe(scanner[scanner["Signal"].str.contains("BUY",na=False)].head(4),use_container_width=True,hide_index=True)
        with c2:
            st.markdown("**📉 Sells**")
            st.dataframe(scanner[scanner["Signal"].str.contains("SELL",na=False)].head(4),use_container_width=True,hide_index=True)
        st.markdown("**All Assets**")
        st.dataframe(scanner,use_container_width=True,hide_index=True)

    # ══ TRADE OF THE DAY ══════════════════════════════════
    with tabs[2]:
        st.markdown("### 🏆 Trade of the Day")
        if not premium: st.error("🔒 Premium only.")
        else:
            best={"conf":0,"sig":"WAIT","name":"","sym":"","strats":{}}
            with st.spinner("Finding best setup..."):
                for name,sym in ALL_PAIRS.items():
                    strats,conf,sig=run_all_strategies(sym)
                    if sig!="WAIT" and conf>best["conf"]:
                        best={"conf":conf,"sig":sig,"name":name,"sym":sym,"strats":strats}
            show_signal_banner(best["sig"],best["name"],best["conf"])
            c1,c2,c3=st.columns(3)
            c1.metric("Asset",best["name"]); c2.metric("Signal",best["sig"]); c3.metric("Confidence",f"{best['conf']}%")
            st.progress(best["conf"]/100)
            entry,sl,tp1,tp2,tp3,_=get_trade_setup(best["sym"],best["sig"])
            if entry:
                # MTF
                tf_res,mtf_sig,mtf_note=run_mtf(best["sym"])
                mtf_col="#3fb950" if "BUY" in mtf_sig else "#f85149" if "SELL" in mtf_sig else "#8b949e"
                st.markdown(f"<div style='background:#161b22;border-radius:8px;padding:10px;border-left:4px solid {mtf_col};margin-bottom:10px;font-size:13px'>🕐 <b>Multi-Timeframe:</b> {mtf_sig} — {mtf_note}</div>",unsafe_allow_html=True)
                st.markdown("---")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
                c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
                col1,col2=st.columns(2)
                with col1:
                    if st.button("🎫 Auto Ticket",use_container_width=True,key="totd_ticket"):
                        ok,msg=auto_add_to_journal(best["name"],best["sig"],best["conf"],
                            entry,sl,tp1,tp2,tp3,"Trade of Day")
                        st.success("✅ Ticket created! Check Journal.") if ok else st.warning(f"⚠️ {msg}")
                with col2:
                    if st.button("➕ Manual Add",use_container_width=True,key="totd_manual"):
                        ok,msg=auto_add_to_journal(best["name"],best["sig"],best["conf"],
                            entry,sl,tp1,tp2,tp3,"Manual")
                        st.success("✅ Added!") if ok else st.warning(f"⚠️ {msg}")
                st.markdown("---")
                show_price_chart(best["sym"],best["name"],best["sig"],entry,sl,tp1,tp2,chart_key="totd_chart")

    # ══ DEEP ANALYSIS ═════════════════════════════════════
    with tabs[3]:
        st.markdown("### 🔬 Deep Strategy Analysis")
        if not premium: st.error("🔒 Premium only.")
        else:
            selected=st.selectbox("Choose Asset",list(ALL_PAIRS.keys()),key="deep_sel")
            sym=ALL_PAIRS[selected]
            with st.spinner(f"Analysing {selected} across 10 strategies..."):
                strats,conf,sig=run_all_strategies(sym)
                tf_res,mtf_sig,mtf_note=run_mtf(sym)
            show_signal_banner(sig,selected,conf)
            c1,c2,c3=st.columns(3)
            c1.metric("Signal",sig); c2.metric("Confidence",f"{conf}%"); c3.metric("Strategies","10")
            st.progress(conf/100)
            # MTF strip
            mtf_col="#3fb950" if "BUY" in mtf_sig else "#f85149" if "SELL" in mtf_sig else "#8b949e"
            st.markdown(f"<div style='background:#161b22;border-radius:8px;padding:10px;border-left:4px solid {mtf_col};margin-bottom:10px;font-size:13px'>🕐 <b>Multi-Timeframe:</b> {mtf_sig} — {mtf_note} &nbsp;|&nbsp; " +
                " &nbsp;·&nbsp; ".join([f"{tf}: {s}" for tf,(s,c) in tf_res.items()]) + "</div>",unsafe_allow_html=True)
            st.markdown("---")
            for name,(s,reason) in strats.items():
                color="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
                icon="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
                sr=reason.replace("<","&lt;").replace(">","&gt;")
                is_smc=name in SMC_STRATS
                is_div=name=="RSI Divergence"
                badge=("<span class='smc-tag'>SMC</span>" if is_smc else
                       "<span style='background:#e67e22;color:#fff;border-radius:6px;padding:2px 7px;font-size:11px'>DIV</span>" if is_div else "")
                border_r="border-right:2px solid #7c3aed" if is_smc else "border-right:2px solid #e67e22" if is_div else ""
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:10px 14px;
                margin-bottom:8px;border-left:4px solid {color};{border_r}'>
                <b>{icon} {name}</b>{badge} &nbsp;
                <span style='background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px'>{s}</span>
                <br><small style='color:#8b949e'>{sr}</small></div>""",unsafe_allow_html=True)
            buys=sum(1 for s,_ in strats.values() if s=="BUY"); sells=sum(1 for s,_ in strats.values() if s=="SELL")
            c1,c2,c3=st.columns(3)
            c1.metric("🟢 Buy",buys); c2.metric("🔴 Sell",sells); c3.metric("🟡 Neutral",10-buys-sells)
            entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
            if entry and sig!="WAIT":
                st.markdown("---")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
                c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
                if conf>=75: st.success(f"✅ HIGH confidence — {conf}% agree")
                elif conf>=60: st.warning(f"⚠️ MODERATE — {conf}%. Reduce size.")
                else: st.error(f"🚨 LOW — {conf}%. Consider waiting.")
                if st.button("🎫 Auto Ticket",key="deep_ticket",use_container_width=True):
                    ok,msg=auto_add_to_journal(selected,sig,conf,entry,sl,tp1,tp2,tp3,"Deep Analysis")
                    st.success("✅ Ticket created!") if ok else st.warning(f"⚠️ {msg}")
                st.markdown("---")
                show_price_chart(sym,selected,sig,entry,sl,tp1,tp2,chart_key=f"deep_{selected}")

    # ══ NEWS TRADING ══════════════════════════════════════
    with tabs[4]:
        st.markdown("### 🗞️ News Trading")
        if not premium: st.error("🔒 Premium only.")
        else:
            with st.spinner("Loading calendar..."): ndf=fetch_forex_news()
            st.markdown("#### 📅 This Week")
            if "Impact" in ndf.columns:
                high_ev=ndf[ndf["Impact"]=="High"]; med_ev=ndf[ndf["Impact"]=="Medium"]
                if not high_ev.empty:
                    st.markdown("**🔴 High Impact:**")
                    for _,row in high_ev.iterrows():
                        curr=row.get("Currency",""); affected=NEWS_PAIRS.get(curr,[curr+" pairs"])
                        st.markdown(f"""<div class='news-trade-card'>
                        <div style='display:flex;justify-content:space-between'>
                          <div><span style='background:#f85149;color:#fff;border-radius:6px;
                          padding:2px 8px;font-size:11px'>HIGH</span>
                          &nbsp;<b>{row.get("Event","")}</b></div>
                          <div style='color:#8b949e;font-size:13px'>{row.get("Time","")}</div>
                        </div>
                        <div style='margin-top:8px;font-size:13px;color:#8b949e'>
                          <b style='color:#ffd200'>{curr}</b> &nbsp;|&nbsp;
                          Forecast: <b>{row.get("Forecast","—")}</b> &nbsp;|&nbsp;
                          Previous: <b>{row.get("Previous","—")}</b>
                        </div>
                        <div style='margin-top:6px;font-size:12px;color:#58a6ff'>
                          📌 {" · ".join(affected[:4])}</div>
                        </div>""",unsafe_allow_html=True)
                if not med_ev.empty:
                    with st.expander(f"🟡 Medium Impact ({len(med_ev)})"):
                        for _,row in med_ev.iterrows():
                            st.markdown(f"**{row.get('Time','')}** — {row.get('Currency','')} {row.get('Event','')} | {row.get('Forecast','—')}")
            st.markdown("---")
            st.markdown("#### 🎯 News Trade Plan")
            c1,c2=st.columns([2,1])
            with c1: np_=st.selectbox("Pair",list(ALL_PAIRS.keys()),key="np")
            with c2: st.markdown("<br>",unsafe_allow_html=True); run_n=st.button("🔍 Generate",use_container_width=True)
            if run_n:
                sym=ALL_PAIRS[np_]
                with st.spinner("Building plan..."):
                    strats,conf,sig=run_all_strategies(sym)
                    entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
                    ai_txt=analyse_news_with_ai(ndf,np_)
                show_signal_banner(sig,np_,conf)
                c1,c2=st.columns(2)
                with c1:
                    st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
                    <b>📊 Technical Bias</b><br><br>Signal: <b>{sig}</b> — {conf}%<br><br>
                    {"✅ Align with technical bias after news" if sig!="WAIT" else "⚠️ Wait for news reaction then enter"}</div>""",unsafe_allow_html=True)
                with c2:
                    if entry and sig!="WAIT":
                        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
                        <b>🎯 Levels</b><br><br>Entry: <b>{round(entry,5)}</b><br>
                        SL: <b style='color:#f85149'>{round(sl,5)}</b><br>
                        TP1: <b style='color:#3fb950'>{round(tp1,5)}</b></div>""",unsafe_allow_html=True)
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:16px;
                border-left:4px solid #58a6ff;line-height:1.8;font-size:14px;margin-top:12px'>
                {ai_txt.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)
                if entry: st.markdown("---"); show_price_chart(sym,np_,sig,entry,sl,tp1,tp2,chart_key=f"news_{np_}")
            st.markdown("---")
            c1,c2=st.columns(2)
            with c1:
                st.markdown("""<div class='card'><b style='color:#3fb950'>✅ DO</b><br><br>
                Wait for candle to <b>close</b> after news<br>Trade the <b>surprise</b> direction<br>
                Use <b>wider stops</b> — spreads spike<br>Take profits quickly<br>
                Check <b>both currencies</b></div>""",unsafe_allow_html=True)
            with c2:
                st.markdown("""<div class='card'><b style='color:#f85149'>❌ DON'T</b><br><br>
                Don't trade <b>into</b> the release<br>Don't hold blindly through NFP/FOMC<br>
                Don't ignore the <b>previous reading</b><br>Don't risk more than <b>1%</b><br>
                Don't trade if spread is <b>wide</b></div>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: TRADE TICKETS
# ════════════════════════════════════════════════════════════
elif page=="Tickets":
    st.title("🎫 Trade Ticket Panel")
    st.markdown("<div style='color:#8b949e;margin-bottom:20px'>All active open trades. Close tickets here to update your journal automatically.</div>",unsafe_allow_html=True)
    if not premium: st.error("🔒 Premium only."); st.stop()

    # Auto-scan for new tickets
    col1,col2=st.columns([3,1])
    with col2:
        if st.button("🔄 Auto-Scan & Ticket All Strong Signals",use_container_width=True):
            added=0
            with st.spinner("Scanning and creating tickets..."):
                for name,sym in ALL_PAIRS.items():
                    strats,conf,sig=run_all_strategies(sym)
                    if sig in ("STRONG BUY","STRONG SELL") and conf>=70:
                        entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
                        if entry:
                            ok,_=auto_add_to_journal(name,sig,conf,entry,sl,tp1,tp2,tp3,"Auto Scan")
                            if ok: added+=1
            st.success(f"✅ {added} new ticket(s) created!")

    # Show open tickets
    open_trades=[t for t in st.session_state.trade_journal if t.get("Result")=="Open"]

    if not open_trades:
        st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
        border-radius:14px;padding:40px;text-align:center'>
        <div style='font-size:36px'>🎫</div>
        <div style='font-size:18px;color:#8b949e;margin-top:12px'>No open tickets</div>
        <div style='color:#8b949e;font-size:13px;margin-top:8px'>
        Scan for signals and hit Auto Ticket, or use Pulse Signal to create tickets automatically.</div>
        </div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(open_trades)} open position(s):**")
        for i,trade in enumerate(open_trades):
            is_buy="BUY" in trade.get("Signal","")
            border="#3fb950" if is_buy else "#f85149"
            icon="🚀" if is_buy else "📉"
            # Find index in full journal
            journal_idx=next((j for j,t in enumerate(st.session_state.trade_journal)
                              if t==trade),None)

            st.markdown(f"""<div class='ticket-card' style='border-color:{border}'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
              <div>
                <span style='font-size:18px;font-weight:900;color:{border}'>{icon} {trade.get("Signal","")}</span>
                &nbsp;<span style='font-size:20px;font-weight:700;color:#e6edf3'>{trade.get("Asset","")}</span>
              </div>
              <div style='text-align:right;font-size:12px;color:#8b949e'>
                {trade.get("Date","")} {trade.get("Time","")}<br>
                Confidence: <b style='color:#ffd200'>{trade.get("Confidence",0)}%</b><br>
                Source: {trade.get("Source","Manual")}
              </div>
            </div>
            <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px'>
              <div style='background:#0d1117;border-radius:8px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>ENTRY</div>
                <div style='font-size:13px;font-weight:700'>{trade.get("Entry","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:8px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>STOP</div>
                <div style='font-size:13px;font-weight:700;color:#f85149'>{trade.get("SL","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:8px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>TP1</div>
                <div style='font-size:13px;font-weight:700;color:#3fb950'>{trade.get("TP1","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:8px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>TP2</div>
                <div style='font-size:13px;font-weight:700;color:#3fb950'>{trade.get("TP2","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:8px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>TP3</div>
                <div style='font-size:13px;font-weight:700;color:#3fb950'>{trade.get("TP3","—")}</div>
              </div>
            </div></div>""",unsafe_allow_html=True)

            # Close ticket buttons
            if journal_idx is not None:
                bc1,bc2,bc3,bc4=st.columns(4)
                with bc1:
                    if st.button("✅ Win",key=f"win_{i}_{journal_idx}",use_container_width=True):
                        st.session_state.trade_journal[journal_idx]["Result"]="Win"; st.rerun()
                with bc2:
                    if st.button("❌ Loss",key=f"loss_{i}_{journal_idx}",use_container_width=True):
                        st.session_state.trade_journal[journal_idx]["Result"]="Loss"; st.rerun()
                with bc3:
                    if st.button("➖ B/E",key=f"be_{i}_{journal_idx}",use_container_width=True):
                        st.session_state.trade_journal[journal_idx]["Result"]="Breakeven"; st.rerun()
                with bc4:
                    if st.button("🗑️ Remove",key=f"del_{i}_{journal_idx}",use_container_width=True):
                        st.session_state.trade_journal.pop(journal_idx); st.rerun()
            st.markdown("<hr style='border-color:#21262d;margin:4px 0 16px 0'>",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: JOURNAL
# ════════════════════════════════════════════════════════════
elif page=="Journal":
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()

    # Signal history
    if st.session_state.signal_history:
        with st.expander(f"📡 Signal History — {len(st.session_state.signal_history)} signals logged"):
            sh=pd.DataFrame(st.session_state.signal_history)
            # Allow updating results
            st.dataframe(sh,use_container_width=True,hide_index=True)
            st.caption("Signal history logs every signal that fires on Pulse. Update results in the table above.")

    with st.expander("➕ Manual Trade Entry"):
        c1,c2,c3=st.columns(3)
        ja=c1.selectbox("Asset",list(ALL_PAIRS.keys()))
        js=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"])
        jr=c3.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c4,c5,c6=st.columns(3)
        je=c4.number_input("Entry",format="%.5f")
        jsl=c5.number_input("SL",format="%.5f")
        jtp=c6.number_input("TP1",format="%.5f")
        c7,c8=st.columns(2)
        jc=c7.slider("Confidence",0,100,70); jn=c8.text_input("Notes")
        if st.button("Save Trade"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),
                "Time":datetime.datetime.now().strftime("%H:%M"),
                "Asset":ja,"Signal":js,"Entry":je,"SL":jsl,"TP1":jtp,
                "TP2":0,"TP3":0,"Confidence":jc,"Result":jr,"Notes":jn,"Source":"Manual"})
            st.success("✅ Saved!")

    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df,use_container_width=True,hide_index=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
        wr=round(wins/tot*100,1) if tot>0 else 0
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total",len(df)); c2.metric("Open",len(df[df["Result"]=="Open"]))
        c3.metric("Win Rate",f"{wr}%"); c4.metric("Wins/Losses",f"{wins}/{loss}")
    else: st.info("No trades yet. Use Auto Ticket from Pulse Signal or add manually above.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif page=="Performance":
    st.title("📈 Performance Dashboard")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
    wr=round(wins/tot*100,1) if tot>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total",tot); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
    st.divider()
    if "Asset" in df.columns and tot>0:
        st.subheader("📊 Win Rate by Asset")
        asset_stats=df[df["Result"].isin(["Win","Loss"])].groupby("Asset")["Result"].value_counts().unstack(fill_value=0)
        if "Win" in asset_stats.columns and "Loss" in asset_stats.columns:
            asset_stats["Win Rate %"]=round(asset_stats["Win"]/(asset_stats["Win"]+asset_stats["Loss"])*100,1)
            st.dataframe(asset_stats.sort_values("Win Rate %",ascending=False),use_container_width=True)
        st.divider()
        st.subheader("📊 Win Rate by Signal Type")
        if "Signal" in df.columns:
            sig_stats=df[df["Result"].isin(["Win","Loss"])].groupby("Signal")["Result"].value_counts().unstack(fill_value=0)
            st.dataframe(sig_stats,use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ════════════════════════════════════════════════════════════
elif page=="Risk":
    st.title("💰 Risk Calculator")
    c1,c2=st.columns(2)
    with c1:
        balance=st.number_input("Account Balance ($)",min_value=10.0,value=1000.0)
        rp=st.slider("Risk per trade (%)",0.5,10.0,2.0,step=0.5)
        slp=st.number_input("Stop Loss (pips)",min_value=1.0,value=20.0)
        pv=st.number_input("Pip Value per 0.01 lot ($)",value=0.10)
        rr=st.slider("Target Risk:Reward",1,5,2)
    ra=balance*rp/100; lot=round(ra/(slp*pv/0.01)*0.01,2) if slp>0 else 0
    with c2:
        st.metric("$ at Risk",f"${ra:.2f}"); st.metric("Lot Size",f"{lot} lots")
        st.metric("Potential Profit",f"${ra*rr:.2f}"); st.metric("R:R",f"1:{rr}")
        st.progress(rp/10)
        if rp<=2:  st.success("✅ Conservative")
        elif rp<=5: st.warning("⚠️ Moderate")
        else:       st.error("🚨 High risk")

# ════════════════════════════════════════════════════════════
# PAGE: PRICING
# ════════════════════════════════════════════════════════════
elif page=="Pricing":
    st.title("💎 Plans & Pricing")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'>
        <h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        5 assets · Basic signals<br><br>
        ❌ Pulse Signal<br>❌ Multi-timeframe<br>❌ SMC Strategies<br>
        ❌ Auto Trade Tickets<br>❌ Signal History<br>❌ News Trading
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$15/mo</h2><hr>
        ✅ <b>⚡ Pulse Signal</b> live feed<br>
        ✅ <b>🕐 Multi-timeframe</b> (1H+4H+Daily)<br>
        ✅ <b>SMC</b> Order Blocks + FVG + Liquidity<br>
        ✅ <b>RSI Divergence</b> detection<br>
        ✅ <b>🎫 Auto Trade Tickets</b><br>
        ✅ Signal History + Win Rate by Asset<br>
        ✅ AI Daily Briefing + News Trading<br>
        ✅ Fibonacci + Pivot Points on charts
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.info("💬 Contact us to get your premium password after payment.")

# ════════════════════════════════════════════════════════════
# PAGE: LEARN SMC
# ════════════════════════════════════════════════════════════
elif page=="LearnSMC":
    st.title("📚 Learn Smart Money Concepts")
    st.markdown("<div style='color:#8b949e;margin-bottom:20px'>Understand how institutional traders move the market — and how to trade with them.</div>",unsafe_allow_html=True)

    t1,t2,t3,t4=st.tabs(["📦 Order Blocks","📊 Fair Value Gaps","💧 Liquidity Zones","📖 How to Read Signals"])

    with t1:
        st.markdown("""### 📦 Order Blocks
**What is an Order Block?**
An Order Block is the last bearish candle before a bullish impulse (Bullish OB) or the last bullish candle before a bearish impulse (Bearish OB). This is where institutions — banks, hedge funds, central banks — placed large orders.

**Why do they work?**
Institutions can't fill their entire position in one candle. They leave unfilled orders behind. When price returns to that zone, those orders get filled — causing price to bounce strongly.

**Bullish Order Block:**""")
        st.markdown("""<div class='card' style='border-left:4px solid #3fb950'>
        <b>Setup:</b> Find a bearish (red) candle followed by a strong bullish move that breaks above recent highs<br><br>
        <b>Entry:</b> When price returns to that bearish candle's range<br>
        <b>Stop Loss:</b> Below the order block low<br>
        <b>Target:</b> Next liquidity level above<br><br>
        <b>Confirmation:</b> Look for SMC FVG or RSI divergence at the same level — much higher probability
        </div>""",unsafe_allow_html=True)
        st.markdown("""**Bearish Order Block:**""")
        st.markdown("""<div class='card' style='border-left:4px solid #f85149'>
        <b>Setup:</b> Find a bullish (green) candle followed by a strong bearish move that breaks below recent lows<br><br>
        <b>Entry:</b> When price returns to that bullish candle's range<br>
        <b>Stop Loss:</b> Above the order block high<br>
        <b>Target:</b> Next liquidity level below
        </div>""",unsafe_allow_html=True)

    with t2:
        st.markdown("""### 📊 Fair Value Gaps (FVG / Imbalance)
**What is a Fair Value Gap?**
An FVG occurs when price moves so fast that it leaves a gap between candle 1's high and candle 3's low (bullish FVG) or candle 1's low and candle 3's high (bearish FVG). This represents a price imbalance.

**Why do they work?**
Markets are efficient — they want to fill imbalances. Price is magnetically attracted back to FVGs to "rebalance" before continuing in the original direction.

**How to trade:**""")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #3fb950'>
            <b>Bullish FVG 🟢</b><br><br>
            Gap between candle 1 high and candle 3 low<br>
            Price dips into the gap = BUY opportunity<br>
            Enter at 50% of the gap<br>
            Stop below the gap<br>
            Target: next resistance
            </div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #f85149'>
            <b>Bearish FVG 🔴</b><br><br>
            Gap between candle 1 low and candle 3 high<br>
            Price rallies into the gap = SELL opportunity<br>
            Enter at 50% of the gap<br>
            Stop above the gap<br>
            Target: next support
            </div>""",unsafe_allow_html=True)

    with t3:
        st.markdown("""### 💧 Liquidity Zones
**What is Liquidity?**
Liquidity = where stop losses are clustered. When many traders place stop losses at the same level (e.g. just below a swing low or just above a swing high), that creates a liquidity pool.

**Why do institutions target liquidity?**
To fill large orders, institutions need someone to trade against. By pushing price into liquidity pools (triggering retail stop losses), they get the volume they need — then reverse direction.

**The Stop Hunt Pattern:**""")
        st.markdown("""<div class='card' style='border-left:4px solid #7c3aed'>
        <b>Step 1:</b> Identify areas where retail stops cluster (below swing lows, above swing highs, round numbers)<br><br>
        <b>Step 2:</b> Wait for price to sweep into that liquidity zone<br><br>
        <b>Step 3:</b> Watch for a sharp rejection — this is institutions filling orders against retail stops<br><br>
        <b>Step 4:</b> Enter in the reversal direction after the sweep<br><br>
        <b>The app detects:</b> Equal highs/lows (multiple touches = clustered stops = liquidity pool)
        </div>""",unsafe_allow_html=True)
        st.info("💡 **Key insight:** If you've ever had your stop hunted right before price goes your way — that was a liquidity sweep. Now you can trade with it instead of being the victim.")

    with t4:
        st.markdown("""### 📖 How to Read Sparro FX AI Signals

**Confidence Score:**""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #3fb950;text-align:center'>
            <div style='font-size:24px;font-weight:900;color:#3fb950'>75-100%</div>
            <b>HIGH</b><br>Strong agreement<br>Full position size
            </div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd700;text-align:center'>
            <div style='font-size:24px;font-weight:900;color:#ffd700'>60-74%</div>
            <b>MODERATE</b><br>Good setup<br>Reduce size by 50%
            </div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #f85149;text-align:center'>
            <div style='font-size:24px;font-weight:900;color:#f85149'>Below 60%</div>
            <b>LOW</b><br>Weak signal<br>Skip or paper trade
            </div>""",unsafe_allow_html=True)
        st.markdown("""
**Badges:**
- 🟣 **SMC ✓** — Smart Money Concepts strategies are confirming the signal. Highest quality.
- 🟠 **DIV** — RSI Divergence detected. Strong reversal signal.
- 🟢 **MTF CONFIRM** — Daily, 4H and 1H all agree. Very high probability.
- 🟡 **MTF MIXED** — Not all timeframes agree. Reduce position size.

**Multi-Timeframe rule:**
> If all 3 timeframes agree → trade full size
> If 2/3 agree → trade half size
> If 1/3 agree → wait

**Entry rules:**
1. Signal fires on Pulse
2. Check MTF — does it confirm?
3. Check for SMC badge — are institutions involved?
4. Use Risk Calculator to size position correctly
5. Hit Auto Ticket → trade goes to journal automatically
        """)

# ════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ════════════════════════════════════════════════════════════
elif page=="About":
    st.title("ℹ️ About Sparro FX AI")
    st.markdown("""
**Sparro FX AI** uses 10 institutional-grade strategies including Smart Money Concepts.

| Strategy | Type | What it detects |
|---|---|---|
| EMA Trend | Trend | 20/50/200 EMA alignment |
| RSI Momentum | Momentum | Overbought/oversold |
| MACD Crossover | Momentum | Signal line crossovers |
| Support/Resistance | Structure | Key price levels |
| ADX Trend Strength | Filter | Trend strength confirmation |
| Stochastic Oscillator | Momentum | Oversold/overbought crossovers |
| SMC Order Blocks | Smart Money | Institutional buy/sell zones |
| SMC Fair Value Gap | Smart Money | Price imbalances |
| RSI Divergence | Reversal | Price/RSI divergence |
| SMC Liquidity Zones | Smart Money | Stop hunt levels |

⚠️ *Trade responsibly. Past signals do not guarantee future results.*
    """)

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ════════════════════════════════════════════════════════════
elif page=="Admin":
    if atype!="admin": st.error("🔒 Admin only."); st.stop()
    st.title("👑 Admin Panel")
    t1,t2,t3=st.tabs(["🔐 Passwords","👥 Subscribers","📊 Stats"])
    with t1:
        st.markdown("### Password Management")
        st.info("""Update in **Streamlit Cloud → App Settings → Secrets**:
```toml
ADMIN_PASSWORD    = "your-admin-password"
PREMIUM_PASSWORD  = "your-premium-password"
FREE_PASSWORD     = "sparro_free"
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```
**Change PREMIUM_PASSWORD to lock out non-payers instantly.**""")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>👑 Admin Password</b><br><span style='color:#8b949e;font-size:13px'>Only you. Never share.</span>
            </div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #3fb950'>
            <b>⚡ Premium Password</b><br><span style='color:#8b949e;font-size:13px'>Share with paying subscribers. Change to revoke.</span>
            </div>""",unsafe_allow_html=True)
    with t2:
        st.markdown("### Subscriber List")
        with st.expander("➕ Add Subscriber"):
            c1,c2,c3=st.columns(3)
            sn=c1.text_input("Name"); se=c2.text_input("Email")
            sp=c3.selectbox("Plan",["Premium $15/mo","Trial","Free"])
            sd=st.date_input("Start Date",datetime.date.today()); sno=st.text_input("Notes")
            if st.button("➕ Add"):
                if sn and se:
                    st.session_state.subscribers.append({"Name":sn,"Email":se,"Plan":sp,
                        "Start":str(sd),"Notes":sno,"Status":"Active"})
                    st.success(f"✅ {sn} added!")
                else: st.error("Name and email required.")
        if st.session_state.subscribers:
            st.dataframe(pd.DataFrame(st.session_state.subscribers),use_container_width=True,hide_index=True)
        else: st.info("No subscribers yet.")
    with t3:
        subs=st.session_state.subscribers
        pc=len([s for s in subs if "Premium" in s.get("Plan","")])
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Subscribers",len(subs)); c2.metric("Premium",pc)
        c3.metric("Monthly Revenue",f"${pc*15}"); c4.metric("Annual Run Rate",f"${pc*15*12}")
        st.markdown("---\n**🔗 Quick Links**")
        st.markdown("""
- 🌐 [Streamlit Cloud](https://share.streamlit.io)
- 📦 [GitHub Repo](https://github.com/sparroxhalo-stack/ai-forex-analyzer)
- 🤖 [Anthropic Console](https://console.anthropic.com)
        """)
