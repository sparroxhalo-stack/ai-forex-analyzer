import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib
import secrets as _secrets

st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")

st.markdown("""
<style>
body,.main{background:#0d1117;color:#e6edf3}
.block-container{padding-top:1.5rem}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#161b22;border-radius:12px;padding:5px}
.stTabs [data-baseweb="tab"]{border-radius:8px;padding:7px 14px;color:#8b949e;font-weight:600;font-size:12px}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0072ff,#00c6ff) !important;color:#fff !important}
.stMetric{background:#161b22;border-radius:10px;padding:12px}
.stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}
.login-box{background:#161b22;border-radius:16px;padding:28px;border:1px solid #30363d}
.card{background:#161b22;border-radius:12px;padding:16px;margin-bottom:10px;border:1px solid #30363d}
.tier-box{background:#161b22;border-radius:14px;padding:20px;text-align:center;border:2px solid #30363d}
.tier-box.gold{border-color:#ffd200}
.pulse-dot{display:inline-block;width:9px;height:9px;background:#3fb950;border-radius:50%;margin-right:6px;animation:blink 1.2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.smc-badge{background:#7c3aed;color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.grade-a{background:linear-gradient(90deg,#238636,#2ea043);color:#fff;border-radius:8px;padding:3px 12px;font-size:14px;font-weight:900}
.grade-b{background:linear-gradient(90deg,#9e6a03,#d4a017);color:#fff;border-radius:8px;padding:3px 12px;font-size:14px;font-weight:900}
.grade-c{background:linear-gradient(90deg,#b94040,#da3633);color:#fff;border-radius:8px;padding:3px 12px;font-size:14px;font-weight:900}
@media(max-width:768px){
  .block-container{padding:0.5rem 0.5rem 70px 0.5rem !important}
  .stTabs [data-baseweb="tab"]{padding:5px 7px !important;font-size:10px !important}
  h1{font-size:20px !important}
  .stButton button{min-height:46px !important;font-size:14px !important}
  .card,.login-box,.tier-box{padding:14px !important}
}
.compact-toggle{background:#161b22;border:1px solid #30363d;border-radius:8px;
  padding:6px 12px;font-size:12px;color:#8b949e;cursor:pointer}
</style>
""", unsafe_allow_html=True)

# ─── SOUND ─────────────────────────────────────────────────────────────────────
def play_sound(sig):
    f1="880" if "BUY" in sig else "440"
    f2="1100" if "BUY" in sig else "330"
    st.markdown(f"""<script>(function(){{try{{
    var c=new(window.AudioContext||window.webkitAudioContext)();
    function b(f,t,d){{var o=c.createOscillator(),g=c.createGain();
    o.connect(g);g.connect(c.destination);o.frequency.value=f;o.type='sine';
    g.gain.setValueAtTime(0.3,t);g.gain.exponentialRampToValueAtTime(0.001,t+d);
    o.start(t);o.stop(t+d)}}
    b({f1},c.currentTime,0.4);b({f2},c.currentTime+0.45,0.35);
    }}catch(e){{}}}})()</script>""",unsafe_allow_html=True)

# ─── AUTH ──────────────────────────────────────────────────────────────────────
def _tok(at,em,ts,did=""):
    return hashlib.sha256(f"{at}|{em}|{ts}|{did}|fx2024".encode()).hexdigest()[:16]

def save_session(at,em,ts=""):
    # device_id is generated once per browser session and stored in session_state
    # This means even if someone shares the URL, the token won't validate on a different device
    did=st.session_state.get("_device_id","")
    if not did:
        did=_secrets.token_hex(8)
        st.session_state["_device_id"]=did
    tok=_tok(at,em,ts,did)
    # We store the device_id in the URL so the same browser can reload without re-login
    st.query_params["s"]=f"{at}|{em}|{ts}|{tok}|{did}"

def load_session():
    try:
        raw=st.query_params.get("s","")
        if not raw: return None
        parts=raw.split("|")
        # Support both old format (4 parts) and new format (5 parts with device_id)
        if len(parts)==4:
            at,em,ts,tok=parts; did=""
        elif len(parts)==5:
            at,em,ts,tok,did=parts
        else: return None
        if tok!=_tok(at,em,ts,did): return None
        # Restore device_id into session so future saves stay consistent
        if did: st.session_state["_device_id"]=did
        return {"account_type":at,"email":em,
                "trial_start":datetime.datetime.fromisoformat(ts) if ts else None}
    except: return None

def clear_session(): st.query_params.clear()

DEFS={"logged_in":False,"account_type":None,"trial_start":None,"email":"",
      "journal":[],"subscribers":[],"sig_history":[],"page":"Dashboard",
      "_loaded":False,"_device_id":""}
for k,v in DEFS.items():
    if k not in st.session_state: st.session_state[k]=v
if not st.session_state._loaded:
    s=load_session()
    if s: st.session_state.update(logged_in=True,email=s["email"],
                                   account_type=s["account_type"],trial_start=s["trial_start"])
    st.session_state._loaded=True

def _sec(k,fb):
    try: return st.secrets.get(k,fb)
    except: return fb

ADM_PW=_sec("ADMIN_PASSWORD","sparro_admin_2024")
PRE_PW=_sec("PREMIUM_PASSWORD","sparro_pro_2024")
FREE_PW=_sec("FREE_PASSWORD","sparro_free")
AI_KEY=_sec("ANTHROPIC_API_KEY","")
TRIAL_H=48

def hours_left():
    if not st.session_state.trial_start: return 0
    return max(0,TRIAL_H-int((datetime.datetime.now()-st.session_state.trial_start).total_seconds()/3600))
def is_pro():
    at=st.session_state.account_type
    if at in ("admin","premium"): return True
    if at=="trial" and hours_left()>0: return True
    return False

# ─── LOGIN ─────────────────────────────────────────────────────────────────────
def login_page():
    st.markdown("""<div style='text-align:center;padding:40px 0 20px'>
    <div style='font-size:60px'>🚀</div>
    <div style='font-size:36px;font-weight:900;background:linear-gradient(90deg,#00c6ff,#0072ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent'>Sparro FX AI</div>
    <div style='color:#8b949e;margin-top:6px'>Realistic AI-Powered Forex & Commodity Signals</div>
    </div>""",unsafe_allow_html=True)
    st.markdown("""<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
    max-width:700px;margin:0 auto 24px auto'>
    <div style='background:linear-gradient(135deg,#1a1400,#2a2000);border:2px solid #ffd200;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>🥇</div>
    <div style='font-weight:900;color:#ffd200;font-size:15px'>Gold</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>SMC + S/R + EMA200<br>Specialist Pair</div>
    </div>
    <div style='background:linear-gradient(135deg,#1a0d00,#2a1500);border:2px solid #f7931a;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>₿</div>
    <div style='font-weight:900;color:#f7931a;font-size:15px'>Bitcoin</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>FVG + Divergence<br>Specialist Pair</div>
    </div>
    <div style='background:linear-gradient(135deg,#00001a,#000033);border:2px solid #4488ff;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>€</div>
    <div style='font-weight:900;color:#4488ff;font-size:15px'>EUR/USD</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>EMA + ADX + FVG<br>Specialist Pair</div>
    </div>
    </div>""",unsafe_allow_html=True)
    _,mid,_=st.columns([1,2,1])
    with mid:
        t1,t2,t3=st.tabs(["🔑 Login","🎁 48hr Free Trial","ℹ️ About"])
        with t1:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            em=st.text_input("Email",key="l_em",placeholder="you@email.com")
            pw=st.text_input("Password",key="l_pw",type="password")
            rem=st.checkbox("Stay logged in",value=True,key="l_rem")
            if st.button("🔓 Login",use_container_width=True,type="primary",key="l_btn"):
                at=("admin" if pw==ADM_PW else "premium" if pw==PRE_PW
                    else "free" if pw==FREE_PW else None)
                if at:
                    st.session_state.update(logged_in=True,account_type=at,email=em)
                    if rem: save_session(at,em)
                    st.rerun()
                else: st.error("❌ Wrong password.")
            st.markdown("</div>",unsafe_allow_html=True)
        with t2:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;margin-bottom:14px'>
            <span style='background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;
            border-radius:20px;padding:5px 16px;font-weight:700'>🎁 48 Hours FREE — Full Access</span>
            </div>""",unsafe_allow_html=True)
            st.markdown("- ✅ All 16 assets incl. Gold, Silver, Bitcoin, Ethereum, EUR/USD\n- ✅ Quality-filtered signals (aims for 70%+)\n- ✅ Signal Grade A/B/C + Market Condition\n- ✅ Session timing + Correlation warnings\n- ✅ Auto Trade Tickets + Position Sizing")
            te=st.text_input("Email",key="t_em",placeholder="you@email.com")
            tn=st.text_input("Name",key="t_nm",placeholder="First name")
            if st.button("🚀 Start Free Trial",use_container_width=True,type="primary",key="t_btn"):
                if "@" not in te: st.error("❌ Valid email needed")
                elif not tn.strip(): st.error("❌ Name needed")
                else:
                    ts=datetime.datetime.now()
                    st.session_state.update(logged_in=True,account_type="trial",trial_start=ts,email=te)
                    save_session("trial",te,ts.isoformat()); st.rerun()
            st.markdown("</div>",unsafe_allow_html=True)
        with t3:
            st.markdown("""<div class='login-box'>
            <h4 style='margin-top:0'>What is Sparro FX AI?</h4>
            <p style='color:#8b949e'>Realistic signal platform with quality filters designed for 70%+ win rate.
            Signals only fire when trend, strength, momentum, institutional zones AND session timing all align.</p>
            <b>🆓 Free</b> — Gold, BTC, EUR/USD + 2 pairs · basic signals<br><br>
            <b>🎁 Trial 48h</b> — full access · no card<br><br>
            <b>⚡ Premium $15/mo</b> — everything<br><br>
            <hr style='border-color:#30363d'>
            <small style='color:#8b949e'>Trade responsibly. No signal app guarantees profits.</small>
            </div>""",unsafe_allow_html=True)

if not st.session_state.logged_in: login_page(); st.stop()
if st.session_state.account_type=="trial" and hours_left()==0:
    st.error("⏰ Trial ended. Upgrade — $15/mo")
    if st.button("🔓 Login with premium password",key="exp_btn"):
        clear_session(); st.session_state.logged_in=False; st.rerun()
    st.stop()

pro=is_pro(); atype=st.session_state.account_type

# ═══════════════════════════════════════════════════════════════════════════════
# ASSETS & SPECIALIST CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
SPECIALISTS={
    "Gold (XAU/USD)":{"sym":"GC=F","icon":"🥇","color":"#ffd200","label":"GOLD",
        "best":["SMC Order Blocks","Support/Resistance","EMA Trend"],
        "why":"Institution-driven. SMC OBs and round numbers ($1900/$2000/$2100) are most reliable. EMA200 is gold's key level.",
        "sessions":["London","New York"],"tf_best":"Daily + 4H"},
    "Bitcoin":{"sym":"BTC-USD","icon":"₿","color":"#f7931a","label":"BTC",
        "best":["SMC Fair Value Gap","RSI + Divergence","Support/Resistance"],
        "why":"BTC leaves massive FVGs that always fill. RSI divergences on 4H are highly reliable. Round numbers ($60k/$70k/$80k) are magnets.",
        "sessions":["All"],"tf_best":"4H + Daily"},
    "EUR/USD":{"sym":"EURUSD=X","icon":"€","color":"#4488ff","label":"EUR/USD",
        "best":["EMA Trend","ADX Strength","SMC Fair Value Gap"],
        "why":"Most trend-following pair in forex. EMA stack is highly reliable. ADX confirms strong trends during London/NY overlap.",
        "sessions":["London","New York"],"tf_best":"1H + 4H"},
}

ALL_PAIRS={
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","EUR/USD":"EURUSD=X",
    "GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X","AUD/USD":"AUDUSD=X",
    "USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X","NZD/USD":"NZDUSD=X",
    "EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X","AUD/JPY":"AUDJPY=X",
    "Silver (XAG/USD)":"SI=F","Ethereum":"ETH-USD",
    "NASDAQ":"^IXIC","S&P 500":"^GSPC",
}
# Correlated pairs — warning when both signal same direction
CORRELATIONS=[
    (["EUR/USD","GBP/USD","AUD/USD","NZD/USD"],"USD pairs — same USD exposure"),
    (["USD/JPY","USD/CHF","USD/CAD"],"USD pairs — same USD exposure"),
    (["EUR/JPY","GBP/JPY","AUD/JPY"],"JPY cross pairs — same JPY exposure"),
    (["Gold (XAU/USD)","Silver (XAG/USD)"],"Precious metals — move together"),
    (["Gold (XAU/USD)","Bitcoin"],"Safe haven/risk assets — correlated in risk-off"),
    (["Bitcoin","Ethereum"],"Crypto majors — highly correlated"),
]
FREE_PAIRS=dict(list(ALL_PAIRS.items())[:5])
pairs=ALL_PAIRS if pro else FREE_PAIRS

# ─── DATA ──────────────────────────────────────────────────────────────────────
def get_df(sym,period="6mo",interval="1d"):
    try:
        df=yf.download(sym,period=period,interval=interval,progress=False,auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return None

# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY FILTERS — what makes signals realistic
# ═══════════════════════════════════════════════════════════════════════════════

def check_candle_quality(df):
    """
    Filter 1: Candle body filter
    If the last candle is a doji/indecision (body < 25% of range),
    the signal is unreliable. Returns True if candle is valid.
    """
    try:
        if "Open" not in df.columns: return True, "No OHLC data"
        o=float(df["Open"].iloc[-1]); c=float(df["Close"].iloc[-1])
        h=float(df["High"].iloc[-1]); l=float(df["Low"].iloc[-1])
        body=abs(c-o); rng=h-l
        if rng==0: return True,"No range data"
        ratio=body/rng
        if ratio<0.25:
            return False,f"Doji/indecision candle (body={round(ratio*100)}% of range) — wait for conviction"
        return True,f"Solid candle body ({round(ratio*100)}% of range) ✅"
    except: return True,"Candle check error"

def check_atr_filter(df):
    """
    Filter 2: ATR volatility filter
    If ATR is extremely low (<0.1% of price) = dead market, avoid
    If ATR is extremely high (>3% of price) = news spike, avoid
    Returns True if market has normal volatility.
    """
    try:
        c=df["Close"]; h=df["High"]; l=df["Low"]
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1])
        price=float(c.iloc[-1])
        atr_pct=atr/price*100
        if atr_pct<0.08: return False,f"ATR too low ({round(atr_pct,2)}%) — dead market, avoid"
        if atr_pct>4.0:  return False,f"ATR too high ({round(atr_pct,2)}%) — news spike, avoid"
        return True,f"Normal volatility ATR={round(atr_pct,2)}% ✅"
    except: return True,"ATR check error"

def check_weekly_trend(sym,sig):
    """
    Filter 3: Weekly trend alignment
    Signal must agree with the weekly timeframe trend.
    Counter-trend signals on weekly are lower quality.
    """
    try:
        df=get_df(sym,"1y","1wk")
        if df is None or len(df)<10: return True,"Weekly data unavailable",True
        c=df["Close"]
        e20w=float(c.ewm(20).mean().iloc[-1]); e10w=float(c.ewm(10).mean().iloc[-1])
        pw=float(c.iloc[-1])
        weekly_bull=pw>e20w and e10w>e20w
        weekly_bear=pw<e20w and e10w<e20w
        if "BUY" in sig and weekly_bull:
            return True,"Weekly trend BULLISH ✅ — signal aligned",True
        if "SELL" in sig and weekly_bear:
            return True,"Weekly trend BEARISH ✅ — signal aligned",True
        if "BUY" in sig and weekly_bear:
            return False,"Weekly trend BEARISH ⚠️ — buying against weekly trend",False
        if "SELL" in sig and weekly_bull:
            return False,"Weekly trend BULLISH ⚠️ — selling against weekly trend",False
        return True,"Weekly trend neutral — proceed with caution",False
    except: return True,"Weekly check error",False

def get_session_status(asset_name):
    """
    Returns whether we're in the optimal trading session for this asset.
    """
    now_utc=datetime.datetime.utcnow()
    hour=now_utc.hour
    london_open=7<=hour<16      # 7am-4pm UTC
    newyork_open=13<=hour<22   # 1pm-10pm UTC
    asian_open=(hour>=22 or hour<7)
    spec=SPECIALISTS.get(asset_name,{})
    sessions=spec.get("sessions",["All"])
    if "All" in sessions: return True,"24/7 asset — any time is fine ✅"
    in_london=(london_open and "London" in sessions)
    in_ny=(newyork_open and "New York" in sessions)
    if in_london and in_ny: return True,"London/New York overlap — BEST session ✅"
    if in_london: return True,"London session — good timing ✅"
    if in_ny: return True,"New York session — good timing ✅"
    if asian_open:
        return False,f"Asian session — {', '.join(sessions)} pairs trade better in London/NY"
    return False,f"Outside optimal session for {asset_name} — lower probability"

def get_market_condition(df):
    """
    Detect if market is Trending, Ranging, or Volatile.
    This tells users how to adjust their approach.
    """
    try:
        c=df["Close"]; h=df["High"]; l=df["Low"]
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1])
        atr_ma=float(tr.rolling(14).mean().rolling(14).mean().iloc[-1])
        up=h.diff(); dn=-l.diff()
        pdm=up.where((up>dn)&(up>0),0); ndm=dn.where((dn>up)&(dn>0),0)
        atr_s=tr.ewm(14).mean()
        pdi=100*(pdm.ewm(14).mean()/atr_s); ndi=100*(ndm.ewm(14).mean()/atr_s)
        adx=float((100*(pdi-ndi).abs()/(pdi+ndi)).ewm(14).mean().iloc[-1])
        atr_ratio=atr/atr_ma if atr_ma>0 else 1
        if atr_ratio>1.5: return "Volatile","⚡","#f7931a","High volatility — reduce position size, use wider stops"
        if adx>25:        return "Trending","📈","#3fb950","Strong trend — ideal for signals, trend-following works"
        if adx>18:        return "Moderate","📊","#ffd200","Moderate trend — proceed normally, use standard size"
        return "Ranging","↔️","#8b949e","Ranging market — lower win rate expected, reduce size or avoid"
    except: return "Unknown","❓","#8b949e","Market condition unknown"

# ═══════════════════════════════════════════════════════════════════════════════
# 6 PRECISION STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════════
def s_ema(df):
    c=df["Close"]
    e20=float(c.ewm(20).mean().iloc[-1]); e50=float(c.ewm(50).mean().iloc[-1])
    e200=float(c.ewm(200).mean().iloc[-1]); p=float(c.iloc[-1])
    if e20>e50>e200 and p>e20: return "BUY","EMA20>EMA50>EMA200 — full bullish stack"
    if e20<e50<e200 and p<e20: return "SELL","EMA20<EMA50<EMA200 — full bearish stack"
    if e20>e200 and p>e50:     return "BUY","Above EMA200 — long-term uptrend"
    if e20<e200 and p<e50:     return "SELL","Below EMA200 — long-term downtrend"
    return "NEUTRAL","EMA stack mixed"

def s_adx(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        up=h.diff(); dn=-l.diff()
        pdm=up.where((up>dn)&(up>0),0); ndm=dn.where((dn>up)&(dn>0),0)
        atr=tr.ewm(14,min_periods=14).mean()
        pdi=100*(pdm.ewm(14,min_periods=14).mean()/atr)
        ndi=100*(ndm.ewm(14,min_periods=14).mean()/atr)
        adx=float((100*(pdi-ndi).abs()/(pdi+ndi)).ewm(14,min_periods=14).mean().iloc[-1])
        pv=float(pdi.iloc[-1]); nv=float(ndi.iloc[-1])
        if adx>=30 and pv>nv: return "BUY", f"ADX={round(adx,1)} — strong uptrend confirmed"
        if adx>=30 and nv>pv: return "SELL",f"ADX={round(adx,1)} — strong downtrend confirmed"
        if adx>=20 and pv>nv: return "BUY", f"ADX={round(adx,1)} — moderate uptrend"
        if adx>=20 and nv>pv: return "SELL",f"ADX={round(adx,1)} — moderate downtrend"
        return "NEUTRAL",f"ADX={round(adx,1)} — ranging, avoid trend trades"
    except: return "NEUTRAL","ADX error"

def s_rsi(df):
    try:
        c=df["Close"]; d=c.diff()
        g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
        rsi=100-(100/(1+(g/l))); rv=float(rsi.iloc[-1])
        prices=c.iloc[-20:].values; rsis=rsi.iloc[-20:].values
        ph=[i for i in range(1,len(prices)-1) if prices[i]>prices[i-1] and prices[i]>prices[i+1]]
        pl=[i for i in range(1,len(prices)-1) if prices[i]<prices[i-1] and prices[i]<prices[i+1]]
        if len(ph)>=2:
            h1,h2=ph[-2],ph[-1]
            if prices[h2]>prices[h1] and rsis[h2]<rsis[h1]:
                return "SELL",f"RSI={round(rv,1)} Bearish Divergence — momentum weakening"
        if len(pl)>=2:
            l1,l2=pl[-2],pl[-1]
            if prices[l2]<prices[l1] and rsis[l2]>rsis[l1]:
                return "BUY",f"RSI={round(rv,1)} Bullish Divergence — momentum recovering"
        if rv>60: return "BUY", f"RSI={round(rv,1)} — bullish momentum"
        if rv>52: return "BUY", f"RSI={round(rv,1)} — building bullish"
        if rv<40: return "SELL",f"RSI={round(rv,1)} — bearish momentum"
        if rv<48: return "SELL",f"RSI={round(rv,1)} — building bearish"
        return "NEUTRAL",f"RSI={round(rv,1)} — neutral"
    except: return "NEUTRAL","RSI error"

def s_ob(df):
    try:
        o=df["Open"]; h=df["High"]; l=df["Low"]; c=df["Close"]
        cp=float(c.iloc[-1]); bobs=[]; sobs=[]
        for i in range(2,min(60,len(df)-3)):
            idx=-i
            if (c.iloc[idx]<o.iloc[idx] and c.iloc[idx+1]>o.iloc[idx+1]
                    and c.iloc[idx+2]>o.iloc[idx+2] and c.iloc[idx+2]>float(h.iloc[idx])):
                bobs.append((float(l.iloc[idx]),float(h.iloc[idx])))
            if (c.iloc[idx]>o.iloc[idx] and c.iloc[idx+1]<o.iloc[idx+1]
                    and c.iloc[idx+2]<o.iloc[idx+2] and c.iloc[idx+2]<float(l.iloc[idx])):
                sobs.append((float(l.iloc[idx]),float(h.iloc[idx])))
        for lo,hi in bobs[:3]:
            if lo<=cp<=hi*1.003: return "BUY",f"SMC Bullish OB {round(lo,4)}-{round(hi,4)} — institutional buy zone"
            if hi<cp<=hi*1.01:   return "BUY",f"SMC Above Bullish OB {round(lo,4)} — institutional support"
        for lo,hi in sobs[:3]:
            if lo*0.997<=cp<=hi: return "SELL",f"SMC Bearish OB {round(lo,4)}-{round(hi,4)} — institutional sell zone"
            if lo*0.99<=cp<lo:   return "SELL",f"SMC Below Bearish OB {round(hi,4)} — institutional resistance"
        return "NEUTRAL","No active Order Blocks near price"
    except: return "NEUTRAL","SMC OB insufficient data"

def s_fvg(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        cp=float(c.iloc[-1]); bfvg=[]; sfvg=[]
        for i in range(2,min(50,len(df)-3)):
            idx=-i
            ph=float(h.iloc[idx-1]); nl=float(l.iloc[idx+1])
            if nl>ph and (nl-ph)/ph>0.0008: bfvg.append((ph,nl))
            pl2=float(l.iloc[idx-1]); nh=float(h.iloc[idx+1])
            if pl2>nh and (pl2-nh)/pl2>0.0008: sfvg.append((nh,pl2))
        for lo,hi in bfvg[:5]:
            if lo<=cp<=hi:        return "BUY",f"SMC Bullish FVG {round(lo,4)}-{round(hi,4)} — filling imbalance"
            if cp<lo and cp>=lo*0.997: return "BUY",f"SMC Bullish FVG magnet at {round(lo,4)}"
        for lo,hi in sfvg[:5]:
            if lo<=cp<=hi:        return "SELL",f"SMC Bearish FVG {round(lo,4)}-{round(hi,4)} — filling imbalance"
            if cp>hi and cp<=hi*1.003: return "SELL",f"SMC Bearish FVG magnet at {round(hi,4)}"
        return "NEUTRAL","No active Fair Value Gaps near price"
    except: return "NEUTRAL","SMC FVG insufficient data"

def s_sr(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        p=float(c.iloc[-1])
        res=float(h.rolling(20).max().iloc[-1]); sup=float(l.rolling(20).min().iloc[-1])
        mid=(res+sup)/2; rng=res-sup; zone=rng*0.10
        pct=round((p-sup)/rng*100,1) if rng>0 else 50
        if p>=res-zone: return "SELL",f"At resistance {round(res,4)} ({pct}% of range)"
        if p<=sup+zone: return "BUY", f"At support {round(sup,4)} ({pct}% of range)"
        if p>mid+zone:  return "BUY", f"Upper range {pct}% — bullish bias"
        if p<mid-zone:  return "SELL",f"Lower range {pct}% — bearish bias"
        return "NEUTRAL",f"Mid-range {pct}%"
    except: return "NEUTRAL","S/R error"

STRATS={"EMA Trend":(s_ema,"📈","Trend Direction"),
        "ADX Strength":(s_adx,"💪","Trend Strength Filter"),
        "RSI + Divergence":(s_rsi,"⚡","Momentum & Divergence"),
        "SMC Order Blocks":(s_ob,"🏦","Institutional Zones"),
        "SMC Fair Value Gap":(s_fvg,"🕳️","Price Imbalances"),
        "Support/Resistance":(s_sr,"🧱","Key Price Levels")}

# ─── SIGNAL GRADE ──────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL REAL SMC / STRUCTURE DETECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def detect_bos_choch(df):
    """
    Break of Structure (BOS) = trend continuation (new HH in uptrend / new LL in downtrend)
    Change of Character (CHOCH) = trend reversal (structure breaks against prevailing trend)
    """
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        recent_h=h.iloc[-30:]; recent_l=l.iloc[-30:]
        swings_h=[]; swings_l=[]
        for i in range(2,len(recent_h)-2):
            if recent_h.iloc[i]>recent_h.iloc[i-1] and recent_h.iloc[i]>recent_h.iloc[i-2] and \
               recent_h.iloc[i]>recent_h.iloc[i+1] and recent_h.iloc[i]>recent_h.iloc[i+2]:
                swings_h.append(float(recent_h.iloc[i]))
            if recent_l.iloc[i]<recent_l.iloc[i-1] and recent_l.iloc[i]<recent_l.iloc[i-2] and \
               recent_l.iloc[i]<recent_l.iloc[i+1] and recent_l.iloc[i]<recent_l.iloc[i+2]:
                swings_l.append(float(recent_l.iloc[i]))
        cp=float(c.iloc[-1])
        if len(swings_h)>=2 and len(swings_l)>=2:
            last_hh=swings_h[-1]; prev_hh=swings_h[-2]
            last_ll=swings_l[-1]; prev_ll=swings_l[-2]
            uptrend=last_hh>prev_hh and last_ll>prev_ll
            downtrend=last_hh<prev_hh and last_ll<prev_ll
            if uptrend and cp>last_hh:
                return "BUY","BOS","Break of Structure — new higher high, uptrend continuing"
            if downtrend and cp<last_ll:
                return "SELL","BOS","Break of Structure — new lower low, downtrend continuing"
            if uptrend and cp<last_ll:
                return "SELL","CHOCH","Change of Character — uptrend broken, reversal warning"
            if downtrend and cp>last_hh:
                return "BUY","CHOCH","Change of Character — downtrend broken, reversal warning"
        return "NEUTRAL","—","No clear BOS/CHOCH structure"
    except: return "NEUTRAL","—","Structure detection error"

def detect_liquidity_sweep(df):
    """Price wicks beyond a recent swing high/low then closes back inside — stop hunt."""
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]; o=df["Open"]
        recent_h=float(h.iloc[-15:-1].max()); recent_l=float(l.iloc[-15:-1].min())
        last_h=float(h.iloc[-1]); last_l=float(l.iloc[-1]); last_c=float(c.iloc[-1])
        if last_h>recent_h and last_c<recent_h:
            return "SELL",f"Liquidity Sweep — wicked above {round(recent_h,4)} then rejected"
        if last_l<recent_l and last_c>recent_l:
            return "BUY",f"Liquidity Sweep — wicked below {round(recent_l,4)} then rejected"
        return "NEUTRAL","No recent liquidity sweep detected"
    except: return "NEUTRAL","Liquidity sweep error"

def detect_premium_discount(df):
    """Divides recent range into thirds — discount (buy zone) / premium (sell zone)."""
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        swing_h=float(h.iloc[-30:].max()); swing_l=float(l.iloc[-30:].min())
        rng=swing_h-swing_l
        if rng<=0: return "NEUTRAL","No range",50
        cp=float(c.iloc[-1])
        pct=(cp-swing_l)/rng*100
        if pct<=30: return "BUY",f"DISCOUNT zone ({round(pct)}%) — favorable buying area",round(pct)
        if pct>=70: return "SELL",f"PREMIUM zone ({round(pct)}%) — favorable selling area",round(pct)
        return "NEUTRAL",f"EQUILIBRIUM zone ({round(pct)}%) — wait for premium/discount",round(pct)
    except: return "NEUTRAL","Premium/discount error",50

def detect_candle_pattern(df):
    """Engulfing, Pin Bar, Doji pattern detection."""
    try:
        o=df["Open"]; h=df["High"]; l=df["Low"]; c=df["Close"]
        o1,h1,l1,c1=float(o.iloc[-1]),float(h.iloc[-1]),float(l.iloc[-1]),float(c.iloc[-1])
        o2,c2=float(o.iloc[-2]),float(c.iloc[-2])
        body1=abs(c1-o1); range1=h1-l1
        upper_wick=h1-max(c1,o1); lower_wick=min(c1,o1)-l1
        if c1>o1 and c2<o2 and c1>o2 and o1<c2:
            return "BUY","Bullish Engulfing","Strong reversal — buyers overwhelmed sellers"
        if c1<o1 and c2>o2 and c1<o2 and o1>c2:
            return "SELL","Bearish Engulfing","Strong reversal — sellers overwhelmed buyers"
        if range1>0 and lower_wick>body1*2 and upper_wick<body1*0.5:
            return "BUY","Bullish Pin Bar","Long lower wick — rejection of lower prices"
        if range1>0 and upper_wick>body1*2 and lower_wick<body1*0.5:
            return "SELL","Bearish Pin Bar","Long upper wick — rejection of higher prices"
        if range1>0 and body1/range1<0.1:
            return "NEUTRAL","Doji","Indecision candle — no clear direction"
        return "NEUTRAL","No Pattern","No significant candlestick pattern"
    except: return "NEUTRAL","Error","Pattern detection error"

def calc_currency_strength():
    """Currency Strength Meter — relative % change of each currency across its pairs."""
    pairs_map={"EURUSD=X":("EUR","USD"),"GBPUSD=X":("GBP","USD"),"USDJPY=X":("USD","JPY"),
               "AUDUSD=X":("AUD","USD"),"USDCHF=X":("USD","CHF"),"USDCAD=X":("USD","CAD")}
    scores={"EUR":[],"USD":[],"GBP":[],"JPY":[],"AUD":[],"CHF":[],"CAD":[]}
    for sym,(base,quote) in pairs_map.items():
        df=get_df(sym,"5d","1h")
        if df is None or len(df)<2: continue
        try:
            chg=float((df["Close"].iloc[-1]/df["Close"].iloc[0]-1)*100)
            scores[base].append(chg); scores[quote].append(-chg)
        except: continue
    result={}
    for cur,vals in scores.items():
        result[cur]=round(sum(vals)/len(vals),3) if vals else 0.0
    return dict(sorted(result.items(),key=lambda x:x[1],reverse=True))

def calc_risk_of_ruin(win_rate,avg_rr,risk_pct):
    """Simplified risk-of-ruin estimate from win rate, R:R and risk per trade."""
    try:
        wr=win_rate/100
        if wr<=0 or wr>=1: return 100.0
        edge=(wr*avg_rr)-(1-wr)
        if edge<=0: return 95.0
        a=((1-wr)/wr)**(100/max(risk_pct,0.5))
        return min(100.0,round(a*100,1))
    except: return 50.0

def detect_overtrading(journal):
    """AI Trading Coach: flags overtrading and revenge trading patterns from journal data."""
    flags=[]
    if not journal: return flags
    df=pd.DataFrame(journal)
    if "Date" in df.columns:
        today=str(datetime.date.today())
        today_trades=df[df["Date"]==today]
        if len(today_trades)>=5:
            flags.append(("⚠️ Overtrading","You've logged "+str(len(today_trades))+" trades today. More than 4-5 trades/day often means lower-quality setups are being taken."))
    # Revenge trading: a loss followed quickly by another trade on the same asset same day
    if "Result" in df.columns and "Asset" in df.columns and len(df)>=2:
        recent=df.tail(10)
        for i in range(1,len(recent)):
            prev=recent.iloc[i-1]; cur=recent.iloc[i]
            if prev.get("Result")=="Loss" and cur.get("Asset")==prev.get("Asset") and cur.get("Date")==prev.get("Date"):
                flags.append(("🔴 Possible Revenge Trading","Re-entered "+str(cur.get("Asset"))+" same day right after a loss. Consider waiting before re-entering the same asset."))
                break
    closed=df[df["Result"].isin(["Win","Loss"])] if "Result" in df.columns else pd.DataFrame()
    if len(closed)>=5:
        wins=len(closed[closed["Result"]=="Win"]); wr=wins/len(closed)*100
        if wr<40:
            flags.append(("📉 Low Win Rate Warning","Your recent win rate is "+str(round(wr,1))+"%. Consider only taking Grade A signals until this improves."))
    return flags


def get_signal_grade(conf, candle_ok, atr_ok, weekly_ok, session_ok, mtf_ok, is_spec):
    """
    Grade A: Best setup  — all filters pass, MTF confirmed, specialist pair
    Grade B: Good setup  — most filters pass, tradeable
    Grade C: Marginal    — some filters fail, reduce size or skip
    Grade D: Poor        — multiple filters fail, skip
    """
    score=0
    if conf>=83:     score+=3
    elif conf>=67:   score+=2
    else:            score+=1
    if candle_ok:    score+=2
    if atr_ok:       score+=1
    if weekly_ok:    score+=2
    if session_ok:   score+=2
    if mtf_ok:       score+=3
    if is_spec:      score+=1
    if score>=12:    return "A","grade-a","🏆 Grade A — Highest Quality","Take full position"
    if score>=9:     return "B","grade-b","⭐ Grade B — Good Setup","Take normal position"
    if score>=6:     return "C","grade-c","⚠️ Grade C — Marginal","Take 50% position or skip"
    return "D","grade-c","🚫 Grade D — Poor Quality","Skip this signal"

# ─── WEIGHTED STRATEGY SCORING ─────────────────────────────────────────────────
def run_strats(sym,period="6mo",asset_name=None):
    df=get_df(sym,period)
    if df is None or len(df)<50: return {},0,"ERROR",df
    spec=SPECIALISTS.get(asset_name,{})
    best=spec.get("best",[])
    res={}
    for name,(fn,ico,desc) in STRATS.items():
        try: res[name]=fn(df)
        except: res[name]=("NEUTRAL","Error")
    bs=0; ss=0; tw=0
    for name,(sig,_) in res.items():
        w=2.0 if name in best else 1.0; tw+=w
        if sig=="BUY": bs+=w
        if sig=="SELL": ss+=w
    if bs>ss:
        conf=round(bs/tw*100)
        sig="STRONG BUY" if bs/tw>=0.83 else "BUY" if bs/tw>=0.67 else "WAIT"
    elif ss>bs:
        conf=round(ss/tw*100)
        sig="STRONG SELL" if ss/tw>=0.83 else "SELL" if ss/tw>=0.67 else "WAIT"
    else:
        conf=50; sig="WAIT"
    return res,conf,sig,df

def run_mtf(sym,asset_name=None):
    tfs={}
    for label,period,interval in [("Daily","6mo","1d"),("4H","60d","4h"),("1H","5d","1h")]:
        df=get_df(sym,period,interval)
        if df is None or len(df)<30: tfs[label]=("WAIT",0); continue
        spec=SPECIALISTS.get(asset_name,{}); best=spec.get("best",[])
        res={}
        for name,(fn,_,__) in STRATS.items():
            try: res[name]=fn(df)
            except: res[name]=("NEUTRAL","Error")
        bs=0; ss=0; tw=0
        for name,(sg,_) in res.items():
            w=2.0 if name in best else 1.0; tw+=w
            if sg=="BUY": bs+=w
            if sg=="SELL": ss+=w
        if bs>ss and bs/tw>=0.67:   tfs[label]=("BUY",round(bs/tw*100))
        elif ss>bs and ss/tw>=0.67: tfs[label]=("SELL",round(ss/tw*100))
        else:                        tfs[label]=("WAIT",50)
    sigs=[s for s,_ in tfs.values() if s!="WAIT"]
    bc=sum(1 for s in sigs if s=="BUY"); sc=sum(1 for s in sigs if s=="SELL")
    if bc==3:   ms="STRONG BUY";  mn="All 3 timeframes aligned ✅"
    elif bc==2: ms="BUY";         mn="2/3 timeframes agree"
    elif sc==3: ms="STRONG SELL"; mn="All 3 timeframes aligned ✅"
    elif sc==2: ms="SELL";        mn="2/3 timeframes agree"
    else:       ms="WAIT";        mn="Timeframes conflicting"
    return tfs,ms,mn

# ─── FULL TIMEFRAME SELECTOR (M1 → W1) ─────────────────────────────────────────
# Yahoo Finance data limits per interval — used to pick safe period for each TF.
TF_CONFIG={
    "M1": {"interval":"1m","period":"7d","label":"1 Minute","light":True},
    "M5": {"interval":"5m","period":"60d","label":"5 Minutes","light":True},
    "M15":{"interval":"15m","period":"60d","label":"15 Minutes","light":True},
    "M30":{"interval":"30m","period":"60d","label":"30 Minutes","light":False},
    "H1": {"interval":"1h","period":"730d","label":"1 Hour","light":False},
    "H4": {"interval":"4h" if False else "1h","period":"60d","label":"4 Hours","light":False,"resample":"4h"},
    "D1": {"interval":"1d","period":"2y","label":"Daily","light":False},
    "W1": {"interval":"1wk","period":"5y","label":"Weekly","light":False},
}

def resample_to_4h(df):
    try:
        agg={"Open":"first","High":"max","Low":"min","Close":"last"}
        if "Volume" in df.columns: agg["Volume"]="sum"
        return df.resample("4h").agg(agg).dropna()
    except: return df

def run_single_timeframe(sym,tf_key,asset_name=None):
    """
    Run analysis on ANY single timeframe from M1 to W1.
    Light timeframes (M1/M5/M15) have limited history, so we use a lighter
    3-strategy check (EMA, RSI, S/R) instead of the full 6, since SMC/EMA200
    need more candles than these short timeframes provide.
    """
    cfg=TF_CONFIG.get(tf_key)
    if not cfg: return None,0,"ERROR",None,"Invalid timeframe"
    df=get_df(sym,cfg["period"],cfg["interval"])
    if df is None or len(df)<20:
        return None,0,"NO DATA",None,f"Not enough {cfg['label']} data available"
    if tf_key=="H4":
        df=resample_to_4h(df)
        if len(df)<20: return None,0,"NO DATA",None,"Not enough data to build 4H candles"

    if cfg["light"]:
        # Reduced strategy set for very short timeframes (not enough candles for EMA200/SMC)
        res={}
        try: res["EMA Trend (short)"]=s_ema(df) if len(df)>=200 else ("NEUTRAL","Not enough candles for EMA200 on this TF")
        except: res["EMA Trend (short)"]=("NEUTRAL","Error")
        try: res["RSI + Divergence"]=s_rsi(df)
        except: res["RSI + Divergence"]=("NEUTRAL","Error")
        try: res["Support/Resistance"]=s_sr(df)
        except: res["Support/Resistance"]=("NEUTRAL","Error")
        b=sum(1 for s,_ in res.values() if s=="BUY"); s=sum(1 for s,_ in res.values() if s=="SELL")
        t=len(res)
        if b>s and b>=2:   conf=round(b/t*100); sig="BUY"
        elif s>b and s>=2: conf=round(s/t*100); sig="SELL"
        else: conf=50; sig="WAIT"
        note=f"⚠️ {cfg['label']} has limited history — using lighter 3-strategy check (EMA200/SMC need more candles)"
    else:
        res={}
        for name,(fn,ico,desc) in STRATS.items():
            try: res[name]=fn(df)
            except: res[name]=("NEUTRAL","Error")
        b=sum(1 for s,_ in res.values() if s=="BUY"); s=sum(1 for s,_ in res.values() if s=="SELL")
        t=len(res)
        if b>s and b/t>=0.67:   conf=round(b/t*100); sig="STRONG BUY" if b/t>=0.83 else "BUY"
        elif s>b and s/t>=0.67: conf=round(s/t*100); sig="STRONG SELL" if s/t>=0.83 else "SELL"
        else: conf=50; sig="WAIT"
        note=f"Full 6-strategy analysis on {cfg['label']}"
    return res,conf,sig,df,note

def get_setup(sym,direction):
    try:
        df=get_df(sym,"3mo"); c=df["Close"]; h=df["High"]; l=df["Low"]; p=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); risk=atr*1.5
        if "BUY" in direction: return p,p-risk,p+risk,p+risk*2,p+risk*3,atr
        else:                  return p,p+risk,p-risk,p-risk*2,p-risk*3,atr
    except: return None,None,None,None,None,None

# ═══════════════════════════════════════════════════════════════════════════════
# PRECISION ENTRY TOOLS — for small accounts wanting tighter, structural risk
# ═══════════════════════════════════════════════════════════════════════════════

def get_structure_sl(sym,direction,entry,atr):
    """
    Structure-based stop loss: uses the nearest real swing high/low instead
    of a flat ATR multiple. Often tighter than ATR×1.5, but anchored to an
    actual price level that would invalidate the trade if broken — not an
    arbitrary distance. Falls back to the ATR stop if no clean swing is found
    or if structure stop would be tighter than 0.5×ATR (too tight to be real).
    """
    try:
        df=get_df(sym,"1mo","1h")
        if df is None or len(df)<20:
            df=get_df(sym,"3mo","1d")
        if df is None or len(df)<10: return None,"No data for structure stop"
        h=df["High"]; l=df["Low"]
        lookback=min(40,len(df)-1)
        min_dist=atr*0.5  # structure stop must be at least this far to be valid
        if "BUY" in direction:
            # nearest swing low below entry
            recent_low=float(l.iloc[-lookback:].min())
            if recent_low>=entry: return None,"No clean swing low found below entry"
            dist=entry-recent_low
            if dist<min_dist:
                return None,f"Nearest swing low too close ({round(dist,5)}) — using ATR stop instead"
            sl=recent_low-(atr*0.1)  # small buffer below the swing
            return sl,f"Structure SL at swing low {round(recent_low,5)} (+buffer)"
        else:
            recent_high=float(h.iloc[-lookback:].max())
            if recent_high<=entry: return None,"No clean swing high found above entry"
            dist=recent_high-entry
            if dist<min_dist:
                return None,f"Nearest swing high too close ({round(dist,5)}) — using ATR stop instead"
            sl=recent_high+(atr*0.1)
            return sl,f"Structure SL at swing high {round(recent_high,5)} (+buffer)"
    except Exception as e:
        return None,f"Structure stop error: {e}"

def get_entry_zone(sym,direction,entry,atr):
    """
    Instead of one exact entry price, gives a realistic zone to enter within.
    This lets a person scale in or wait for a slightly better price rather
    than chasing the market price the instant the signal fires.
    Zone width is a fraction of ATR — tight enough to stay relevant, wide
    enough to be achievable.
    """
    try:
        zone_width=atr*0.15
        if "BUY" in direction:
            zone_low=entry-zone_width; zone_high=entry
        else:
            zone_low=entry; zone_high=entry+zone_width
        return zone_low,zone_high
    except: return entry,entry

def get_account_warning(balance,entry,sl,risk_pct,is_forex=True):
    """
    Tells a small-account trader whether this setup is actually safely
    tradeable at their balance and risk %, accounting for typical spread
    cost eating into a small stop distance.
    """
    try:
        risk_amt=balance*risk_pct/100
        sl_distance=abs(entry-sl)
        if is_forex:
            pips=sl_distance*10000
            typical_spread_pips=1.5  # rough typical spread, varies by broker/pair
            if pips<=0: return "error","Invalid stop distance"
            spread_cost_pct=(typical_spread_pips/pips)*100
            min_lot_value=risk_amt/(pips*10) if pips>0 else 0
            if spread_cost_pct>25:
                return "warning",f"⚠️ Stop is only {round(pips,1)} pips — spread could eat {round(spread_cost_pct)}% of your risk. Consider a less tight setup or a bigger account."
            if balance<100 and min_lot_value<0.01:
                return "warning","⚠️ Risk amount is very small for this stop distance — position size may round to the broker's minimum lot, increasing effective risk %."
            return "ok",f"✅ Spread impact ~{round(spread_cost_pct)}% of risk — acceptable for this account size."
        else:
            if sl_distance<=0: return "error","Invalid stop distance"
            return "ok","✅ Setup looks tradeable for this account size."
    except Exception as e:
        return "error",f"Account check error: {e}"

def get_position_size(balance,risk_pct,sl,entry,is_forex=True):
    """Auto position sizing based on signal grade and ATR."""
    try:
        risk_amt=balance*risk_pct/100
        sl_distance=abs(entry-sl)
        if is_forex: pip_value=10; pips=sl_distance*10000; lot=round(risk_amt/(pips*pip_value)*100)/100
        else: lot=round(risk_amt/sl_distance,4)
        return round(lot,2)
    except: return 0.01

def get_fibs(sym):
    try:
        df=get_df(sym,"3mo")
        hi=float(df["High"].iloc[-20:].max()); lo=float(df["Low"].iloc[-20:].min()); d=hi-lo
        return {"0.786":hi-d*0.214,"0.618":hi-d*0.382,"0.5":hi-d*0.5,
                "0.382":hi-d*0.618,"0.236":hi-d*0.764}
    except: return {}

def get_pivots(sym):
    try:
        df=get_df(sym,"5d"); prev=df.iloc[-2]
        hi=float(prev["High"]); lo=float(prev["Low"]); cl=float(prev["Close"])
        pp=(hi+lo+cl)/3
        return {"R2":pp+(hi-lo),"R1":2*pp-lo,"PP":pp,"S1":2*pp-hi,"S2":pp-(hi-lo)}
    except: return {}

def auto_ticket(asset,sig,conf,entry,sl,tp1,tp2,tp3,grade,src="Auto"):
    today=str(datetime.date.today())
    dup=[t for t in st.session_state.journal
         if t.get("Asset")==asset and t.get("Date")==today and t.get("Signal")==sig]
    if dup: return False
    now_iso=datetime.datetime.now().isoformat()
    st.session_state.journal.append({
        "Date":today,"Time":datetime.datetime.now().strftime("%H:%M"),
        "Asset":asset,"Signal":sig,"Grade":grade,"Entry":round(entry,5),"SL":round(sl,5),
        "TP1":round(tp1,5),"TP2":round(tp2,5),"TP3":round(tp3,5),
        "Confidence":conf,"Result":"Open","Source":src,"CreatedAt":now_iso})
    st.session_state.sig_history.append({
        "DateTime":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Asset":asset,"Signal":sig,"Grade":grade,"Confidence":conf,
        "Entry":round(entry,5),"Result":"Pending"})
    return True

# ─── SIGNAL CARD HELPERS ───────────────────────────────────────────────────────
def calc_rr(entry,sl,tp1):
    """Calculate risk:reward ratio for display, e.g. '1:2'."""
    try:
        risk=abs(entry-sl); reward=abs(tp1-entry)
        if risk<=0: return "—"
        ratio=round(reward/risk,1)
        return f"1:{ratio}"
    except: return "—"

def time_ago(scanned_at):
    """Format a datetime as 'Xm ago' / 'Xh ago' for signal freshness."""
    try:
        delta=datetime.datetime.now()-scanned_at
        mins=int(delta.total_seconds()/60)
        if mins<1: return "just now"
        if mins<60: return f"{mins}m ago"
        hrs=mins//60
        return f"{hrs}h ago"
    except: return "just now"

def build_one_liner(asset,sig,agreeing_strats,grade):
    """
    One tight plain-English sentence summarizing the setup, similar in spirit
    to a single-paragraph signal reasoning. Built from our own real strategy
    agreement data — not a templated guess.
    """
    direction="bullish" if "BUY" in sig else "bearish"
    n=len(agreeing_strats)
    lead=agreeing_strats[0] if agreeing_strats else "multiple signals"
    conviction={"A":"high","B":"good","C":"moderate"}.get(grade,"moderate")
    return f"{lead} is leading a {direction} case on {asset}, with {n} strategies in agreement — conviction rated {conviction} for this {grade}-grade setup."

def build_copy_text(asset,sig,entry,sl,tp1,tp2,tp3,rr,grade):
    """Plain text block a person can copy and paste into MT4/MT5 manually."""
    return (f"{asset} — {sig} (Grade {grade})\n"
            f"Entry: {round(entry,5)}\n"
            f"Stop Loss: {round(sl,5)}\n"
            f"TP1: {round(tp1,5)}  TP2: {round(tp2,5)}  TP3: {round(tp3,5)}\n"
            f"Risk:Reward {rr}\n"
            f"— Sparro FX AI")

# ─── CORRELATION CHECK ──────────────────────────────────────────────────────────
def check_correlations(active_signals):
    warnings=[]
    for group,msg in CORRELATIONS:
        active_in_group=[a for a in active_signals if a in group]
        if len(active_in_group)>=2:
            warnings.append(f"⚠️ Correlation: {' + '.join(active_in_group)} — {msg}. Trading both doubles your risk.")
    return warnings

# ─── SIGNAL BANNER ─────────────────────────────────────────────────────────────
def banner(sig,asset,conf,grade=None):
    spec=SPECIALISTS.get(asset,{})
    sc=spec.get("color","")
    g_tag=f"&nbsp;<span class='grade-{grade.lower()}' style='font-size:13px'>{grade}</span>" if grade else ""
    if sig=="STRONG BUY":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#0d5c2e,#1a7a3e);
        border:2px solid #3fb950;border-radius:14px;padding:20px;text-align:center;
        margin-bottom:12px;box-shadow:0 0 20px rgba(63,185,80,0.4)'>
        <div style='font-size:24px;font-weight:900;color:#3fb950'>🚀 STRONG BUY — BUY NOW{g_tag}</div>
        <div style='font-size:15px;color:#e6edf3;margin-top:5px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="BUY":
        st.markdown(f"""<div style='background:#0d2b1a;border:2px solid #3fb950;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'>
        <div style='font-size:20px;font-weight:800;color:#3fb950'>🟢 BUY SIGNAL{g_tag}</div>
        <div style='font-size:14px;color:#e6edf3;margin-top:4px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="STRONG SELL":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#5c0d0d,#7a1a1a);
        border:2px solid #f85149;border-radius:14px;padding:20px;text-align:center;
        margin-bottom:12px;box-shadow:0 0 20px rgba(248,81,73,0.4)'>
        <div style='font-size:24px;font-weight:900;color:#f85149'>📉 STRONG SELL — SELL NOW{g_tag}</div>
        <div style='font-size:15px;color:#e6edf3;margin-top:5px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="SELL":
        st.markdown(f"""<div style='background:#2b0d0d;border:2px solid #f85149;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'>
        <div style='font-size:20px;font-weight:800;color:#f85149'>🔴 SELL SIGNAL{g_tag}</div>
        <div style='font-size:14px;color:#e6edf3;margin-top:4px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#161b22;border:1px solid #30363d;
        border-radius:14px;padding:14px;text-align:center;margin-bottom:12px'>
        <div style='font-size:17px;color:#8b949e'>⏳ WAIT — {asset} — strategies not aligned</div>
        </div>""",unsafe_allow_html=True)

# ─── CHART ─────────────────────────────────────────────────────────────────────
def chart(sym,name,sig,entry,sl,tp1,tp2,ckey="chart",asset_name=None):
    df=get_df(sym,"3mo","1d")
    if df is None: st.warning("Chart unavailable"); return
    cl=df["Close"]; e20=cl.ewm(20).mean(); e50=cl.ewm(50).mean(); e200=cl.ewm(200).mean()
    res=float(df["High"].rolling(20).max().iloc[-1]); sup=float(df["Low"].rolling(20).min().iloc[-1])
    dates=df.index; fig=go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],
            low=df["Low"],close=cl,name="Price",
            increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates,y=cl,name="Price",line=dict(color="#58a6ff",width=2)))
    fig.add_trace(go.Scatter(x=dates,y=e20,name="EMA20",line=dict(color="#ffd700",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=e50,name="EMA50",line=dict(color="#ff7f50",width=1,dash="dot")))
    e200c="#ffd200" if asset_name=="Gold (XAU/USD)" else "#da70d6"
    e200w=2 if asset_name=="Gold (XAU/USD)" else 1
    fig.add_trace(go.Scatter(x=dates,y=e200,name="EMA200",line=dict(color=e200c,width=e200w,dash="dash")))
    fig.add_hline(y=res,line_color="#f85149",line_dash="dash",
        annotation_text=f"Res {round(res,4)}",annotation_position="right",annotation_font_size=9)
    fig.add_hline(y=sup,line_color="#3fb950",line_dash="dash",
        annotation_text=f"Sup {round(sup,4)}",annotation_position="right",annotation_font_size=9)
    if entry:
        ec="#3fb950" if "BUY" in sig else "#f85149"
        fig.add_hline(y=entry,line_color=ec,line_width=2,
            annotation_text=f"Entry {round(entry,4)}",annotation_position="left",annotation_font_size=9)
        fig.add_hline(y=sl,line_color="#f85149",line_dash="dash",
            annotation_text=f"SL {round(sl,4)}",annotation_position="left",annotation_font_size=9)
        fig.add_hline(y=tp1,line_color="#3fb950",line_dash="dash",
            annotation_text=f"TP1 {round(tp1,4)}",annotation_position="left",annotation_font_size=9)
        fig.add_hline(y=tp2,line_color="#3fb950",line_dash="dot",
            annotation_text=f"TP2 {round(tp2,4)}",annotation_position="left",annotation_font_size=9)
    fc={"0.382":"#9b59b6","0.5":"#3498db","0.618":"#e67e22","0.786":"#e74c3c"}
    for lv,pr in get_fibs(sym).items():
        fig.add_hline(y=pr,line_color=fc.get(lv,"#888"),line_width=1,line_dash="dot",
            annotation_text=f"Fib {lv}",annotation_position="right",annotation_font_size=8)
    pc={"PP":"#ffffff","R1":"#ff6b6b","R2":"#ff4444","S1":"#51cf66","S2":"#37b24d"}
    for lv,pr in get_pivots(sym).items():
        fig.add_hline(y=pr,line_color=pc.get(lv,"#888"),line_width=1,line_dash="longdash",
            annotation_text=lv,annotation_position="left",annotation_font_size=8)
    lp=float(cl.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[lp],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in sig else "triangle-down",
                    size=13,color="#3fb950" if "BUY" in sig else "#f85149"),name="Signal"))
    spec=SPECIALISTS.get(asset_name,{})
    tc=spec.get("color","#e6edf3")
    fig.update_layout(title=dict(text=name,font=dict(color=tc)),
        plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",font=dict(color="#e6edf3"),height=430,
        xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),yaxis=dict(gridcolor="#21262d"),
        legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1,font_size=9),
        margin=dict(l=50,r=120,t=40,b=30))
    st.plotly_chart(fig,use_container_width=True,key=ckey)

# ─── NEWS ──────────────────────────────────────────────────────────────────────
def get_news():
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
        {"Time":"Tomorrow","Currency":"USD","Event":"FOMC Minutes","Impact":"High","Forecast":"—","Previous":"—"},
    ])
NP={"USD":["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CHF","USD/CAD","Gold (XAU/USD)"],
    "EUR":["EUR/USD"],"GBP":["GBP/USD"],"JPY":["USD/JPY"],
    "AUD":["AUD/USD"],"CHF":["USD/CHF"],"CAD":["USD/CAD"],
    "XAU":["Gold (XAU/USD)"],"BTC":["Bitcoin"]}

def ai_call(prompt,max_tokens=500):
    if not AI_KEY: return "Add ANTHROPIC_API_KEY in Streamlit secrets to enable AI."
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":AI_KEY,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,
                  "messages":[{"role":"user","content":prompt}]},timeout=25)
        if r.status_code==200: return r.json()["content"][0]["text"]
        return f"AI error {r.status_code}"
    except Exception as e: return f"Error: {e}"

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='text-align:center;font-size:22px;font-weight:900;
    background:linear-gradient(90deg,#00c6ff,#0072ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px'>
    🚀 Sparro FX AI</div>""",unsafe_allow_html=True)
    st.markdown("""<div style='display:flex;gap:6px;justify-content:center;margin-bottom:10px'>
    <span style='background:#2a2000;border:1px solid #ffd200;border-radius:8px;padding:3px 7px;font-size:12px'>🥇 Gold</span>
    <span style='background:#2a1500;border:1px solid #f7931a;border-radius:8px;padding:3px 7px;font-size:12px'>₿ BTC</span>
    <span style='background:#000033;border:1px solid #4488ff;border-radius:8px;padding:3px 7px;font-size:12px'>€ EUR</span>
    </div>""",unsafe_allow_html=True)
    st.divider()
    if atype=="admin":     st.success("👑 Admin")
    elif atype=="premium": st.success("⚡ Premium Active")
    elif atype=="trial":
        h=hours_left(); st.warning(f"🎁 Trial — {h}h left")
        if h<=12: st.error("⏰ Upgrade now!")
    else:
        st.info("🆓 Free Plan")
        if st.button("⚡ Upgrade $15/mo",use_container_width=True,key="upg"):
            st.info("Contact us for your premium password.")
    if st.session_state.email: st.caption(f"👤 {st.session_state.email}")
    st.divider()
    nav=[("🏠 Dashboard","Dashboard"),("🕐 Timeframes","Timeframes"),
         ("🎫 Tickets","Tickets"),("📓 Journal","Journal"),
         ("📈 Performance","Performance"),("💰 Risk Calc","Risk")]
    for lbl,key in nav:
        active=st.session_state.page==key
        if st.button(lbl,use_container_width=True,
                     type="primary" if active else "secondary",key=f"p_{key}"):
            st.session_state.page=key; st.rerun()
    with st.expander("≫ More"):
        more=[("💪 Currency Strength","Strength"),("🧘 AI Coach","Coach"),
              ("📷 Chart Analyzer","ChartAI"),("🛡️ Prop Firm Tools","PropFirm"),
              ("💎 Pricing","Pricing"),("📚 Learn","Learn"),("ℹ️ About","About")]
        if atype=="admin": more.append(("👑 Admin","Admin"))
        for lbl,key in more:
            if st.button(lbl,use_container_width=True,key=f"p_{key}"):
                st.session_state.page=key; st.rerun()
    st.divider()
    if st.button("🚪 Logout",use_container_width=True,key="logout"):
        clear_session()
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

pg=st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if pg=="Dashboard":
    now=datetime.datetime.utcnow().strftime("%A %d %b %Y  •  %H:%M UTC")
    st.markdown(f"""<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:14px'>
    <div style='font-size:22px;font-weight:900'>📊 Sparro FX AI</div>
    <div style='color:#8b949e;font-size:12px'>🕐 {now}</div>
    </div>""",unsafe_allow_html=True)
    if not pro: st.warning(f"🔒 Free plan — {', '.join(list(FREE_PAIRS.keys()))}. Upgrade for all {len(ALL_PAIRS)} assets.")

    # Mobile quick-action bar — real buttons that actually navigate
    qa1,qa2,qa3=st.columns(3)
    with qa1:
        if st.button("🎫 Tickets",key="qa_tickets",use_container_width=True):
            st.session_state.page="Tickets"; st.rerun()
    with qa2:
        if st.button("📓 Journal",key="qa_journal",use_container_width=True):
            st.session_state.page="Journal"; st.rerun()
    with qa3:
        if st.button("💰 Risk Calc",key="qa_risk",use_container_width=True):
            st.session_state.page="Risk"; st.rerun()
    st.caption("⚡ Pulse and 👁️ Watchlist are the tabs just below")
    st.markdown("<div style='height:4px'></div>",unsafe_allow_html=True)

    if pro:
        with st.expander("📰 Daily Market Briefing + Risk Warning",expanded=False):
            ndf=get_news()
            hi_ev=ndf[ndf["Impact"]=="High"] if "Impact" in ndf.columns else pd.DataFrame()
            if not hi_ev.empty:
                ev_str=" · ".join([f"{r.get('Time','')} {r.get('Currency','')} {r.get('Event','')}"
                                   for _,r in hi_ev.head(3).iterrows()])
                st.error(f"⚠️ HIGH IMPACT NEWS: {ev_str} — reduce position sizes today")
            with st.spinner("Generating briefing..."):
                brief=ai_call(f"3-sentence market briefing focusing on Gold, Bitcoin, EUR/USD. Events: {ndf.to_string(index=False) if len(ndf)>0 else 'none'}. Be direct.",350)
            st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;
            border-left:4px solid #00c6ff;font-size:14px;line-height:1.8'>
            {brief.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)

    t1,t1b,t2,t3,t4,t5,t6=st.tabs(["⚡ Pulse","🏃 Fast Pulse (M15)","👁️ Watchlist","📊 Scanner","🏆 Trade of Day","🔬 Deep Analysis","🗞️ News Trading"])

    # ── PULSE ──────────────────────────────────────────────────────────────────
    with t1:
        st.markdown("""<div style='display:flex;align-items:center;margin-bottom:6px'>
        <span class='pulse-dot'></span>
        <span style='font-size:19px;font-weight:800'>Live Pulse Signal</span></div>
        <div style='color:#8b949e;font-size:13px;margin-bottom:14px'>
        Quality-filtered signals. Candle quality · ATR filter · Weekly trend · Session timing · MTF confirmation.
        Grade A/B signals aim for 70%+ win rate.</div>""",unsafe_allow_html=True)

        if not pro: st.error("🔒 Upgrade to access Pulse Signals.")
        else:
            rc,rb,rv=st.columns([2,1,1])
            with rb:
                if st.button("🔄 Refresh",use_container_width=True,key="pulse_ref"): st.rerun()
            with rv:
                compact=st.toggle("Compact",value=False,key="pulse_compact")
            with rc: st.caption(f"Scan: {datetime.datetime.now().strftime('%H:%M:%S')}")

            with st.spinner("Scanning and applying quality filters..."):
                hits=[]; active_assets=[]
                for name,sym in ALL_PAIRS.items():
                    res,conf,sig,df_raw=run_strats(sym,asset_name=name)
                    if sig=="WAIT" or conf<67 or df_raw is None: continue
                    entry,sl,tp1,tp2,tp3,atr=get_setup(sym,sig)
                    if not entry: continue
                    # Quality filters
                    candle_ok,candle_msg=check_candle_quality(df_raw)
                    atr_ok,atr_msg=check_atr_filter(df_raw)
                    weekly_ok,weekly_msg,weekly_aligned=check_weekly_trend(sym,sig)
                    session_ok,session_msg=get_session_status(name)
                    tf_res,mtf_sig,mtf_note=run_mtf(sym,asset_name=name)
                    mtf_ok=(("BUY" in mtf_sig and "BUY" in sig) or ("SELL" in mtf_sig and "SELL" in sig))
                    cond,cond_icon,cond_color,cond_msg=get_market_condition(df_raw)
                    grade,grade_cls,grade_label,grade_action=get_signal_grade(
                        conf,candle_ok,atr_ok,weekly_aligned,session_ok,mtf_ok,name in SPECIALISTS)
                    # Only show Grade A, B, C — skip D
                    if grade=="D": continue
                    active_assets.append(name)
                    hits.append({"name":name,"sym":sym,"sig":sig,"conf":conf,
                        "entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"atr":atr,
                        "res":res,"tf":tf_res,"mtf_sig":mtf_sig,"mtf_note":mtf_note,"mtf_ok":mtf_ok,
                        "grade":grade,"grade_cls":grade_cls,"grade_label":grade_label,"grade_action":grade_action,
                        "candle_ok":candle_ok,"candle_msg":candle_msg,
                        "atr_ok":atr_ok,"atr_msg":atr_msg,
                        "weekly_ok":weekly_ok,"weekly_msg":weekly_msg,
                        "session_ok":session_ok,"session_msg":session_msg,
                        "cond":cond,"cond_icon":cond_icon,"cond_color":cond_color,"cond_msg":cond_msg,
                        "is_spec":name in SPECIALISTS,"scanned_at":datetime.datetime.now()})
                hits.sort(key=lambda x:(x["is_spec"],x["grade"]=="A",x["grade"]=="B",x["conf"]),reverse=True)
                # Correlation check
                corr_warnings=check_correlations(active_assets)

            if hits: play_sound(hits[0]["sig"])

            # Correlation warnings
            for w in corr_warnings:
                st.warning(w)

            if not hits:
                st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
                border-radius:14px;padding:40px;text-align:center'>
                <div style='font-size:36px'>😴</div>
                <div style='font-size:17px;color:#8b949e;margin-top:10px'>No quality signals right now</div>
                <div style='color:#8b949e;font-size:13px;margin-top:6px'>
                Waiting for signals that pass all quality filters.<br>
                Grade D signals are automatically excluded.</div>
                </div>""",unsafe_allow_html=True)
            else:
                grade_counts={"A":sum(1 for h in hits if h["grade"]=="A"),
                              "B":sum(1 for h in hits if h["grade"]=="B"),
                              "C":sum(1 for h in hits if h["grade"]=="C")}
                ga_tag = f"<span class='grade-a'>A x{grade_counts['A']}</span>" if grade_counts["A"] else ""
                gb_tag = f"<span class='grade-b'>B x{grade_counts['B']}</span>" if grade_counts["B"] else ""
                gc_tag = f"<span class='grade-c'>C x{grade_counts['C']}</span>" if grade_counts["C"] else ""
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:10px 14px;
                margin-bottom:12px;display:flex;gap:16px;align-items:center'>
                <span style='color:#8b949e;font-size:13px'>{len(hits)} signal(s):</span>
                {ga_tag}{gb_tag}{gc_tag}
                <span style='color:#8b949e;font-size:12px;margin-left:auto'>Specialists shown first</span>
                </div>""",unsafe_allow_html=True)

                for idx,p in enumerate(hits):
                    ib="BUY" in p["sig"]
                    brd="#3fb950" if ib else "#f85149"
                    bg="linear-gradient(135deg,#0d3b20,#0d1f14)" if ib else "linear-gradient(135deg,#3b0d0d,#1f0d0d)"
                    icon="🚀" if ib else "📉"
                    cfc="#3fb950" if p["conf"]>=83 else "#ffd700" if p["conf"]>=67 else "#f85149"
                    dr="BUY" if ib else "SELL"
                    agr=[n for n,(s,_) in p["res"].items() if s==dr]
                    smc_on=any("SMC" in n for n in agr)
                    mtf_col="#3fb950" if p["mtf_ok"] else "#ffd700"
                    spec=SPECIALISTS.get(p["name"],{})
                    spec_col=spec.get("color","")
                    spec_icon=spec.get("icon","")

                    tf_html="".join([
                        f"<div style='background:#00000044;border-radius:6px;padding:5px 3px;"
                        f"text-align:center;color:{'#3fb950' if s=='BUY' else '#f85149' if s=='SELL' else '#8b949e'};"
                        f"font-size:11px'>{tf}<br><b>{s}</b></div>"
                        for tf,(s,_) in p["tf"].items()])

                    # Quality filter status row
                    filters=[
                        ("🕯️",p["candle_ok"],"Candle"),("📊",p["atr_ok"],"Volatility"),
                        ("📅",p["weekly_ok"],"Weekly"),("🕐",p["session_ok"],"Session"),
                        ("🕐",p["mtf_ok"],"MTF")]
                    filter_html="".join([
                        f"<div style='text-align:center;font-size:10px;color:{'#3fb950' if ok else '#f85149'}'>"
                        f"{ico}<br>{lbl}<br>{'✅' if ok else '❌'}</div>"
                        for ico,ok,lbl in filters])

                    spec_border=f"border-top:3px solid {spec_col};" if spec else ""
                    spec_tag=f"{spec_icon} " if spec else ""
                    rr=calc_rr(p["entry"],p["sl"],p["tp1"])
                    tago=time_ago(p["scanned_at"])
                    one_liner=build_one_liner(p["name"],p["sig"],agr,p["grade"])
                    copy_text=build_copy_text(p["name"],p["sig"],p["entry"],p["sl"],
                                               p["tp1"],p["tp2"],p["tp3"],rr,p["grade"])

                    if compact:
                        # Condensed single-line mobile-friendly card
                        st.markdown(f"""<div style='background:{bg};border:2px solid {brd};
                        {spec_border}border-radius:12px;padding:12px 14px;margin-bottom:8px'>
                        <div style='display:flex;justify-content:space-between;align-items:center'>
                          <div>
                            <span style='font-size:15px;font-weight:900;color:{brd}'>{spec_tag}{icon} {p["sig"]}</span>
                            &nbsp;<span class='{p["grade_cls"]}' style='font-size:11px'>{p["grade"]}</span>
                            &nbsp;<span style='color:#8b949e;font-size:10px'>RR {rr} · {tago}</span>
                            <div style='font-size:16px;font-weight:700;color:#e6edf3'>{p["name"]}</div>
                          </div>
                          <div style='text-align:right'>
                            <div style='font-size:22px;font-weight:900;color:{cfc}'>{p["conf"]}%</div>
                            <div style='font-size:10px;color:#8b949e'>Entry {round(p["entry"],4)}</div>
                          </div>
                        </div></div>""",unsafe_allow_html=True)
                        if st.button(f"🎫 Ticket — {p['name']}",key=f"atk_{idx}",use_container_width=True):
                            ok=auto_ticket(p["name"],p["sig"],p["conf"],p["entry"],
                                          p["sl"],p["tp1"],p["tp2"],p["tp3"],p["grade"],"Pulse")
                            st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                        continue

                    st.markdown(f"""<div style='background:{bg};border:2px solid {brd};
                    {spec_border}border-radius:14px;padding:16px;margin-bottom:12px;
                    box-shadow:0 0 14px {brd}33'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:10px'>
                      <div>
                        <div style='font-size:18px;font-weight:900;color:{brd}'>{spec_tag}{icon} {p["sig"]}
                          &nbsp;<span class='{p["grade_cls"]}' style='font-size:13px'>{p["grade"]}</span>
                          {"&nbsp;<span class='smc-badge'>SMC</span>" if smc_on else ""}
                        </div>
                        <div style='font-size:19px;font-weight:700;color:#e6edf3'>{p["name"]}</div>
                        <div style='font-size:11px;color:#8b949e;margin-top:2px'>🕐 {tago} &nbsp;|&nbsp; RR <b style='color:#ffd700'>{rr}</b></div>
                        <div style='font-size:11px;color:{mtf_col};margin-top:3px'>MTF: {p["mtf_sig"]} — {p["mtf_note"]}</div>
                        <div style='font-size:11px;color:{p["cond_color"]};margin-top:2px'>{p["cond_icon"]} {p["cond"]} market — {p["cond_msg"]}</div>
                      </div>
                      <div style='text-align:right'>
                        <div style='font-size:28px;font-weight:900;color:{cfc}'>{p["conf"]}%</div>
                        <div style='font-size:10px;color:#8b949e'>{len(agr)}/6 agree</div>
                        <div style='font-size:11px;color:#8b949e;margin-top:4px'>{p["grade_action"]}</div>
                      </div>
                    </div>
                    <div style='font-size:12px;color:#c9d1d9;background:#00000033;border-radius:8px;
                    padding:8px 10px;margin-bottom:10px;line-height:1.5'>💬 {one_liner}</div>
                    <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:8px'>
                      <div style='background:#00000044;border-radius:6px;padding:7px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>ENTRY</div>
                        <div style='font-size:11px;font-weight:700;color:#e6edf3'>{round(p["entry"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:6px;padding:7px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>STOP</div>
                        <div style='font-size:11px;font-weight:700;color:#f85149'>{round(p["sl"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:6px;padding:7px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>TP1</div>
                        <div style='font-size:11px;font-weight:700;color:#3fb950'>{round(p["tp1"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:6px;padding:7px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>TP2</div>
                        <div style='font-size:11px;font-weight:700;color:#3fb950'>{round(p["tp2"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:6px;padding:7px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>TP3</div>
                        <div style='font-size:11px;font-weight:700;color:#3fb950'>{round(p["tp3"],4)}</div>
                      </div>
                    </div>
                    <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:8px'>
                      {filter_html}
                    </div>
                    <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:8px'>
                      {tf_html}
                    </div>
                    <div style='font-size:11px;color:#8b949e'>✅ {" · ".join(agr)}</div>
                    </div>""",unsafe_allow_html=True)

                    ca,cb,cc=st.columns(3)
                    with ca:
                        if st.button(f"🎫 Auto Ticket",key=f"atk_{idx}",use_container_width=True):
                            ok=auto_ticket(p["name"],p["sig"],p["conf"],p["entry"],
                                          p["sl"],p["tp1"],p["tp2"],p["tp3"],p["grade"],"Pulse")
                            st.success("✅ Ticket created! Go to Tickets.") if ok else st.warning("Already ticketed today.")
                    with cb:
                        with st.popover("📋 Copy"):
                            st.code(copy_text,language=None)
                            st.caption("Tap and hold the box above to copy, then paste into MT4/MT5.")
                    with cc:
                        with st.expander(f"📊 {p['name']}"):
                            # Quality filter detail
                            st.markdown(f"**Candle:** {p['candle_msg']}")
                            st.markdown(f"**Volatility:** {p['atr_msg']}")
                            st.markdown(f"**Weekly:** {p['weekly_msg']}")
                            st.markdown(f"**Session:** {p['session_msg']}")
                            chart(p["sym"],p["name"],p["sig"],p["entry"],p["sl"],
                                  p["tp1"],p["tp2"],ckey=f"pc_{idx}",asset_name=p["name"])

    # ── FAST PULSE (M15) ──────────────────────────────────────────────────────
    with t1b:
        st.markdown("""<div style='display:flex;align-items:center;margin-bottom:6px'>
        <span class='pulse-dot' style='background:#ffa500'></span>
        <span style='font-size:19px;font-weight:800'>Fast Pulse — 15 Minute</span></div>
        <div style='color:#8b949e;font-size:13px;margin-bottom:6px'>
        Higher-frequency, lower-conviction signals for active intraday trading.</div>""",unsafe_allow_html=True)

        st.warning("⚠️ **Read this first:** M15 has limited price history, so EMA200, SMC Order Blocks/FVG and the Weekly Trend filter can't run reliably here. This feed uses a lighter 3-strategy check (EMA-short, RSI, Support/Resistance) and is capped at **Grade B** — never Grade A. Treat it as a faster, noisier feed alongside the main ⚡ Pulse, not a replacement for it.")

        if not pro:
            st.error("🔒 Upgrade to access Fast Pulse.")
        else:
            fr1,fr2=st.columns([3,1])
            with fr2:
                if st.button("🔄 Refresh",use_container_width=True,key="fastpulse_ref"): st.rerun()
            with fr1: st.caption(f"Scan: {datetime.datetime.now().strftime('%H:%M:%S')}")

            with st.spinner("Scanning M15 across all assets..."):
                fast_hits=[]
                for name,sym in ALL_PAIRS.items():
                    res,conf,sig,df15,note=run_single_timeframe(sym,"M15",asset_name=name)
                    if res is None or sig in ("WAIT","NO DATA","ERROR") or conf<67:
                        continue
                    entry=float(df15["Close"].iloc[-1]) if df15 is not None else None
                    if entry is None: continue
                    # Tighter, faster ATR for M15 (shorter period since data is limited)
                    try:
                        h15=df15["High"]; l15=df15["Low"]; c15=df15["Close"]
                        tr15=pd.concat([h15-l15,(h15-c15.shift()).abs(),(l15-c15.shift()).abs()],axis=1).max(axis=1)
                        atr15=float(tr15.rolling(14).mean().iloc[-1])
                    except: atr15=None
                    if not atr15 or atr15<=0: continue
                    risk15=atr15*1.2
                    if "BUY" in sig: sl15=entry-risk15; tp1_15=entry+risk15; tp2_15=entry+risk15*2
                    else:            sl15=entry+risk15; tp1_15=entry-risk15; tp2_15=entry-risk15*2
                    session_ok,session_msg=get_session_status(name)
                    grade="B" if (conf>=83 and session_ok) else "C"
                    fast_hits.append({"name":name,"sym":sym,"sig":sig,"conf":conf,"res":res,
                        "entry":entry,"sl":sl15,"tp1":tp1_15,"tp2":tp2_15,"grade":grade,
                        "session_ok":session_ok,"session_msg":session_msg,
                        "is_spec":name in SPECIALISTS,"scanned_at":datetime.datetime.now()})
                fast_hits.sort(key=lambda x:(x["is_spec"],x["grade"]=="B",x["conf"]),reverse=True)

            if not fast_hits:
                st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
                border-radius:14px;padding:30px;text-align:center'>
                <div style='font-size:30px'>🏃</div>
                <div style='color:#8b949e;margin-top:8px'>No M15 setups firing right now.</div>
                </div>""",unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#ffa500;font-weight:700;margin-bottom:10px'>⚡ {len(fast_hits)} fast signal(s) on M15</div>",unsafe_allow_html=True)
                for fidx,f in enumerate(fast_hits):
                    ib="BUY" in f["sig"]
                    brd="#3fb950" if ib else "#f85149"
                    icon="🚀" if ib else "📉"
                    spec=SPECIALISTS.get(f["name"],{})
                    spec_icon=spec.get("icon","")
                    gc="grade-b" if f["grade"]=="B" else "grade-c"
                    agr=[n for n,(s,_) in f["res"].items() if s==("BUY" if ib else "SELL")]
                    rr15=calc_rr(f["entry"],f["sl"],f["tp1"])
                    tago15=time_ago(f["scanned_at"])
                    one_liner15=build_one_liner(f["name"],f["sig"],agr,f["grade"])
                    copy_text15=build_copy_text(f["name"],f["sig"],f["entry"],f["sl"],
                                                 f["tp1"],f["tp2"],f["tp1"],rr15,f["grade"])
                    st.markdown(f"""<div style='background:#161b22;border:2px solid {brd};
                    border-radius:12px;padding:12px 14px;margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                      <div>
                        <span style='font-size:16px;font-weight:900;color:{brd}'>{spec_icon} {icon} {f["sig"]}</span>
                        &nbsp;<span class='{gc}' style='font-size:11px'>{f["grade"]}</span>
                        <div style='font-size:16px;font-weight:700;color:#e6edf3'>{f["name"]} <span style='font-size:11px;color:#8b949e'>(M15)</span></div>
                        <div style='font-size:10px;color:#8b949e;margin-top:2px'>🕐 {tago15} &nbsp;|&nbsp; RR <b style='color:#ffd700'>{rr15}</b></div>
                      </div>
                      <div style='text-align:right'>
                        <div style='font-size:22px;font-weight:900;color:{"#3fb950" if f["conf"]>=83 else "#ffd700"}'>{f["conf"]}%</div>
                        <div style='font-size:10px;color:#8b949e'>{len(agr)}/3 agree</div>
                      </div>
                    </div>
                    <div style='font-size:11px;color:#c9d1d9;background:#00000033;border-radius:7px;
                    padding:6px 8px;margin-bottom:8px;line-height:1.4'>💬 {one_liner15}</div>
                    <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:6px'>
                      <div style='background:#00000044;border-radius:6px;padding:6px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>ENTRY</div>
                        <div style='font-size:11px;font-weight:700'>{round(f["entry"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:6px;padding:6px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>STOP</div>
                        <div style='font-size:11px;font-weight:700;color:#f85149'>{round(f["sl"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:6px;padding:6px;text-align:center'>
                        <div style='font-size:9px;color:#8b949e'>TP1</div>
                        <div style='font-size:11px;font-weight:700;color:#3fb950'>{round(f["tp1"],4)}</div>
                      </div>
                    </div>
                    <div style='font-size:11px;color:{"#3fb950" if f["session_ok"] else "#ffa500"}'>{f["session_msg"]}</div>
                    </div>""",unsafe_allow_html=True)
                    fc1,fc2=st.columns(2)
                    with fc1:
                        if st.button(f"🎫 Quick Ticket",key=f"fast_tk_{fidx}",use_container_width=True):
                            ok=auto_ticket(f["name"],f["sig"],f["conf"],f["entry"],f["sl"],
                                           f["tp1"],f["tp2"],f["tp1"],f["grade"],"Fast Pulse M15")
                            st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                    with fc2:
                        with st.popover("📋 Copy"):
                            st.code(copy_text15,language=None)
                            st.caption("Tap and hold to copy, then paste into MT4/MT5.")

    # ── WATCHLIST ──────────────────────────────────────────────────────────────
    with t2:
        st.markdown("### 👁️ Watchlist — Setups Building")
        st.markdown("""<div style='color:#8b949e;font-size:13px;margin-bottom:14px'>
        These haven't fired a full signal yet, but strategies are starting to align.
        Not trade calls — things worth watching so you always have something on your radar.</div>""",unsafe_allow_html=True)

        if not pro:
            st.error("🔒 Upgrade to access the Watchlist.")
        else:
            with st.spinner("Scanning for building setups..."):
                watch=[]
                for name,sym in ALL_PAIRS.items():
                    res,conf,sig,df_raw=run_strats(sym,asset_name=name)
                    if df_raw is None: continue
                    b=sum(1 for s,_ in res.values() if s=="BUY")
                    s=sum(1 for s,_ in res.values() if s=="SELL")
                    lean="BUY" if b>s else "SELL" if s>b else None
                    agree=max(b,s)
                    # Only show items NOT already a full Pulse signal (2 or 3 out of 6 = building)
                    if lean and agree in (2,3):
                        candle_ok,_=check_candle_quality(df_raw)
                        atr_ok,_=check_atr_filter(df_raw)
                        session_ok,session_msg=get_session_status(name)
                        cond,cond_icon,cond_color,cond_msg=get_market_condition(df_raw)
                        filters_passing=sum([candle_ok,atr_ok,session_ok])
                        watch.append({"name":name,"sym":sym,"lean":lean,"agree":agree,
                            "filters_passing":filters_passing,"cond":cond,"cond_icon":cond_icon,
                            "cond_color":cond_color,"is_spec":name in SPECIALISTS})
                watch.sort(key=lambda x:(x["agree"],x["filters_passing"],x["is_spec"]),reverse=True)

            if not watch:
                st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
                border-radius:14px;padding:30px;text-align:center'>
                <div style='font-size:30px'>🔭</div>
                <div style='color:#8b949e;margin-top:8px'>Nothing building right now — markets are quiet or already firing on Pulse.</div>
                </div>""",unsafe_allow_html=True)
            else:
                for w in watch[:10]:
                    ib=w["lean"]=="BUY"
                    col="#3fb950" if ib else "#f85149"
                    icon="👀"
                    spec=SPECIALISTS.get(w["name"],{})
                    spec_icon=spec.get("icon","")
                    progress_pct=round(w["agree"]/6*100)
                    st.markdown(f"""<div style='background:#161b22;border:1px solid {col}55;
                    border-left:4px solid {col};border-radius:10px;padding:12px 14px;margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                      <div>
                        <b>{icon} {spec_icon} {w["name"]}</b>
                        <span style='color:{col};font-weight:700;margin-left:8px'>{w["lean"]} leaning</span>
                      </div>
                      <span style='color:#8b949e;font-size:12px'>{w["agree"]}/6 strategies · {w["filters_passing"]}/3 filters ready</span>
                    </div>
                    <div style='background:#0d1117;border-radius:5px;height:6px;margin-top:8px;overflow:hidden'>
                      <div style='background:{col};height:100%;width:{progress_pct}%'></div>
                    </div>
                    <div style='font-size:11px;color:{w["cond_color"]};margin-top:6px'>{w["cond_icon"]} {w["cond"]} market</div>
                    </div>""",unsafe_allow_html=True)
                st.caption("💡 When agreement reaches 4+/6 with filters passing, it'll appear on the Pulse tab as a real signal.")

    # ── SCANNER ────────────────────────────────────────────────────────────────
    with t3:
        st.markdown("### 📊 Market Scanner")
        st.caption("Specialists first. Grade shown for signal quality.")
        rows=[]; prog=st.progress(0); items=list(pairs.items())
        for i,(name,sym) in enumerate(items):
            res,conf,sig,df_raw=run_strats(sym,asset_name=name)
            b=sum(1 for s,_ in res.values() if s=="BUY")
            s=sum(1 for s,_ in res.values() if s=="SELL")
            spec=SPECIALISTS.get(name,{})
            cond,cond_icon,cond_color,_=get_market_condition(df_raw) if df_raw is not None else ("—","","","")
            rows.append({"Asset":name,"Signal":sig,
                "Confidence":f"{conf}%" if pro else "🔒",
                "Agree":f"{max(b,s)}/6" if pro else "🔒",
                "Market":f"{cond_icon} {cond}" if pro else "🔒",
                "Specialist":"⭐" if spec else ""})
            prog.progress((i+1)/len(items))
        prog.empty()
        sc=pd.DataFrame(rows)
        strong=[r for r in rows if r["Signal"] in ("STRONG BUY","STRONG SELL")]
        if strong:
            for r in strong:
                cv=int(r["Confidence"].replace("%","")) if "%" in str(r["Confidence"]) else 0
                banner(r["Signal"],r["Asset"],cv)
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**🚀 Buys**")
            st.dataframe(sc[sc["Signal"].str.contains("BUY",na=False)].head(5),use_container_width=True,hide_index=True)
        with c2:
            st.markdown("**📉 Sells**")
            st.dataframe(sc[sc["Signal"].str.contains("SELL",na=False)].head(5),use_container_width=True,hide_index=True)
        st.dataframe(sc,use_container_width=True,hide_index=True)

    # ── TRADE OF THE DAY ───────────────────────────────────────────────────────
    with t4:
        st.markdown("### 🏆 Trade of the Day")
        st.caption("Best quality setup after all filters applied.")
        if not pro: st.error("🔒 Premium only.")
        else:
            best={"conf":0,"sig":"WAIT","name":"","sym":"","res":{},"grade":"D","is_spec":False}
            with st.spinner("Finding best quality setup..."):
                for name,sym in ALL_PAIRS.items():
                    res,conf,sig,df_raw=run_strats(sym,asset_name=name)
                    if sig=="WAIT" or conf<67 or df_raw is None: continue
                    candle_ok,_=check_candle_quality(df_raw)
                    atr_ok,_=check_atr_filter(df_raw)
                    weekly_ok,_,weekly_aligned=check_weekly_trend(sym,sig)
                    session_ok,_=get_session_status(name)
                    tf_res,mtf_sig,mtf_note=run_mtf(sym,asset_name=name)
                    mtf_ok=(("BUY" in mtf_sig and "BUY" in sig) or ("SELL" in mtf_sig and "SELL" in sig))
                    grade,_,_,_=get_signal_grade(conf,candle_ok,atr_ok,weekly_aligned,session_ok,mtf_ok,name in SPECIALISTS)
                    is_spec=name in SPECIALISTS
                    grade_score={"A":4,"B":3,"C":2,"D":1}.get(grade,0)
                    best_score={"A":4,"B":3,"C":2,"D":1}.get(best["grade"],0)
                    eff=conf+grade_score*5+(5 if is_spec else 0)
                    best_eff=best["conf"]+best_score*5+(5 if best["is_spec"] else 0)
                    if eff>best_eff and grade!="D":
                        best={"conf":conf,"sig":sig,"name":name,"sym":sym,"res":res,
                              "grade":grade,"is_spec":is_spec,"tf_res":tf_res,
                              "mtf_sig":mtf_sig,"mtf_note":mtf_note,"mtf_ok":mtf_ok}

            banner(best["sig"],best["name"],best["conf"],best.get("grade"))
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Asset",best["name"]); c2.metric("Signal",best["sig"])
            c3.metric("Confidence",f"{best['conf']}%"); c4.metric("Grade",best.get("grade","—"))
            st.progress(best["conf"]/100)
            entry,sl,tp1,tp2,tp3,atr=get_setup(best["sym"],best["sig"])
            if entry:
                mtf_sig=best.get("mtf_sig","—"); mtf_note=best.get("mtf_note","")
                mtfc="#3fb950" if "BUY" in mtf_sig else "#f85149" if "SELL" in mtf_sig else "#8b949e"
                st.markdown(f"""<div style='background:#161b22;border-radius:8px;padding:10px;
                border-left:4px solid {mtfc};margin:10px 0;font-size:13px'>
                🕐 <b>MTF:</b> {mtf_sig} — {mtf_note}</div>""",unsafe_allow_html=True)
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{round(entry,4)}"); c2.metric("SL",f"{round(sl,4)}")
                c3.metric("TP1",f"{round(tp1,4)}"); c4.metric("TP2",f"{round(tp2,4)}"); c5.metric("TP3",f"{round(tp3,4)}")
                if st.button("🎫 Auto Ticket",key="totd_tk",use_container_width=True):
                    ok=auto_ticket(best["name"],best["sig"],best["conf"],entry,sl,tp1,tp2,tp3,best["grade"],"Trade of Day")
                    st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                chart(best["sym"],best["name"],best["sig"],entry,sl,tp1,tp2,ckey="totd_chart",asset_name=best["name"])

    # ── DEEP ANALYSIS ──────────────────────────────────────────────────────────
    with t5:
        st.markdown("### 🔬 Deep Analysis")
        if not pro: st.error("🔒 Premium only.")
        else:
            sel=st.selectbox("Choose Asset",list(ALL_PAIRS.keys()),key="deep_sel")
            sym=ALL_PAIRS[sel]
            with st.spinner(f"Full analysis of {sel}..."):
                res,conf,sig,df_raw=run_strats(sym,asset_name=sel)
                tf_res,mtf_sig,mtf_note=run_mtf(sym,asset_name=sel)
                if df_raw is not None:
                    candle_ok,candle_msg=check_candle_quality(df_raw)
                    atr_ok,atr_msg=check_atr_filter(df_raw)
                    weekly_ok,weekly_msg,weekly_aligned=check_weekly_trend(sym,sig)
                    session_ok,session_msg=get_session_status(sel)
                    mtf_ok=(("BUY" in mtf_sig and "BUY" in sig) or ("SELL" in mtf_sig and "SELL" in sig))
                    cond,cond_icon,cond_color,cond_msg=get_market_condition(df_raw)
                    grade,grade_cls,grade_label,grade_action=get_signal_grade(
                        conf,candle_ok,atr_ok,weekly_aligned,session_ok,mtf_ok,sel in SPECIALISTS)
                else:
                    candle_ok=atr_ok=weekly_ok=session_ok=mtf_ok=True
                    candle_msg=atr_msg=weekly_msg=session_msg="No data"
                    cond,cond_icon,cond_color,cond_msg="Unknown","❓","#8b949e","No data"
                    grade,grade_cls,grade_label,grade_action="C","grade-c","⚠️ Grade C","Proceed with caution"

            banner(sig,sel,conf,grade)

            # Grade + Market Condition strip
            st.markdown(f"""<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:12px'>
            <div style='background:#161b22;border-radius:10px;padding:12px;border-left:4px solid {"#238636" if grade=="A" else "#9e6a03" if grade=="B" else "#da3633"}'>
            <b>{grade_label}</b><br><span style='color:#8b949e;font-size:13px'>{grade_action}</span>
            </div>
            <div style='background:#161b22;border-radius:10px;padding:12px;border-left:4px solid {cond_color}'>
            <b>{cond_icon} {cond} Market</b><br><span style='color:#8b949e;font-size:13px'>{cond_msg}</span>
            </div>
            </div>""",unsafe_allow_html=True)

            # Quality filters
            st.markdown("#### ✅ Quality Filters")
            filters=[
                ("🕯️ Candle Quality",candle_ok,candle_msg),
                ("📊 ATR/Volatility",atr_ok,atr_msg),
                ("📅 Weekly Trend",weekly_ok,weekly_msg),
                ("🕐 Session Timing",session_ok,session_msg),
                ("🔀 Multi-Timeframe",mtf_ok,f"{mtf_sig} — {mtf_note}")]
            fc1,fc2=st.columns(2)
            for i,(label,ok,msg) in enumerate(filters):
                col=fc1 if i%2==0 else fc2
                col.markdown(f"""<div style='background:#161b22;border-radius:8px;padding:10px;
                margin-bottom:8px;border-left:3px solid {"#3fb950" if ok else "#f85149"}'>
                <b>{"✅" if ok else "❌"} {label}</b><br>
                <span style='color:#8b949e;font-size:12px'>{msg}</span></div>""",unsafe_allow_html=True)

            st.markdown("#### 📊 Strategy Breakdown")
            spec=SPECIALISTS.get(sel,{}); best_strats=spec.get("best",[])
            for name,(fn,ico,desc) in STRATS.items():
                s,reason=res.get(name,("NEUTRAL","No data"))
                col="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
                dot="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
                sr=reason.replace("<","&lt;").replace(">","&gt;")
                is_smc="SMC" in name; is_best=name in best_strats
                border_r=f";border-right:2px solid #7c3aed" if is_smc else ""
                if is_best and spec:
                    sc2=spec.get("color","#ffd200")
                    border_r=f";border-right:3px solid {sc2}"
                smc_tag="&nbsp;<span class='smc-badge'>SMC</span>" if is_smc else ""
                best_tag=""
                if is_best and spec:
                    sc3=spec.get("color","#ffd200")
                    best_tag=f"&nbsp;<span style='background:{sc3};color:#000;border-radius:4px;padding:1px 5px;font-size:10px;font-weight:700'>⭐ 2×</span>"
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:10px 12px;
                margin-bottom:7px;border-left:4px solid {col}{border_r}'>
                <div style='display:flex;justify-content:space-between;align-items:center'>
                  <div><b>{dot} {ico} {name}</b>{smc_tag}{best_tag}
                    <span style='color:#8b949e;font-size:11px;margin-left:6px'>{desc}</span></div>
                  <span style='background:{col};color:#fff;padding:2px 10px;border-radius:8px;font-size:12px;font-weight:700'>{s}</span>
                </div>
                <div style='color:#8b949e;font-size:12px;margin-top:5px'>{sr}</div>
                </div>""",unsafe_allow_html=True)

            b=sum(1 for s,_ in res.values() if s=="BUY"); sv=sum(1 for s,_ in res.values() if s=="SELL")
            c1,c2,c3=st.columns(3)
            c1.metric("🟢 Buying",b); c2.metric("🔴 Selling",sv); c3.metric("🟡 Neutral",6-b-sv)

            entry,sl,tp1,tp2,tp3,atr=get_setup(sym,sig)
            if entry and sig!="WAIT":
                st.markdown("---")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{round(entry,4)}"); c2.metric("SL",f"{round(sl,4)}")
                c3.metric("TP1",f"{round(tp1,4)}"); c4.metric("TP2",f"{round(tp2,4)}"); c5.metric("TP3",f"{round(tp3,4)}")
                # Position sizing suggestion
                is_forex="USD" in sel or "EUR" in sel or "GBP" in sel or "JPY" in sel or "AUD" in sel or "CHF" in sel or "CAD" in sel
                risk_adj=2.0 if grade=="A" else 1.5 if grade=="B" else 1.0
                st.info(f"💡 **Suggested risk:** {risk_adj}% for Grade {grade} signal — adjust in Risk Calculator")

                st.markdown("#### 🎯 Precision Entry Tools — for small accounts")
                struct_sl,struct_msg=get_structure_sl(sym,sig,entry,atr)
                zone_low,zone_high=get_entry_zone(sym,sig,entry,atr)
                pc1,pc2=st.columns(2)
                with pc1:
                    st.markdown(f"""<div class='card' style='border-left:4px solid #58a6ff'>
                    <b>📍 Entry Zone</b><br><br>
                    Instead of chasing one exact price, aim to enter between:<br>
                    <b style='color:#58a6ff;font-size:16px'>{round(min(zone_low,zone_high),5)} – {round(max(zone_low,zone_high),5)}</b><br><br>
                    <span style='color:#8b949e;font-size:12px'>Waiting for price inside this zone avoids chasing and improves your average entry.</span>
                    </div>""",unsafe_allow_html=True)
                with pc2:
                    if struct_sl:
                        risk_atr=abs(entry-sl); risk_struct=abs(entry-struct_sl)
                        tighter=risk_struct<risk_atr
                        st.markdown(f"""<div class='card' style='border-left:4px solid #ffd700'>
                        <b>🧱 Structure-Based SL</b><br><br>
                        <b style='color:#ffd700;font-size:16px'>{round(struct_sl,5)}</b>
                        {" &nbsp;<span style='color:#3fb950;font-size:11px'>(tighter than ATR stop)</span>" if tighter else " <span style='color:#8b949e;font-size:11px'>(wider than ATR stop)</span>"}<br><br>
                        <span style='color:#8b949e;font-size:12px'>{struct_msg}</span>
                        </div>""",unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div class='card' style='border-left:4px solid #8b949e'>
                        <b>🧱 Structure-Based SL</b><br><br>
                        <span style='color:#8b949e;font-size:13px'>{struct_msg}</span><br><br>
                        <span style='color:#8b949e;font-size:12px'>Using the standard ATR-based stop instead.</span>
                        </div>""",unsafe_allow_html=True)

                st.markdown("##### 💰 Is this tradeable on your account?")
                ac1,ac2=st.columns([2,1])
                with ac2:
                    small_bal=st.number_input("Your balance ($)",min_value=10.0,value=200.0,key="deep_small_bal")
                final_sl=struct_sl if struct_sl else sl
                status,msg=get_account_warning(small_bal,entry,final_sl,risk_adj,is_forex)
                with ac1:
                    if status=="ok": st.success(msg)
                    elif status=="warning": st.warning(msg)
                    else: st.error(msg)

                if st.button("🎫 Auto Ticket",key="deep_tk",use_container_width=True):
                    ok=auto_ticket(sel,sig,conf,entry,sl,tp1,tp2,tp3,grade,"Deep Analysis")
                    st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                chart(sym,sel,sig,entry,sl,tp1,tp2,ckey=f"deep_{sel}",asset_name=sel)

    # ── NEWS TRADING ───────────────────────────────────────────────────────────
    with t6:
        st.markdown("### 🗞️ News Trading")
        if not pro: st.error("🔒 Premium only.")
        else:
            with st.spinner("Loading calendar..."): ndf=get_news()
            if "Impact" in ndf.columns:
                hi=ndf[ndf["Impact"]=="High"]; me=ndf[ndf["Impact"]=="Medium"]
                if not hi.empty:
                    st.markdown("**🔴 High Impact Events:**")
                    for _,row in hi.iterrows():
                        curr=row.get("Currency",""); aff=NP.get(curr,[curr])
                        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:12px;
                        margin-bottom:8px;border-left:4px solid #ffd200'>
                        <div style='display:flex;justify-content:space-between'>
                          <div><span style='background:#f85149;color:#fff;border-radius:5px;
                          padding:1px 7px;font-size:11px'>HIGH</span>&nbsp;<b>{row.get("Event","")}</b></div>
                          <div style='color:#8b949e;font-size:12px'>{row.get("Time","")}</div>
                        </div>
                        <div style='margin-top:6px;font-size:13px;color:#8b949e'>
                          <b style='color:#ffd200'>{curr}</b> · Forecast: <b>{row.get("Forecast","—")}</b>
                          · Previous: <b>{row.get("Previous","—")}</b></div>
                        <div style='margin-top:5px;font-size:12px;color:#58a6ff'>📌 {" · ".join(aff[:4])}</div>
                        </div>""",unsafe_allow_html=True)
                if not me.empty:
                    with st.expander(f"🟡 Medium ({len(me)})"):
                        for _,row in me.iterrows():
                            st.write(f"**{row.get('Time','')}** — {row.get('Currency','')} {row.get('Event','')} | {row.get('Forecast','—')}")
            st.markdown("---")
            c1,c2=st.columns([2,1])
            with c1: np_=st.selectbox("Pair to trade",list(ALL_PAIRS.keys()),key="news_pair")
            with c2:
                st.markdown("<br>",unsafe_allow_html=True)
                run_n=st.button("🔍 Generate Plan",key="news_gen",use_container_width=True)
            if run_n:
                sym=ALL_PAIRS[np_]; res,conf,sig,df_raw=run_strats(sym,asset_name=np_)
                entry,sl,tp1,tp2,tp3,_=get_setup(sym,sig)
                banner(sig,np_,conf)
                c1,c2=st.columns(2)
                with c1:
                    st.markdown(f"""<div class='card' style='border-left:4px solid #0072ff'>
                    <b>📊 Technical</b><br>Signal: <b>{sig}</b> — {conf}%<br><br>
                    {"✅ Use after news confirms" if sig!="WAIT" else "⚠️ Wait for reaction"}</div>""",unsafe_allow_html=True)
                with c2:
                    if entry and sig!="WAIT":
                        st.markdown(f"""<div class='card' style='border-left:4px solid #ffd700'>
                        <b>🎯 Levels</b><br>Entry: <b>{round(entry,4)}</b><br>
                        SL: <b style='color:#f85149'>{round(sl,4)}</b><br>
                        TP1: <b style='color:#3fb950'>{round(tp1,4)}</b></div>""",unsafe_allow_html=True)
                with st.spinner("AI analysis..."):
                    ai_txt=ai_call(f"Forex news trader. Asset: {np_}\nCalendar:\n{ndf.to_string(index=False)}\nEvents affecting asset, direction, timing, risk, trade plan. Bullets only.",500)
                st.markdown(f"""<div class='card' style='border-left:4px solid #58a6ff;line-height:1.8'>
                {ai_txt.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)
                if entry: st.markdown("---"); chart(sym,np_,sig,entry,sl,tp1,tp2,ckey=f"news_{np_}",asset_name=np_)
            st.markdown("---")
            c1,c2=st.columns(2)
            with c1:
                st.markdown("""<div class='card'><b style='color:#3fb950'>✅ DO</b><br><br>
                Wait for candle <b>close</b> after news<br>Trade the <b>surprise</b> direction<br>
                Use <b>wider stops</b> on Gold/BTC<br>Take profits <b>quickly</b></div>""",unsafe_allow_html=True)
            with c2:
                st.markdown("""<div class='card'><b style='color:#f85149'>❌ DON'T</b><br><br>
                Don't trade <b>into</b> the release<br>Don't hold through NFP/FOMC blind<br>
                Max <b>1% risk</b> on news trades<br>Don't trade if spread is <b>very wide</b></div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TIMEFRAME ANALYZER (M1 → W1)
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Timeframes":
    st.title("🕐 Multi-Timeframe Analyzer")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>Analyze any single timeframe from M1 to W1, or compare several side by side.</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()

    c1,c2=st.columns([2,1])
    with c1: tf_asset=st.selectbox("Asset",list(ALL_PAIRS.keys()),key="tf_asset")
    with c2: st.markdown("<br>",unsafe_allow_html=True)

    tf_keys=list(TF_CONFIG.keys())
    selected_tfs=st.multiselect("Timeframes to compare",tf_keys,
                                  default=["M15","H1","H4","D1"],key="tf_multi")

    if not selected_tfs:
        st.info("Select at least one timeframe above.")
    else:
        sym=ALL_PAIRS[tf_asset]
        cols=st.columns(len(selected_tfs))
        results_summary=[]
        for i,tf_key in enumerate(selected_tfs):
            with st.spinner(f"Analyzing {tf_key}..."):
                res,conf,sig,df_tf,note=run_single_timeframe(sym,tf_key,asset_name=tf_asset)
            cfg=TF_CONFIG[tf_key]
            with cols[i]:
                if sig in ("NO DATA","ERROR"):
                    st.markdown(f"""<div class='card' style='text-align:center'>
                    <b>{tf_key}</b><br><span style='color:#8b949e;font-size:12px'>{note}</span></div>""",unsafe_allow_html=True)
                    continue
                col="#3fb950" if "BUY" in sig else "#f85149" if "SELL" in sig else "#8b949e"
                st.markdown(f"""<div class='card' style='text-align:center;border-left:4px solid {col}'>
                <b>{cfg['label']}</b><br>
                <span style='font-size:18px;font-weight:900;color:{col}'>{sig}</span><br>
                <span style='font-size:13px;color:#8b949e'>{conf}% confidence</span>
                </div>""",unsafe_allow_html=True)
                results_summary.append((tf_key,sig,conf))
            if cfg["light"]:
                st.caption(f"⚠️ {note}")

        if results_summary:
            buys=sum(1 for _,s,_ in results_summary if "BUY" in s)
            sells=sum(1 for _,s,_ in results_summary if "SELL" in s)
            st.markdown("---")
            if buys>sells and buys>=len(results_summary)*0.6:
                st.success(f"✅ {buys}/{len(results_summary)} timeframes lean BUY — reasonable alignment")
            elif sells>buys and sells>=len(results_summary)*0.6:
                st.error(f"📉 {sells}/{len(results_summary)} timeframes lean SELL — reasonable alignment")
            else:
                st.warning("⚠️ Timeframes are conflicting — no clear cross-timeframe agreement")

        st.markdown("---")
        st.markdown("#### 🔬 Detailed breakdown for selected timeframe")
        detail_tf=st.selectbox("View details for",selected_tfs,key="tf_detail")
        res,conf,sig,df_tf,note=run_single_timeframe(sym,detail_tf,asset_name=tf_asset)
        if res:
            st.caption(note)
            for name,(s,reason) in res.items():
                col="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
                dot="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
                sr=reason.replace("<","&lt;").replace(">","&gt;")
                st.markdown(f"""<div style='background:#161b22;border-radius:8px;padding:10px 12px;
                margin-bottom:6px;border-left:3px solid {col}'>
                <b>{dot} {name}</b>
                <span style='background:{col};color:#fff;padding:1px 8px;border-radius:7px;font-size:11px;margin-left:8px'>{s}</span>
                <br><small style='color:#8b949e'>{sr}</small></div>""",unsafe_allow_html=True)
            if df_tf is not None and len(df_tf)>10:
                fig=go.Figure()
                if "Open" in df_tf.columns:
                    fig.add_trace(go.Candlestick(x=df_tf.index,open=df_tf["Open"],high=df_tf["High"],
                        low=df_tf["Low"],close=df_tf["Close"],increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
                else:
                    fig.add_trace(go.Scatter(x=df_tf.index,y=df_tf["Close"],line=dict(color="#58a6ff")))
                fig.update_layout(title=f"{tf_asset} — {TF_CONFIG[detail_tf]['label']}",
                    plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",font=dict(color="#e6edf3"),
                    height=350,xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
                    yaxis=dict(gridcolor="#21262d"))
                st.plotly_chart(fig,use_container_width=True,key=f"tf_chart_{detail_tf}")
        else:
            st.warning(note)

# ══════════════════════════════════════════════════════════════════════════════
# TRADE TICKETS
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Tickets":
    st.title("🎫 Trade Ticket Panel")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>All open positions. Close here to update your journal.</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()

    if st.button("🔄 Auto-Scan & Ticket All Grade A+B Signals",key="scan_all",use_container_width=True):
        added=0
        with st.spinner("Scanning with all quality filters..."):
            for name,sym in ALL_PAIRS.items():
                res,conf,sig,df_raw=run_strats(sym,asset_name=name)
                if sig=="WAIT" or conf<67 or df_raw is None: continue
                candle_ok,_=check_candle_quality(df_raw)
                atr_ok,_=check_atr_filter(df_raw)
                _,_,weekly_aligned=check_weekly_trend(sym,sig)
                session_ok,_=get_session_status(name)
                tf_res,mtf_sig,_=run_mtf(sym,asset_name=name)
                mtf_ok=(("BUY" in mtf_sig and "BUY" in sig) or ("SELL" in mtf_sig and "SELL" in sig))
                grade,_,_,_=get_signal_grade(conf,candle_ok,atr_ok,weekly_aligned,session_ok,mtf_ok,name in SPECIALISTS)
                if grade in ("A","B"):
                    entry,sl,tp1,tp2,tp3,_=get_setup(sym,sig)
                    if entry and auto_ticket(name,sig,conf,entry,sl,tp1,tp2,tp3,grade,"Auto Scan"):
                        added+=1
        st.success(f"✅ {added} Grade A/B ticket(s) created!")

    open_t=[t for t in st.session_state.journal if t.get("Result")=="Open"]
    if not open_t:
        st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
        border-radius:14px;padding:40px;text-align:center;margin-top:20px'>
        <div style='font-size:36px'>🎫</div>
        <div style='font-size:17px;color:#8b949e;margin-top:10px'>No open tickets</div>
        <div style='color:#8b949e;font-size:13px;margin-top:6px'>Use Pulse Signal or scan above.</div>
        </div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(open_t)} open position(s):**")
        for i,tr in enumerate(open_t):
            ib="BUY" in tr.get("Signal","")
            brd="#3fb950" if ib else "#f85149"
            icon="🚀" if ib else "📉"
            grade=tr.get("Grade","—")
            gc="grade-a" if grade=="A" else "grade-b" if grade=="B" else "grade-c"
            ji=next((j for j,t in enumerate(st.session_state.journal) if t==tr),None)
            spec=SPECIALISTS.get(tr.get("Asset",""),{})
            spec_icon=spec.get("icon","")
            st.markdown(f"""<div style='background:#161b22;border:2px solid {brd};
            border-radius:12px;padding:16px;margin-bottom:10px'>
            <div style='display:flex;justify-content:space-between;margin-bottom:10px'>
              <div>
                <span style='font-size:17px;font-weight:900;color:{brd}'>{icon} {tr.get("Signal","")}</span>
                &nbsp;<span class='{gc}' style='font-size:12px'>{grade}</span>
                &nbsp;<span style='font-size:18px;font-weight:700;color:#e6edf3'>{spec_icon} {tr.get("Asset","")}</span>
              </div>
              <div style='text-align:right;font-size:12px;color:#8b949e'>
                {tr.get("Date","")} {tr.get("Time","")}<br>
                <b style='color:#ffd200'>{tr.get("Confidence",0)}%</b> · {tr.get("Source","Manual")}
              </div>
            </div>
            <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:5px'>
              <div style='background:#0d1117;border-radius:6px;padding:7px;text-align:center'>
                <div style='font-size:9px;color:#8b949e'>ENTRY</div>
                <div style='font-size:11px;font-weight:700'>{tr.get("Entry","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:6px;padding:7px;text-align:center'>
                <div style='font-size:9px;color:#8b949e'>STOP</div>
                <div style='font-size:11px;font-weight:700;color:#f85149'>{tr.get("SL","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:6px;padding:7px;text-align:center'>
                <div style='font-size:9px;color:#8b949e'>TP1</div>
                <div style='font-size:11px;font-weight:700;color:#3fb950'>{tr.get("TP1","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:6px;padding:7px;text-align:center'>
                <div style='font-size:9px;color:#8b949e'>TP2</div>
                <div style='font-size:11px;font-weight:700;color:#3fb950'>{tr.get("TP2","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:6px;padding:7px;text-align:center'>
                <div style='font-size:9px;color:#8b949e'>TP3</div>
                <div style='font-size:11px;font-weight:700;color:#3fb950'>{tr.get("TP3","—")}</div>
              </div>
            </div></div>""",unsafe_allow_html=True)
            if ji is not None:
                b1,b2,b3,b4=st.columns(4)
                with b1:
                    if st.button("✅ Win",key=f"w_{i}",use_container_width=True):
                        st.session_state.journal[ji]["Result"]="Win"; st.rerun()
                with b2:
                    if st.button("❌ Loss",key=f"l_{i}",use_container_width=True):
                        st.session_state.journal[ji]["Result"]="Loss"; st.rerun()
                with b3:
                    if st.button("➖ B/E",key=f"b_{i}",use_container_width=True):
                        st.session_state.journal[ji]["Result"]="Breakeven"; st.rerun()
                with b4:
                    if st.button("🗑️ Remove",key=f"r_{i}",use_container_width=True):
                        st.session_state.journal.pop(ji); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Journal":
    st.title("📓 Trade Journal")
    if not pro: st.error("🔒 Premium only."); st.stop()
    if st.session_state.sig_history:
        with st.expander(f"📡 Signal History — {len(st.session_state.sig_history)} logged"):
            st.dataframe(pd.DataFrame(st.session_state.sig_history),use_container_width=True,hide_index=True)
    with st.expander("➕ Add Manually"):
        c1,c2,c3=st.columns(3)
        ja=c1.selectbox("Asset",list(ALL_PAIRS.keys()),key="j_a")
        js=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"],key="j_s")
        jr=c3.selectbox("Result",["Open","Win","Loss","Breakeven"],key="j_r")
        c4,c5=st.columns(2)
        je=c4.number_input("Entry",format="%.5f",key="j_e"); jsl=c5.number_input("SL",format="%.5f",key="j_sl")
        jc=st.slider("Confidence",0,100,67,key="j_c"); jn=st.text_input("Notes",key="j_n")
        if st.button("💾 Save",key="j_save"):
            st.session_state.journal.append({
                "Date":str(datetime.date.today()),"Time":datetime.datetime.now().strftime("%H:%M"),
                "Asset":ja,"Signal":js,"Grade":"Manual","Entry":je,"SL":jsl,
                "TP1":0,"TP2":0,"TP3":0,"Confidence":jc,"Result":jr,"Source":"Manual","Notes":jn})
            st.success("✅ Saved!")
    if st.session_state.journal:
        df=pd.DataFrame(st.session_state.journal)
        st.dataframe(df,use_container_width=True,hide_index=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
        wr=round(wins/tot*100,1) if tot>0 else 0
        # Streak tracker
        results=[t["Result"] for t in reversed(st.session_state.journal) if t["Result"] in ("Win","Loss")]
        streak=0; streak_type=""
        if results:
            streak_type=results[0]
            for r in results:
                if r==streak_type: streak+=1
                else: break
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Total",len(df)); c2.metric("Open",len(df[df["Result"]=="Open"]))
        c3.metric("Win Rate",f"{wr}%"); c4.metric("W/L",f"{wins}/{loss}")
        streak_label=f"🔥 {streak} Win streak" if streak_type=="Win" else f"❄️ {streak} Loss streak" if streak_type=="Loss" else "—"
        c5.metric("Streak",streak_label)
    else: st.info("No trades yet.")

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Performance":
    st.title("📈 Performance Dashboard")
    if not pro: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
    wr=round(wins/tot*100,1) if tot>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total Trades",tot); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
    if wr>=70: st.success(f"🎯 {wr}% win rate — above target! Keep following Grade A/B signals.")
    elif wr>=60: st.warning(f"⚠️ {wr}% win rate — focus on Grade A signals only.")
    else: st.error(f"🚨 {wr}% win rate — only take Grade A signals and ensure MTF confirmation.")
    st.divider()
    closed=df[df["Result"].isin(["Win","Loss"])]
    if not closed.empty:
        st.subheader("Win Rate by Asset")
        av=closed.groupby("Asset")["Result"].value_counts().unstack(fill_value=0)
        if "Win" in av.columns and "Loss" in av.columns:
            av["Win Rate %"]=round(av["Win"]/(av["Win"]+av["Loss"])*100,1)
            st.dataframe(av.sort_values("Win Rate %",ascending=False),use_container_width=True)
        st.divider()
        if "Grade" in df.columns:
            st.subheader("Win Rate by Signal Grade")
            gv=closed.groupby("Grade")["Result"].value_counts().unstack(fill_value=0)
            if "Win" in gv.columns and "Loss" in gv.columns:
                gv["Win Rate %"]=round(gv["Win"]/(gv["Win"]+gv["Loss"])*100,1)
                st.dataframe(gv,use_container_width=True)
        if "Signal" in df.columns:
            st.divider(); st.subheader("Win Rate by Signal Type")
            sv=closed.groupby("Signal")["Result"].value_counts().unstack(fill_value=0)
            st.dataframe(sv,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# RISK CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Risk":
    st.title("💰 Risk Calculator")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>Adjust risk % by signal grade: Grade A = 2%, Grade B = 1.5%, Grade C = 1%</div>",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        bal=st.number_input("Balance ($)",min_value=10.0,value=1000.0,key="r_bal")
        sg=st.selectbox("Signal Grade",["A — Full size (2%)","B — Normal (1.5%)","C — Half (1%)","Manual"],key="r_sg")
        default_risk=2.0 if "A" in sg else 1.5 if "B" in sg else 1.0
        rp=st.slider("Risk %",0.5,10.0,default_risk,step=0.5,key="r_rp")
        slp=st.number_input("Stop Loss (pips)",min_value=1.0,value=20.0,key="r_sl")
        pv=st.number_input("Pip value per 0.01 lot ($)",value=0.10,key="r_pv")
        rr=st.slider("Risk:Reward",1,5,2,key="r_rr")
    ra=bal*rp/100; lot=round(ra/(slp*pv/0.01)*0.01,2) if slp>0 else 0
    with c2:
        st.metric("Risk Amount",f"${ra:.2f}"); st.metric("Lot Size",f"{lot} lots")
        st.metric("Potential Profit",f"${ra*rr:.2f}"); st.metric("R:R",f"1:{rr}")
        st.progress(rp/10)
        if rp<=2: st.success("✅ Conservative — recommended")
        elif rp<=5: st.warning("⚠️ Moderate")
        else: st.error("🚨 High risk — reduce size")

    st.markdown("---")
    st.markdown("#### 🔍 Small Account Check")
    typical_spread=1.5
    if slp>0:
        spread_pct=(typical_spread/slp)*100
        if bal<200:
            st.warning(f"💡 With a ${bal:.0f} account, spread costs roughly **{round(spread_pct)}%** of this trade's risk. For small accounts, prefer setups with stops of 15+ pips where spread matters less — use the **Structure SL** shown in Deep Analysis for tighter, more precise stops anchored to real price levels rather than a flat distance.")
        elif spread_pct>25:
            st.info(f"ℹ️ This stop ({slp:.0f} pips) is tight — spread is ~{round(spread_pct)}% of your risk. Still workable on a larger account, but check the Structure SL option in Deep Analysis for an alternative.")
        else:
            st.success(f"✅ Spread impact is low (~{round(spread_pct)}%) relative to this stop size — efficient risk usage.")

# ══════════════════════════════════════════════════════════════════════════════
# PRICING
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Pricing":
    st.title("💎 Plans & Pricing")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'>
        <h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        Gold · Bitcoin · EUR/USD + 2 pairs<br>Basic signals only<br><br>
        ❌ Quality filters (Grade system)<br>❌ Session timing filter<br>❌ Weekly trend filter<br>
        ❌ Market condition detector<br>❌ Correlation warnings<br>❌ Auto Trade Tickets<br>❌ Position sizing by grade
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$15/mo</h2><hr>
        ✅ All 16 assets<br>
        ✅ 🥇 Gold · ₿ BTC · € EUR/USD Specialist Analysis<br>
        ✅ <b>Grade A/B/C quality filtering</b><br>
        ✅ Candle quality · ATR · Weekly trend · Session filter<br>
        ✅ Market condition (Trending/Ranging/Volatile)<br>
        ✅ Correlation warnings — avoid double risk<br>
        ✅ 🎫 Auto Trade Tickets (Grade A/B only)<br>
        ✅ Position sizing by signal grade<br>
        ✅ Win Rate by Grade tracking<br>
        ✅ Streak tracker<br>
        ✅ AI Daily Briefing + News Trading<br>
        ✅ Fibonacci + Pivot Points on charts
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.info("💬 Contact us to get your premium password after payment.")

# ══════════════════════════════════════════════════════════════════════════════
# LEARN
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Learn":
    st.title("📚 Education & Strategy Guide")
    t1,t2,t3,t4=st.tabs(["🥇 Gold","₿ Bitcoin","€ EUR/USD","📖 Signal Guide"])

    with t1:
        st.markdown("### 🥇 Gold (XAU/USD) Trading Guide")
        st.markdown("""**Why Gold is special:** Institution-driven. SMC Order Blocks + round numbers + EMA200 are the most reliable signals.

**Best setups:**""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>🏦 SMC Order Block</b><br><br>Last red candle before big rally<br>
            Entry: at OB zone<br>Stop: below OB<br>Target: round number above</div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>🧱 Round Numbers</b><br><br>$1900/$2000/$2100/$2200<br>
            Act as massive S/R<br>Combine with OB at same level<br>= very high probability</div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>📈 EMA200 Daily</b><br><br>Gold bounces off EMA200 reliably<br>
            Highlighted in gold on chart<br>Price below = bearish bias<br>Price above = bullish bias</div>""",unsafe_allow_html=True)
        st.info("💡 Gold spikes on USD news (NFP/FOMC/CPI). Use wider stops. Best: London + NY sessions.")

    with t2:
        st.markdown("### ₿ Bitcoin Trading Guide")
        st.markdown("""**Why BTC is special:** Massive Fair Value Gaps that always fill. RSI Divergences on 4H are highly reliable.""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #f7931a'>
            <b>🕳️ Fair Value Gaps</b><br><br>BTC leaves massive FVGs<br>
            They always fill eventually<br>Enter when price returns to gap<br>Stop: beyond the gap</div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #f7931a'>
            <b>⚡ RSI Divergence</b><br><br>4H divergences are very reliable<br>
            Bullish div at support = strong BUY<br>Bearish div at resistance = SELL<br>Best with FVG at same level</div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #f7931a'>
            <b>🧱 Round Numbers</b><br><br>$60k/$65k/$70k/$75k/$80k<br>
            BTC always tests round numbers<br>OB or FVG at round number<br>= highest probability setup</div>""",unsafe_allow_html=True)
        st.info("💡 BTC reacts to risk sentiment. Wider stops needed — BTC can wick 3-5%. Best on 4H/Daily.")

    with t3:
        st.markdown("### € EUR/USD Trading Guide")
        st.markdown("""**Why EUR/USD is special:** Most trend-following pair. EMA alignment + ADX + FVGs are very reliable.""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #4488ff'>
            <b>📈 EMA Stack</b><br><br>20>50>200 = strong uptrend<br>
            Pullback to EMA20 = entry<br>ADX must be above 20<br>Most reliable on 4H</div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #4488ff'>
            <b>💪 ADX Filter</b><br><br>ADX above 25 = trending<br>
            ADX above 30 = strong — full size<br>ADX below 20 = ranging, avoid<br>Best during London/NY overlap</div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #4488ff'>
            <b>🕳️ Clean FVGs</b><br><br>EUR/USD fills FVGs reliably<br>
            High liquidity = efficient market<br>Enter on FVG retest in trend<br>Stop: beyond FVG</div>""",unsafe_allow_html=True)
        st.info("💡 Most active: London open (3am EST) and NY open (8am EST). Avoid 5pm-midnight EST.")

    with t4:
        st.markdown("### 📖 How to Read Sparro FX AI Signals")
        st.markdown("**Signal Grades:**")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #238636;text-align:center'>
            <span class='grade-a'>Grade A</span><br><br>
            All filters pass<br>MTF confirmed<br>Good session<br>Weekly aligned<br><br>
            <b>2% risk — full size</b></div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #9e6a03;text-align:center'>
            <span class='grade-b'>Grade B</span><br><br>
            Most filters pass<br>Good setup<br>Minor concerns<br><br><br>
            <b>1.5% risk — normal size</b></div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #b94040;text-align:center'>
            <span class='grade-c'>Grade C</span><br><br>
            Some filters fail<br>Marginal setup<br>Proceed with caution<br><br>
            <b>1% risk — half size or skip</b></div>""",unsafe_allow_html=True)
        st.markdown("""
**Quality Filters explained:**
- 🕯️ **Candle Quality** — body must be 25%+ of range. Doji = indecision = skip
- 📊 **ATR Filter** — volatility must be normal. Dead markets and news spikes are excluded
- 📅 **Weekly Trend** — signal must agree with weekly timeframe. Counter-trend = lower grade
- 🕐 **Session Timing** — EUR/USD/Gold only in London/NY. BTC any time
- 🔀 **Multi-Timeframe** — Daily + 4H + 1H must agree for highest grade

**Correlation Warning:**
If EUR/USD AND GBP/USD both signal BUY — that's double exposure to USD weakness.
The app warns you automatically. Pick the better grade signal, not both.
        """)

# ══════════════════════════════════════════════════════════════════════════════
# ABOUT
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="About":
    st.title("ℹ️ About Sparro FX AI")
    st.markdown("""**Sparro FX AI** — realistic signal platform designed for 70%+ win rate.

**The 6 Strategies:**

| Strategy | Measures | Role |
|---|---|---|
| EMA Trend | Direction | Full 20/50/200 stack alignment |
| ADX Strength | Trend strength | Filters out ranging markets |
| RSI + Divergence | Momentum | Divergence for reversals |
| SMC Order Blocks | Institutional zones | Bank order locations |
| SMC Fair Value Gap | Price imbalances | Magnetic price levels |
| Support/Resistance | Key levels | Entry quality check |

**Quality Filters (what makes this realistic):**

| Filter | What it removes |
|---|---|
| Candle body filter | Doji/indecision signals |
| ATR volatility filter | Dead markets + news spikes |
| Weekly trend check | Counter-trend lower-probability trades |
| Session timing | Trading outside optimal hours |
| Multi-timeframe | Single-timeframe false signals |
| Grade D exclusion | All poor quality setups |

**Expected performance by grade:**
- Grade A: Target 70%+ win rate
- Grade B: Target 60-70% win rate
- Grade C: Target 50-60% win rate — use small size or skip

⚠️ *No app guarantees profits. Trade responsibly with money you can afford to risk.*""")

# ══════════════════════════════════════════════════════════════════════════════
# CURRENCY STRENGTH METER
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Strength":
    st.title("💪 Currency Strength Meter")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>Relative strength of each major currency based on its % move across all pairs (last 5 days, hourly data).</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()

    with st.spinner("Calculating currency strength..."):
        strength=calc_currency_strength()

    max_abs=max([abs(v) for v in strength.values()]+[0.01])
    for cur,val in strength.items():
        pct=abs(val)/max_abs*100
        col="#3fb950" if val>0 else "#f85149" if val<0 else "#8b949e"
        bar_w=max(pct,2)
        st.markdown(f"""<div style='margin-bottom:10px'>
        <div style='display:flex;justify-content:space-between;margin-bottom:4px'>
          <b>{cur}</b><span style='color:{col};font-weight:700'>{val:+.3f}%</span>
        </div>
        <div style='background:#161b22;border-radius:6px;height:14px;overflow:hidden'>
          <div style='background:{col};height:100%;width:{bar_w}%;border-radius:6px'></div>
        </div></div>""",unsafe_allow_html=True)

    st.markdown("---")
    strongest=list(strength.keys())[0]; weakest=list(strength.keys())[-1]
    st.info(f"💡 **Strongest:** {strongest} &nbsp;|&nbsp; **Weakest:** {weakest} — consider pairs combining these two for the cleanest directional move (e.g. {strongest}/{weakest} if that pair exists).")
    st.caption("This is a momentum snapshot, not a signal — combine with Pulse Signal and your own analysis.")

# ══════════════════════════════════════════════════════════════════════════════
# AI TRADING COACH
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Coach":
    st.title("🧘 AI Trading Coach")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>Behavioral analysis from your journal — overtrading, revenge trading, and performance patterns.</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()

    flags=detect_overtrading(st.session_state.journal)
    if not flags:
        st.success("✅ No concerning patterns detected in your recent trading. Keep following your plan.")
    else:
        for title,msg in flags:
            st.warning(f"**{title}**\n\n{msg}")

    st.markdown("---")
    if st.session_state.journal:
        df=pd.DataFrame(st.session_state.journal)
        st.markdown("#### 📊 Daily Trade Count")
        if "Date" in df.columns:
            counts=df["Date"].value_counts().sort_index()
            st.bar_chart(counts)
        st.markdown("#### 🤖 AI Performance Review")
        if st.button("Generate AI Review",key="coach_review",use_container_width=True):
            with st.spinner("Reviewing your trading..."):
                summary=df.to_string(index=False) if len(df)<=30 else df.tail(30).to_string(index=False)
                review=ai_call(f"You are a trading psychology coach. Review this trade journal and give 3-4 sentences of honest, constructive feedback on patterns, discipline, and what to improve. Journal:\n{summary}",450)
            st.markdown(f"""<div class='card' style='border-left:4px solid #58a6ff;line-height:1.8'>
            {review.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)
    else:
        st.info("Log trades in the Journal to get coaching insights.")

# ══════════════════════════════════════════════════════════════════════════════
# AI CHART ANALYZER (screenshot upload)
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="ChartAI":
    st.title("📷 AI Chart Analyzer")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>Upload a chart screenshot — AI reads it for trend, key zones, and an SMC-style read.</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()
    if not AI_KEY:
        st.warning("⚠️ Add ANTHROPIC_API_KEY in Streamlit secrets to enable this feature.")
    uploaded=st.file_uploader("Upload chart screenshot",type=["png","jpg","jpeg"],key="chart_upload")
    if uploaded and AI_KEY:
        st.image(uploaded,use_container_width=True)
        if st.button("🔍 Analyze Chart",key="analyze_chart",use_container_width=True):
            import base64
            img_bytes=uploaded.getvalue()
            b64=base64.b64encode(img_bytes).decode()
            media_type=uploaded.type
            with st.spinner("AI reading the chart..."):
                try:
                    r=requests.post("https://api.anthropic.com/v1/messages",
                        headers={"Content-Type":"application/json","x-api-key":AI_KEY,"anthropic-version":"2023-06-01"},
                        json={"model":"claude-sonnet-4-6","max_tokens":700,
                              "messages":[{"role":"user","content":[
                                  {"type":"image","source":{"type":"base64","media_type":media_type,"data":b64}},
                                  {"type":"text","text":"You are an SMC/price-action trading analyst. Look at this chart screenshot and give: 1) Overall trend direction 2) Key support/resistance or order block zones you can see 3) Any visible Fair Value Gaps or imbalances 4) A possible entry zone, stop loss and target IF a setup is visible 5) Confidence level (low/medium/high) and why. Be honest if the image is unclear or no clear setup exists. Bullet points."}
                              ]}]},timeout=40)
                    if r.status_code==200:
                        analysis=r.json()["content"][0]["text"]
                    else:
                        analysis=f"AI error {r.status_code}: {r.text[:200]}"
                except Exception as e:
                    analysis=f"Error analyzing chart: {e}"
            st.markdown(f"""<div class='card' style='border-left:4px solid #7c3aed;line-height:1.8'>
            {analysis.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)
            st.caption("⚠️ AI chart reading is supplementary — always confirm with the live Pulse Signal and your own analysis.")
    elif uploaded and not AI_KEY:
        st.error("Cannot analyze — ANTHROPIC_API_KEY missing.")

# ══════════════════════════════════════════════════════════════════════════════
# PROP FIRM TOOLS
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="PropFirm":
    st.title("🛡️ Prop Firm Tools")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>Track drawdown limits, consistency, and risk of ruin for prop firm challenges.</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()

    st.markdown("#### 📉 Daily Drawdown Monitor")
    c1,c2,c3=st.columns(3)
    starting_bal=c1.number_input("Account starting balance ($)",min_value=100.0,value=10000.0,key="pf_bal")
    current_bal=c2.number_input("Current balance ($)",min_value=0.0,value=10000.0,key="pf_cur")
    max_daily_dd=c3.number_input("Max daily drawdown allowed (%)",min_value=1.0,value=5.0,key="pf_dd")
    daily_loss_limit=starting_bal*max_daily_dd/100
    current_dd=max(0,starting_bal-current_bal)
    dd_pct=current_dd/starting_bal*100 if starting_bal>0 else 0
    remaining=daily_loss_limit-current_dd
    c1,c2,c3=st.columns(3)
    c1.metric("Current Drawdown",f"${current_dd:.2f}",f"{dd_pct:.2f}%")
    c2.metric("Daily Limit",f"${daily_loss_limit:.2f}")
    c3.metric("Room Remaining",f"${max(0,remaining):.2f}")
    if remaining<=0: st.error("🚨 Daily drawdown limit breached or at limit. Stop trading today.")
    elif remaining<daily_loss_limit*0.3: st.warning("⚠️ Approaching daily drawdown limit. Trade carefully.")
    else: st.success("✅ Within safe drawdown range.")

    st.markdown("---")
    st.markdown("#### 🎲 Risk of Ruin Estimator")
    c1,c2,c3=st.columns(3)
    df_j=pd.DataFrame(st.session_state.journal) if st.session_state.journal else pd.DataFrame()
    closed=df_j[df_j["Result"].isin(["Win","Loss"])] if not df_j.empty and "Result" in df_j.columns else pd.DataFrame()
    default_wr=round(len(closed[closed["Result"]=="Win"])/len(closed)*100,1) if len(closed)>0 else 50.0
    wr_input=c1.slider("Win rate (%)",10.0,90.0,default_wr,key="pf_wr")
    rr_input=c2.slider("Average Risk:Reward",1.0,5.0,2.0,key="pf_rr")
    risk_input=c3.slider("Risk per trade (%)",0.5,5.0,2.0,key="pf_risk")
    ror=calc_risk_of_ruin(wr_input,rr_input,risk_input)
    c1,c2=st.columns(2)
    c1.metric("Estimated Risk of Ruin",f"{ror}%")
    if ror<5: c2.success("✅ Low risk of ruin — sustainable approach")
    elif ror<25: c2.warning("⚠️ Moderate risk — consider reducing risk % per trade")
    else: c2.error("🚨 High risk of ruin — reduce position sizing significantly")
    st.caption("Simplified estimate. Real risk of ruin depends on trade sequencing and variance — use as a directional guide only.")

    st.markdown("---")
    st.markdown("#### 📊 Consistency Score")
    if not closed.empty and "Confidence" in closed.columns:
        results_only=closed["Result"].tolist()
        wins=results_only.count("Win")
        consistency=round(wins/len(results_only)*100,1) if results_only else 0
        st.metric("Consistency Score",f"{consistency}%")
        st.caption("Based on win/loss consistency in your logged trades. Prop firms often want stable performance, not one huge win carrying the account.")
    else:
        st.info("Log more trades to calculate consistency score.")

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Admin":
    if atype!="admin": st.error("🔒 Admin only."); st.stop()
    st.title("👑 Admin Panel")
    t1,t2,t3=st.tabs(["🔐 Passwords","👥 Subscribers","📊 Stats"])
    with t1:
        st.info("""Set in **Streamlit Cloud → App Settings → Secrets**:
```toml
ADMIN_PASSWORD    = "your-admin-pass"
PREMIUM_PASSWORD  = "your-premium-pass"
FREE_PASSWORD     = "sparro_free"
ANTHROPIC_API_KEY = "sk-ant-xxx"
```
**Change PREMIUM_PASSWORD to lock out non-payers instantly.**""")
    with t2:
        with st.expander("➕ Add Subscriber"):
            c1,c2,c3=st.columns(3)
            sn=c1.text_input("Name",key="s_n"); se=c2.text_input("Email",key="s_e")
            sp=c3.selectbox("Plan",["Premium $15/mo","Trial","Free"],key="s_p")
            sd=st.date_input("Start",datetime.date.today(),key="s_d"); sno=st.text_input("Notes",key="s_no")
            if st.button("➕ Add",key="s_add"):
                if sn and se:
                    st.session_state.subscribers.append({"Name":sn,"Email":se,"Plan":sp,"Start":str(sd),"Notes":sno})
                    st.success(f"✅ {sn} added!")
                else: st.error("Name and email required.")
        if st.session_state.subscribers:
            st.dataframe(pd.DataFrame(st.session_state.subscribers),use_container_width=True,hide_index=True)
        else: st.info("No subscribers yet.")
    with t3:
        subs=st.session_state.subscribers
        pc=len([s for s in subs if "Premium" in s.get("Plan","")])
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total",len(subs)); c2.metric("Premium",pc)
        c3.metric("Monthly",f"${pc*15}"); c4.metric("Annual",f"${pc*15*12}")
        st.markdown("---\n**🔗 Links**")
        st.markdown("- [Streamlit Cloud](https://share.streamlit.io)\n- [GitHub](https://github.com/sparroxhalo-stack/ai-forex-analyzer)\n- [Anthropic Console](https://console.anthropic.com)")
