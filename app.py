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
  body, .main { background:#0d1117; color:#e6edf3 }
  .block-container { padding-top:1.5rem }
  .stTabs [data-baseweb="tab-list"] { gap:6px; background:#161b22; border-radius:12px; padding:6px }
  .stTabs [data-baseweb="tab"] { border-radius:8px; padding:8px 18px; color:#8b949e; font-weight:600 }
  .stTabs [aria-selected="true"] { background:linear-gradient(90deg,#0072ff,#00c6ff) !important; color:#fff !important }
  .stMetric { background:#161b22; border-radius:10px; padding:12px }
  .stProgress>div>div { background:linear-gradient(90deg,#00c6ff,#0072ff) }
  .tier-box { background:#161b22; border-radius:14px; padding:20px; text-align:center; border:2px solid #30363d }
  .tier-box.gold { border-color:#ffd200 }
  .card { background:#161b22; border-radius:12px; padding:16px; margin-bottom:10px; border:1px solid #30363d }
  .login-box { background:#161b22; border-radius:16px; padding:30px 26px; border:1px solid #30363d }
  .pulse-live { display:inline-block; width:10px; height:10px; background:#3fb950;
    border-radius:50%; margin-right:6px; animation:blink 1.2s infinite }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
  .news-trade-card { background:#161b22; border-radius:12px; padding:16px;
    margin-bottom:10px; border-left:4px solid #ffd200 }
  .smc-tag { background:#7c3aed; color:#fff; border-radius:6px;
    padding:2px 8px; font-size:11px; font-weight:700; margin-left:6px }
</style>
""", unsafe_allow_html=True)

# ════════ PERSISTENT LOGIN ════════
def make_token(account_type, email, ts):
    raw = f"{account_type}|{email}|{ts}|sparro_salt_2024"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def save_login(account_type, email, trial_start=None):
    ts = trial_start.isoformat() if trial_start else ""
    token = make_token(account_type, email, ts)
    st.query_params["session"] = f"{account_type}|{email}|{ts}|{token}"

def load_login():
    try:
        raw = st.query_params.get("session", "")
        if not raw: return None
        parts = raw.split("|")
        if len(parts) != 4: return None
        account_type, email, ts, token = parts
        if token != make_token(account_type, email, ts): return None
        trial_start = datetime.datetime.fromisoformat(ts) if ts else None
        return {"account_type": account_type, "email": email, "trial_start": trial_start}
    except: return None

def clear_login():
    st.query_params.clear()

# ════════ SESSION STATE ════════
DEFAULTS = {
    "logged_in": False, "account_type": None, "trial_start": None,
    "user_email": "", "trade_journal": [], "subscribers": [],
    "session_loaded": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.session_loaded:
    saved = load_login()
    if saved:
        st.session_state.update(logged_in=True, **saved)
    st.session_state.session_loaded = True

# ════════ CREDENTIALS ════════
def _secret(key, fallback):
    try:    return st.secrets.get(key, fallback)
    except: return fallback

ADMIN_PASSWORD   = _secret("ADMIN_PASSWORD",   "sparro_admin_2024")
PREMIUM_PASSWORD = _secret("PREMIUM_PASSWORD", "sparro_pro_2024")
FREE_PASSWORD    = _secret("FREE_PASSWORD",    "sparro_free")
TRIAL_HOURS      = 48

def trial_hours_left():
    if st.session_state.trial_start is None: return 0
    elapsed = (datetime.datetime.now() - st.session_state.trial_start).total_seconds() / 3600
    return max(0, TRIAL_HOURS - int(elapsed))

def is_premium_access():
    if st.session_state.account_type in ("premium", "admin"): return True
    if st.session_state.account_type == "trial" and trial_hours_left() > 0: return True
    return False

# ════════ LOGIN PAGE ════════
def show_login_page():
    st.markdown("""
    <div style='max-width:480px;margin:50px auto 0 auto;text-align:center'>
      <div style='font-size:64px'>🚀</div>
      <div style='font-size:38px;font-weight:900;background:linear-gradient(90deg,#00c6ff,#0072ff);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent'>Sparro FX AI</div>
      <div style='color:#8b949e;font-size:15px;margin-bottom:28px'>
        Professional AI-Powered Forex Signal Platform</div>
    </div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        tab1, tab2, tab3 = st.tabs(["🔑 Login", "🎁 Free 48hr Trial", "ℹ️ About"])

        with tab1:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.markdown("#### Welcome back 👋")
            email    = st.text_input("Email", placeholder="you@email.com", key="li_email")
            password = st.text_input("Password", type="password", placeholder="Your password", key="li_pass")
            remember = st.checkbox("Keep me logged in", value=True)
            if st.button("🔓 Login", use_container_width=True, type="primary"):
                pw = password.strip()
                atype = ("admin"   if pw == ADMIN_PASSWORD   else
                         "premium" if pw == PREMIUM_PASSWORD else
                         "free"    if pw == FREE_PASSWORD    else None)
                if atype:
                    st.session_state.update(logged_in=True, account_type=atype, user_email=email)
                    if remember: save_login(atype, email)
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Try the Free Trial or contact us.")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:#8b949e;font-size:13px;margin-top:10px'>No account? Use <b>Free 48hr Trial</b> above.</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;margin-bottom:16px'>
              <span style='background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;
              border-radius:20px;padding:6px 18px;font-weight:700'>🎁 48 Hours FREE — Full Premium</span>
            </div>""", unsafe_allow_html=True)
            st.markdown("""No card needed. Full access for 48 hours:
- ✅ All 10 assets · 8 pro strategies + SMC
- ✅ ⚡ Pulse Signal live feed
- ✅ News Trading setups
- ✅ Charts with Entry / SL / TP
- ✅ AI News Analysis""")
            trial_email = st.text_input("Email", placeholder="you@email.com", key="tr_email")
            trial_name  = st.text_input("Name",  placeholder="First name",    key="tr_name")
            if st.button("🚀 Start Free Trial", use_container_width=True, type="primary"):
                if not trial_email or "@" not in trial_email:
                    st.error("❌ Valid email required.")
                elif not trial_name.strip():
                    st.error("❌ Name required.")
                else:
                    ts = datetime.datetime.now()
                    st.session_state.update(logged_in=True, account_type="trial",
                                            trial_start=ts, user_email=trial_email)
                    save_login("trial", trial_email, ts)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:#8b949e;font-size:13px;margin-top:10px'>After trial, upgrade for <b>$15/mo</b>.</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("""<div class='login-box'>
            <h4 style='margin-top:0'>What is Sparro FX AI?</h4>
            <p style='color:#8b949e'>Professional forex signal platform — 8 institutional-grade strategies
            including Smart Money Concepts (SMC), live Pulse Signal feed, news trading and real-time analysis.</p>
            <b>🆓 Free</b> — 5 assets, basic signals<br><br>
            <b>🎁 Trial (48h)</b> — full premium, no card<br><br>
            <b>⚡ Premium $15/mo</b> — everything unlocked<br><br>
            <hr style='border-color:#30363d'>
            <span style='color:#8b949e;font-size:12px'>Trade responsibly. Past signals do not guarantee future results.</span>
            </div>""", unsafe_allow_html=True)

# ════════ GATE ════════
if not st.session_state.logged_in:
    show_login_page(); st.stop()

if st.session_state.account_type == "trial" and trial_hours_left() == 0:
    st.error("⏰ Your 48-hour free trial has ended.")
    st.markdown("### Upgrade to Premium — $15/mo")
    st.markdown("Contact us to get your premium password and keep full access.")
    if st.button("🔓 Login with premium password"):
        clear_login(); st.session_state.logged_in = False; st.rerun()
    st.stop()

premium = is_premium_access()
atype   = st.session_state.account_type

# ════════ ASSETS ════════
ALL_PAIRS = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])
pairs = ALL_PAIRS if premium else FREE_PAIRS

# ════════════════════════════════════════════════════════════
# STRATEGY ENGINE — 8 professional strategies incl. SMC
# ════════════════════════════════════════════════════════════
def fetch_data(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

# 1. EMA TREND ─────────────────────────────────────────────
def strategy_ema_trend(df):
    c=df["Close"]
    e20=c.ewm(span=20).mean().iloc[-1]
    e50=c.ewm(span=50).mean().iloc[-1]
    e200=c.ewm(span=200).mean().iloc[-1]
    if e20>e50 and e50>e200: return "BUY",  "EMA20 > EMA50 > EMA200 — full bullish stack"
    if e20<e50 and e50<e200: return "SELL", "EMA20 < EMA50 < EMA200 — full bearish stack"
    if e20>e200: return "BUY",  "Price above EMA200 — long-term bullish bias"
    if e20<e200: return "SELL", "Price below EMA200 — long-term bearish bias"
    return "NEUTRAL","EMA stack mixed — no clear trend"

# 2. RSI MOMENTUM ──────────────────────────────────────────
def strategy_rsi(df):
    c=df["Close"]; d=c.diff()
    g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
    rsi=(100-(100/(1+(g/l)))).iloc[-1]
    if rsi>65:   return "BUY",  f"RSI={round(rsi,1)} — strong bullish momentum"
    if rsi>55:   return "BUY",  f"RSI={round(rsi,1)} — moderate bullish momentum"
    if rsi<35:   return "SELL", f"RSI={round(rsi,1)} — strong bearish momentum"
    if rsi<45:   return "SELL", f"RSI={round(rsi,1)} — moderate bearish momentum"
    return "NEUTRAL",f"RSI={round(rsi,1)} — neutral zone (45-55)"

# 3. MACD CROSSOVER ────────────────────────────────────────
def strategy_macd(df):
    c=df["Close"]
    m=c.ewm(span=12).mean()-c.ewm(span=26).mean()
    s=m.ewm(span=9).mean(); h=m-s
    macd_val=round(float(m.iloc[-1]),6); sig_val=round(float(s.iloc[-1]),6)
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2] and m.iloc[-1]>0:
        return "BUY",  f"MACD bullish crossover above zero — strong signal"
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2]:
        return "BUY",  f"MACD bullish crossover — momentum turning up"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2] and m.iloc[-1]<0:
        return "SELL", f"MACD bearish crossover below zero — strong signal"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2]:
        return "SELL", f"MACD bearish crossover — momentum turning down"
    return "NEUTRAL","MACD no clear crossover"

# 4. SUPPORT & RESISTANCE ──────────────────────────────────
def strategy_sr(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    # Use 20-period for more accurate S/R
    res=float(h.rolling(20).max().iloc[-1]); sup=float(l.rolling(20).min().iloc[-1])
    mid=(res+sup)/2; zone=(res-sup)*0.12
    if p>=res-zone:     return "SELL", f"At key resistance {round(res,4)} — high rejection probability"
    if p<=sup+zone:     return "BUY",  f"At key support {round(sup,4)} — high bounce probability"
    if p>mid+zone:      return "BUY",  f"Above midrange {round(mid,4)} — bullish bias"
    if p<mid-zone:      return "SELL", f"Below midrange {round(mid,4)} — bearish bias"
    return "NEUTRAL",   f"Mid-range — S={round(sup,4)} R={round(res,4)}"

# 5. ADX TREND STRENGTH ────────────────────────────────────
def strategy_adx(df):
    """ADX measures trend strength — above 25 means strong trend."""
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        # True Range
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        # Directional Movement
        up_move=h.diff(); down_move=-l.diff()
        pdm=up_move.where((up_move>down_move)&(up_move>0),0)
        ndm=down_move.where((down_move>up_move)&(down_move>0),0)
        period=14
        atr=tr.ewm(span=period).mean()
        pdi=100*(pdm.ewm(span=period).mean()/atr)
        ndi=100*(ndm.ewm(span=period).mean()/atr)
        dx=100*(pdi-ndi).abs()/(pdi+ndi)
        adx=dx.ewm(span=period).mean().iloc[-1]
        pdi_val=pdi.iloc[-1]; ndi_val=ndi.iloc[-1]

        if adx>=30 and pdi_val>ndi_val: return "BUY",  f"ADX={round(adx,1)} — strong uptrend confirmed"
        if adx>=30 and ndi_val>pdi_val: return "SELL", f"ADX={round(adx,1)} — strong downtrend confirmed"
        if adx>=20 and pdi_val>ndi_val: return "BUY",  f"ADX={round(adx,1)} — moderate uptrend"
        if adx>=20 and ndi_val>pdi_val: return "SELL", f"ADX={round(adx,1)} — moderate downtrend"
        return "NEUTRAL",f"ADX={round(adx,1)} — weak trend, ranging market (below 20)"
    except: return "NEUTRAL","ADX calculation error"

# 6. STOCHASTIC OSCILLATOR ─────────────────────────────────
def strategy_stochastic(df):
    """Stochastic — overbought above 80, oversold below 20."""
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        period=14; smooth=3
        low_min=l.rolling(period).min(); high_max=h.rolling(period).max()
        k=100*(c-low_min)/(high_max-low_min)
        d=k.rolling(smooth).mean()
        k_val=k.iloc[-1]; d_val=d.iloc[-1]
        k_prev=k.iloc[-2]; d_prev=d.iloc[-2]

        # Oversold + bullish crossover
        if k_val<20 and d_val<20:
            return "BUY", f"Stoch K={round(k_val,1)} D={round(d_val,1)} — oversold, strong BUY zone"
        if k_val<35 and k_val>k_prev and k_val>d_val:
            return "BUY", f"Stoch K={round(k_val,1)} — bullish crossover from low"
        # Overbought + bearish crossover
        if k_val>80 and d_val>80:
            return "SELL",f"Stoch K={round(k_val,1)} D={round(d_val,1)} — overbought, strong SELL zone"
        if k_val>65 and k_val<k_prev and k_val<d_val:
            return "SELL",f"Stoch K={round(k_val,1)} — bearish crossover from high"
        return "NEUTRAL",f"Stoch K={round(k_val,1)} D={round(d_val,1)} — neutral zone"
    except: return "NEUTRAL","Stochastic calculation error"

# 7. SMC ORDER BLOCKS ──────────────────────────────────────
def strategy_smc_orderblock(df):
    """
    Smart Money Concepts — Order Blocks.
    An order block is the last bearish candle before a bullish impulse (bullish OB)
    or the last bullish candle before a bearish impulse (bearish OB).
    Price returning to these zones is a high-probability entry.
    """
    try:
        o=df["Open"]; h=df["High"]; l=df["Low"]; c=df["Close"]
        current_price=float(c.iloc[-1])

        bullish_obs=[]; bearish_obs=[]
        lookback=min(50,len(df)-3)

        for i in range(2, lookback):
            idx=-i
            # Bullish OB: bearish candle followed by strong bullish move
            if c.iloc[idx]<o.iloc[idx]:  # bearish candle
                # Check if followed by bullish impulse (next 2 candles)
                if (c.iloc[idx+1]>o.iloc[idx+1] and
                    c.iloc[idx+2]>o.iloc[idx+2] and
                    c.iloc[idx+2]>h.iloc[idx]):  # broke above OB high
                    ob_high=float(h.iloc[idx])
                    ob_low =float(l.iloc[idx])
                    bullish_obs.append((ob_low, ob_high))

            # Bearish OB: bullish candle followed by strong bearish move
            if c.iloc[idx]>o.iloc[idx]:  # bullish candle
                if (c.iloc[idx+1]<o.iloc[idx+1] and
                    c.iloc[idx+2]<o.iloc[idx+2] and
                    c.iloc[idx+2]<l.iloc[idx]):  # broke below OB low
                    ob_high=float(h.iloc[idx])
                    ob_low =float(l.iloc[idx])
                    bearish_obs.append((ob_low, ob_high))

        # Check if price is at a bullish OB (buy zone)
        for ob_low,ob_high in bullish_obs[:3]:
            if ob_low <= current_price <= ob_high*1.002:
                return "BUY", f"SMC Bullish Order Block {round(ob_low,4)}-{round(ob_high,4)} — institutional buy zone"

        # Check if price is at a bearish OB (sell zone)
        for ob_low,ob_high in bearish_obs[:3]:
            if ob_low*0.998 <= current_price <= ob_high:
                return "SELL",f"SMC Bearish Order Block {round(ob_low,4)}-{round(ob_high,4)} — institutional sell zone"

        # Price approaching OB
        for ob_low,ob_high in bullish_obs[:3]:
            if current_price <= ob_high*1.01 and current_price > ob_high:
                return "BUY", f"SMC Approaching Bullish OB at {round(ob_low,4)}-{round(ob_high,4)}"

        for ob_low,ob_high in bearish_obs[:3]:
            if current_price >= ob_low*0.99 and current_price < ob_low:
                return "SELL",f"SMC Approaching Bearish OB at {round(ob_low,4)}-{round(ob_high,4)}"

        return "NEUTRAL","SMC No active order blocks near price"
    except: return "NEUTRAL","SMC Order Block — insufficient data"

# 8. SMC FAIR VALUE GAP ────────────────────────────────────
def strategy_smc_fvg(df):
    """
    Smart Money Concepts — Fair Value Gap (FVG) / Imbalance.
    An FVG occurs when there is a gap between candle 1 high and candle 3 low (bullish)
    or candle 1 low and candle 3 high (bearish). Price tends to return to fill these gaps.
    """
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        current_price=float(c.iloc[-1])

        bullish_fvgs=[]; bearish_fvgs=[]
        lookback=min(40,len(df)-3)

        for i in range(2,lookback):
            idx=-i
            # Bullish FVG: gap between candle[-i-1] high and candle[-i+1] low
            prev_high=float(h.iloc[idx-1])
            next_low =float(l.iloc[idx+1])
            if next_low > prev_high:  # gap exists
                gap_size=(next_low-prev_high)/prev_high
                if gap_size>0.001:  # min 0.1% gap
                    bullish_fvgs.append((prev_high,next_low,gap_size))

            # Bearish FVG: gap between candle[-i-1] low and candle[-i+1] high
            prev_low =float(l.iloc[idx-1])
            next_high=float(h.iloc[idx+1])
            if prev_low > next_high:  # gap exists
                gap_size=(prev_low-next_high)/prev_low
                if gap_size>0.001:
                    bearish_fvgs.append((next_high,prev_low,gap_size))

        # Price inside or near a bullish FVG (unfilled — good buy)
        for fvg_low,fvg_high,gap in bullish_fvgs[:4]:
            if fvg_low<=current_price<=fvg_high:
                return "BUY", f"SMC Bullish FVG {round(fvg_low,4)}-{round(fvg_high,4)} — price filling imbalance"
            if current_price<=fvg_low*1.005:
                return "BUY", f"SMC Bullish FVG above at {round(fvg_low,4)}-{round(fvg_high,4)} — magnet zone"

        # Price inside or near a bearish FVG
        for fvg_low,fvg_high,gap in bearish_fvgs[:4]:
            if fvg_low<=current_price<=fvg_high:
                return "SELL",f"SMC Bearish FVG {round(fvg_low,4)}-{round(fvg_high,4)} — price filling imbalance"
            if current_price>=fvg_high*0.995:
                return "SELL",f"SMC Bearish FVG below at {round(fvg_low,4)}-{round(fvg_high,4)} — magnet zone"

        return "NEUTRAL","SMC No active Fair Value Gaps near price"
    except: return "NEUTRAL","SMC FVG — insufficient data"

# ── Strategy registry ────────────────────────────────────────
STRATEGIES = {
    "EMA Trend":              strategy_ema_trend,
    "RSI Momentum":           strategy_rsi,
    "MACD Crossover":         strategy_macd,
    "Support / Resistance":   strategy_sr,
    "ADX Trend Strength":     strategy_adx,
    "Stochastic Oscillator":  strategy_stochastic,
    "SMC Order Blocks":       strategy_smc_orderblock,
    "SMC Fair Value Gap":     strategy_smc_fvg,
}

SMC_STRATEGIES = {"SMC Order Blocks","SMC Fair Value Gap"}

def run_all_strategies(symbol, period="6mo"):
    df=fetch_data(symbol,period)
    if df is None: return {},0,"ERROR"
    results={}
    for name,fn in STRATEGIES.items():
        try:    results[name]=fn(df)
        except: results[name]=("NEUTRAL","Error")
    buys =sum(1 for s,_ in results.values() if s=="BUY")
    sells=sum(1 for s,_ in results.values() if s=="SELL")
    total=len(results)
    if buys>sells:   conf=round(buys/total*100);  sig="STRONG BUY"  if buys>=6  else "BUY"
    elif sells>buys: conf=round(sells/total*100); sig="STRONG SELL" if sells>=6 else "SELL"
    else:            conf=50; sig="WAIT"
    return results,conf,sig

def get_trade_setup(symbol, direction):
    try:
        df=fetch_data(symbol,"3mo"); c=df["Close"]; h=df["High"]; l=df["Low"]; p=float(c.iloc[-1])
        tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); risk=atr*1.5
        if "BUY" in direction: return p,p-risk,p+risk,p+risk*2,p+risk*3,round(atr,5)
        else:                  return p,p+risk,p-risk,p-risk*2,p-risk*3,round(atr,5)
    except: return None,None,None,None,None,None

# ════════ SIGNAL BANNER ════════
def show_signal_banner(sig, asset, conf):
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

# ════════ PRICE CHART ════════
def show_price_chart(symbol, pair_name, signal, entry, sl, tp1, tp2):
    df=fetch_data(symbol,"3mo","1d")
    if df is None: st.warning("Chart unavailable."); return
    close=df["Close"]; ema20=close.ewm(span=20).mean()
    ema50=close.ewm(span=50).mean(); ema200=close.ewm(span=200).mean()
    res=float(df["High"].rolling(20).max().iloc[-1])
    sup=float(df["Low"].rolling(20).min().iloc[-1])
    dates=df.index; fig=go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],
            low=df["Low"],close=close,name="Price",
            increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates,y=close,name="Price",line=dict(color="#58a6ff",width=2)))
    fig.add_trace(go.Scatter(x=dates,y=ema20, name="EMA20", line=dict(color="#ffd700",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema50, name="EMA50", line=dict(color="#ff7f50",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema200,name="EMA200",line=dict(color="#da70d6",width=1,dash="dash")))
    fig.add_hline(y=res,line_color="#f85149",line_dash="dash",
        annotation_text=f"Resistance {round(res,4)}",annotation_position="right")
    fig.add_hline(y=sup,line_color="#3fb950",line_dash="dash",
        annotation_text=f"Support {round(sup,4)}",annotation_position="right")
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
    lp=float(close.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[lp],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in signal else "triangle-down",
                    size=14,color="#3fb950" if "BUY" in signal else "#f85149"),name="Signal"))
    fig.update_layout(title=f"{pair_name}",plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),
        legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
        height=420,margin=dict(l=50,r=110,t=40,b=30))
    st.plotly_chart(fig,use_container_width=True)

    # Why take this trade
    pve20="above" if lp>float(ema20.iloc[-1]) else "below"
    pve200="above" if lp>float(ema200.iloc[-1]) else "below"
    trend="uptrend" if float(ema20.iloc[-1])>float(ema200.iloc[-1]) else "downtrend"
    ma=float(close.iloc[-22]) if len(close)>22 else float(close.iloc[0])
    cp=round((lp-ma)/ma*100,2); cs=f"up {cp}%" if cp>0 else f"down {abs(cp)}%"
    slope="rising" if float(ema20.iloc[-1])-float(ema20.iloc[-5])>0 else "falling"
    ta=(("BUY" in signal and trend=="uptrend") or ("SELL" in signal and trend=="downtrend"))
    nr=abs(lp-res)/lp<0.005; ns=abs(lp-sup)/lp<0.005
    zn=("⚠️ Near resistance" if nr else "✅ Near support — bounce zone" if ns else "📊 Mid range")
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
        <b>📈 Price Context</b><br><br>
        Moved <b>{cs}</b> over past 30 days<br>
        Short-term: <b>{"bullish" if pve20=="above" else "bearish"}</b> (price {pve20} EMA20)<br>
        Long-term: <b>{"bullish" if pve200=="above" else "bearish"}</b> (price {pve200} EMA200)<br>
        EMA20 is <b>{slope}</b> — momentum {"building" if slope=="rising" else "weakening"}<br>
        Overall: <b>{trend.upper()}</b>
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
        <b>🎯 Trade Reasoning</b><br><br>
        Signal: <b>{signal}</b><br>
        Resistance: <b>{round(res,4)}</b> &nbsp;|&nbsp; Support: <b>{round(sup,4)}</b><br>
        Position: {zn}<br><br>
        {"✅ Trend + signal AGREE — high probability setup" if ta else "⚠️ Counter-trend — reduce position size"}
        </div>""",unsafe_allow_html=True)

# ════════ NEWS ════════
def fetch_forex_news():
    try:
        r=requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",timeout=8)
        if r.status_code==200:
            return pd.DataFrame([{
                "Time":e.get("date","")[:16].replace("T"," "),"Currency":e.get("currency",""),
                "Event":e.get("title",""),"Impact":e.get("impact",""),
                "Forecast":e.get("forecast","—"),"Previous":e.get("previous","—")
            } for e in r.json()[:30]])
    except: pass
    return pd.DataFrame([
        {"Time":"Today 08:30","Currency":"USD","Event":"Non-Farm Payrolls","Impact":"High","Forecast":"180K","Previous":"175K"},
        {"Time":"Today 10:00","Currency":"EUR","Event":"ECB Rate Decision","Impact":"High","Forecast":"4.5%","Previous":"4.5%"},
        {"Time":"Today 13:30","Currency":"GBP","Event":"CPI y/y","Impact":"Medium","Forecast":"3.1%","Previous":"3.4%"},
        {"Time":"Tomorrow 14:00","Currency":"USD","Event":"FOMC Minutes","Impact":"High","Forecast":"—","Previous":"—"},
        {"Time":"Tomorrow 09:00","Currency":"GBP","Event":"GDP m/m","Impact":"High","Forecast":"0.2%","Previous":"0.1%"},
    ])

NEWS_PAIRS = {
    "USD":["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CHF","USD/CAD","Gold (XAU/USD)"],
    "EUR":["EUR/USD"],"GBP":["GBP/USD"],"JPY":["USD/JPY"],
    "AUD":["AUD/USD"],"CHF":["USD/CHF"],"CAD":["USD/CAD"],"XAU":["Gold (XAU/USD)"],
}

def analyse_news_with_ai(news_df, pair):
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json",
                     "x-api-key":_secret("ANTHROPIC_API_KEY",""),
                     "anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":700,
                  "messages":[{"role":"user","content":
                    f"You are a professional forex news trader. Asset: {pair}\n\n"
                    f"Calendar:\n{news_df.to_string(index=False)}\n\n"
                    "Give: 1) Which events affect this pair most? 2) Expected direction after each event? "
                    "3) Best time to trade (before/after)? 4) Risk level? 5) Quick actionable trade plan. "
                    "Be specific. Use bullet points."}]},timeout=30)
        if r.status_code==200: return r.json()["content"][0]["text"]
        return "AI unavailable — add ANTHROPIC_API_KEY in Streamlit secrets."
    except Exception as e: return f"Error: {e}"

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""<div style='text-align:center;font-size:26px;font-weight:900;
    background:linear-gradient(90deg,#00c6ff,#0072ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent'>🚀 Sparro FX AI</div>""",
    unsafe_allow_html=True)
    st.divider()

    if atype=="admin":
        st.success("👑 Admin")
    elif atype=="premium":
        st.success("⚡ Premium Active")
    elif atype=="trial":
        h=trial_hours_left()
        st.warning(f"🎁 Trial — {h}h left")
        if h<=12: st.error("⏰ Upgrade now!")
    elif atype=="free":
        st.info("🆓 Free Plan")
        if st.button("⚡ Upgrade — $15/mo",use_container_width=True):
            st.info("Contact us for your premium password.")

    if st.session_state.user_email:
        st.caption(f"👤 {st.session_state.user_email}")
    st.divider()

    page=st.radio("",["🏠 Dashboard","📓 Trade Journal","📈 Performance","💰 Risk Calculator"],
                  label_visibility="collapsed")

    with st.expander("≫ More"):
        extra=st.radio("",["💎 Pricing","👑 Admin Panel" if atype=="admin" else "ℹ️ About"],
                       label_visibility="collapsed")
        page=extra

    st.divider()
    if st.button("🚪 Logout",use_container_width=True):
        clear_login()
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
if "Dashboard" in page:
    now=datetime.datetime.utcnow().strftime("%A %d %b %Y  •  %H:%M UTC")
    st.markdown(f"""<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:16px'>
      <div style='font-size:24px;font-weight:900'>📊 Sparro FX AI — Dashboard</div>
      <div style='color:#8b949e;font-size:13px'>🕐 {now}</div>
    </div>""",unsafe_allow_html=True)

    if not premium:
        st.warning("🔒 Free plan — 5 assets only. **Upgrade for full access.**")

    tab_pulse,tab_scanner,tab_totd,tab_deep,tab_news=st.tabs([
        "⚡ Pulse Signal","📊 Scanner","🏆 Trade of the Day","🔬 Deep Analysis","🗞️ News Trading"])

    # ══ PULSE SIGNAL ══════════════════════════════════════════
    with tab_pulse:
        st.markdown("""<div style='display:flex;align-items:center;margin-bottom:6px'>
          <span class='pulse-live'></span>
          <span style='font-size:20px;font-weight:800'>Live Pulse Signal</span>
        </div>
        <div style='color:#8b949e;font-size:13px;margin-bottom:18px'>
        Only STRONG signals with 70%+ confidence appear here. These are your highest-probability setups.</div>""",
        unsafe_allow_html=True)

        if not premium:
            st.error("🔒 Upgrade to see live Pulse Signals.")
        else:
            cr,cb=st.columns([3,1])
            with cb:
                if st.button("🔄 Refresh",use_container_width=True): st.rerun()
            with cr:
                st.caption(f"Last scan: {datetime.datetime.now().strftime('%H:%M:%S')}")

            with st.spinner("🔍 Scanning all markets..."):
                pulse_signals=[]
                for name,sym in ALL_PAIRS.items():
                    strats,conf,sig=run_all_strategies(sym)
                    if sig in ("STRONG BUY","STRONG SELL") and conf>=70:
                        entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
                        if entry:
                            pulse_signals.append({"name":name,"sym":sym,"sig":sig,"conf":conf,
                                "entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"strats":strats})
                pulse_signals.sort(key=lambda x:x["conf"],reverse=True)

            if not pulse_signals:
                st.markdown("""<div style='background:#161b22;border:1px solid #30363d;
                border-radius:14px;padding:50px;text-align:center'>
                <div style='font-size:40px'>😴</div>
                <div style='font-size:18px;color:#8b949e;margin-top:12px'>No strong signals right now</div>
                <div style='color:#8b949e;font-size:13px;margin-top:6px'>Market is quiet. Check back soon.</div>
                </div>""",unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#3fb950;font-weight:700;margin-bottom:12px'>✅ {len(pulse_signals)} strong signal(s) active</div>",unsafe_allow_html=True)
                for p in pulse_signals:
                    is_buy="BUY" in p["sig"]
                    border="#3fb950" if is_buy else "#f85149"
                    bg="linear-gradient(135deg,#0d3b20,#0d1f14)" if is_buy else "linear-gradient(135deg,#3b0d0d,#1f0d0d)"
                    icon="🚀" if is_buy else "📉"
                    cf_color="#3fb950" if p["conf"]>=80 else "#ffd700" if p["conf"]>=65 else "#f85149"
                    direction="BUY" if is_buy else "SELL"
                    agreeing=[n for n,(s,_) in p["strats"].items() if s==direction]
                    smc_active=any(n in SMC_STRATEGIES for n in agreeing)

                    st.markdown(f"""<div style='background:{bg};border:2px solid {border};
                    border-radius:14px;padding:18px;margin-bottom:14px;box-shadow:0 0 16px {border}44'>
                      <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px'>
                        <div>
                          <div style='font-size:20px;font-weight:900;color:{border}'>{icon} {p["sig"]}
                            {"&nbsp;<span style='background:#7c3aed;color:#fff;border-radius:6px;padding:2px 8px;font-size:11px'>SMC ✓</span>" if smc_active else ""}
                          </div>
                          <div style='font-size:22px;font-weight:700;color:#e6edf3'>{p["name"]}</div>
                        </div>
                        <div style='text-align:right'>
                          <div style='font-size:32px;font-weight:900;color:{cf_color}'>{p["conf"]}%</div>
                          <div style='font-size:11px;color:#8b949e'>CONFIDENCE</div>
                        </div>
                      </div>
                      <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px'>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e;margin-bottom:4px'>ENTRY</div>
                          <div style='font-size:13px;font-weight:700;color:#e6edf3'>{round(p["entry"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e;margin-bottom:4px'>STOP LOSS</div>
                          <div style='font-size:13px;font-weight:700;color:#f85149'>{round(p["sl"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e;margin-bottom:4px'>TP1</div>
                          <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp1"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e;margin-bottom:4px'>TP2</div>
                          <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp2"],5)}</div>
                        </div>
                        <div style='background:#00000044;border-radius:8px;padding:10px;text-align:center'>
                          <div style='font-size:10px;color:#8b949e;margin-bottom:4px'>TP3</div>
                          <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp3"],5)}</div>
                        </div>
                      </div>
                      <div style='font-size:12px;color:#8b949e'>
                        ✅ {" &nbsp;·&nbsp; ".join(agreeing)}
                      </div>
                    </div>""",unsafe_allow_html=True)
                    with st.expander(f"📊 View {p['name']} Chart"):
                        show_price_chart(p["sym"],p["name"],p["sig"],p["entry"],p["sl"],p["tp1"],p["tp2"])

    # ══ SCANNER ═══════════════════════════════════════════════
    with tab_scanner:
        st.markdown("### 📊 Market Scanner")
        st.markdown("<div style='color:#8b949e;font-size:13px;margin-bottom:16px'>All assets scanned across 8 professional strategies including SMC.</div>",unsafe_allow_html=True)
        results=[]; prog=st.progress(0); items=list(pairs.items())
        for i,(name,sym) in enumerate(items):
            strats,conf,sig=run_all_strategies(sym)
            buys=sum(1 for s,_ in strats.values() if s=="BUY")
            sells=sum(1 for s,_ in strats.values() if s=="SELL")
            smc_b=sum(1 for n,(s,_) in strats.items() if s=="BUY" and n in SMC_STRATEGIES)
            smc_s=sum(1 for n,(s,_) in strats.items() if s=="SELL" and n in SMC_STRATEGIES)
            results.append({"Asset":name,"Signal":sig,
                "Confidence":f"{conf}%" if premium else "🔒",
                "Buy Votes":buys if premium else "🔒",
                "Sell Votes":sells if premium else "🔒",
                "SMC":f"✅ {max(smc_b,smc_s)}/2" if premium else "🔒"})
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

    # ══ TRADE OF THE DAY ══════════════════════════════════════
    with tab_totd:
        st.markdown("### 🏆 Trade of the Day")
        st.markdown("<div style='color:#8b949e;font-size:13px;margin-bottom:16px'>Highest-confidence setup across all 10 assets today.</div>",unsafe_allow_html=True)
        if not premium:
            st.error("🔒 Premium only.")
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
                st.markdown("---")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
                c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
                if st.button("➕ Add to Journal",key="totd_j"):
                    st.session_state.trade_journal.append({"Date":str(datetime.date.today()),
                        "Asset":best["name"],"Signal":best["sig"],"Entry":entry,
                        "SL":sl,"TP1":tp1,"Confidence":best["conf"],"Result":"Open","Notes":""})
                    st.success("✅ Added!")
                st.markdown("---")
                show_price_chart(best["sym"],best["name"],best["sig"],entry,sl,tp1,tp2)

    # ══ DEEP ANALYSIS ═════════════════════════════════════════
    with tab_deep:
        st.markdown("### 🔬 Deep Strategy Analysis")
        st.markdown("<div style='color:#8b949e;font-size:13px;margin-bottom:16px'>See exactly what all 8 strategies say about any asset — including SMC Order Blocks and Fair Value Gaps.</div>",unsafe_allow_html=True)
        if not premium:
            st.error("🔒 Premium only.")
        else:
            selected=st.selectbox("Choose Asset",list(ALL_PAIRS.keys()),key="deep_sel")
            sym=ALL_PAIRS[selected]
            with st.spinner(f"Analysing {selected}..."):
                strats,conf,sig=run_all_strategies(sym)
            show_signal_banner(sig,selected,conf)
            c1,c2,c3=st.columns(3)
            c1.metric("Signal",sig); c2.metric("Confidence",f"{conf}%"); c3.metric("Strategies","8")
            st.progress(conf/100)
            st.markdown("---")
            for name,(s,reason) in strats.items():
                color="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
                icon ="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
                sr=reason.replace("<","&lt;").replace(">","&gt;")
                is_smc=name in SMC_STRATEGIES
                smc_badge="<span class='smc-tag'>SMC</span>" if is_smc else ""
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:10px 14px;
                margin-bottom:8px;border-left:4px solid {color}{"};border-right:2px solid #7c3aed" if is_smc else "}"}'>
                <b>{icon} {name}</b>{smc_badge} &nbsp;
                <span style='background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px'>{s}</span>
                <br><small style='color:#8b949e'>{sr}</small></div>""",unsafe_allow_html=True)
            buys=sum(1 for s,_ in strats.values() if s=="BUY")
            sells=sum(1 for s,_ in strats.values() if s=="SELL")
            c1,c2,c3=st.columns(3)
            c1.metric("🟢 Buy Votes",buys); c2.metric("🔴 Sell Votes",sells); c3.metric("🟡 Neutral",8-buys-sells)
            entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
            if entry and sig!="WAIT":
                st.markdown("---")
                c1,c2,c3,c4,c5=st.columns(5)
                c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
                c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
                if conf>=75:   st.success(f"✅ HIGH confidence — {conf}% agree")
                elif conf>=60: st.warning(f"⚠️ MODERATE — {conf}%. Reduce position size.")
                else:          st.error(f"🚨 LOW — {conf}%. Consider waiting.")
                st.markdown("---")
                show_price_chart(sym,selected,sig,entry,sl,tp1,tp2)

    # ══ NEWS TRADING ══════════════════════════════════════════
    with tab_news:
        st.markdown("### 🗞️ News Trading")
        st.markdown("<div style='color:#8b949e;font-size:13px;margin-bottom:16px'>Trade around high-impact economic events — know what's coming, which pairs move and how to position.</div>",unsafe_allow_html=True)
        if not premium:
            st.error("🔒 Premium only.")
        else:
            with st.spinner("Loading calendar..."):
                news_df=fetch_forex_news()

            st.markdown("#### 📅 This Week's Calendar")
            if "Impact" in news_df.columns:
                high_ev=news_df[news_df["Impact"]=="High"]
                med_ev =news_df[news_df["Impact"]=="Medium"]
                if not high_ev.empty:
                    st.markdown("**🔴 High Impact Events:**")
                    for _,row in high_ev.iterrows():
                        curr=row.get("Currency",""); affected=NEWS_PAIRS.get(curr,[curr+" pairs"])
                        st.markdown(f"""<div class='news-trade-card'>
                        <div style='display:flex;justify-content:space-between'>
                          <div><span style='background:#f85149;color:#fff;border-radius:6px;
                          padding:2px 8px;font-size:11px;font-weight:700'>HIGH</span>
                          &nbsp;<b>{row.get("Event","")}</b></div>
                          <div style='color:#8b949e;font-size:13px'>{row.get("Time","")}</div>
                        </div>
                        <div style='margin-top:8px;font-size:13px;color:#8b949e'>
                          Currency: <b style='color:#ffd200'>{curr}</b> &nbsp;|&nbsp;
                          Forecast: <b style='color:#e6edf3'>{row.get("Forecast","—")}</b> &nbsp;|&nbsp;
                          Previous: <b style='color:#e6edf3'>{row.get("Previous","—")}</b>
                        </div>
                        <div style='margin-top:6px;font-size:12px;color:#58a6ff'>
                          📌 Watch: {" · ".join(affected)}</div>
                        </div>""",unsafe_allow_html=True)
                if not med_ev.empty:
                    with st.expander(f"🟡 Medium Impact ({len(med_ev)})"):
                        for _,row in med_ev.iterrows():
                            st.markdown(f"**{row.get('Time','')}** — {row.get('Currency','')} {row.get('Event','')} | Forecast: {row.get('Forecast','—')}")
            else:
                st.dataframe(news_df,use_container_width=True,hide_index=True)

            st.markdown("---")
            st.markdown("#### 🎯 News Trade Setup Generator")
            c1,c2=st.columns([2,1])
            with c1: news_pair=st.selectbox("Select pair",list(ALL_PAIRS.keys()),key="np")
            with c2: st.markdown("<br>",unsafe_allow_html=True); run_n=st.button("🔍 Generate Plan",use_container_width=True)

            if run_n:
                sym=ALL_PAIRS[news_pair]
                with st.spinner(f"Building news trade plan for {news_pair}..."):
                    strats,conf,sig=run_all_strategies(sym)
                    entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
                    ai_txt=analyse_news_with_ai(news_df,news_pair)
                show_signal_banner(sig,news_pair,conf)
                c1,c2=st.columns(2)
                with c1:
                    st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
                    <b>📊 Technical Bias</b><br><br>Signal: <b>{sig}</b> &nbsp;|&nbsp; Confidence: <b>{conf}%</b><br><br>
                    {"✅ Technical aligns — look for confirmation after news" if sig!="WAIT" else "⚠️ No clear bias — wait for news reaction then enter"}
                    </div>""",unsafe_allow_html=True)
                with c2:
                    if entry and sig!="WAIT":
                        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
                        <b>🎯 Trade Levels</b><br><br>
                        Entry: <b>{round(entry,5)}</b><br>
                        SL: <b style='color:#f85149'>{round(sl,5)}</b><br>
                        TP1: <b style='color:#3fb950'>{round(tp1,5)}</b> &nbsp;|&nbsp; TP2: <b style='color:#3fb950'>{round(tp2,5)}</b>
                        </div>""",unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("#### 🤖 AI News Trade Analysis")
                st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:16px;
                border-left:4px solid #58a6ff;line-height:1.8;font-size:14px'>
                {ai_txt.replace(chr(10),"<br>")}</div>""",unsafe_allow_html=True)
                if entry:
                    st.markdown("---"); show_price_chart(sym,news_pair,sig,entry,sl,tp1,tp2)

            st.markdown("---")
            st.markdown("#### 📖 News Trading Rules")
            c1,c2=st.columns(2)
            with c1:
                st.markdown("""<div class='card'><b style='color:#3fb950'>✅ DO</b><br><br>
                • Wait for candle to <b>close</b> after news before entering<br>
                • Trade in direction of the <b>surprise</b> (actual vs forecast)<br>
                • Use <b>wider stops</b> — spreads spike during news<br>
                • Take profits quickly — news moves are fast<br>
                • Check <b>both currencies</b> in the pair</div>""",unsafe_allow_html=True)
            with c2:
                st.markdown("""<div class='card'><b style='color:#f85149'>❌ DON'T</b><br><br>
                • Don't trade <b>into</b> the news — wait for the reaction<br>
                • Don't hold through NFP, FOMC, rate decisions blindly<br>
                • Don't ignore the <b>previous reading</b> — it matters<br>
                • Don't risk more than <b>1%</b> on news trades<br>
                • Don't trade if spread is <b>unusually wide</b></div>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("➕ Log a Trade"):
        c1,c2,c3=st.columns(3)
        ja=c1.selectbox("Asset",list(ALL_PAIRS.keys()))
        js=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"])
        jr=c3.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c4,c5,c6=st.columns(3)
        je=c4.number_input("Entry",format="%.5f"); jc=c5.slider("Confidence",0,100,70); jn=c6.text_input("Notes")
        if st.button("Save Trade"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),"Asset":ja,
                "Signal":js,"Entry":je,"SL":0,"TP1":0,"Confidence":jc,"Result":jr,"Notes":jn})
            st.success("✅ Saved!")
    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df,use_container_width=True,hide_index=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
        wr=round(wins/tot*100,1) if tot>0 else 0
        c1,c2,c3=st.columns(3)
        c1.metric("Total",len(df)); c2.metric("Win Rate",f"{wr}%"); c3.metric("Open",len(df[df["Result"]=="Open"]))
    else: st.info("No trades logged yet.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.title("📈 Performance Dashboard")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal: st.info("Log trades in the Journal to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
    wr=round(wins/tot*100,1) if tot>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total Trades",tot); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
    if "Asset" in df.columns:
        st.subheader("Results by Asset")
        st.dataframe(df.groupby("Asset")["Result"].value_counts().unstack(fill_value=0),use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ════════════════════════════════════════════════════════════
elif "Risk" in page:
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
        if rp<=2:  st.success("✅ Conservative — good risk management")
        elif rp<=5: st.warning("⚠️ Moderate — manage carefully")
        else:       st.error("🚨 High risk — consider reducing")

# ════════════════════════════════════════════════════════════
# PAGE: PRICING
# ════════════════════════════════════════════════════════════
elif "Pricing" in page:
    st.title("💎 Plans & Pricing")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'>
        <h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        5 assets &nbsp;·&nbsp; Basic signals only<br><br>
        ❌ Pulse Signal<br>❌ News Trading<br>
        ❌ SMC Strategies<br>❌ Confidence scores<br>
        ❌ Price charts<br>❌ Trade Journal
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$15/mo</h2><hr>
        ✅ <b>⚡ Pulse Signal</b> — live strong trades<br>
        ✅ <b>🗞️ News Trading</b> — trade around events<br>
        ✅ <b>SMC Order Blocks + Fair Value Gaps</b><br>
        ✅ All 10 assets &nbsp;·&nbsp; 8-strategy engine<br>
        ✅ ADX + Stochastic confirmation<br>
        ✅ Charts with Entry / SL / TP<br>
        ✅ AI News Analysis<br>
        ✅ Trade Journal + Performance
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.info("💬 Contact us to get your premium password after payment.")

# ════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ════════════════════════════════════════════════════════════
elif "About" in page:
    st.title("ℹ️ About Sparro FX AI")
    st.markdown("""
**Sparro FX AI** uses 8 institutional-grade strategies to generate high-probability trade signals.

**The 8 Strategies:**

| Strategy | Type | What it does |
|---|---|---|
| EMA Trend | Trend | 20/50/200 EMA alignment |
| RSI Momentum | Momentum | Overbought/Oversold levels |
| MACD Crossover | Momentum | Signal line crossovers |
| Support/Resistance | Structure | Key price levels |
| ADX Trend Strength | Filter | Confirms trend is strong enough to trade |
| Stochastic Oscillator | Momentum | Oversold/Overbought with crossover |
| SMC Order Blocks | Smart Money | Institutional buy/sell zones |
| SMC Fair Value Gap | Smart Money | Price imbalances that attract price back |

**Why SMC?** Smart Money Concepts reveal where banks and institutions place orders — the biggest players in forex. Trading at Order Blocks and FVGs puts you in line with the market makers, not against them.

⚠️ *Trade responsibly. Past signals do not guarantee future results.*
    """)

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ════════════════════════════════════════════════════════════
elif "Admin" in page:
    if atype!="admin": st.error("🔒 Admin only."); st.stop()
    st.title("👑 Admin Panel")

    tab_pw,tab_subs,tab_stats=st.tabs(["🔐 Passwords","👥 Subscribers","📊 Stats"])

    with tab_pw:
        st.markdown("### Password Management")
        st.info("""Update in **Streamlit Cloud → App Settings → Secrets**:
```toml
ADMIN_PASSWORD    = "your-admin-password"
PREMIUM_PASSWORD  = "your-premium-password"
FREE_PASSWORD     = "sparro_free"
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```
**Change PREMIUM_PASSWORD anytime to lock out non-paying subscribers instantly.**""")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("""<div class='card' style='border-left:4px solid #ffd200'>
            <b>👑 Admin Password</b><br>
            <span style='color:#8b949e;font-size:13px'>Only you. Never share this.</span>
            </div>""",unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class='card' style='border-left:4px solid #3fb950'>
            <b>⚡ Premium Password</b><br>
            <span style='color:#8b949e;font-size:13px'>Share with paying subscribers. Change to revoke access instantly.</span>
            </div>""",unsafe_allow_html=True)

    with tab_subs:
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
            df_s=pd.DataFrame(st.session_state.subscribers)
            st.dataframe(df_s,use_container_width=True,hide_index=True)
        else:
            st.info("No subscribers yet. Add your first one above.")

    with tab_stats:
        st.markdown("### Business Stats")
        subs=st.session_state.subscribers
        pc=len([s for s in subs if "Premium" in s.get("Plan","")])
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Subscribers",len(subs))
        c2.metric("Premium",pc)
        c3.metric("Monthly Revenue",f"${pc*15}")
        c4.metric("Annual Run Rate",f"${pc*15*12}")
        st.markdown("---")
        st.markdown("**🔗 Quick Links**")
        st.markdown("""
- 🌐 [Streamlit Cloud](https://share.streamlit.io) — manage secrets and deployment
- 📦 [GitHub Repo](https://github.com/sparroxhalo-stack/ai-forex-analyzer) — update code
- 🤖 [Anthropic Console](https://console.anthropic.com) — manage AI API key
        """)
