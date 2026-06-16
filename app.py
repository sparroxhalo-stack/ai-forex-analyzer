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
.gold-badge{background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.btc-badge{background:linear-gradient(90deg,#f7931a,#ff6600);color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.eur-badge{background:linear-gradient(90deg,#003399,#0055cc);color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.specialist-card{border:2px solid #ffd200 !important;box-shadow:0 0 12px rgba(255,210,0,0.2)}
@media(max-width:768px){
  .block-container{padding:0.5rem !important}
  .stTabs [data-baseweb="tab"]{padding:5px 7px !important;font-size:10px !important}
  h1{font-size:20px !important}
}
</style>
""", unsafe_allow_html=True)

# ─── SOUND ALERT ──────────────────────────────────────────────────────────────
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

# ─── PERSISTENT LOGIN ──────────────────────────────────────────────────────────
def _tok(at,em,ts):
    return hashlib.sha256(f"{at}|{em}|{ts}|fx2024".encode()).hexdigest()[:16]

def save_session(at,em,ts=""):
    st.query_params["s"]=f"{at}|{em}|{ts}|{_tok(at,em,ts)}"

def load_session():
    try:
        raw=st.query_params.get("s","")
        if not raw: return None
        at,em,ts,tok=raw.split("|")
        if tok!=_tok(at,em,ts): return None
        return {"account_type":at,"email":em,
                "trial_start":datetime.datetime.fromisoformat(ts) if ts else None}
    except: return None

def clear_session(): st.query_params.clear()

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
DEFS={"logged_in":False,"account_type":None,"trial_start":None,
      "email":"","journal":[],"subscribers":[],"sig_history":[],
      "page":"Dashboard","_loaded":False}
for k,v in DEFS.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state._loaded:
    s=load_session()
    if s: st.session_state.update(logged_in=True,email=s["email"],
                                   account_type=s["account_type"],
                                   trial_start=s["trial_start"])
    st.session_state._loaded=True

def _sec(k,fb):
    try: return st.secrets.get(k,fb)
    except: return fb

ADM_PW  = _sec("ADMIN_PASSWORD","sparro_admin_2024")
PRE_PW  = _sec("PREMIUM_PASSWORD","sparro_pro_2024")
FREE_PW = _sec("FREE_PASSWORD","sparro_free")
AI_KEY  = _sec("ANTHROPIC_API_KEY","")
TRIAL_H = 48

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
    <div style='color:#8b949e;margin-top:6px'>Professional AI-Powered Forex & Commodity Signal Platform</div>
    </div>""",unsafe_allow_html=True)

    # Specialist pairs showcase
    st.markdown("""<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
    max-width:700px;margin:0 auto 24px auto'>
    <div style='background:linear-gradient(135deg,#1a1400,#2a2000);border:2px solid #ffd200;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>🥇</div>
    <div style='font-weight:900;color:#ffd200;font-size:15px'>Gold</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>SMC + S/R + EMA200<br>Specialist Analysis</div>
    </div>
    <div style='background:linear-gradient(135deg,#1a0d00,#2a1500);border:2px solid #f7931a;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>₿</div>
    <div style='font-weight:900;color:#f7931a;font-size:15px'>Bitcoin</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>FVG + Divergence<br>Specialist Analysis</div>
    </div>
    <div style='background:linear-gradient(135deg,#00001a,#000033);border:2px solid #4488ff;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>€</div>
    <div style='font-weight:900;color:#4488ff;font-size:15px'>EUR/USD</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>EMA + ADX + FVG<br>Specialist Analysis</div>
    </div>
    </div>""",unsafe_allow_html=True)

    _,mid,_=st.columns([1,2,1])
    with mid:
        t1,t2,t3=st.tabs(["🔑 Login","🎁 48hr Free Trial","ℹ️ About"])
        with t1:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            st.markdown("#### Welcome back 👋")
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
            st.markdown("- ✅ All 10 assets incl. Gold, Bitcoin, EUR/USD\n- ✅ Specialist analysis for top 3 pairs\n- ✅ 6 precision strategies\n- ✅ Multi-timeframe confirmation\n- ✅ Auto Trade Tickets\n- ✅ Fibonacci + Pivot charts")
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
            <p style='color:#8b949e'>6 precision strategies measuring genuinely different things.
            Gold, Bitcoin and EUR/USD get specialist analysis tuned to how each market actually behaves.</p>
            <b>🆓 Free</b> — 5 assets · basic signals<br><br>
            <b>🎁 Trial 48h</b> — full access · no card<br><br>
            <b>⚡ Premium $15/mo</b> — everything<br><br>
            <hr style='border-color:#30363d'>
            <small style='color:#8b949e'>Trade responsibly. Past signals do not guarantee future results.</small>
            </div>""",unsafe_allow_html=True)

if not st.session_state.logged_in: login_page(); st.stop()
if st.session_state.account_type=="trial" and hours_left()==0:
    st.error("⏰ Trial ended. Upgrade — $15/mo")
    if st.button("🔓 Login with premium password",key="exp_btn"):
        clear_session(); st.session_state.logged_in=False; st.rerun()
    st.stop()

pro=is_pro(); atype=st.session_state.account_type

# ═══════════════════════════════════════════════════════════════════════════════
# ASSETS — specialist pairs pinned first
# ═══════════════════════════════════════════════════════════════════════════════
# Specialist pairs with their best strategies and period/interval
SPECIALISTS = {
    "Gold (XAU/USD)": {
        "sym":    "GC=F",
        "icon":   "🥇",
        "badge":  "gold-badge",
        "label":  "GOLD",
        "color":  "#ffd200",
        "best":   ["SMC Order Blocks","Support/Resistance","EMA Trend"],
        "why":    "Gold is institution-driven — SMC Order Blocks and S/R at big round numbers ($1900/$2000/$2100) are the most reliable signals. EMA200 is gold's most respected long-term level.",
        "period": "6mo",
        "tf_best":"Daily + 4H",
    },
    "Bitcoin": {
        "sym":    "BTC-USD",
        "icon":   "₿",
        "badge":  "btc-badge",
        "label":  "BTC",
        "color":  "#f7931a",
        "best":   ["SMC Fair Value Gap","RSI + Divergence","Support/Resistance"],
        "why":    "Bitcoin leaves massive Fair Value Gaps that always get filled. RSI Divergences on BTC are some of the most reliable reversal signals in any market. Round numbers ($60k/$70k/$80k) act as strong magnets.",
        "period": "3mo",
        "tf_best":"4H + Daily",
    },
    "EUR/USD": {
        "sym":    "EURUSD=X",
        "icon":   "€",
        "badge":  "eur-badge",
        "label":  "EUR/USD",
        "color":  "#4488ff",
        "best":   ["EMA Trend","ADX Strength","SMC Fair Value Gap"],
        "why":    "EUR/USD is the most trend-following pair in forex. EMA stack alignment is highly reliable. ADX confirms strong trends during London/NY overlap. FVGs are very clean due to EUR/USD's extreme liquidity.",
        "period": "6mo",
        "tf_best":"1H + 4H (London/NY session)",
    },
}

ALL_PAIRS = {
    # Specialists first
    "Gold (XAU/USD)":  "GC=F",
    "Bitcoin":         "BTC-USD",
    "EUR/USD":         "EURUSD=X",
    # Then others
    "GBP/USD":         "GBPUSD=X",
    "USD/JPY":         "USDJPY=X",
    "AUD/USD":         "AUDUSD=X",
    "USD/CHF":         "USDCHF=X",
    "USD/CAD":         "USDCAD=X",
    "NASDAQ":          "^IXIC",
    "S&P 500":         "^GSPC",
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])  # Gold, BTC, EURUSD + GBP, JPY
pairs = ALL_PAIRS if pro else FREE_PAIRS

# ─── DATA ──────────────────────────────────────────────────────────────────────
def get_df(sym,period="6mo",interval="1d"):
    try:
        df=yf.download(sym,period=period,interval=interval,progress=False,auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return None

# ═══════════════════════════════════════════════════════════════════════════════
# 6 PRECISION STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════════

# 1. EMA TREND — Direction
def s_ema(df):
    c=df["Close"]
    e20=float(c.ewm(20).mean().iloc[-1])
    e50=float(c.ewm(50).mean().iloc[-1])
    e200=float(c.ewm(200).mean().iloc[-1])
    p=float(c.iloc[-1])
    if e20>e50>e200 and p>e20:
        return "BUY","EMA stack bullish (20>50>200) — all timeframes aligned up"
    if e20<e50<e200 and p<e20:
        return "SELL","EMA stack bearish (20<50<200) — all timeframes aligned down"
    if e20>e200 and p>e50:
        return "BUY","Above EMA200 — long-term uptrend intact"
    if e20<e200 and p<e50:
        return "SELL","Below EMA200 — long-term downtrend intact"
    return "NEUTRAL","EMA stack mixed — no clear trend direction"

# 2. ADX STRENGTH — Trend strength filter
def s_adx(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        up=h.diff(); dn=-l.diff()
        pdm=up.where((up>dn)&(up>0),0)
        ndm=dn.where((dn>up)&(dn>0),0)
        atr=tr.ewm(14,min_periods=14).mean()
        pdi=100*(pdm.ewm(14,min_periods=14).mean()/atr)
        ndi=100*(ndm.ewm(14,min_periods=14).mean()/atr)
        dx=100*(pdi-ndi).abs()/(pdi+ndi)
        adx=float(dx.ewm(14,min_periods=14).mean().iloc[-1])
        pv=float(pdi.iloc[-1]); nv=float(ndi.iloc[-1])
        if adx>=30 and pv>nv: return "BUY", f"ADX={round(adx,1)} — strong uptrend, worth trading"
        if adx>=30 and nv>pv: return "SELL",f"ADX={round(adx,1)} — strong downtrend, worth trading"
        if adx>=20 and pv>nv: return "BUY", f"ADX={round(adx,1)} — moderate uptrend building"
        if adx>=20 and nv>pv: return "SELL",f"ADX={round(adx,1)} — moderate downtrend building"
        return "NEUTRAL",f"ADX={round(adx,1)} — market ranging, avoid trend trades"
    except: return "NEUTRAL","ADX error"

# 3. RSI + DIVERGENCE — Momentum & reversals
def s_rsi(df):
    try:
        c=df["Close"]; d=c.diff()
        g=d.where(d>0,0).rolling(14).mean()
        l=(-d.where(d<0,0)).rolling(14).mean()
        rsi=100-(100/(1+(g/l)))
        rv=float(rsi.iloc[-1])
        prices=c.iloc[-20:].values; rsis=rsi.iloc[-20:].values
        ph=[i for i in range(1,len(prices)-1) if prices[i]>prices[i-1] and prices[i]>prices[i+1]]
        pl=[i for i in range(1,len(prices)-1) if prices[i]<prices[i-1] and prices[i]<prices[i+1]]
        if len(ph)>=2:
            h1,h2=ph[-2],ph[-1]
            if prices[h2]>prices[h1] and rsis[h2]<rsis[h1]:
                return "SELL",f"RSI={round(rv,1)} — Bearish Divergence (price up, RSI down — reversal warning)"
        if len(pl)>=2:
            l1,l2=pl[-2],pl[-1]
            if prices[l2]<prices[l1] and rsis[l2]>rsis[l1]:
                return "BUY",f"RSI={round(rv,1)} — Bullish Divergence (price down, RSI up — reversal signal)"
        if rv>60:  return "BUY", f"RSI={round(rv,1)} — strong bullish momentum"
        if rv>52:  return "BUY", f"RSI={round(rv,1)} — building bullish momentum"
        if rv<40:  return "SELL",f"RSI={round(rv,1)} — strong bearish momentum"
        if rv<48:  return "SELL",f"RSI={round(rv,1)} — building bearish momentum"
        return "NEUTRAL",f"RSI={round(rv,1)} — neutral momentum"
    except: return "NEUTRAL","RSI error"

# 4. SMC ORDER BLOCKS — Institutional buy/sell zones
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
            if lo<=cp<=hi*1.003:
                return "BUY",f"SMC Bullish Order Block {round(lo,4)}-{round(hi,4)} — institutional buy zone"
            if hi<cp<=hi*1.01:
                return "BUY",f"SMC Price above Bullish OB {round(lo,4)} — institutional support"
        for lo,hi in sobs[:3]:
            if lo*0.997<=cp<=hi:
                return "SELL",f"SMC Bearish Order Block {round(lo,4)}-{round(hi,4)} — institutional sell zone"
            if lo*0.99<=cp<lo:
                return "SELL",f"SMC Price below Bearish OB {round(hi,4)} — institutional resistance"
        return "NEUTRAL","SMC No active Order Blocks near price"
    except: return "NEUTRAL","SMC OB insufficient data"

# 5. SMC FAIR VALUE GAP — Price imbalances
def s_fvg(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        cp=float(c.iloc[-1]); bfvg=[]; sfvg=[]
        for i in range(2,min(50,len(df)-3)):
            idx=-i
            ph=float(h.iloc[idx-1]); nl=float(l.iloc[idx+1])
            if nl>ph and (nl-ph)/ph>0.0008: bfvg.append((ph,nl))
            pl=float(l.iloc[idx-1]); nh=float(h.iloc[idx+1])
            if pl>nh and (pl-nh)/pl>0.0008: sfvg.append((nh,pl))
        for lo,hi in bfvg[:5]:
            if lo<=cp<=hi:
                return "BUY",f"SMC Bullish FVG {round(lo,4)}-{round(hi,4)} — filling imbalance, continuation up"
            if cp<lo and cp>=lo*0.997:
                return "BUY",f"SMC Bullish FVG magnet above {round(lo,4)}-{round(hi,4)}"
        for lo,hi in sfvg[:5]:
            if lo<=cp<=hi:
                return "SELL",f"SMC Bearish FVG {round(lo,4)}-{round(hi,4)} — filling imbalance, continuation down"
            if cp>hi and cp<=hi*1.003:
                return "SELL",f"SMC Bearish FVG magnet below {round(lo,4)}-{round(hi,4)}"
        return "NEUTRAL","SMC No active Fair Value Gaps near price"
    except: return "NEUTRAL","SMC FVG insufficient data"

# 6. SUPPORT & RESISTANCE — Key price levels
def s_sr(df):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        p=float(c.iloc[-1])
        res=float(h.rolling(20).max().iloc[-1])
        sup=float(l.rolling(20).min().iloc[-1])
        mid=(res+sup)/2; rng=res-sup; zone=rng*0.10
        pct=round((p-sup)/rng*100,1) if rng>0 else 50
        if p>=res-zone:
            return "SELL",f"At resistance {round(res,4)} ({pct}% of range) — rejection likely"
        if p<=sup+zone:
            return "BUY", f"At support {round(sup,4)} ({pct}% of range) — bounce likely"
        if p>mid+zone:
            return "BUY", f"Upper half of range {pct}% — bullish bias, room to resistance"
        if p<mid-zone:
            return "SELL",f"Lower half of range {pct}% — bearish bias, room to support"
        return "NEUTRAL",f"Mid-range {pct}% — S={round(sup,4)} R={round(res,4)}"
    except: return "NEUTRAL","S/R error"

STRATS={
    "EMA Trend":          (s_ema,"📈","Trend Direction"),
    "ADX Strength":       (s_adx,"💪","Trend Strength Filter"),
    "RSI + Divergence":   (s_rsi,"⚡","Momentum & Divergence"),
    "SMC Order Blocks":   (s_ob, "🏦","Institutional Zones"),
    "SMC Fair Value Gap": (s_fvg,"🕳️","Price Imbalances"),
    "Support/Resistance": (s_sr, "🧱","Key Price Levels"),
}

# ─── SPECIALIST SCORING ────────────────────────────────────────────────────────
def run_strats(sym,period="6mo",asset_name=None):
    """
    Run all 6 strategies. For specialist pairs, the best 3 strategies
    count double — giving them more weight in the confidence score.
    """
    df=get_df(sym,period)
    if df is None or len(df)<50: return {},0,"ERROR"

    # Get specialist info if applicable
    spec=SPECIALISTS.get(asset_name,None)
    best_strats=spec["best"] if spec else []

    res={}
    for name,(fn,ico,desc) in STRATS.items():
        try: res[name]=fn(df)
        except: res[name]=("NEUTRAL","Calculation error")

    # Weighted scoring for specialist pairs
    buy_score=0; sell_score=0; total_weight=0
    for name,(sig,reason) in res.items():
        weight=2.0 if (name in best_strats) else 1.0
        total_weight+=weight
        if sig=="BUY":  buy_score+=weight
        if sig=="SELL": sell_score+=weight

    if buy_score>sell_score:
        conf=round(buy_score/total_weight*100)
        sig="STRONG BUY"  if buy_score/total_weight>=0.83 else "BUY" if buy_score/total_weight>=0.67 else "WAIT"
    elif sell_score>buy_score:
        conf=round(sell_score/total_weight*100)
        sig="STRONG SELL" if sell_score/total_weight>=0.83 else "SELL" if sell_score/total_weight>=0.67 else "WAIT"
    else:
        conf=50; sig="WAIT"

    return res,conf,sig

def run_mtf(sym,asset_name=None):
    tfs={}
    for label,period,interval in [("Daily","6mo","1d"),("4H","60d","4h"),("1H","5d","1h")]:
        df=get_df(sym,period,interval)
        if df is None or len(df)<30: tfs[label]=("WAIT",0); continue
        res={}
        spec=SPECIALISTS.get(asset_name,None)
        best_strats=spec["best"] if spec else []
        for name,(fn,_,__) in STRATS.items():
            try: res[name]=fn(df)
            except: res[name]=("NEUTRAL","Error")
        bs=0; ss=0; tw=0
        for name,(sg,_) in res.items():
            w=2.0 if name in best_strats else 1.0
            tw+=w
            if sg=="BUY": bs+=w
            if sg=="SELL": ss+=w
        if bs>ss and bs/tw>=0.67:   tfs[label]=("BUY",round(bs/tw*100))
        elif ss>bs and ss/tw>=0.67: tfs[label]=("SELL",round(ss/tw*100))
        else:                        tfs[label]=("WAIT",50)
    sigs=[s for s,_ in tfs.values() if s!="WAIT"]
    bc=sum(1 for s in sigs if s=="BUY"); sc=sum(1 for s in sigs if s=="SELL")
    if bc==3:   ms="STRONG BUY";  mn="All 3 timeframes aligned ✅ — highest probability"
    elif bc==2: ms="BUY";         mn="2/3 timeframes agree — good setup"
    elif sc==3: ms="STRONG SELL"; mn="All 3 timeframes aligned ✅ — highest probability"
    elif sc==2: ms="SELL";        mn="2/3 timeframes agree — good setup"
    else:       ms="WAIT";        mn="Timeframes conflicting — stand aside"
    return tfs,ms,mn

def get_setup(sym,direction):
    try:
        df=get_df(sym,"3mo"); c=df["Close"]; h=df["High"]; l=df["Low"]; p=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); risk=atr*1.5
        if "BUY" in direction: return p,p-risk,p+risk,p+risk*2,p+risk*3
        else:                  return p,p+risk,p-risk,p-risk*2,p-risk*3
    except: return None,None,None,None,None

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

def auto_ticket(asset,sig,conf,entry,sl,tp1,tp2,tp3,src="Auto"):
    today=str(datetime.date.today())
    dup=[t for t in st.session_state.journal
         if t.get("Asset")==asset and t.get("Date")==today and t.get("Signal")==sig]
    if dup: return False
    st.session_state.journal.append({
        "Date":today,"Time":datetime.datetime.now().strftime("%H:%M"),
        "Asset":asset,"Signal":sig,"Entry":round(entry,5),"SL":round(sl,5),
        "TP1":round(tp1,5),"TP2":round(tp2,5),"TP3":round(tp3,5),
        "Confidence":conf,"Result":"Open","Source":src})
    st.session_state.sig_history.append({
        "DateTime":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Asset":asset,"Signal":sig,"Confidence":conf,
        "Entry":round(entry,5),"Result":"Pending"})
    return True

# ─── SPECIALIST CARD ───────────────────────────────────────────────────────────
def specialist_header(name):
    spec=SPECIALISTS.get(name)
    if not spec: return
    st.markdown(f"""<div style='background:linear-gradient(135deg,#161b22,#0d1117);
    border:2px solid {spec["color"]};border-radius:12px;padding:14px;margin-bottom:14px'>
    <div style='display:flex;align-items:center;gap:12px'>
      <div style='font-size:32px'>{spec["icon"]}</div>
      <div>
        <div style='font-weight:900;font-size:18px;color:{spec["color"]}'>{name} — Specialist Analysis</div>
        <div style='font-size:12px;color:#8b949e;margin-top:3px'>
          Best strategies: <b style='color:{spec["color"]}'>{" · ".join(spec["best"])}</b>
          &nbsp;|&nbsp; Best timeframe: <b>{spec["tf_best"]}</b>
        </div>
        <div style='font-size:12px;color:#8b949e;margin-top:3px'>{spec["why"]}</div>
      </div>
    </div>
    </div>""",unsafe_allow_html=True)

# ─── SIGNAL BANNER ─────────────────────────────────────────────────────────────
def banner(sig,asset,conf):
    spec=SPECIALISTS.get(asset)
    spec_tag=""
    if spec:
        badge_cls=spec["badge"]
        spec_icon=spec["icon"]
        spec_lbl=spec["label"]
        spec_tag=f"&nbsp;<span class='{badge_cls}'>{spec_icon} {spec_lbl} SPECIALIST</span>"
    if sig=="STRONG BUY":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#0d5c2e,#1a7a3e);
        border:2px solid #3fb950;border-radius:14px;padding:20px;text-align:center;
        margin-bottom:12px;box-shadow:0 0 20px rgba(63,185,80,0.4)'>
        <div style='font-size:24px;font-weight:900;color:#3fb950'>🚀 STRONG BUY — BUY NOW {spec_tag}</div>
        <div style='font-size:15px;color:#e6edf3;margin-top:5px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="BUY":
        st.markdown(f"""<div style='background:#0d2b1a;border:2px solid #3fb950;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'>
        <div style='font-size:20px;font-weight:800;color:#3fb950'>🟢 BUY SIGNAL {spec_tag}</div>
        <div style='font-size:14px;color:#e6edf3;margin-top:4px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="STRONG SELL":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#5c0d0d,#7a1a1a);
        border:2px solid #f85149;border-radius:14px;padding:20px;text-align:center;
        margin-bottom:12px;box-shadow:0 0 20px rgba(248,81,73,0.4)'>
        <div style='font-size:24px;font-weight:900;color:#f85149'>📉 STRONG SELL — SELL NOW {spec_tag}</div>
        <div style='font-size:15px;color:#e6edf3;margin-top:5px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    elif sig=="SELL":
        st.markdown(f"""<div style='background:#2b0d0d;border:2px solid #f85149;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'>
        <div style='font-size:20px;font-weight:800;color:#f85149'>🔴 SELL SIGNAL {spec_tag}</div>
        <div style='font-size:14px;color:#e6edf3;margin-top:4px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#161b22;border:1px solid #30363d;
        border-radius:14px;padding:14px;text-align:center;margin-bottom:12px'>
        <div style='font-size:17px;color:#8b949e'>⏳ WAIT — {asset} — strategies not aligned yet</div>
        </div>""",unsafe_allow_html=True)

# ─── CHART ─────────────────────────────────────────────────────────────────────
def chart(sym,name,sig,entry,sl,tp1,tp2,ckey="chart",asset_name=None):
    df=get_df(sym,"3mo","1d")
    if df is None: st.warning("Chart unavailable"); return
    cl=df["Close"]; e20=cl.ewm(20).mean(); e50=cl.ewm(50).mean(); e200=cl.ewm(200).mean()
    res=float(df["High"].rolling(20).max().iloc[-1])
    sup=float(df["Low"].rolling(20).min().iloc[-1])
    dates=df.index; fig=go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],
            low=df["Low"],close=cl,name="Price",
            increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates,y=cl,name="Price",line=dict(color="#58a6ff",width=2)))
    fig.add_trace(go.Scatter(x=dates,y=e20,name="EMA20",line=dict(color="#ffd700",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=e50,name="EMA50",line=dict(color="#ff7f50",width=1,dash="dot")))
    # EMA200 highlighted for Gold (most important level)
    ema200_color="#ffd200" if asset_name=="Gold (XAU/USD)" else "#da70d6"
    ema200_width=2 if asset_name=="Gold (XAU/USD)" else 1
    fig.add_trace(go.Scatter(x=dates,y=e200,name="EMA200",
        line=dict(color=ema200_color,width=ema200_width,dash="dash")))
    fig.add_hline(y=res,line_color="#f85149",line_dash="dash",
        annotation_text=f"Res {round(res,4)}",annotation_position="right",annotation_font_size=9)
    fig.add_hline(y=sup,line_color="#3fb950",line_dash="dash",
        annotation_text=f"Sup {round(sup,4)}",annotation_position="right",annotation_font_size=9)
    if entry:
        ec="#3fb950" if "BUY" in sig else "#f85149"
        fig.add_hline(y=entry,line_color=ec,line_width=2,
            annotation_text=f"Entry {round(entry,5)}",annotation_position="left",annotation_font_size=9)
        fig.add_hline(y=sl,line_color="#f85149",line_dash="dash",
            annotation_text=f"SL {round(sl,5)}",annotation_position="left",annotation_font_size=9)
        fig.add_hline(y=tp1,line_color="#3fb950",line_dash="dash",
            annotation_text=f"TP1 {round(tp1,5)}",annotation_position="left",annotation_font_size=9)
        fig.add_hline(y=tp2,line_color="#3fb950",line_dash="dot",
            annotation_text=f"TP2 {round(tp2,5)}",annotation_position="left",annotation_font_size=9)
    # Fibonacci
    fc={"0.382":"#9b59b6","0.5":"#3498db","0.618":"#e67e22","0.786":"#e74c3c"}
    for lv,pr in get_fibs(sym).items():
        fig.add_hline(y=pr,line_color=fc.get(lv,"#888"),line_width=1,line_dash="dot",
            annotation_text=f"Fib {lv}",annotation_position="right",annotation_font_size=8)
    # Pivots
    pc={"PP":"#ffffff","R1":"#ff6b6b","R2":"#ff4444","S1":"#51cf66","S2":"#37b24d"}
    for lv,pr in get_pivots(sym).items():
        fig.add_hline(y=pr,line_color=pc.get(lv,"#888"),line_width=1,line_dash="longdash",
            annotation_text=lv,annotation_position="left",annotation_font_size=8)
    lp=float(cl.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[lp],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in sig else "triangle-down",
                    size=13,color="#3fb950" if "BUY" in sig else "#f85149"),name="Signal"))
    spec=SPECIALISTS.get(asset_name)
    title_color=spec["color"] if spec else "#e6edf3"
    fig.update_layout(
        title=dict(text=f"{name}{' ⭐ Specialist' if spec else ''}",font=dict(color=title_color)),
        plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),height=430,
        xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),
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

    # Specialist pair quick icons
    st.markdown("""<div style='display:flex;gap:6px;justify-content:center;margin-bottom:10px'>
    <span style='background:#2a2000;border:1px solid #ffd200;border-radius:8px;padding:4px 8px;font-size:13px'>🥇 Gold</span>
    <span style='background:#2a1500;border:1px solid #f7931a;border-radius:8px;padding:4px 8px;font-size:13px'>₿ BTC</span>
    <span style='background:#000033;border:1px solid #4488ff;border-radius:8px;padding:4px 8px;font-size:13px'>€ EUR</span>
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

    nav=[("🏠 Dashboard","Dashboard"),("🎫 Tickets","Tickets"),
         ("📓 Journal","Journal"),("📈 Performance","Performance"),
         ("💰 Risk Calc","Risk")]
    for lbl,key in nav:
        active=st.session_state.page==key
        if st.button(lbl,use_container_width=True,
                     type="primary" if active else "secondary",key=f"p_{key}"):
            st.session_state.page=key; st.rerun()

    with st.expander("≫ More"):
        more=[("💎 Pricing","Pricing"),("📚 Learn","Learn"),("ℹ️ About","About")]
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

    if not pro: st.warning("🔒 Free plan — Gold, Bitcoin, EUR/USD + 2 pairs. Upgrade for all 10.")

    # Daily briefing
    if pro:
        with st.expander("📰 Daily Market Briefing — AI Generated",expanded=False):
            ndf=get_news()
            hi_ev=ndf[ndf["Impact"]=="High"] if "Impact" in ndf.columns else pd.DataFrame()
            if not hi_ev.empty:
                ev_str=" · ".join([f"{r.get('Time','')} {r.get('Currency','')} {r.get('Event','')}"
                                   for _,r in hi_ev.head(3).iterrows()])
                st.error(f"⚠️ HIGH IMPACT NEWS: {ev_str}")
            with st.spinner("Generating briefing..."):
                brief=ai_call(f"Write a 3-sentence daily forex/gold/bitcoin market briefing. Focus on Gold, Bitcoin and EUR/USD. Key events: {ndf.to_string(index=False) if len(ndf)>0 else 'none'}. Be direct and actionable.",400)
            st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;
            border-left:4px solid #00c6ff;font-size:14px;line-height:1.8'>
            {brief.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)

    t1,t2,t3,t4,t5=st.tabs(["⚡ Pulse","📊 Scanner","🏆 Trade of Day","🔬 Deep Analysis","🗞️ News Trading"])

    # ── PULSE ──────────────────────────────────────────────────────────────────
    with t1:
        st.markdown("""<div style='display:flex;align-items:center;margin-bottom:6px'>
        <span class='pulse-dot'></span>
        <span style='font-size:19px;font-weight:800'>Live Pulse Signal</span></div>
        <div style='color:#8b949e;font-size:13px;margin-bottom:14px'>
        4+/6 strategies must agree. Gold, Bitcoin and EUR/USD use specialist-weighted scoring.</div>""",unsafe_allow_html=True)

        if not pro:
            st.error("🔒 Upgrade to access Pulse Signals.")
        else:
            rc,rb=st.columns([3,1])
            with rb:
                if st.button("🔄 Refresh",use_container_width=True,key="pulse_ref"): st.rerun()
            with rc: st.caption(f"Last scan: {datetime.datetime.now().strftime('%H:%M:%S')}")

            with st.spinner("Scanning all markets..."):
                hits=[]
                for name,sym in ALL_PAIRS.items():
                    res,conf,sig=run_strats(sym,asset_name=name)
                    if sig in ("STRONG BUY","STRONG SELL","BUY","SELL") and conf>=67:
                        entry,sl,tp1,tp2,tp3=get_setup(sym,sig)
                        if entry:
                            tf_res,mtf_sig,mtf_note=run_mtf(sym,asset_name=name)
                            mtf_ok=(("BUY" in mtf_sig and "BUY" in sig) or
                                    ("SELL" in mtf_sig and "SELL" in sig))
                            hits.append({"name":name,"sym":sym,"sig":sig,"conf":conf,
                                "entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,
                                "res":res,"tf":tf_res,"mtf_sig":mtf_sig,
                                "mtf_note":mtf_note,"mtf_ok":mtf_ok,
                                "is_spec":name in SPECIALISTS})
                # Sort: specialists first, then by MTF confirmation, then confidence
                hits.sort(key=lambda x:(x["is_spec"],x["mtf_ok"],x["conf"]),reverse=True)

            if hits: play_sound(hits[0]["sig"])

            if not hits:
                st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
                border-radius:14px;padding:40px;text-align:center'>
                <div style='font-size:36px'>😴</div>
                <div style='font-size:17px;color:#8b949e;margin-top:10px'>No signals right now</div>
                <div style='color:#8b949e;font-size:13px;margin-top:6px'>
                Waiting for 4+/6 strategies to align. Quality over quantity.</div>
                </div>""",unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#3fb950;font-weight:700;margin-bottom:10px'>✅ {len(hits)} signal(s) active — specialists shown first</div>",unsafe_allow_html=True)
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
                    mtf_lbl="🟢 MTF CONFIRMED" if p["mtf_ok"] else "🟡 MTF MIXED"
                    spec=SPECIALISTS.get(p["name"])
                    spec_border=f"border-top:3px solid {spec['color']};" if spec else ""
                    extra_shadow = f";box-shadow:0 0 20px {spec['color']}44" if spec else ''
                    if spec:
                        _bc=spec["badge"]; _si=spec["icon"]; _sl=spec["label"]
                        spec_tag=f"&nbsp;<span class='{_bc}'>{_si} {_sl}</span>"
                    else:
                        spec_tag=""

                    tf_html="".join([
                        f"<div style='background:#00000044;border-radius:6px;padding:6px 4px;"
                        f"text-align:center;color:{'#3fb950' if s=='BUY' else '#f85149' if s=='SELL' else '#8b949e'};"
                        f"font-size:12px'>{tf}<br><b>{s}</b></div>"
                        for tf,(s,_) in p["tf"].items()])

                    st.markdown(f"""<div style='background:{bg};border:2px solid {brd};
                    {spec_border}border-radius:14px;padding:16px;margin-bottom:12px;
                    box-shadow:0 0 14px {brd}33{extra_shadow}'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:10px'>
                      <div>
                        <div style='font-size:19px;font-weight:900;color:{brd}'>{icon} {p["sig"]}{spec_tag}
                          {"&nbsp;<span class='smc-badge'>SMC ✓</span>" if smc_on else ""}
                        </div>
                        <div style='font-size:20px;font-weight:700;color:#e6edf3'>{p["name"]}</div>
                        <div style='font-size:12px;color:{mtf_col};margin-top:3px'>{mtf_lbl} — {p["mtf_note"]}</div>
                      </div>
                      <div style='text-align:right'>
                        <div style='font-size:30px;font-weight:900;color:{cfc}'>{p["conf"]}%</div>
                        <div style='font-size:10px;color:#8b949e'>{len(agr)}/6 AGREE</div>
                      </div>
                    </div>
                    <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:10px'>
                      <div style='background:#00000044;border-radius:7px;padding:8px;text-align:center'>
                        <div style='font-size:10px;color:#8b949e'>ENTRY</div>
                        <div style='font-size:12px;font-weight:700;color:#e6edf3'>{round(p["entry"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:7px;padding:8px;text-align:center'>
                        <div style='font-size:10px;color:#8b949e'>STOP</div>
                        <div style='font-size:12px;font-weight:700;color:#f85149'>{round(p["sl"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:7px;padding:8px;text-align:center'>
                        <div style='font-size:10px;color:#8b949e'>TP1</div>
                        <div style='font-size:12px;font-weight:700;color:#3fb950'>{round(p["tp1"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:7px;padding:8px;text-align:center'>
                        <div style='font-size:10px;color:#8b949e'>TP2</div>
                        <div style='font-size:12px;font-weight:700;color:#3fb950'>{round(p["tp2"],4)}</div>
                      </div>
                      <div style='background:#00000044;border-radius:7px;padding:8px;text-align:center'>
                        <div style='font-size:10px;color:#8b949e'>TP3</div>
                        <div style='font-size:12px;font-weight:700;color:#3fb950'>{round(p["tp3"],4)}</div>
                      </div>
                    </div>
                    <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:8px'>
                      {tf_html}
                    </div>
                    <div style='font-size:11px;color:#8b949e'>✅ {" · ".join(agr)}</div>
                    </div>""",unsafe_allow_html=True)

                    ca,cb=st.columns(2)
                    with ca:
                        if st.button(f"🎫 Auto Ticket",key=f"atk_{idx}",use_container_width=True):
                            ok=auto_ticket(p["name"],p["sig"],p["conf"],p["entry"],
                                          p["sl"],p["tp1"],p["tp2"],p["tp3"],"Pulse")
                            st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                    with cb:
                        with st.expander(f"📊 {p['name']} Chart"):
                            chart(p["sym"],p["name"],p["sig"],p["entry"],p["sl"],
                                  p["tp1"],p["tp2"],ckey=f"pc_{idx}",asset_name=p["name"])

    # ── SCANNER ────────────────────────────────────────────────────────────────
    with t2:
        st.markdown("### 📊 Market Scanner")
        st.caption("Specialists (Gold/BTC/EUR) shown first with weighted scoring.")
        rows=[]; prog=st.progress(0); items=list(pairs.items())
        for i,(name,sym) in enumerate(items):
            res,conf,sig=run_strats(sym,asset_name=name)
            b=sum(1 for s,_ in res.values() if s=="BUY")
            s=sum(1 for s,_ in res.values() if s=="SELL")
            spec=SPECIALISTS.get(name)
            spec_label=f"{spec['icon']} SPEC" if spec else ""
            rows.append({"Asset":name,"Specialist":spec_label,"Signal":sig,
                "Confidence":f"{conf}%" if pro else "🔒",
                "Agree":f"{max(b,s)}/6" if pro else "🔒"})
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
    with t3:
        st.markdown("### 🏆 Trade of the Day")
        st.caption("Highest-confidence setup. Specialist pairs given priority.")
        if not pro: st.error("🔒 Premium only.")
        else:
            best={"conf":0,"sig":"WAIT","name":"","sym":"","res":{},"is_spec":False}
            with st.spinner("Finding best setup..."):
                for name,sym in ALL_PAIRS.items():
                    res,conf,sig=run_strats(sym,asset_name=name)
                    is_spec=name in SPECIALISTS
                    # Specialists get +5% boost to prioritise them when close
                    eff_conf=conf+(5 if is_spec else 0)
                    if sig!="WAIT" and eff_conf>best["conf"]:
                        best={"conf":conf,"sig":sig,"name":name,"sym":sym,"res":res,"is_spec":is_spec}
            if best["is_spec"]: specialist_header(best["name"])
            banner(best["sig"],best["name"],best["conf"])
            c1,c2,c3=st.columns(3)
            c1.metric("Asset",best["name"]); c2.metric("Signal",best["sig"]); c3.metric("Confidence",f"{best['conf']}%")
            st.progress(best["conf"]/100)
            entry,sl,tp1,tp2,tp3=get_setup(best["sym"],best["sig"])
            if entry:
                tf_res,mtf_sig,mtf_note=run_mtf(best["sym"],asset_name=best["name"])
                mtfc="#3fb950" if "BUY" in mtf_sig else "#f85149" if "SELL" in mtf_sig else "#8b949e"
                st.markdown(f"""<div style='background:#161b22;border-radius:8px;padding:10px;
                border-left:4px solid {mtfc};margin:10px 0;font-size:13px'>
                🕐 <b>Multi-Timeframe:</b> {mtf_sig} — {mtf_note}</div>""",unsafe_allow_html=True)
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{round(entry,4)}"); c2.metric("SL",f"{round(sl,4)}")
                c3.metric("TP1",f"{round(tp1,4)}"); c4.metric("TP2",f"{round(tp2,4)}"); c5.metric("TP3",f"{round(tp3,4)}")
                if st.button("🎫 Auto Ticket",key="totd_tk",use_container_width=True):
                    ok=auto_ticket(best["name"],best["sig"],best["conf"],entry,sl,tp1,tp2,tp3,"Trade of Day")
                    st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                chart(best["sym"],best["name"],best["sig"],entry,sl,tp1,tp2,
                      ckey="totd_chart",asset_name=best["name"])

    # ── DEEP ANALYSIS ──────────────────────────────────────────────────────────
    with t4:
        st.markdown("### 🔬 Deep Analysis")
        if not pro: st.error("🔒 Premium only.")
        else:
            sel=st.selectbox("Choose Asset",list(ALL_PAIRS.keys()),key="deep_sel")
            sym=ALL_PAIRS[sel]
            with st.spinner(f"Running 6 strategies on {sel}..."):
                res,conf,sig=run_strats(sym,asset_name=sel)
                tf_res,mtf_sig,mtf_note=run_mtf(sym,asset_name=sel)

            if sel in SPECIALISTS: specialist_header(sel)
            banner(sig,sel,conf)
            c1,c2,c3=st.columns(3)
            c1.metric("Signal",sig); c2.metric("Confidence",f"{conf}%"); c3.metric("Strategies","6")
            st.progress(conf/100)
            mtfc="#3fb950" if "BUY" in mtf_sig else "#f85149" if "SELL" in mtf_sig else "#8b949e"
            tf_str=" &nbsp;·&nbsp; ".join([f"{tf}: {s}" for tf,(s,_) in tf_res.items()])
            st.markdown(f"""<div style='background:#161b22;border-radius:8px;padding:10px;
            border-left:4px solid {mtfc};margin:10px 0;font-size:13px'>
            🕐 <b>MTF:</b> {mtf_sig} — {mtf_note} &nbsp;|&nbsp; {tf_str}</div>""",unsafe_allow_html=True)
            st.markdown("---")

            spec=SPECIALISTS.get(sel)
            best_strats=spec["best"] if spec else []
            for name,(fn,ico,desc) in STRATS.items():
                s,reason=res.get(name,("NEUTRAL","No data"))
                col="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
                dot="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
                sr=reason.replace("<","&lt;").replace(">","&gt;")
                is_smc="SMC" in name
                is_best=name in best_strats
                br=";border-right:2px solid #7c3aed" if is_smc else ""
                spec_br=f";border-right:3px solid {spec['color']}" if (is_best and spec) else br
                smc_tag="&nbsp;<span class='smc-badge'>SMC</span>" if is_smc else ""
                best_tag=f"&nbsp;<span style='background:{spec['color']};color:#000;border-radius:5px;padding:1px 6px;font-size:11px;font-weight:700'>⭐ SPECIALIST</span>" if (is_best and spec) else ""
                weight_tag="&nbsp;<span style='color:#ffd200;font-size:11px'>(2× weight)</span>" if (is_best and spec) else ""
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:12px;
                margin-bottom:8px;border-left:4px solid {col}{spec_br}'>
                <div style='display:flex;justify-content:space-between;align-items:center'>
                  <div>
                    <b>{dot} {ico} {name}</b>{smc_tag}{best_tag}{weight_tag}
                    <span style='color:#8b949e;font-size:11px;margin-left:6px'>{desc}</span>
                  </div>
                  <span style='background:{col};color:#fff;padding:2px 10px;border-radius:8px;font-size:12px;font-weight:700'>{s}</span>
                </div>
                <div style='color:#8b949e;font-size:13px;margin-top:6px'>{sr}</div>
                </div>""",unsafe_allow_html=True)

            b=sum(1 for s,_ in res.values() if s=="BUY"); sv=sum(1 for s,_ in res.values() if s=="SELL")
            c1,c2,c3=st.columns(3)
            c1.metric("🟢 Buying",b); c2.metric("🔴 Selling",sv); c3.metric("🟡 Neutral",6-b-sv)
            entry,sl,tp1,tp2,tp3=get_setup(sym,sig)
            if entry and sig!="WAIT":
                st.markdown("---")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{round(entry,4)}"); c2.metric("SL",f"{round(sl,4)}")
                c3.metric("TP1",f"{round(tp1,4)}"); c4.metric("TP2",f"{round(tp2,4)}"); c5.metric("TP3",f"{round(tp3,4)}")
                if conf>=83: st.success(f"✅ STRONG — {b if 'BUY' in sig else sv}/6 agree. High probability.")
                elif conf>=67: st.warning(f"⚠️ MODERATE — trade smaller size.")
                else: st.error("🚨 Not enough agreement. Wait.")
                if st.button("🎫 Auto Ticket",key="deep_tk",use_container_width=True):
                    ok=auto_ticket(sel,sig,conf,entry,sl,tp1,tp2,tp3,"Deep Analysis")
                    st.success("✅ Ticket created!") if ok else st.warning("Already ticketed today.")
                chart(sym,sel,sig,entry,sl,tp1,tp2,ckey=f"deep_{sel}",asset_name=sel)

    # ── NEWS TRADING ───────────────────────────────────────────────────────────
    with t5:
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
                          padding:1px 7px;font-size:11px'>HIGH</span>
                          &nbsp;<b>{row.get("Event","")}</b></div>
                          <div style='color:#8b949e;font-size:12px'>{row.get("Time","")}</div>
                        </div>
                        <div style='margin-top:6px;font-size:13px;color:#8b949e'>
                          <b style='color:#ffd200'>{curr}</b> · Forecast: <b>{row.get("Forecast","—")}</b>
                          · Previous: <b>{row.get("Previous","—")}</b></div>
                        <div style='margin-top:5px;font-size:12px;color:#58a6ff'>
                          📌 {" · ".join(aff[:4])}</div>
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
                sym=ALL_PAIRS[np_]; res,conf,sig=run_strats(sym,asset_name=np_)
                entry,sl,tp1,tp2,tp3=get_setup(sym,sig)
                if np_ in SPECIALISTS: specialist_header(np_)
                banner(sig,np_,conf)
                c1,c2=st.columns(2)
                with c1:
                    st.markdown(f"""<div class='card' style='border-left:4px solid #0072ff'>
                    <b>📊 Technical Bias</b><br>Signal: <b>{sig}</b> — {conf}%<br><br>
                    {"✅ Use technical direction after news confirms" if sig!="WAIT" else "⚠️ Wait for reaction"}</div>""",unsafe_allow_html=True)
                with c2:
                    if entry and sig!="WAIT":
                        st.markdown(f"""<div class='card' style='border-left:4px solid #ffd700'>
                        <b>🎯 Levels</b><br>Entry: <b>{round(entry,4)}</b><br>
                        SL: <b style='color:#f85149'>{round(sl,4)}</b><br>
                        TP1: <b style='color:#3fb950'>{round(tp1,4)}</b></div>""",unsafe_allow_html=True)
                with st.spinner("AI analysis..."):
                    ai_txt=ai_call(f"Forex/commodity news trader. Asset: {np_}\nCalendar:\n{ndf.to_string(index=False)}\nGive: events affecting this asset, expected direction, entry timing, risk, trade plan. Bullets only.",500)
                st.markdown(f"""<div class='card' style='border-left:4px solid #58a6ff;line-height:1.8'>
                {ai_txt.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)
                if entry: st.markdown("---"); chart(sym,np_,sig,entry,sl,tp1,tp2,ckey=f"news_{np_}",asset_name=np_)
            st.markdown("---")
            c1,c2=st.columns(2)
            with c1:
                st.markdown("""<div class='card'><b style='color:#3fb950'>✅ DO</b><br><br>
                Wait for candle <b>close</b> after news<br>Trade the <b>surprise</b> direction<br>
                Use <b>wider stops</b> on Gold/BTC<br>Take profits <b>quickly</b><br>
                Check <b>both currencies</b></div>""",unsafe_allow_html=True)
            with c2:
                st.markdown("""<div class='card'><b style='color:#f85149'>❌ DON'T</b><br><br>
                Don't trade <b>into</b> the release<br>Don't hold through NFP/FOMC blind<br>
                Gold spikes on USD news — <b>be ready</b><br>BTC reacts to <b>risk sentiment</b><br>
                Max <b>1% risk</b> on news trades</div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TRADE TICKETS
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Tickets":
    st.title("🎫 Trade Ticket Panel")
    st.markdown("<div style='color:#8b949e;margin-bottom:16px'>All open positions. Close here to update your journal.</div>",unsafe_allow_html=True)
    if not pro: st.error("🔒 Premium only."); st.stop()

    if st.button("🔄 Auto-Scan & Ticket All Strong Signals",key="scan_all",use_container_width=True):
        added=0
        with st.spinner("Scanning..."):
            for name,sym in ALL_PAIRS.items():
                res,conf,sig=run_strats(sym,asset_name=name)
                if sig in ("STRONG BUY","STRONG SELL") and conf>=83:
                    entry,sl,tp1,tp2,tp3=get_setup(sym,sig)
                    if entry and auto_ticket(name,sig,conf,entry,sl,tp1,tp2,tp3,"Auto Scan"):
                        added+=1
        st.success(f"✅ {added} new ticket(s) created!")

    open_t=[t for t in st.session_state.journal if t.get("Result")=="Open"]
    if not open_t:
        st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
        border-radius:14px;padding:40px;text-align:center;margin-top:20px'>
        <div style='font-size:36px'>🎫</div>
        <div style='font-size:17px;color:#8b949e;margin-top:10px'>No open tickets</div>
        <div style='color:#8b949e;font-size:13px;margin-top:6px'>Use Pulse Signal to create tickets.</div>
        </div>""",unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(open_t)} open position(s):**")
        for i,tr in enumerate(open_t):
            ib="BUY" in tr.get("Signal","")
            brd="#3fb950" if ib else "#f85149"
            icon="🚀" if ib else "📉"
            ji=next((j for j,t in enumerate(st.session_state.journal) if t==tr),None)
            spec=SPECIALISTS.get(tr.get("Asset",""))
            spec_border=f"border-top:2px solid {spec['color']};" if spec else ""
            if spec:
                _sb=spec["badge"]; _si=spec["icon"]
                spec_label=f"<span class='{_sb}'>{_si}</span>&nbsp;"
            else:
                spec_label=""
            st.markdown(f"""<div style='background:#161b22;border:2px solid {brd};
            {spec_border}border-radius:12px;padding:16px;margin-bottom:10px'>
            <div style='display:flex;justify-content:space-between;margin-bottom:10px'>
              <div>
                <span style='font-size:17px;font-weight:900;color:{brd}'>{icon} {tr.get("Signal","")}</span>
                &nbsp;{spec_label}<span style='font-size:19px;font-weight:700;color:#e6edf3'>{tr.get("Asset","")}</span>
              </div>
              <div style='text-align:right;font-size:12px;color:#8b949e'>
                {tr.get("Date","")} {tr.get("Time","")}<br>
                <b style='color:#ffd200'>{tr.get("Confidence",0)}%</b> · {tr.get("Source","Manual")}
              </div>
            </div>
            <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:6px'>
              <div style='background:#0d1117;border-radius:7px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>ENTRY</div>
                <div style='font-size:12px;font-weight:700'>{tr.get("Entry","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:7px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>STOP</div>
                <div style='font-size:12px;font-weight:700;color:#f85149'>{tr.get("SL","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:7px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>TP1</div>
                <div style='font-size:12px;font-weight:700;color:#3fb950'>{tr.get("TP1","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:7px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>TP2</div>
                <div style='font-size:12px;font-weight:700;color:#3fb950'>{tr.get("TP2","—")}</div>
              </div>
              <div style='background:#0d1117;border-radius:7px;padding:8px;text-align:center'>
                <div style='font-size:10px;color:#8b949e'>TP3</div>
                <div style='font-size:12px;font-weight:700;color:#3fb950'>{tr.get("TP3","—")}</div>
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
                "Asset":ja,"Signal":js,"Entry":je,"SL":jsl,"TP1":0,"TP2":0,"TP3":0,
                "Confidence":jc,"Result":jr,"Source":"Manual","Notes":jn})
            st.success("✅ Saved!")
    if st.session_state.journal:
        df=pd.DataFrame(st.session_state.journal)
        st.dataframe(df,use_container_width=True,hide_index=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
        wr=round(wins/tot*100,1) if tot>0 else 0
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total",len(df)); c2.metric("Open",len(df[df["Result"]=="Open"]))
        c3.metric("Win Rate",f"{wr}%"); c4.metric("W/L",f"{wins}/{loss}")
    else: st.info("No trades yet.")

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Performance":
    st.title("📈 Performance")
    if not pro: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
    wr=round(wins/tot*100,1) if tot>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total",tot); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
    st.divider()
    closed=df[df["Result"].isin(["Win","Loss"])]
    if not closed.empty:
        st.subheader("Win Rate by Asset")
        av=closed.groupby("Asset")["Result"].value_counts().unstack(fill_value=0)
        if "Win" in av.columns and "Loss" in av.columns:
            av["Win Rate %"]=round(av["Win"]/(av["Win"]+av["Loss"])*100,1)
            st.dataframe(av.sort_values("Win Rate %",ascending=False),use_container_width=True)
        if "Signal" in df.columns:
            st.divider(); st.subheader("Win Rate by Signal Type")
            sv=closed.groupby("Signal")["Result"].value_counts().unstack(fill_value=0)
            st.dataframe(sv,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# RISK CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="Risk":
    st.title("💰 Risk Calculator")
    c1,c2=st.columns(2)
    with c1:
        bal=st.number_input("Balance ($)",min_value=10.0,value=1000.0,key="r_bal")
        rp=st.slider("Risk %",0.5,10.0,2.0,step=0.5,key="r_rp")
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
        ❌ Specialist scoring<br>❌ Pulse Signal<br>❌ Multi-timeframe<br>
        ❌ Auto Trade Tickets<br>❌ Signal History<br>❌ News Trading<br>❌ Fib + Pivots
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$15/mo</h2><hr>
        ✅ All 10 assets<br>
        ✅ 🥇 Gold · ₿ Bitcoin · € EUR/USD Specialist Analysis<br>
        ✅ 6 precision strategies with specialist weighting<br>
        ✅ ⚡ Pulse Signal — specialists shown first<br>
        ✅ 🕐 Multi-timeframe (1H+4H+Daily)<br>
        ✅ SMC Order Blocks + Fair Value Gaps<br>
        ✅ RSI + Divergence detection<br>
        ✅ 🎫 Auto Trade Tickets<br>
        ✅ Signal History + Win Rate by Asset<br>
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
    t1,t2,t3,t4=st.tabs(["🥇 Gold Strategy","₿ Bitcoin Strategy","€ EUR/USD Strategy","📖 Signal Guide"])

    with t1:
        st.markdown("### 🥇 Gold (XAU/USD) — How We Trade It")
        specialist_header("Gold (XAU/USD)")
        st.markdown("""
**Why Gold is special:**
Gold is driven by institutions and central banks — it's one of the most SMC-friendly markets.
Big round numbers ($1900, $2000, $2100, $2200) act as massive support/resistance.
The EMA200 on the daily chart is gold's most respected long-term level.

**Best setups for Gold:**""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>🏦 SMC Order Block</b><br><br>
            Institutions place massive orders in OBs<br>
            Gold respects these zones very strongly<br>
            Entry: at OB zone<br>
            Stop: below/above OB<br>
            Target: next round number</div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>🧱 S/R + Round Numbers</b><br><br>
            $2000, $2050, $2100 etc act as magnets<br>
            When price hits these = high reaction<br>
            Combine with OB or FVG at same level<br>
            = very high probability setup</div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>📈 EMA200 Daily</b><br><br>
            Gold bounces off EMA200 consistently<br>
            Price below EMA200 = bearish bias<br>
            Price above EMA200 = bullish bias<br>
            EMA200 highlighted in gold on chart</div>""",unsafe_allow_html=True)
        st.info("💡 Gold spikes heavily on USD news (NFP, FOMC, CPI). Use wider stops on news days. Best trading hours: London open and New York session.")

    with t2:
        st.markdown("### ₿ Bitcoin — How We Trade It")
        specialist_header("Bitcoin")
        st.markdown("""
**Why Bitcoin is special:**
BTC moves in massive impulses leaving huge Fair Value Gaps. These gaps ALWAYS get filled eventually.
RSI Divergences on BTC 4H are among the most reliable reversal signals in any market.
Round numbers ($60k, $65k, $70k, $75k, $80k) are extremely strong magnets.""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #f7931a'>
            <b>🕳️ Fair Value Gaps</b><br><br>
            BTC leaves massive FVGs during pumps/dumps<br>
            These always get filled — it's reliable<br>
            Enter when price returns to the gap<br>
            Stop: beyond the gap<br>
            Target: next resistance/support</div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #f7931a'>
            <b>⚡ RSI Divergence</b><br><br>
            BTC divergences on 4H are powerful<br>
            Bullish div at key support = strong BUY<br>
            Bearish div at key resistance = strong SELL<br>
            Best combined with FVG at same level<br>
            = very high probability reversal</div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #f7931a'>
            <b>🧱 Round Number S/R</b><br><br>
            $60k/$65k/$70k/$75k/$80k are magnets<br>
            BTC always tests these levels<br>
            Watch for OB or FVG at round numbers<br>
            = institutional + psychological level<br>
            = highest probability entry</div>""",unsafe_allow_html=True)
        st.info("💡 BTC reacts to risk sentiment and crypto news. Wider stops needed — BTC can wick 3-5% before reversing. Best on 4H and Daily charts.")

    with t3:
        st.markdown("### € EUR/USD — How We Trade It")
        specialist_header("EUR/USD")
        st.markdown("""
**Why EUR/USD is special:**
EUR/USD is the world's most liquid forex pair. Trends are clean and EMA alignment is highly reliable.
It has very clean Fair Value Gaps due to extreme liquidity — price fills them efficiently.
ADX readings during London/New York overlap are some of the strongest in forex.""")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #4488ff'>
            <b>📈 EMA Stack Trend</b><br><br>
            When 20>50>200 — pure uptrend<br>
            When 20 crosses above 50 with price above 200 = entry<br>
            EUR/USD trends last days/weeks<br>
            Most reliable on 4H chart<br>
            Trade pullbacks to EMA20</div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #4488ff'>
            <b>💪 ADX Confirmation</b><br><br>
            Wait for ADX above 25 before entering<br>
            ADX above 30 = strong trend, full size<br>
            ADX below 20 = ranging, avoid<br>
            Best during London/NY overlap<br>
            (8am-12pm EST)</div>""",unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='card' style='border-left:4px solid #4488ff'>
            <b>🕳️ Clean FVGs</b><br><br>
            EUR/USD FVGs fill very reliably<br>
            High liquidity = efficient price discovery<br>
            Enter on FVG retest in trend direction<br>
            Stop: beyond the FVG<br>
            Target: previous high/low</div>""",unsafe_allow_html=True)
        st.info("💡 EUR/USD is most active London open (3am EST) and New York open (8am EST). Avoid trading 5pm-midnight EST — low volume, choppy.")

    with t4:
        st.markdown("### 📖 How to Read Sparro FX AI Signals")
        st.markdown("**The 6 strategies and what each confirms:**")
        for name,(fn,ico,desc) in STRATS.items():
            is_smc="SMC" in name
            badge="<span class='smc-badge'>SMC</span>&nbsp;" if is_smc else ""
            st.markdown(f"""<div class='card'>
            <b>{ico} {name}</b>&nbsp;{badge}
            <span style='color:#8b949e'>— {desc}</span></div>""",unsafe_allow_html=True)
        st.markdown("""
**Confidence thresholds:**

| Agreement | Confidence | Action |
|---|---|---|
| 6/6 agree | 100% | Max size — extremely rare |
| 5/6 agree | 83% | Full size — STRONG signal |
| 4/6 agree | 67% | Half size — good signal |
| 3/6 agree | 50% | Wait — not enough alignment |

**Specialist pair rule:**
For Gold, Bitcoin and EUR/USD — their 3 best strategies count double.
This means when their specialist strategies agree, confidence is genuinely higher.

**Multi-Timeframe Rule:**
> All 3 timeframes agree → full size
> 2/3 agree → half size
> 1/3 → wait

**Auto Ticket Workflow:**
1. Open Pulse ⚡ — specialists shown first
2. Signal fires with 4+/6 strategies aligned
3. Check MTF confirmation
4. Hit Auto Ticket → journal automatically
5. Go to Tickets to close with Win/Loss/B-E
        """)

# ══════════════════════════════════════════════════════════════════════════════
# ABOUT
# ══════════════════════════════════════════════════════════════════════════════
elif pg=="About":
    st.title("ℹ️ About Sparro FX AI")
    st.markdown("""**Sparro FX AI** — 6 precision strategies, 3 specialist pairs.

**The 6 Strategies:**

| Strategy | Measures | Role |
|---|---|---|
| EMA Trend | Direction | Are we in an uptrend or downtrend? |
| ADX Strength | Trend strength | Is the trend strong enough to trade? |
| RSI + Divergence | Momentum | Is buying/selling pressure building or fading? |
| SMC Order Blocks | Institutional zones | Where did banks place their orders? |
| SMC Fair Value Gap | Price imbalances | Where must price return to balance? |
| Support/Resistance | Key levels | Are we at a good entry or a bad one? |

**The 3 Specialist Pairs:**

| Pair | Best Strategies | Why |
|---|---|---|
| 🥇 Gold | SMC OB + S/R + EMA200 | Institution-driven, respects round numbers |
| ₿ Bitcoin | FVG + Divergence + S/R | Massive FVGs, reliable divergences |
| € EUR/USD | EMA + ADX + FVG | Trend-following, clean FVGs, strong ADX |

For specialist pairs, their 3 best strategies count **2× in the confidence score** — making signals genuinely more meaningful.

⚠️ *Trade responsibly. Past signals do not guarantee future results.*""")

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
        c1,c2=st.columns(2)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>👑 Admin Password</b><br><span style='color:#8b949e;font-size:13px'>Only you. Never share.</span></div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #3fb950'>
            <b>⚡ Premium Password</b><br><span style='color:#8b949e;font-size:13px'>Share with subscribers. Change to revoke.</span></div>""",unsafe_allow_html=True)
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
