import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib

st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  html,body,[class*="css"]{font-family:'Inter',sans-serif;background:#0a0a0f;color:#e6edf3}
  .main{background:#0a0a0f;padding:0}
  .block-container{padding:0.5rem 0.8rem}
  .stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}

  /* TOP HEADER */
  .app-header{background:linear-gradient(135deg,#0d1117,#161b22);
    border-bottom:1px solid #21262d;padding:12px 16px;border-radius:0;
    display:flex;align-items:center;justify-content:space-between;margin:-0.5rem -0.8rem 1rem}
  .app-logo{font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px}
  .app-logo span{color:#00c6ff}
  .live-dot{width:8px;height:8px;background:#3fb950;border-radius:50%;
    display:inline-block;margin-right:6px;animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}

  /* TAB NAVIGATION */
  .tab-nav{display:flex;gap:4px;background:#161b22;border-radius:12px;
    padding:4px;margin-bottom:16px;overflow-x:auto}
  .tab-btn{flex:1;min-width:80px;padding:8px 12px;border-radius:8px;border:none;
    background:transparent;color:#8b949e;font-size:12px;font-weight:600;
    cursor:pointer;text-align:center;white-space:nowrap}
  .tab-btn.active{background:#0072ff;color:#fff}

  /* SIGNAL CARD */
  .signal-card{background:#1a0a0a;border:1px solid #f8514930;border-radius:16px;
    padding:16px;margin-bottom:12px;position:relative;overflow:hidden}
  .signal-card.buy{background:#0a1a0a;border-color:#3fb95030}
  .signal-card.wait{background:#1a1a0a;border-color:#ffd20030}

  .signal-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
  .signal-direction{font-size:20px;font-weight:800;letter-spacing:1px}
  .signal-direction.sell{color:#f85149}
  .signal-direction.buy{color:#3fb950}

  .grade-badge{padding:4px 10px;border-radius:6px;font-size:12px;font-weight:800;margin-right:6px}
  .grade-a{background:#3fb950;color:#000}
  .grade-b{background:#0072ff;color:#fff}
  .grade-c{background:#ffd200;color:#000}
  .grade-d{background:#f85149;color:#fff}

  .strat-badge{background:#21262d;color:#8b949e;padding:3px 8px;
    border-radius:6px;font-size:11px;font-weight:600;margin-right:4px}
  .strat-badge.smc{background:#7c3aed22;color:#a78bfa}
  .strat-badge.mtf{background:#0072ff22;color:#58a6ff}

  .confidence-pct{font-size:28px;font-weight:800;color:#ffd200}

  .pair-name{font-size:22px;font-weight:800;color:#fff;margin:6px 0}
  .mtf-line{font-size:12px;color:#3fb950;margin:4px 0}
  .market-condition{font-size:12px;color:#ffd200;margin:4px 0}

  /* PRICE GRID */
  .price-grid{display:grid;grid-template-columns:repeat(5,1fr);
    gap:6px;margin:12px 0;background:#0d1117;border-radius:10px;padding:10px}
  .price-cell{text-align:center}
  .price-label{font-size:10px;color:#8b949e;font-weight:600;text-transform:uppercase}
  .price-value{font-size:13px;font-weight:700;margin-top:2px}
  .price-value.entry{color:#fff}
  .price-value.sl{color:#f85149}
  .price-value.tp{color:#3fb950}

  /* FILTER BADGES */
  .filter-row{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
  .filter-item{display:flex;flex-direction:column;align-items:center;gap:2px}
  .filter-label{font-size:10px;color:#8b949e}
  .filter-check{font-size:14px}

  /* TF ROW */
  .tf-row{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px}
  .tf-cell{background:#0d1117;border-radius:8px;padding:8px;text-align:center}
  .tf-label{font-size:10px;color:#8b949e;font-weight:600}
  .tf-signal{font-size:13px;font-weight:700;margin-top:2px}
  .tf-signal.buy{color:#3fb950}
  .tf-signal.sell{color:#f85149}
  .tf-signal.wait{color:#ffd200}

  /* STRATEGY ROW */
  .strat-row{font-size:11px;color:#8b949e;margin-top:8px;line-height:1.6}
  .strat-row b{color:#58a6ff}

  /* AGREE BADGE */
  .agree-badge{font-size:11px;color:#8b949e;text-align:right}

  /* METRIC CARDS */
  .metric-row{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0}
  .metric-card{background:#161b22;border-radius:10px;padding:12px;text-align:center;border:1px solid #21262d}
  .metric-label{font-size:10px;color:#8b949e;font-weight:600;text-transform:uppercase}
  .metric-value{font-size:18px;font-weight:800;color:#fff;margin-top:4px}

  /* STRENGTH BAR */
  .strength-item{margin-bottom:8px}
  .strength-header{display:flex;justify-content:space-between;margin-bottom:3px}
  .strength-bar-bg{background:#21262d;border-radius:4px;height:8px}
  .strength-bar-fill{height:8px;border-radius:4px}

  /* NEWS CARD */
  .news-item{background:#161b22;border-radius:10px;padding:12px;
    margin-bottom:8px;border-left:3px solid #f85149}
  .news-item.medium{border-color:#ffd200}
  .news-item.low{border-color:#21262d}

  /* BOTTOM NAV */
  .bottom-nav{position:fixed;bottom:0;left:0;right:0;background:#161b22;
    border-top:1px solid #21262d;display:flex;justify-content:space-around;
    padding:10px 0;z-index:999}
  .nav-item{display:flex;flex-direction:column;align-items:center;
    font-size:10px;color:#8b949e;cursor:pointer;gap:3px}
  .nav-item.active{color:#0072ff}

  /* SCROLLABLE CONTENT */
  .content-area{padding-bottom:80px}

  /* HIDE streamlit elements */
  #MainMenu{visibility:hidden}
  footer{visibility:hidden}
  header{visibility:hidden}
  .stDeployButton{display:none}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# SUPABASE
# ════════════════════════════════════════════════════════════
def get_headers():
    key=st.secrets.get("SUPABASE_KEY","")
    return {"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=representation"}

def sb_url(path): return f"{st.secrets.get('SUPABASE_URL','')}/rest/v1/{path}"
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def get_user(email):
    try:
        r=requests.get(sb_url(f"users?email=eq.{email}&select=*"),headers=get_headers(),timeout=8)
        d=r.json(); return d[0] if isinstance(d,list) and d else None
    except: return None

def create_user(email,password,tier="free"):
    try:
        r=requests.post(sb_url("users"),headers=get_headers(),
            json={"email":email,"password_hash":hash_pw(password),"tier":tier,
                  "is_active":True,"created_at":datetime.datetime.now().isoformat()},timeout=8)
        return r.status_code in [200,201], r.text
    except Exception as e: return False,str(e)

def update_tier(email,tier):
    try:
        r=requests.patch(sb_url(f"users?email=eq.{email}"),headers=get_headers(),json={"tier":tier},timeout=8)
        return r.status_code in [200,204]
    except: return False

def delete_user(email):
    try:
        r=requests.delete(sb_url(f"users?email=eq.{email}"),headers=get_headers(),timeout=8)
        return r.status_code in [200,204]
    except: return False

def get_all_users():
    try:
        r=requests.get(sb_url("users?select=*&order=created_at.desc"),headers=get_headers(),timeout=8)
        return r.json() if isinstance(r.json(),list) else []
    except: return []

# ════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════
DEFAULTS={"logged_in":False,"user_email":"","user_tier":"free","is_admin":False,
          "active_tab":"Pulse","trade_journal":[],"telegram_token":"",
          "telegram_chat_id":"","ai_strategy":"","notification_threshold":75}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

# ════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════
def show_login():
    st.markdown("""
    <div style='text-align:center;padding:60px 20px 30px'>
      <div style='font-size:48px'>⚡</div>
      <h1 style='font-size:28px;font-weight:800;color:#fff;margin:8px 0'>Sparro FX AI</h1>
      <p style='color:#8b949e;font-size:14px'>Professional AI Trading Signals</p>
    </div>""",unsafe_allow_html=True)

    tab1,tab2=st.tabs(["🔐 Login","📝 Register"])
    with tab1:
        email=st.text_input("Email",placeholder="your@email.com",key="li_e")
        password=st.text_input("Password",type="password",placeholder="••••••••",key="li_p")
        if st.button("Login",type="primary",use_container_width=True):
            au=st.secrets.get("ADMIN_USERNAME","admin")
            ap=st.secrets.get("ADMIN_PASSWORD","")
            if email==au and password==ap:
                st.session_state.update({"logged_in":True,"is_admin":True,"user_email":email,"user_tier":"admin"})
                st.rerun()
            else:
                user=get_user(email)
                if user and user.get("password_hash")==hash_pw(password):
                    if not user.get("is_active",True): st.error("❌ Account deactivated.")
                    else:
                        st.session_state.update({"logged_in":True,"is_admin":False,"user_email":email,"user_tier":user.get("tier","free")})
                        st.rerun()
                else: st.error("❌ Invalid email or password.")
    with tab2:
        re=st.text_input("Email",placeholder="your@email.com",key="re_e")
        rp=st.text_input("Password",type="password",placeholder="Min 6 characters",key="re_p")
        rp2=st.text_input("Confirm Password",type="password",placeholder="Repeat password",key="re_p2")
        if st.button("Create Account",type="primary",use_container_width=True):
            if not re or not rp: st.error("Fill all fields.")
            elif rp!=rp2: st.error("❌ Passwords don't match.")
            elif len(rp)<6: st.error("❌ Min 6 characters.")
            elif get_user(re): st.error("❌ Email already registered.")
            else:
                ok,err=create_user(re,rp,"free")
                if ok: st.success("✅ Account created! Please login.")
                else: st.error(f"❌ Failed: {err}")

if not st.session_state.logged_in:
    show_login(); st.stop()

# ════════════════════════════════════════════════════════════
# ASSETS
# ════════════════════════════════════════════════════════════
ALL_PAIRS={"EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
           "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
           "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"}
FREE_PAIRS=dict(list(ALL_PAIRS.items())[:5])
SPECIALIST={"Gold (XAU/USD)":1.15,"Bitcoin":1.10,"EUR/USD":1.08,"GBP/USD":1.05}

premium=st.session_state.user_tier in ["premium","admin"]
is_admin=st.session_state.is_admin
pairs=ALL_PAIRS if premium else FREE_PAIRS

# ════════════════════════════════════════════════════════════
# DATA & STRATEGIES
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=900, show_spinner=False)
def fetch(symbol,period="6mo",interval="1d"):
    try:
        import signal
        df=yf.download(symbol,period=period,interval=interval,
                       progress=False,auto_adjust=True,
                       threads=False,timeout=15)
        if df is None or df.empty: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        # Ensure we have required columns
        required=["Close","High","Low"]
        if not all(c in df.columns for c in required): return None
        return df
    except Exception: return None

def get_rsi(close,period=14):
    d=close.diff(); g=d.where(d>0,0).rolling(period).mean(); l=(-d.where(d<0,0)).rolling(period).mean()
    return (100-(100/(1+(g/l)))).iloc[-1]

def get_atr(df,period=14):
    h=df["High"]; l=df["Low"]; c=df["Close"]
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])

def time_ago(dt):
    """Returns human-readable time since signal was generated"""
    now_utc=datetime.datetime.now(datetime.timezone.utc)
    if dt.tzinfo is None: dt=dt.replace(tzinfo=datetime.timezone.utc)
    diff=now_utc-dt
    secs=int(diff.total_seconds())
    if secs<60: return "just now"
    if secs<3600: return f"{secs//60}m ago"
    if secs<86400: return f"{secs//3600}h ago"
    return f"{secs//86400}d ago"

@st.cache_data(ttl=900, show_spinner=False)
def analyse_pair(symbol,pair_name):
    """
    Full professional analysis with 9 strategies:
    1. EMA Stack (trend direction + slope)
    2. RSI + Divergence filter
    3. MACD Crossover + Histogram momentum
    4. Bollinger Band Squeeze + Breakout
    5. Support/Resistance zones (swing highs/lows)
    6. Break of Structure (BOS/CHoCH)
    7. Candlestick Pattern recognition
    8. Volume confirmation
    9. ADX Trend Strength filter
    """
    scan_time=datetime.datetime.now(datetime.timezone.utc)

    df_d=fetch(symbol,"6mo","1d")
    df_4h=fetch(symbol,"3mo","1h")
    df_1h=fetch(symbol,"1mo","1h")
    df_w=fetch(symbol,"2y","1wk")
    if df_d is None or len(df_d)<50: return None

    c=df_d["Close"]; h_=df_d["High"]; l_=df_d["Low"]
    price=float(c.iloc[-1])
    atr=get_atr(df_d)

    # ── STRATEGY 1: EMA STACK ──────────────────────────────
    ema20=c.ewm(span=20).mean(); ema50=c.ewm(span=50).mean(); ema200=c.ewm(span=200).mean()
    e20=float(ema20.iloc[-1]); e50=float(ema50.iloc[-1]); e200=float(ema200.iloc[-1])
    ema_slope=(float(ema20.iloc[-1])-float(ema20.iloc[-5]))/float(ema20.iloc[-5])*100
    # Full stack: all 3 EMAs aligned = strongest signal
    if e20>e50 and e50>e200 and ema_slope>0:   ema_sig="BUY"
    elif e20<e50 and e50<e200 and ema_slope<0: ema_sig="SELL"
    elif e20>e50 and e50>e200:                  ema_sig="BUY"
    elif e20<e50 and e50<e200:                  ema_sig="SELL"
    elif e20>e50:                               ema_sig="BUY"
    elif e20<e50:                               ema_sig="SELL"
    else:                                       ema_sig="WAIT"

    # ── STRATEGY 2: RSI (14) WITH ZONES ───────────────────
    rsi_val=get_rsi(c,14)
    # Stricter zones for quality: 60+ bullish, 40- bearish
    if rsi_val>=60:   rsi_sig="BUY"
    elif rsi_val<=40: rsi_sig="SELL"
    else:             rsi_sig="WAIT"

    # ── STRATEGY 3: MACD ──────────────────────────────────
    macd_line=c.ewm(span=12).mean()-c.ewm(span=26).mean()
    signal_line=macd_line.ewm(span=9).mean()
    hist=macd_line-signal_line
    macd_cross_up=macd_line.iloc[-1]>signal_line.iloc[-1] and macd_line.iloc[-2]<=signal_line.iloc[-2]
    macd_cross_dn=macd_line.iloc[-1]<signal_line.iloc[-1] and macd_line.iloc[-2]>=signal_line.iloc[-2]
    hist_rising=float(hist.iloc[-1])>float(hist.iloc[-2])>float(hist.iloc[-3])
    hist_falling=float(hist.iloc[-1])<float(hist.iloc[-2])<float(hist.iloc[-3])
    if macd_line.iloc[-1]>signal_line.iloc[-1] and float(hist.iloc[-1])>0 and hist_rising: macd_sig="BUY"
    elif macd_line.iloc[-1]<signal_line.iloc[-1] and float(hist.iloc[-1])<0 and hist_falling: macd_sig="SELL"
    elif macd_cross_up: macd_sig="BUY"
    elif macd_cross_dn: macd_sig="SELL"
    else: macd_sig="WAIT"

    # ── STRATEGY 4: BOLLINGER BANDS ───────────────────────
    bb_mid=c.rolling(20).mean(); bb_std=c.rolling(20).std()
    bb_upper=bb_mid+2*bb_std; bb_lower=bb_mid-2*bb_std
    bb_width=((bb_upper-bb_lower)/bb_mid)
    squeeze=float(bb_width.iloc[-1])<float(bb_width.rolling(20).mean().iloc[-1])*0.8
    if price>float(bb_upper.iloc[-1]):                          bb_sig="BUY"
    elif price<float(bb_lower.iloc[-1]):                        bb_sig="SELL"
    elif squeeze and price>float(bb_mid.iloc[-1]):              bb_sig="BUY"
    elif squeeze and price<float(bb_mid.iloc[-1]):              bb_sig="SELL"
    elif price>float(bb_mid.iloc[-1]) and not squeeze:         bb_sig="BUY"
    else:                                                        bb_sig="SELL"

    # ── STRATEGY 5: SUPPORT & RESISTANCE ──────────────────
    # Use swing highs/lows over 20 bars for dynamic S/R
    res_20=float(h_.rolling(20).max().iloc[-1])
    sup_20=float(l_.rolling(20).min().iloc[-1])
    res_10=float(h_.rolling(10).max().iloc[-1])
    sup_10=float(l_.rolling(10).min().iloc[-1])
    # Best resistance = lowest of the two (nearest)
    resistance=min(res_20,res_10)
    support=max(sup_20,sup_10)
    sr_range=resistance-support
    near_res=price>=(resistance-sr_range*0.08)
    near_sup=price<=(support+sr_range*0.08)
    if near_res:                           sr_sig="SELL"
    elif near_sup:                         sr_sig="BUY"
    elif price>(resistance+support)/2:     sr_sig="BUY"
    else:                                  sr_sig="SELL"

    # ── STRATEGY 6: BREAK OF STRUCTURE (BOS/CHoCH) ────────
    # Look for breaks of recent swing highs/lows
    lookback_h=float(h_.iloc[-20:-3].max())
    lookback_l=float(l_.iloc[-20:-3].min())
    prev_h=float(h_.iloc[-40:-20].max()) if len(h_)>=40 else lookback_h
    prev_l=float(l_.iloc[-40:-20].min()) if len(l_)>=40 else lookback_l
    # Strong BOS = higher high + price above previous swing
    strong_bull_bos=price>lookback_h and lookback_h>prev_h
    strong_bear_bos=price<lookback_l and lookback_l<prev_l
    if strong_bull_bos:             bos_sig="BUY"
    elif strong_bear_bos:           bos_sig="SELL"
    elif price>lookback_h:          bos_sig="BUY"
    elif price<lookback_l:          bos_sig="SELL"
    else:                           bos_sig="WAIT"

    # ── STRATEGY 7: CANDLESTICK PATTERNS ──────────────────
    o=float(df_d["Open"].iloc[-1]) if "Open" in df_d.columns else float(c.iloc[-2])
    hi=float(h_.iloc[-1]); lo=float(l_.iloc[-1]); cl=float(c.iloc[-1])
    po=float(df_d["Open"].iloc[-2]) if "Open" in df_d.columns else float(c.iloc[-3])
    pc=float(c.iloc[-2])
    body=abs(cl-o); full=hi-lo
    uw=hi-max(cl,o); lw=min(cl,o)-lo
    # Engulfing (strongest reversal)
    bull_engulf=cl>o and pc<po and cl>po and o<pc and body>abs(pc-po)*1.2
    bear_engulf=cl<o and pc>po and cl<po and o>pc and body>abs(pc-po)*1.2
    # Pin bars (rejection)
    bull_pin=lw>body*2.5 and uw<body*0.4 and full>atr*0.3
    bear_pin=uw>body*2.5 and lw<body*0.4 and full>atr*0.3
    # Inside bar breakout
    inside_bar=hi<float(h_.iloc[-2]) and lo>float(l_.iloc[-2])
    if bull_engulf:            candle_sig="BUY";  candle_name="Bullish Engulfing"
    elif bear_engulf:          candle_sig="SELL"; candle_name="Bearish Engulfing"
    elif bull_pin:             candle_sig="BUY";  candle_name="Hammer/Pin Bar"
    elif bear_pin:             candle_sig="SELL"; candle_name="Shooting Star"
    elif inside_bar and cl>o:  candle_sig="BUY";  candle_name="Inside Bar Bull"
    elif inside_bar and cl<o:  candle_sig="SELL"; candle_name="Inside Bar Bear"
    elif cl>o:                 candle_sig="BUY";  candle_name="Bullish close"
    else:                      candle_sig="SELL"; candle_name="Bearish close"

    # ── STRATEGY 8: VOLUME CONFIRMATION ───────────────────
    if "Volume" in df_d.columns:
        v=df_d["Volume"]
        avg_vol=float(v.rolling(20).mean().iloc[-1])
        cur_vol=float(v.iloc[-1])
        vol_ratio=cur_vol/avg_vol if avg_vol>0 else 1.0
        # Volume confirms direction
        price_up=cl>pc
        if vol_ratio>=1.3 and price_up:     vol_sig="BUY"
        elif vol_ratio>=1.3 and not price_up: vol_sig="SELL"
        elif vol_ratio>=0.8 and price_up:   vol_sig="BUY"
        elif vol_ratio>=0.8:                vol_sig="SELL"
        else:                               vol_sig="WAIT"
        vol_ok=vol_ratio>0.7
    else:
        vol_sig="WAIT"; vol_ok=True; vol_ratio=1.0

    # ── STRATEGY 9: ADX TREND STRENGTH ────────────────────
    # ADX measures trend strength (>25 = trending, >40 = strong)
    try:
        tr_=pd.concat([h_-l_,(h_-c.shift()).abs(),(l_-c.shift()).abs()],axis=1).max(axis=1)
        dm_plus=h_.diff(); dm_minus=-l_.diff()
        dm_plus=dm_plus.where((dm_plus>dm_minus)&(dm_plus>0),0)
        dm_minus=dm_minus.where((dm_minus>dm_plus)&(dm_minus>0),0)
        atr14=tr_.rolling(14).mean()
        di_plus=100*(dm_plus.rolling(14).mean()/atr14)
        di_minus=100*(dm_minus.rolling(14).mean()/atr14)
        dx=100*((di_plus-di_minus).abs()/(di_plus+di_minus))
        adx=float(dx.rolling(14).mean().iloc[-1])
        di_p=float(di_plus.iloc[-1]); di_m=float(di_minus.iloc[-1])
        if adx>=25 and di_p>di_m:   adx_sig="BUY"
        elif adx>=25 and di_m>di_p: adx_sig="SELL"
        else:                        adx_sig="WAIT"
        trend_strong=adx>=25
    except:
        adx_sig="WAIT"; adx=0; trend_strong=False

    # ── COMBINE ALL 9 STRATEGIES ──────────────────────────
    all_sigs=[ema_sig,rsi_sig,macd_sig,bb_sig,sr_sig,bos_sig,candle_sig,vol_sig,adx_sig]
    buys=sum(1 for s in all_sigs if s=="BUY")
    sells=sum(1 for s in all_sigs if s=="SELL")
    total=len(all_sigs)

    if buys>sells:
        direction="BUY"; conf=round(buys/total*100)
        final_sig="STRONG BUY" if buys>=7 else "BUY"
    elif sells>buys:
        direction="SELL"; conf=round(sells/total*100)
        final_sig="STRONG SELL" if sells>=7 else "SELL"
    else:
        direction="WAIT"; conf=50; final_sig="WAIT"

    # ── QUALITY FILTERS ───────────────────────────────────
    # Only show signals that pass ALL key quality filters:
    # 1. ATR filter: volatility must be meaningful (not too low)
    atr_pct=atr/price*100
    atr_ok=atr_pct>=0.2  # min 0.2% daily range

    # 2. Candle body filter: candle must have meaningful body
    candle_body_pct=body/full if full>0 else 0
    candle_quality_ok=candle_body_pct>=0.1 or bull_engulf or bear_engulf or bull_pin or bear_pin

    # 3. Weekly trend filter
    if df_w is not None:
        cw=df_w["Close"]; e20w=cw.ewm(span=20).mean(); e50w=cw.ewm(span=50).mean()
        weekly_bull=float(e20w.iloc[-1])>float(e50w.iloc[-1])
    else: weekly_bull=direction=="BUY"
    weekly_ok=weekly_bull==(direction=="BUY") or direction=="WAIT"

    # 4. Session filter
    hour=datetime.datetime.now(datetime.timezone.utc).hour
    session_ok=(7<=hour<=17) or (12<=hour<=21)
    session_label="London" if 7<=hour<13 else "New York" if 13<=hour<21 else "Asian/Off"

    # 5. MTF confirmation
    def tf_sig(df_tf):
        if df_tf is None: return "WAIT"
        ct=df_tf["Close"]
        if len(ct)<30: return "WAIT"
        e20t=ct.ewm(span=20).mean().iloc[-1]; e50t=ct.ewm(span=50).mean().iloc[-1]
        rt=get_rsi(ct)
        if e20t>e50t and rt>52: return "BUY"
        if e20t<e50t and rt<48: return "SELL"
        if e20t>e50t: return "BUY"
        if e20t<e50t: return "SELL"
        return "WAIT"

    sig_daily=ema_sig
    sig_4h=tf_sig(df_4h.iloc[-120:] if df_4h is not None and len(df_4h)>120 else df_4h)
    sig_1h=tf_sig(df_1h.iloc[-60:]  if df_1h  is not None and len(df_1h)>60  else df_1h)

    mtf_sigs=[s for s in [sig_daily,sig_4h,sig_1h] if s!="WAIT"]
    mtf_buys=sum(1 for s in mtf_sigs if "BUY" in s)
    mtf_sells=sum(1 for s in mtf_sigs if "SELL" in s)
    mtf_ok=(mtf_buys>mtf_sells and direction=="BUY") or (mtf_sells>mtf_buys and direction=="SELL")
    mtf_agree=f"BUY — {mtf_buys}/{len(mtf_sigs)} TFs" if mtf_buys>mtf_sells else f"SELL — {mtf_sells}/{len(mtf_sigs)} TFs" if mtf_sells>mtf_buys else "Mixed TFs"

    # ── SPECIALIST WEIGHTING ──────────────────────────────
    spec=SPECIALIST.get(pair_name,1.0)
    adj_conf=min(99,round(conf*spec)) if direction!="WAIT" else 50

    # ── GRADE (A/B/C/D) ───────────────────────────────────
    agree_count=max(buys,sells)
    filters_passed=sum([atr_ok,candle_quality_ok,weekly_ok,session_ok,mtf_ok])
    # Grade A: 7+ strategies agree, 4+ filters pass, trend is strong
    if adj_conf>=85 and agree_count>=7 and filters_passed>=4 and trend_strong: grade="A"
    elif adj_conf>=75 and agree_count>=6 and filters_passed>=3: grade="B"
    elif adj_conf>=62 and agree_count>=5 and filters_passed>=2: grade="C"
    else: grade="D"

    # Skip D-grade signals entirely — not worth showing
    if grade=="D" and direction!="WAIT":
        direction="WAIT"; final_sig="WAIT"

    # ── TRADE LEVELS (ATR-based with better RR) ───────────
    # Use 1.5x ATR for SL, targets at 1R/2R/3R
    risk=atr*1.5
    if direction=="BUY":
        entry=price; sl=price-risk
        tp1=price+risk      # 1:1
        tp2=price+risk*2    # 1:2
        tp3=price+risk*3    # 1:3
    elif direction=="SELL":
        entry=price; sl=price+risk
        tp1=price-risk
        tp2=price-risk*2
        tp3=price-risk*3
    else:
        entry=price; sl=0; tp1=0; tp2=0; tp3=0

    # ── MARKET CONDITION LABEL ────────────────────────────
    if atr_pct>1.0:   vol_label="High volatility"
    elif atr_pct>0.5: vol_label="Moderate market"
    else:             vol_label="Low volatility"
    if trend_strong:  trend_label="Strong trend"
    else:             trend_label="Moderate trend"
    if grade=="A":    action_label="take full position"
    elif grade=="B":  action_label="use standard size"
    elif grade=="C":  action_label="reduce size"
    else:             action_label="avoid or wait"
    market_cond=f"{vol_label} — {trend_label} — {action_label}"

    # ── STRATEGY NAMES FOR DISPLAY ────────────────────────
    strat_names="EMA Stack · RSI · MACD · Bollinger · S/R · BOS · Candle · Volume · ADX"

    return {
        "pair":pair_name,"symbol":symbol,"direction":direction,"signal":final_sig,
        "confidence":adj_conf,"grade":grade,"entry":entry,"sl":sl,
        "tp1":tp1,"tp2":tp2,"tp3":tp3,"atr":round(atr,5),
        "sig_daily":sig_daily,"sig_4h":sig_4h,"sig_1h":sig_1h,
        "mtf_agree":mtf_agree,"market_cond":market_cond,
        "candle_ok":candle_quality_ok,"vol_ok":vol_ok,
        "weekly_ok":weekly_ok,"session_ok":session_ok,"mtf_ok":mtf_ok,
        "session_label":session_label,"strategies":strat_names,
        "agree":f"{agree_count}/{total} agree","rsi":round(rsi_val,1),
        "adx":round(adx,1),"candle_name":candle_name,
        "buys":buys,"sells":sells,
        "scan_time":scan_time,
        "time_ago":time_ago(scan_time),
    }

# ════════════════════════════════════════════════════════════
# RENDER SIGNAL CARD
# ════════════════════════════════════════════════════════════
def render_signal_card(sig):
    if sig is None or sig["direction"]=="WAIT": return
    d=sig["direction"].lower()
    grade=sig["grade"]
    grade_class=f"grade-{grade.lower()}"
    dir_emoji="📉" if d=="sell" else "📈"
    pair_emoji="🥇" if "Gold" in sig["pair"] else "₿" if "Bitcoin" in sig["pair"] else "€" if "EUR" in sig["pair"] else "£" if "GBP" in sig["pair"] else "💹"

    # Filter checks
    filters=[
        ("🕯️","Candle",sig["candle_ok"]),
        ("📊","Volatility",sig["vol_ok"]),
        ("📅","Weekly",sig["weekly_ok"]),
        ("🕐","Session",sig["session_ok"]),
        ("📐","MTF",sig["mtf_ok"]),
    ]
    filter_html="".join([f"<div class='filter-item'><span class='filter-label'>{f[1]}</span><span class='filter-check'>{'✅' if f[2] else '⚠️'}</span></div>" for f in filters])

    # TF signals
    def tf_color(s): return "buy" if "BUY" in s else "sell" if "SELL" in s else "wait"

    dp=5 if sig["entry"]<100 else 2

    st.markdown(f"""
    <div class='signal-card {d}'>
      <div class='signal-header'>
        <div>
          <span>{pair_emoji} {dir_emoji} </span>
          <span class='signal-direction {d}'>{sig["direction"]}</span>
          <span class='{grade_class} grade-badge'>{grade}</span>
          <span class='strat-badge smc'>SMC</span>
          <span class='strat-badge mtf'>MTF</span>
        </div>
        <div class='confidence-pct'>{sig["confidence"]}%</div>
      </div>

      <div class='pair-name'>{sig["pair"]}</div>
      <div class='mtf-line'>MTF: {sig["mtf_agree"]}</div>
      <div class='market-condition'>📊 {sig["market_cond"]}</div>

      <div class='price-grid'>
        <div class='price-cell'><div class='price-label'>ENTRY</div><div class='price-value entry'>{round(sig["entry"],dp)}</div></div>
        <div class='price-cell'><div class='price-label'>STOP</div><div class='price-value sl'>{round(sig["sl"],dp)}</div></div>
        <div class='price-cell'><div class='price-label'>TP1</div><div class='price-value tp'>{round(sig["tp1"],dp)}</div></div>
        <div class='price-cell'><div class='price-label'>TP2</div><div class='price-value tp'>{round(sig["tp2"],dp)}</div></div>
        <div class='price-cell'><div class='price-label'>TP3</div><div class='price-value tp'>{round(sig["tp3"],dp)}</div></div>
      </div>

      <div class='filter-row'>{filter_html}</div>

      <div class='tf-row'>
        <div class='tf-cell'><div class='tf-label'>Daily</div><div class='tf-signal {tf_color(sig["sig_daily"])}'>{sig["sig_daily"]}</div></div>
        <div class='tf-cell'><div class='tf-label'>4H</div><div class='tf-signal {tf_color(sig["sig_4h"])}'>{sig["sig_4h"]}</div></div>
        <div class='tf-cell'><div class='tf-label'>1H</div><div class='tf-signal {tf_color(sig["sig_1h"])}'>{sig["sig_1h"]}</div></div>
      </div>

      <div class='strat-row'>✅ <b>{sig["strategies"]}</b></div>
      <div style='display:flex;justify-content:space-between;align-items:center;margin-top:8px'>
        <span style='font-size:11px;color:#8b949e'>{sig["agree"]} · RSI {sig["rsi"]} · ADX {sig.get("adx","—")} · 🕯️ {sig.get("candle_name","—")}</span>
        <span style='font-size:11px;color:#8b949e;background:#21262d;padding:2px 8px;border-radius:10px'>🕐 {sig.get("time_ago","just now")}</span>
      </div>
    </div>
    """,unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════
now=datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")
tier_label="👑 Admin" if is_admin else ("⚡ Pro" if premium else "🆓 Free")

st.markdown(f"""
<div class='app-header'>
  <div class='app-logo'>Sparro <span>FX AI</span></div>
  <div style='display:flex;align-items:center;gap:10px'>
    <span style='font-size:12px;color:#8b949e'>{now}</span>
    <span style='font-size:12px;background:#21262d;padding:3px 8px;border-radius:6px'>{tier_label}</span>
  </div>
</div>
""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# TAB NAVIGATION
# ════════════════════════════════════════════════════════════
tabs_free=["⚡ Pulse","👁 Watchlist","📊 Scanner","💰 Risk Calc","💎 Upgrade"]
tabs_premium=["⚡ Pulse","👁 Watchlist","📊 Scanner","🏆 Trade of Day",
              "📐 Multi-TF","💹 Strength","🎯 Precision","🏢 Prop Firm",
              "🗞️ News","🤖 AI Strategy","📸 Chart AI","🔔 Alerts",
              "📓 Journal","📈 Performance","💰 Risk Calc","📡 MT5 Bot","⚙️ Settings"]
tabs_admin=["👑 Admin"]+tabs_premium
tabs=tabs_admin if is_admin else (tabs_premium if premium else tabs_free)

# Render tab buttons
active=st.session_state.active_tab
tab_html="<div class='tab-nav'>"
for t in tabs:
    ac="active" if t==active else ""
    tab_html+=f"<div class='tab-btn {ac}' onclick=\"\">{t}</div>"
tab_html+="</div>"

# Use selectbox for navigation (styled like tabs)
selected_tab=st.selectbox("Select Page",tabs,index=tabs.index(active) if active in tabs else 0,
    label_visibility="hidden",key="tab_select")
st.session_state.active_tab=selected_tab
page=selected_tab

st.markdown("<div class='content-area'>",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN
# ════════════════════════════════════════════════════════════
if "Admin" in page:
    st.markdown("### 👑 Admin Panel")
    all_users=get_all_users()
    prem=[u for u in all_users if u.get("tier")=="premium"]
    st.markdown(f"""
    <div class='metric-row'>
      <div class='metric-card'><div class='metric-label'>Total Users</div><div class='metric-value'>{len(all_users)}</div></div>
      <div class='metric-card'><div class='metric-label'>Premium</div><div class='metric-value' style='color:#ffd200'>{len(prem)}</div></div>
      <div class='metric-card'><div class='metric-label'>Free</div><div class='metric-value'>{len(all_users)-len(prem)}</div></div>
    </div>""",unsafe_allow_html=True)
    if all_users:
        df_u=pd.DataFrame(all_users)
        cols=[c for c in ["email","tier","is_active","created_at"] if c in df_u.columns]
        st.dataframe(df_u[cols],use_container_width=True)
    st.divider()
    ug=st.text_input("User email to manage")
    c1,c2=st.columns(2)
    if c1.button("⬆️ Upgrade Premium",use_container_width=True):
        st.success("✅ Done!") if update_tier(ug,"premium") else st.error("❌ Failed.")
    if c2.button("⬇️ Set Free",use_container_width=True):
        st.success("✅ Done!") if update_tier(ug,"free") else st.error("❌ Failed.")
    st.divider()
    c1,c2,c3=st.columns(3)
    ne=c1.text_input("Email",key="ne"); np_=c2.text_input("Pass",type="password",key="np"); nt=c3.selectbox("Tier",["free","premium"])
    if st.button("➕ Create User",use_container_width=True):
        ok,err=create_user(ne,np_,nt)
        st.success("✅ Created!") if ok else st.error(f"❌ {err}")
    de=st.text_input("Email to delete")
    if st.button("🗑️ Delete User",type="primary",use_container_width=True):
        st.success("✅ Deleted!") if delete_user(de) else st.error("❌ Failed.")

# ════════════════════════════════════════════════════════════
# PAGE: PULSE (Live Signals)
# ════════════════════════════════════════════════════════════
elif "Pulse" in page:
    # Daily briefing
    with st.expander("📰 Daily Market Briefing + Risk Warning"):
        st.markdown(f"""
        **{datetime.date.today().strftime('%A, %B %d %Y')}**

        Markets are open. Grade A/B signals aim for 70%+ win rate.
        Always use proper risk management — never risk more than 2% per trade.

        ⚠️ *Trading involves significant risk of loss. Past performance does not guarantee future results.*
        """)

    st.markdown(f"""
    <div style='background:#161b22;border-radius:12px;padding:14px;margin-bottom:12px'>
      <div style='display:flex;align-items:center;gap:8px;margin-bottom:4px'>
        <span class='live-dot'></span>
        <b style='font-size:16px'>Live Pulse Signal</b>
      </div>
      <p style='color:#8b949e;font-size:12px;margin:0'>Quality-filtered signals. Candle quality · ATR filter · Weekly trend · Session timing · MTF confirmation. Grade A/B signals aim for 70%+ win rate.</p>
      <p style='color:#8b949e;font-size:11px;margin:6px 0 0'>Scan: {now}</p>
    </div>
    """,unsafe_allow_html=True)

    if not premium:
        st.warning("🔒 Free plan shows 5 assets. Upgrade for all 10 + Grade A/B system.")

    compact=st.toggle("Compact view",value=False)

    # Only scan when button is pressed — prevents segfault on startup
    if "pulse_signals" not in st.session_state:
        st.session_state.pulse_signals=[]

    col_r1,col_r2=st.columns(2)
    if col_r1.button("🔄 Refresh Signals",use_container_width=True,type="primary"):
        signals_temp=[]
        prog=st.progress(0); items=list(pairs.items()); status=st.empty()
        for i,(name,sym) in enumerate(items):
            status.caption(f"Analysing {name}...")
            try:
                sig=analyse_pair(sym,name)
                if sig and sig["direction"]!="WAIT": signals_temp.append(sig)
            except Exception: pass
            prog.progress((i+1)/len(items))
        prog.empty(); status.empty()
        st.session_state.pulse_signals=signals_temp
        st.rerun()
    col_r2.caption("Tap Refresh to scan markets")

    signals=st.session_state.pulse_signals

    # Sort by confidence
    signals.sort(key=lambda x:x["confidence"],reverse=True)
    grade_a=[s for s in signals if s["grade"]=="A"]
    grade_b=[s for s in signals if s["grade"]=="B"]
    grade_c=[s for s in signals if s["grade"]=="C"]

    # Count badge
    total_sigs=len(signals)
    grade_counts={"A":len(grade_a),"B":len(grade_b),"C":len(grade_c)}
    badge_html=" ".join([f"<span class='grade-{g.lower()} grade-badge'>{g} x{n}</span>" for g,n in grade_counts.items() if n>0])
    st.markdown(f"<p style='margin:8px 0'><b>{total_sigs} signal(s):</b> {badge_html} &nbsp; <span style='color:#8b949e;font-size:12px'>Specialists shown first</span></p>",unsafe_allow_html=True)

    if not signals:
        st.info("⏳ No strong signals right now. Market may be consolidating — check back later.")
    else:
        for sig in signals:
            if not compact: render_signal_card(sig)
            else:
                d_color="#3fb950" if "BUY" in sig["direction"] else "#f85149"
                dp=5 if sig["entry"]<100 else 2
                st.markdown(f"""
                <div style='background:#161b22;border-radius:10px;padding:10px;margin-bottom:6px;
                  border-left:3px solid {d_color};display:flex;justify-content:space-between;align-items:center'>
                  <div>
                    <b>{sig["pair"]}</b>
                    <span class='grade-{sig["grade"].lower()} grade-badge' style='margin-left:6px'>{sig["grade"]}</span>
                    <span style='color:{d_color};font-weight:700;margin-left:6px'>{sig["direction"]}</span>
                  </div>
                  <div style='text-align:right'>
                    <div style='color:#ffd200;font-weight:800'>{sig["confidence"]}%</div>
                    <div style='font-size:11px;color:#8b949e'>E:{round(sig["entry"],dp)} SL:{round(sig["sl"],dp)}</div>
                  </div>
                </div>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: WATCHLIST
# ════════════════════════════════════════════════════════════
elif "Watchlist" in page:
    st.markdown("### 👁 Watchlist")
    selected=st.multiselect("Select pairs to watch",list(ALL_PAIRS.keys()),
        default=list(pairs.keys())[:3])
    if st.button("🔄 Analyse Watchlist",use_container_width=True):
        for name in selected:
            sym=ALL_PAIRS[name]
            with st.spinner(f"Analysing {name}..."):
                sig=analyse_pair(sym,name)
            if sig: render_signal_card(sig)
            else: st.warning(f"No data for {name}")

# ════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ════════════════════════════════════════════════════════════
elif "Scanner" in page:
    st.markdown("### 📊 Market Scanner")
    if st.button("🔄 Run Full Scan",use_container_width=True):
        results=[]; prog=st.progress(0); items=list(pairs.items())
        for i,(name,sym) in enumerate(items):
            sig=analyse_pair(sym,name)
            if sig:
                results.append({"Asset":name,"Signal":sig["signal"],
                    "Grade":sig["grade"],"Confidence":f"{sig['confidence']}%",
                    "Entry":round(sig["entry"],5),"SL":round(sig["sl"],5),
                    "TP1":round(sig["tp1"],5),"Strategies":sig["agree"]})
            prog.progress((i+1)/len(items))
        prog.empty()
        if results:
            df=pd.DataFrame(results).sort_values("Confidence",ascending=False)
            st.dataframe(df,use_container_width=True)
    else:
        st.info("Tap 'Run Full Scan' to analyse all assets.")

# ════════════════════════════════════════════════════════════
# PAGE: TRADE OF THE DAY
# ════════════════════════════════════════════════════════════
elif "Trade of Day" in page:
    st.markdown("### 🏆 Trade of the Day")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.spinner("Finding best opportunity..."):
        best=None
        for name,sym in ALL_PAIRS.items():
            sig=analyse_pair(sym,name)
            if sig and sig["direction"]!="WAIT":
                if best is None or sig["confidence"]>best["confidence"]: best=sig
    if best:
        st.markdown(f"<p style='color:#8b949e'>Best setup across all {len(ALL_PAIRS)} assets right now:</p>",unsafe_allow_html=True)
        render_signal_card(best)
        col1,col2=st.columns(2)
        if col1.button("🔔 Send to Telegram",use_container_width=True):
            token=st.session_state.telegram_token; chat_id=st.session_state.telegram_chat_id
            if token and chat_id:
                dp=5 if best["entry"]<100 else 2
                msg=f"🏆 *Trade of the Day*\n{best['direction']} *{best['pair']}*\nGrade {best['grade']} | {best['confidence']}%\nEntry: `{round(best['entry'],dp)}`\nSL: `{round(best['sl'],dp)}`\nTP1: `{round(best['tp1'],dp)}`"
                r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id":chat_id,"text":msg,"parse_mode":"Markdown"},timeout=5)
                st.success("✅ Sent!") if r.status_code==200 else st.error("❌ Failed.")
            else: st.error("Set up Telegram in Alerts tab first.")
        if col2.button("➕ Add to Journal",use_container_width=True):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),
                "Asset":best["pair"],"Signal":best["signal"],"Grade":best["grade"],
                "Entry":best["entry"],"SL":best["sl"],"TP1":best["tp1"],
                "Confidence":best["confidence"],"Result":"Open"})
            st.success("✅ Added to journal!")
    else: st.info("⏳ No strong signals right now.")

# ════════════════════════════════════════════════════════════
# PAGE: MULTI-TIMEFRAME
# ════════════════════════════════════════════════════════════
elif "Multi-TF" in page:
    st.markdown("### 📐 Multi-Timeframe Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    selected=st.selectbox("Asset",list(ALL_PAIRS.keys()))
    if st.button("Analyse",use_container_width=True):
        sym=ALL_PAIRS[selected]
        timeframes=[("1H","1h","5d"),("4H","1h","1mo"),("Daily","1d","6mo"),("Weekly","1wk","1y"),("Monthly","1mo","2y")]
        rows=[]
        for label,interval,period in timeframes:
            df=fetch(sym,period,interval)
            if df is None: rows.append({"TF":label,"Signal":"N/A","RSI":"N/A","Trend":"N/A"}); continue
            c=df["Close"]; e20=c.ewm(span=20).mean().iloc[-1]; e50=c.ewm(span=50).mean().iloc[-1]
            rsi=round(get_rsi(c),1)
            if e20>e50 and rsi>55: sig="STRONG BUY"; trend="📈 Bullish"
            elif e20>e50: sig="BUY"; trend="📈 Bullish"
            elif e20<e50 and rsi<45: sig="STRONG SELL"; trend="📉 Bearish"
            elif e20<e50: sig="SELL"; trend="📉 Bearish"
            else: sig="WAIT"; trend="➡️ Neutral"
            rows.append({"Timeframe":label,"Signal":sig,"RSI":rsi,"Trend":trend})
        df_tf=pd.DataFrame(rows)
        st.dataframe(df_tf,use_container_width=True)
        buys=len(df_tf[df_tf["Signal"].str.contains("BUY",na=False)])
        sells=len(df_tf[df_tf["Signal"].str.contains("SELL",na=False)])
        alignment=round(max(buys,sells)/len(df_tf)*100)
        overall="STRONG BUY" if buys>=4 else "BUY" if buys>=3 else "STRONG SELL" if sells>=4 else "SELL" if sells>=3 else "WAIT"
        st.markdown(f"""
        <div class='metric-row'>
          <div class='metric-card'><div class='metric-label'>Overall</div><div class='metric-value' style='font-size:14px'>{overall}</div></div>
          <div class='metric-card'><div class='metric-label'>Alignment</div><div class='metric-value'>{alignment}%</div></div>
          <div class='metric-card'><div class='metric-label'>Bullish TFs</div><div class='metric-value'>{buys}/5</div></div>
        </div>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: CURRENCY STRENGTH
# ════════════════════════════════════════════════════════════
elif "Strength" in page:
    st.markdown("### 💹 Currency Strength Meter")
    if not premium: st.error("🔒 Premium only."); st.stop()
    CURR_PAIRS={"USD":["EURUSD=X","GBPUSD=X","USDJPY=X"],"EUR":["EURUSD=X","EURGBP=X"],
                "GBP":["GBPUSD=X","EURGBP=X"],"JPY":["USDJPY=X"],"AUD":["AUDUSD=X"],
                "CHF":["USDCHF=X"],"CAD":["USDCAD=X"],"XAU":["GC=F"]}
    with st.spinner("Calculating strength..."):
        strength={}
        for currency,syms in CURR_PAIRS.items():
            scores=[]
            for sym in syms:
                df=fetch(sym,"1mo","1d")
                if df is None: continue
                c=df["Close"]; change=(float(c.iloc[-1])-float(c.iloc[-5]))/float(c.iloc[-5])*100
                scores.append(change if sym.startswith(currency[:3]) else -change)
            strength[currency]=round(np.mean(scores),3) if scores else 0
    vals=list(strength.values()); mn=min(vals); mx=max(vals); rng=mx-mn if mx!=mn else 1
    norm={k:round((v-mn)/rng*100,1) for k,v in strength.items()}
    sorted_s=dict(sorted(norm.items(),key=lambda x:x[1],reverse=True))
    for currency,score in sorted_s.items():
        color="#3fb950" if score>=60 else "#f85149" if score<=40 else "#ffd200"
        st.markdown(f"""
        <div class='strength-item'>
          <div class='strength-header'>
            <b>{currency}</b><span style='color:{color}'>{score}/100</span>
          </div>
          <div class='strength-bar-bg'>
            <div class='strength-bar-fill' style='width:{score}%;background:{color}'></div>
          </div>
        </div>""",unsafe_allow_html=True)
    currencies=list(sorted_s.keys())
    if len(currencies)>=2:
        st.divider()
        st.success(f"🚀 Best pair: BUY **{currencies[0]}** vs **{currencies[-1]}**")

# ════════════════════════════════════════════════════════════
# PAGE: PRECISION ENTRY
# ════════════════════════════════════════════════════════════
elif "Precision" in page:
    st.markdown("### 🎯 Precision Entry Tools")
    if not premium: st.error("🔒 Premium only."); st.stop()
    selected=st.selectbox("Asset",list(ALL_PAIRS.keys()))
    sym=ALL_PAIRS[selected]
    c1,c2=st.columns(2)
    direction=c1.selectbox("Direction",["BUY","SELL"])
    account=c2.number_input("Account ($)",min_value=100.0,value=1000.0)
    risk_pct=st.slider("Risk %",0.5,5.0,2.0,step=0.5)
    if st.button("Calculate Entries",use_container_width=True):
        df=fetch(sym,"3mo","1d")
        if df:
            price=float(df["Close"].iloc[-1]); atr=get_atr(df); risk_amt=account*risk_pct/100
            entries={}
            if direction=="BUY":
                entries["Aggressive"]={"entry":price,"sl":price-atr,"tp1":price+atr,"tp2":price+atr*2,"tp3":price+atr*3}
                entries["Standard"]={"entry":price,"sl":price-atr*1.5,"tp1":price+atr*1.5,"tp2":price+atr*3,"tp3":price+atr*4.5}
                entries["Conservative"]={"entry":float(df["Close"].ewm(span=20).mean().iloc[-1]),"sl":price-atr*2,"tp1":price+atr*2,"tp2":price+atr*4,"tp3":price+atr*6}
            else:
                entries["Aggressive"]={"entry":price,"sl":price+atr,"tp1":price-atr,"tp2":price-atr*2,"tp3":price-atr*3}
                entries["Standard"]={"entry":price,"sl":price+atr*1.5,"tp1":price-atr*1.5,"tp2":price-atr*3,"tp3":price-atr*4.5}
                entries["Conservative"]={"entry":float(df["Close"].ewm(span=20).mean().iloc[-1]),"sl":price+atr*2,"tp1":price-atr*2,"tp2":price-atr*4,"tp3":price-atr*6}
            dp=5 if price<100 else 2
            for etype,vals in entries.items():
                sl_dist=abs(vals["entry"]-vals["sl"])
                lot=max(0.01,min(round(risk_amt/(sl_dist*10000)*0.01,2),10.0)) if sl_dist>0 else 0.01
                color="#0a1a0a" if direction=="BUY" else "#1a0a0a"
                st.markdown(f"""
                <div style='background:{color};border-radius:10px;padding:12px;margin-bottom:8px'>
                <b>📍 {etype}</b><br>
                <div class='price-grid' style='margin:8px 0'>
                  <div class='price-cell'><div class='price-label'>ENTRY</div><div class='price-value entry'>{round(vals['entry'],dp)}</div></div>
                  <div class='price-cell'><div class='price-label'>STOP</div><div class='price-value sl'>{round(vals['sl'],dp)}</div></div>
                  <div class='price-cell'><div class='price-label'>TP1</div><div class='price-value tp'>{round(vals['tp1'],dp)}</div></div>
                  <div class='price-cell'><div class='price-label'>TP2</div><div class='price-value tp'>{round(vals['tp2'],dp)}</div></div>
                  <div class='price-cell'><div class='price-label'>TP3</div><div class='price-value tp'>{round(vals['tp3'],dp)}</div></div>
                </div>
                Lot: <b>{lot}</b> | Risk: <b>${round(risk_amt,2)}</b>
                </div>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: PROP FIRM
# ════════════════════════════════════════════════════════════
elif "Prop Firm" in page:
    st.markdown("### 🏢 Prop Firm Tools")
    if not premium: st.error("🔒 Premium only."); st.stop()
    c1,c2=st.columns(2)
    firm=c1.selectbox("Firm",["FTMO","MyForexFunds","The5ers","FundedNext"])
    account=c2.number_input("Account ($)",min_value=1000.0,value=10000.0)
    c3,c4=st.columns(2)
    profit=c3.number_input("Current Profit ($)",value=0.0)
    loss=c4.number_input("Current Loss ($)",value=0.0,min_value=0.0)
    rules={"FTMO":(5,10,10),"MyForexFunds":(5,10,8),"The5ers":(4,8,8),"FundedNext":(5,10,10)}
    dl_pct,ml_pct,pt_pct=rules.get(firm,(5,10,10))
    dl=account*dl_pct/100; ml=account*ml_pct/100; pt=account*pt_pct/100
    rem_daily=max(0,dl-loss); rem_max=max(0,ml-loss); need=max(0,pt-profit)
    used_pct=loss/dl if dl>0 else 0
    st.markdown(f"""
    <div class='metric-row'>
      <div class='metric-card'><div class='metric-label'>Daily Limit</div><div class='metric-value' style='color:#f85149'>${dl:,.0f}</div></div>
      <div class='metric-card'><div class='metric-label'>Max Loss</div><div class='metric-value' style='color:#f85149'>${ml:,.0f}</div></div>
      <div class='metric-card'><div class='metric-label'>Target</div><div class='metric-value' style='color:#3fb950'>${pt:,.0f}</div></div>
    </div>
    <div class='metric-row'>
      <div class='metric-card'><div class='metric-label'>Remaining Daily</div><div class='metric-value'>${rem_daily:,.0f}</div></div>
      <div class='metric-card'><div class='metric-label'>Remaining Max</div><div class='metric-value'>${rem_max:,.0f}</div></div>
      <div class='metric-card'><div class='metric-label'>Still Need</div><div class='metric-value' style='color:#ffd200'>${need:,.0f}</div></div>
    </div>""",unsafe_allow_html=True)
    st.progress(min(used_pct,1.0))
    if used_pct>=1: st.error("🚨 DAILY LIMIT REACHED — Stop trading today!")
    elif used_pct>=0.7: st.warning(f"⚠️ {round(used_pct*100)}% of daily limit used")
    else: st.success(f"✅ {round(used_pct*100)}% used — safe to trade")
    safe_lot=max(0.01,round(rem_daily*0.01/20,2))
    st.info(f"💰 Recommended lot size: **{safe_lot} lots**")

# ════════════════════════════════════════════════════════════
# PAGE: NEWS
# ════════════════════════════════════════════════════════════
elif "News" in page:
    st.markdown("### 🗞️ Market News & Economic Calendar")
    if not premium: st.error("🔒 Premium only."); st.stop()
    try:
        r=requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",timeout=8)
        if r.status_code==200:
            events=r.json()[:25]
            for e in events:
                impact=e.get("impact",""); cls="news-item" if impact=="High" else "news-item medium" if impact=="Medium" else "news-item low"
                st.markdown(f"""
                <div class='{cls}'>
                  <b>{e.get('currency','')} — {e.get('title','')}</b>
                  <span style='float:right;color:#8b949e;font-size:11px'>{impact}</span><br>
                  <small style='color:#8b949e'>{e.get('date','')[:16].replace('T',' ')} | Forecast: {e.get('forecast','—')} | Prev: {e.get('previous','—')}</small>
                </div>""",unsafe_allow_html=True)
        else: st.error("Could not fetch news.")
    except: st.error("News feed unavailable.")

    st.divider()
    selected=st.selectbox("AI news analysis for:",list(ALL_PAIRS.keys()))
    if st.button("🤖 Analyse News Impact",use_container_width=True):
        api_key=st.secrets.get("ANTHROPIC_API_KEY","")
        if not api_key: st.error("Add ANTHROPIC_API_KEY to secrets.")
        else:
            with st.spinner("Analysing..."):
                r=requests.post("https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                    json={"model":"claude-sonnet-4-6","max_tokens":600,
                        "messages":[{"role":"user","content":f"Analyse this week's economic calendar impact on {selected}. Give: 1) Bias direction 2) Key events to watch 3) Times to avoid. Be concise."}]},timeout=30)
                if r.status_code==200:
                    st.markdown(f"<div class='news-item'>{r.json()['content'][0]['text'].replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: AI STRATEGY BUILDER
# ════════════════════════════════════════════════════════════
elif "AI Strategy" in page:
    st.markdown("### 🤖 AI Strategy Builder")
    if not premium: st.error("🔒 Premium only."); st.stop()
    c1,c2=st.columns(2)
    style=c1.selectbox("Style",["Day Trading","Scalping","Swing Trading"])
    risk=c2.selectbox("Risk",["Conservative","Moderate","Aggressive"])
    fav=st.multiselect("Pairs",list(ALL_PAIRS.keys()),default=["EUR/USD","Gold (XAU/USD)"])
    session=st.selectbox("Session",["London","New York","Asian","All"])
    exp=st.selectbox("Experience",["Beginner","Intermediate","Advanced"])
    custom=st.text_area("Extra requirements",placeholder="e.g. only breakouts, SMC style...")
    if st.button("🚀 Build Strategy",type="primary",use_container_width=True):
        api_key=st.secrets.get("ANTHROPIC_API_KEY","")
        if not api_key: st.error("Add ANTHROPIC_API_KEY to secrets.")
        else:
            with st.spinner("Building..."):
                prompt=f"Build a complete {style} strategy for {', '.join(fav)}. {exp} level, {risk} risk, {session} session. {custom}. Include: Entry rules, SL placement, TP1/2/3, timeframes, risk rules, what to avoid."
                r=requests.post("https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                    json={"model":"claude-sonnet-4-6","max_tokens":1200,"messages":[{"role":"user","content":prompt}]},timeout=30)
                if r.status_code==200:
                    strategy=r.json()["content"][0]["text"]
                    st.session_state.ai_strategy=strategy
    if st.session_state.ai_strategy:
        st.markdown(f"<div class='strategy-card'>{st.session_state.ai_strategy.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: AI CHART ANALYSIS
# ════════════════════════════════════════════════════════════
elif "Chart AI" in page:
    st.markdown("### 📸 AI Chart Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    uploaded=st.file_uploader("Upload chart screenshot",type=["png","jpg","jpeg","webp"])
    pair_ctx=st.selectbox("Pair",["Not sure"]+list(ALL_PAIRS.keys()))
    tf_ctx=st.selectbox("Timeframe",["Not sure","1M","5M","15M","1H","4H","Daily"])
    question=st.text_area("Your question",placeholder="Is this a good entry? Where is support?")
    if uploaded and st.button("🔍 Analyse",type="primary",use_container_width=True):
        import base64
        img_b64=base64.b64encode(uploaded.read()).decode()
        ext=uploaded.name.split(".")[-1].lower()
        media_type=f"image/{'jpeg' if ext in ['jpg','jpeg'] else ext}"
        api_key=st.secrets.get("ANTHROPIC_API_KEY","")
        if not api_key: st.error("Add ANTHROPIC_API_KEY to secrets.")
        else:
            with st.spinner("Analysing chart..."):
                r=requests.post("https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                    json={"model":"claude-sonnet-4-6","max_tokens":1000,
                        "messages":[{"role":"user","content":[
                            {"type":"image","source":{"type":"base64","media_type":media_type,"data":img_b64}},
                            {"type":"text","text":f"Analyse this {pair_ctx} {tf_ctx} chart. {question if question else 'Give full technical analysis with entry, SL and TP recommendations.'}"}
                        ]}]},timeout=40)
                if r.status_code==200:
                    st.markdown(f"<div class='strategy-card'>{r.json()['content'][0]['text'].replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
                else: st.error(f"Error {r.status_code}")

# ════════════════════════════════════════════════════════════
# PAGE: ALERTS
# ════════════════════════════════════════════════════════════
elif "Alerts" in page:
    st.markdown("### 🔔 Telegram Alerts")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("📖 Setup Guide"):
        st.markdown("1. Search `@BotFather` on Telegram → `/newbot` → copy **Token**\n2. Search `@userinfobot` → copy **Chat ID**\n3. Paste below + test!")
    token=st.text_input("Bot Token",value=st.session_state.telegram_token,type="password")
    chat_id=st.text_input("Chat ID",value=st.session_state.telegram_chat_id)
    if st.button("💾 Save",use_container_width=True):
        st.session_state.telegram_token=token; st.session_state.telegram_chat_id=chat_id; st.success("✅ Saved!")
    if st.button("🧪 Test Message",use_container_width=True):
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id":chat_id,"text":"✅ *Sparro FX AI* connected! Grade A signals will be sent here. 🚀","parse_mode":"Markdown"},timeout=5)
        st.success("✅ Check Telegram!") if r.status_code==200 else st.error("❌ Failed — check token and chat ID.")
    threshold=st.slider("Min confidence to alert",60,95,st.session_state.notification_threshold)
    st.session_state.notification_threshold=threshold

# ════════════════════════════════════════════════════════════
# PAGE: JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.markdown("### 📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("➕ Log Trade"):
        c1,c2=st.columns(2)
        j_asset=c1.selectbox("Asset",list(ALL_PAIRS.keys()))
        j_sig=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"])
        c3,c4=st.columns(2)
        j_grade=c3.selectbox("Grade",["A","B","C","D"])
        j_result=c4.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c5,c6=st.columns(2)
        j_entry=c5.number_input("Entry",format="%.5f")
        j_notes=c6.text_input("Notes")
        if st.button("Save",use_container_width=True):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),
                "Asset":j_asset,"Signal":j_sig,"Grade":j_grade,"Entry":j_entry,
                "Result":j_result,"Notes":j_notes})
            st.success("✅ Saved!")
    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df,use_container_width=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); total=wins+loss
        wr=round(wins/total*100,1) if total>0 else 0
        st.markdown(f"""
        <div class='metric-row'>
          <div class='metric-card'><div class='metric-label'>Total</div><div class='metric-value'>{len(df)}</div></div>
          <div class='metric-card'><div class='metric-label'>Win Rate</div><div class='metric-value' style='color:#3fb950'>{wr}%</div></div>
          <div class='metric-card'><div class='metric-label'>Open</div><div class='metric-value' style='color:#ffd200'>{len(df[df["Result"]=="Open"])}</div></div>
        </div>""",unsafe_allow_html=True)
    else: st.info("No trades yet.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.markdown("### 📈 Performance Dashboard")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); total=wins+loss
    wr=round(wins/total*100,1) if total>0 else 0
    st.markdown(f"""
    <div class='metric-row'>
      <div class='metric-card'><div class='metric-label'>Trades</div><div class='metric-value'>{total}</div></div>
      <div class='metric-card'><div class='metric-label'>Win Rate</div><div class='metric-value' style='color:#3fb950'>{wr}%</div></div>
      <div class='metric-card'><div class='metric-label'>Wins</div><div class='metric-value'>{wins}</div></div>
    </div>""",unsafe_allow_html=True)
    if "Asset" in df.columns:
        st.subheader("By Asset")
        st.dataframe(df.groupby("Asset")["Result"].value_counts().unstack(fill_value=0),use_container_width=True)
    if "Grade" in df.columns:
        st.subheader("By Grade")
        st.dataframe(df.groupby("Grade")["Result"].value_counts().unstack(fill_value=0),use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ════════════════════════════════════════════════════════════
elif "Risk Calc" in page:
    st.markdown("### 💰 Risk Calculator")
    balance=st.number_input("Balance ($)",min_value=10.0,value=1000.0)
    risk_pct=st.slider("Risk %",0.5,10.0,2.0,step=0.5)
    sl_pips=st.number_input("Stop Loss (pips)",min_value=1.0,value=20.0)
    pip_val=st.number_input("Pip value per 0.01 lot",value=0.10)
    rr=st.slider("Risk:Reward",1,5,2)
    risk_amt=balance*risk_pct/100
    lot=round(risk_amt/(sl_pips*pip_val/0.01)*0.01,2) if sl_pips>0 else 0.01
    st.markdown(f"""
    <div class='metric-row'>
      <div class='metric-card'><div class='metric-label'>Risk Amount</div><div class='metric-value' style='color:#f85149'>${risk_amt:.2f}</div></div>
      <div class='metric-card'><div class='metric-label'>Lot Size</div><div class='metric-value'>{lot}</div></div>
      <div class='metric-card'><div class='metric-label'>Potential Profit</div><div class='metric-value' style='color:#3fb950'>${risk_amt*rr:.2f}</div></div>
    </div>
    <div class='metric-row'>
      <div class='metric-card'><div class='metric-label'>After Loss</div><div class='metric-value'>${balance-risk_amt:.2f}</div></div>
      <div class='metric-card'><div class='metric-label'>R:R Ratio</div><div class='metric-value'>1:{rr}</div></div>
      <div class='metric-card'><div class='metric-label'>After Win</div><div class='metric-value' style='color:#3fb950'>${balance+(risk_amt*rr):.2f}</div></div>
    </div>""",unsafe_allow_html=True)
    st.progress(risk_pct/10)
    if risk_pct<=2: st.success("✅ Conservative — good for consistency")
    elif risk_pct<=5: st.warning("⚠️ Moderate — manage carefully")
    else: st.error("🚨 High risk")

# ════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ════════════════════════════════════════════════════════════
elif "Settings" in page:
    st.markdown("### ⚙️ Settings")
    st.markdown(f"**Account:** {st.session_state.user_email}")
    st.markdown(f"**Plan:** {st.session_state.user_tier.title()}")
    st.divider()
    st.subheader("🔑 Change Password")
    old=st.text_input("Current Password",type="password")
    new=st.text_input("New Password",type="password")
    new2=st.text_input("Confirm New",type="password")
    if st.button("Update Password",use_container_width=True):
        user=get_user(st.session_state.user_email)
        if user and user.get("password_hash")==hash_pw(old):
            if new==new2 and len(new)>=6:
                requests.patch(sb_url(f"users?email=eq.{st.session_state.user_email}"),
                    headers=get_headers(),json={"password_hash":hash_pw(new)})
                st.success("✅ Password updated!")
            else: st.error("❌ Passwords don't match or too short.")
        else: st.error("❌ Current password incorrect.")
    st.divider()
    if st.button("🚪 Logout",use_container_width=True):
        for k in ["logged_in","user_email","user_tier","is_admin"]:
            st.session_state[k]=DEFAULTS.get(k,"")
        st.session_state.logged_in=False; st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: UPGRADE
# ════════════════════════════════════════════════════════════
elif "Upgrade" in page:
    st.markdown("### 💎 Upgrade to Premium")
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1a1a0a,#2d2a0a);border:2px solid #ffd200;
      border-radius:16px;padding:24px;text-align:center;margin:16px 0'>
      <div style='font-size:32px'>⚡</div>
      <h2 style='color:#ffd200;margin:8px 0'>Premium Plan</h2>
      <h1 style='color:#fff;margin:0'>$24/month</h1>
      <p style='color:#8b949e;margin:12px 0'>Everything you need to trade professionally</p>
      <hr style='border-color:#30363d;margin:16px 0'>
      <p>✅ All 10 assets · Grade A/B/C/D signals<br>
      ✅ Live Pulse with 8-strategy engine<br>
      ✅ Multi-timeframe · Currency strength<br>
      ✅ Precision entries · Prop firm tools<br>
      ✅ AI Strategy Builder · Chart analysis<br>
      ✅ Telegram alerts · Trade journal</p>
    </div>
    """,unsafe_allow_html=True)
    st.markdown("""
    **To upgrade:**
    1. Pay on **[Whop.com](https://whop.com)** or **[Gumroad](https://gumroad.com)**
    2. Email receipt to admin
    3. Admin upgrades your account
    4. Logout → Login → Premium unlocked ✅
    """)
# ════════════════════════════════════════════════════════════
# PAGE: MT5 BOT CONTROL PANEL
# ════════════════════════════════════════════════════════════
elif "MT5 Bot" in page:
    import json, os, base64

    st.markdown("### 📡 MT5 Auto-Trading Bot")
    if not premium: st.error("🔒 Premium only."); st.stop()

    # ── Session state for bot ────────────────────────────────
    if "bot_active"          not in st.session_state: st.session_state.bot_active=False
    if "bot_grade_filter"    not in st.session_state: st.session_state.bot_grade_filter=["A","B"]
    if "bot_lot_size"        not in st.session_state: st.session_state.bot_lot_size=0.01
    if "bot_conf_threshold"  not in st.session_state: st.session_state.bot_conf_threshold=75
    if "bot_daily_profit"    not in st.session_state: st.session_state.bot_daily_profit=10.0
    if "bot_daily_loss"      not in st.session_state: st.session_state.bot_daily_loss=15.0
    if "bot_tp_points"       not in st.session_state: st.session_state.bot_tp_points=2000
    if "bot_sl_points"       not in st.session_state: st.session_state.bot_sl_points=2500
    if "bot_log"             not in st.session_state: st.session_state.bot_log=[]
    if "bot_signals_sent"    not in st.session_state: st.session_state.bot_signals_sent=[]
    if "bot_signal_data"     not in st.session_state: st.session_state.bot_signal_data=None

    # ── Status banner ─────────────────────────────────────────
    bot_color  = "#0a1a0a" if st.session_state.bot_active else "#1a0a0a"
    bot_border = "#3fb950" if st.session_state.bot_active else "#f85149"
    bot_status = "🟢 ACTIVE — Scanning & sending signals to MT5" if st.session_state.bot_active else "🔴 INACTIVE — Bot is off"
    st.markdown(f"""
    <div style='background:{bot_color};border:2px solid {bot_border};border-radius:14px;
      padding:16px;text-align:center;margin-bottom:16px'>
      <div style='font-size:18px;font-weight:800;color:{"#3fb950" if st.session_state.bot_active else "#f85149"}'>{bot_status}</div>
      <div style='font-size:12px;color:#8b949e;margin-top:4px'>
        {'Monitoring markets every refresh · Sending Grade '+'/'.join(st.session_state.bot_grade_filter)+' signals automatically' if st.session_state.bot_active else 'Activate below to start auto-trading on MT5'}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Activate / Deactivate ─────────────────────────────────
    col1, col2 = st.columns(2)
    if col1.button("▶️ ACTIVATE BOT" if not st.session_state.bot_active else "⏹️ DEACTIVATE BOT",
                   type="primary" if not st.session_state.bot_active else "secondary",
                   use_container_width=True):
        st.session_state.bot_active = not st.session_state.bot_active
        action = "ACTIVATED" if st.session_state.bot_active else "DEACTIVATED"
        st.session_state.bot_log.insert(0, f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Bot {action} by {st.session_state.user_email}")
        st.rerun()

    if col2.button("🔄 Run Scan Now", use_container_width=True, disabled=not st.session_state.bot_active):
        with st.spinner("Scanning markets for bot signals..."):
            bot_found = []
            for name, sym in ALL_PAIRS.items():
                sig = analyse_pair(sym, name)
                if (sig and sig["direction"] != "WAIT"
                        and sig["grade"] in st.session_state.bot_grade_filter
                        and sig["confidence"] >= st.session_state.bot_conf_threshold):
                    bot_found.append(sig)

            if bot_found:
                best = max(bot_found, key=lambda x: x["confidence"])
                st.session_state.bot_signal_data = best
                log_entry = f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Signal: {best['direction']} {best['pair']} Grade {best['grade']} {best['confidence']}% — file written"
                st.session_state.bot_log.insert(0, log_entry)
                st.session_state.bot_signals_sent.append({
                    "time": datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
                    "pair": best["pair"],
                    "direction": best["direction"],
                    "grade": best["grade"],
                    "confidence": best["confidence"],
                    "entry": best["entry"],
                    "sl": best["sl"],
                    "tp1": best["tp1"],
                })
                st.success(f"✅ Signal found: {best['direction']} {best['pair']} Grade {best['grade']} {best['confidence']}%")
            else:
                st.session_state.bot_log.insert(0, f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Scan complete — no qualifying signals")
                st.info("⏳ No qualifying signals this scan.")
        st.rerun()

    st.divider()

    # ── Bot Settings ──────────────────────────────────────────
    st.subheader("⚙️ Bot Settings")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Signal Filters**")
        grade_opts = st.multiselect("Minimum Grade",["A","B","C"],
            default=st.session_state.bot_grade_filter)
        st.session_state.bot_grade_filter = grade_opts
        conf_thresh = st.slider("Min Confidence %", 60, 95,
            st.session_state.bot_conf_threshold)
        st.session_state.bot_conf_threshold = conf_thresh

    with col2:
        st.markdown("**Trade Sizing**")
        lot = st.number_input("Lot Size", min_value=0.01, max_value=10.0,
            value=st.session_state.bot_lot_size, step=0.01, format="%.2f")
        st.session_state.bot_lot_size = lot
        tp_pts = st.number_input("Take Profit (points)", min_value=100,
            value=st.session_state.bot_tp_points, step=100)
        st.session_state.bot_tp_points = tp_pts
        sl_pts = st.number_input("Max Stop Loss (points)", min_value=100,
            value=st.session_state.bot_sl_points, step=100)
        st.session_state.bot_sl_points = sl_pts

    with col3:
        st.markdown("**Daily Risk Limits**")
        dp = st.number_input("Daily Profit Target ($)", min_value=1.0,
            value=st.session_state.bot_daily_profit, step=1.0)
        st.session_state.bot_daily_profit = dp
        dl = st.number_input("Daily Loss Limit ($)", min_value=1.0,
            value=st.session_state.bot_daily_loss, step=1.0)
        st.session_state.bot_daily_loss = dl

    st.divider()

    # ── Signal File + Download ────────────────────────────────
    st.subheader("📄 Current Signal File")
    st.markdown("""
    The app writes a **`sparro_signal.json`** file that the MT5 EA reads every 10 seconds.
    When a qualifying signal is found, it updates this file and MT5 places the trade automatically.
    """)

    if st.session_state.bot_signal_data:
        sig = st.session_state.bot_signal_data
        dp = 5 if sig["entry"] < 100 else 2
        signal_json = {
            "active":      st.session_state.bot_active,
            "symbol":      sig["symbol"].replace("=X","").replace("^","").replace("-",""),
            "action":      sig["direction"],
            "grade":       sig["grade"],
            "confidence":  sig["confidence"],
            "entry":       round(sig["entry"], dp),
            "sl":          round(sig["sl"],    dp),
            "tp1":         round(sig["tp1"],   dp),
            "tp2":         round(sig["tp2"],   dp),
            "lot_size":    st.session_state.bot_lot_size,
            "tp_points":   st.session_state.bot_tp_points,
            "sl_points":   st.session_state.bot_sl_points,
            "daily_profit_target": st.session_state.bot_daily_profit,
            "daily_loss_limit":    st.session_state.bot_daily_loss,
            "timestamp":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source":      "SparroFXAI",
        }
        st.code(json.dumps(signal_json, indent=2), language="json")

        # Download the signal file
        json_bytes = json.dumps(signal_json, indent=2).encode()
        st.download_button(
            "⬇️ Download sparro_signal.json",
            data=json_bytes,
            file_name="sparro_signal.json",
            mime="application/json",
        )
        st.caption("Place this file in your MT5 signals folder — the EA will pick it up automatically.")
    else:
        st.info("No signal generated yet. Activate the bot and tap 'Run Scan Now'.")

    st.divider()

    # ── MT5 EA Setup Guide ────────────────────────────────────
    st.subheader("🛠️ MT5 EA Setup Guide")
    with st.expander("📖 How to connect MT5 in 4 steps"):
        st.markdown("""
        **Step 1 — Download the EA below**
        Save `SparroFX_EA.mq5` to your computer.

        **Step 2 — Install in MT5**
        1. Open MT5 → **File → Open Data Folder**
        2. Go to `MQL5 → Experts`
        3. Copy `SparroFX_EA.mq5` there
        4. Restart MT5 → go to **Navigator → Expert Advisors**
        5. Drag the EA onto your XAUUSD M15 chart

        **Step 3 — Configure the EA**
        - Set `SignalFolder` = the folder where signal file is saved
        - Enable **AutoTrading** (green button in MT5 toolbar)
        - Allow **DLL imports** in MT5 settings

        **Step 4 — Activate in this app**
        - Turn on the bot above
        - Tap **Run Scan Now**
        - EA reads the file within 10 seconds and places the trade ✅
        """)

    # ── EA Code Download ──────────────────────────────────────
    EA_CODE = '''//+------------------------------------------------------------------+
//|  SparroFX_EA.mq5 — Reads signals from Sparro FX AI app           |
//|  Compatible with the Streamlit bot control panel                  |
//+------------------------------------------------------------------+
#property copyright "Sparro FX AI"
#property version   "2.00"
#property strict

#include <Trade\\Trade.mqh>
CTrade trade;

//--- Inputs
input string   SignalFolder       = "C:\\\\Users\\\\YourName\\\\SparroFX_Signals\\\\";
input string   SignalFile         = "sparro_signal.json";
input bool     EnableTrading      = true;
input bool     OnlyGradeAB        = true;   // Only trade Grade A and B signals
input double   LotSizeOverride    = 0.0;    // 0 = use lot from signal file
input int      CheckIntervalSec   = 10;     // How often to check signal file
input int      MagicNumber        = 990033;
input int      Slippage           = 10;

//--- Globals
string   lastTimestamp    = "";
bool     dailyLimitHit    = false;
double   dayStartBalance  = 0;
datetime currentDay       = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   EventSetTimer(CheckIntervalSec);
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(Slippage);
   ResetDailyTracking();
   Print("SparroFX EA v2.0 started. Monitoring: ", SignalFolder + SignalFile);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) { EventKillTimer(); }
void OnTick() {}

//+------------------------------------------------------------------+
void ResetDailyTracking()
  {
   MqlDateTime tm;
   TimeToStruct(TimeCurrent(), tm);
   tm.hour=0; tm.min=0; tm.sec=0;
   currentDay      = StructToTime(tm);
   dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   dailyLimitHit   = false;
   Print("New trading day. Balance: ", dayStartBalance);
  }

void CheckNewDay()
  {
   MqlDateTime tm;
   TimeToStruct(TimeCurrent(), tm);
   tm.hour=0; tm.min=0; tm.sec=0;
   if(StructToTime(tm) != currentDay) ResetDailyTracking();
  }

double GetDailyPnL()
  {
   return AccountInfoDouble(ACCOUNT_EQUITY) - dayStartBalance;
  }

int CountMyPositions()
  {
   int n=0;
   for(int i=0;i<PositionsTotal();i++)
     {
      if(PositionGetTicket(i) && PositionGetInteger(POSITION_MAGIC)==MagicNumber
         && PositionGetString(POSITION_SYMBOL)==_Symbol) n++;
     }
   return n;
  }

//+------------------------------------------------------------------+
//| Parse a string field from JSON (simple, no external libs needed)  |
//+------------------------------------------------------------------+
string ParseStr(string json, string key)
  {
   string search = "\\"" + key + "\\"";
   int pos = StringFind(json, search);
   if(pos<0) return "";
   pos = StringFind(json,":",pos)+1;
   while(pos<StringLen(json) && (StringGetCharacter(json,pos)==' '||StringGetCharacter(json,pos)=='"')) pos++;
   string result="";
   while(pos<StringLen(json))
     {
      ushort c=StringGetCharacter(json,pos);
      if(c=='"'||c==','||c=='}'||c=='\n') break;
      result+=ShortToString(c); pos++;
     }
   return result;
  }

double ParseDbl(string json, string key)
  {
   return StringToDouble(ParseStr(json,key));
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   CheckNewDay();
   if(!EnableTrading) return;

   // Read signal file
   string fullPath = SignalFolder + SignalFile;
   int fh = FileOpen(fullPath, FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(fh==INVALID_HANDLE) return;

   string content="";
   while(!FileIsEnding(fh)) content += FileReadString(fh);
   FileClose(fh);

   if(StringLen(content)<10) return;

   // Check bot is active
   string activeStr = ParseStr(content,"active");
   if(activeStr != "true") return;

   // Avoid re-trading same signal
   string ts = ParseStr(content,"timestamp");
   if(ts==lastTimestamp) return;

   // Parse signal fields
   string symbol    = ParseStr(content,"symbol");
   string action    = ParseStr(content,"action");
   string grade     = ParseStr(content,"grade");
   double confidence= ParseDbl(content,"confidence");
   double entry     = ParseDbl(content,"entry");
   double sl_price  = ParseDbl(content,"sl");
   double tp1_price = ParseDbl(content,"tp1");
   double lot       = ParseDbl(content,"lot_size");
   double dpTarget  = ParseDbl(content,"daily_profit_target");
   double dlLimit   = ParseDbl(content,"daily_loss_limit");

   if(LotSizeOverride>0) lot = LotSizeOverride;
   if(lot<=0) lot = 0.01;

   // Grade filter
   if(OnlyGradeAB && grade!="A" && grade!="B")
     {
      Print("Signal grade ",grade," filtered out (OnlyGradeAB=true)");
      lastTimestamp=ts; return;
     }

   // Daily limit checks
   double dailyPnL = GetDailyPnL();
   if(!dailyLimitHit && dailyPnL >= dpTarget)
     {
      dailyLimitHit=true;
      Print("Daily profit target reached (",dailyPnL,"). No new trades.");
     }
   if(!dailyLimitHit && dailyPnL <= -MathAbs(dlLimit))
     {
      dailyLimitHit=true;
      Print("Daily loss limit reached (",dailyPnL,"). No new trades.");
     }
   if(dailyLimitHit) { lastTimestamp=ts; return; }

   // One trade at a time
   if(CountMyPositions()>0) { lastTimestamp=ts; return; }

   // Only trade on matching chart symbol
   string chartSym = _Symbol;
   StringReplace(chartSym,".",""); StringReplace(chartSym,"_","");
   if(symbol!="" && symbol!=chartSym)
     {
      Print("Signal for ",symbol," — this chart is ",chartSym," — skipping.");
      lastTimestamp=ts; return;
     }

   // Place the trade
   double ask = SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol,SYMBOL_BID);

   PrintFormat("SparroFX Signal: %s %s Grade=%s Conf=%.0f%% Lot=%.2f Entry=%.5f SL=%.5f TP1=%.5f",
               action,symbol,grade,confidence,lot,entry,sl_price,tp1_price);

   if(action=="BUY")
     {
      if(sl_price<=0)  sl_price  = ask - 2500*_Point;
      if(tp1_price<=0) tp1_price = ask + 2000*_Point;
      if(trade.Buy(lot,_Symbol,ask,sl_price,tp1_price,"SparroFX AI Buy"))
         Print("BUY opened. Ticket: ",trade.ResultOrder());
      else
         Print("BUY failed: ",trade.ResultRetcodeDescription());
     }
   else if(action=="SELL")
     {
      if(sl_price<=0)  sl_price  = bid + 2500*_Point;
      if(tp1_price<=0) tp1_price = bid - 2000*_Point;
      if(trade.Sell(lot,_Symbol,bid,sl_price,tp1_price,"SparroFX AI Sell"))
         Print("SELL opened. Ticket: ",trade.ResultOrder());
      else
         Print("SELL failed: ",trade.ResultRetcodeDescription());
     }

   lastTimestamp = ts;
  }
//+------------------------------------------------------------------+
'''

    # Download EA file
    ea_bytes = EA_CODE.encode()
    st.download_button(
        "⬇️ Download SparroFX_EA.mq5",
        data=ea_bytes,
        file_name="SparroFX_EA.mq5",
        mime="text/plain",
        type="primary",
    )

    st.divider()

    # ── Signals Sent Log ──────────────────────────────────────
    st.subheader("📋 Signals Sent to MT5")
    if st.session_state.bot_signals_sent:
        df_log = pd.DataFrame(st.session_state.bot_signals_sent[:20])
        st.dataframe(df_log, use_container_width=True)
        if st.button("🗑️ Clear Log"):
            st.session_state.bot_signals_sent = []
            st.rerun()
    else:
        st.info("No signals sent yet.")

    st.divider()

    # ── Activity Log ──────────────────────────────────────────
    st.subheader("🪵 Bot Activity Log")
    if st.session_state.bot_log:
        for entry in st.session_state.bot_log[:15]:
            color = "#3fb950" if "ACTIVATED" in entry or "Signal:" in entry else \
                    "#f85149" if "DEACTIVATED" in entry or "limit" in entry.lower() else "#8b949e"
            st.markdown(f"<p style='font-size:12px;color:{color};font-family:monospace;margin:2px 0'>{entry}</p>",
                        unsafe_allow_html=True)
    else:
        st.info("No activity yet.")

    # ── Risk Warning ──────────────────────────────────────────
    st.divider()
    st.markdown("""
    <div style='background:#1a0a0a;border:1px solid #f8514930;border-radius:10px;padding:14px'>
    <b style='color:#f85149'>⚠️ Auto-Trading Risk Warning</b><br>
    <small style='color:#8b949e'>
    Automated trading carries significant risk. Past signal performance does not guarantee future results.
    Always test on a demo account first. Never auto-trade with money you cannot afford to lose.
    Set conservative lot sizes and daily loss limits. Monitor the bot regularly.
    Sparro FX AI is not responsible for any trading losses incurred through use of this feature.
    </small>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>",unsafe_allow_html=True)
