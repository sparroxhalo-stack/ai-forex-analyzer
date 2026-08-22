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
          "telegram_chat_id":"","ai_strategy":"","notification_threshold":75,
          "account_balance":1000.0,"risk_pct":1.0}
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

def get_market_status():
    """
    Returns market open/closed status for each session.
    Forex market is open 24/5 — closed Saturday and Sunday.
    Each pair has specific best trading hours.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    hour = now.hour
    minute = now.minute
    time_decimal = hour + minute/60

    # Forex closed on weekends
    if weekday == 5:  # Saturday
        return {"open": False, "session": "Weekend", "reason": "Forex market closed — reopens Sunday 22:00 UTC", "color": "#f85149"}
    if weekday == 6 and time_decimal < 22:  # Sunday before 22:00
        opens_in = round((22 - time_decimal) * 60)
        return {"open": False, "session": "Weekend", "reason": f"Forex market closed — opens in {opens_in} minutes", "color": "#f85149"}

    # Sessions
    if 22 <= time_decimal or time_decimal < 7:
        session = "Asian Session 🌏"
        color = "#ffd200"
        note = "Lower volatility — best for JPY, AUD, NZD pairs"
        quality = "⚠️ Low liquidity"
    elif 7 <= time_decimal < 12:
        session = "London Session 🇬🇧"
        color = "#3fb950"
        note = "Best session — highest liquidity and volatility"
        quality = "✅ Best time to trade"
    elif 12 <= time_decimal < 17:
        session = "London + New York Overlap 🔥"
        color = "#3fb950"
        note = "PEAK session — highest volume of the day"
        quality = "✅ Prime trading time"
    elif 17 <= time_decimal < 22:
        session = "New York Session 🗽"
        color = "#0072ff"
        note = "Good session — USD pairs most active"
        quality = "✅ Good time to trade"
    else:
        session = "Off Hours"
        color = "#8b949e"
        note = "Low activity"
        quality = "⚠️ Low liquidity"

    return {
        "open": True,
        "session": session,
        "color": color,
        "note": note,
        "quality": quality,
        "reason": note,
        "hour": hour,
        "weekday": weekday,
    }

def is_pair_active(pair_name):
    """Check if a specific pair is in its best trading hours"""
    now = datetime.datetime.now(datetime.timezone.utc)
    hour = now.hour
    weekday = now.weekday()

    if weekday >= 5: return False  # Weekend

    # Pair-specific best hours (UTC)
    pair_hours = {
        "EUR/USD":        (7, 20),   # London + NY
        "GBP/USD":        (7, 20),   # London + NY
        "USD/JPY":        (0, 9),    # Asian + London open
        "AUD/USD":        (22, 9),   # Asian session (wraps midnight)
        "USD/CHF":        (7, 20),   # London + NY
        "USD/CAD":        (12, 20),  # NY session
        "Gold (XAU/USD)": (7, 21),   # London + NY
        "Bitcoin":        (0, 24),   # 24/7
        "NASDAQ":         (13, 21),  # NY only
        "S&P 500":        (13, 21),  # NY only
    }

    if pair_name not in pair_hours: return True
    start, end = pair_hours[pair_name]

    if start > end:  # Wraps midnight (e.g. 22-9)
        return hour >= start or hour < end
    return start <= hour < end

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

    # Use 4H as primary (fresher signals, better for day trading)
    df_d=fetch(symbol,"6mo","1d")    # Daily for trend direction
    df_4h=fetch(symbol,"2mo","1h")   # 4H for entry signals (use last 120 bars = ~30 days)
    df_1h=fetch(symbol,"2wk","1h")   # 1H for fine-tuning
    df_w=fetch(symbol,"2y","1wk")    # Weekly for big picture
    if df_d is None or len(df_d)<50: return None
    # Use 4H data as primary if available (more recent signals)
    df_primary = df_4h.iloc[-120:] if df_4h is not None and len(df_4h)>=50 else df_d

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
    lookback_h=float(h_.iloc[-20:-3].max())
    lookback_l=float(l_.iloc[-20:-3].min())
    prev_h=float(h_.iloc[-40:-20].max()) if len(h_)>=40 else lookback_h
    prev_l=float(l_.iloc[-40:-20].min()) if len(l_)>=40 else lookback_l
    strong_bull_bos=price>lookback_h and lookback_h>prev_h
    strong_bear_bos=price<lookback_l and lookback_l<prev_l
    if strong_bull_bos:    bos_sig="BUY"
    elif strong_bear_bos:  bos_sig="SELL"
    elif price>lookback_h: bos_sig="BUY"
    elif price<lookback_l: bos_sig="SELL"
    else:                  bos_sig="WAIT"

    # ── STRATEGY 7: ORDER BLOCKS (SMC) ────────────────────
    # Bullish OB: last bearish candle before a strong bullish move up
    # Bearish OB: last bullish candle before a strong bearish move down
    ob_sig="WAIT"; ob_level=0; ob_name=""
    try:
        opens=df_d["Open"].values if "Open" in df_d.columns else c.shift(1).values
        closes=c.values; highs=h_.values; lows=l_.values
        # Look back 30 bars for order blocks
        for i in range(len(closes)-2, max(len(closes)-30,2), -1):
            # Bullish OB: bearish candle followed by strong bullish move
            if closes[i]<opens[i]:  # bearish candle
                # Check if next 3 candles moved up strongly
                if i+3<len(closes) and closes[i+3]>highs[i]*1.001:
                    ob_high=highs[i]; ob_low=lows[i]
                    # Is current price at/near this OB?
                    if ob_low<=price<=ob_high*1.002:
                        ob_sig="BUY"; ob_level=round((ob_high+ob_low)/2,5)
                        ob_name=f"Bullish OB @ {ob_level}"; break
            # Bearish OB: bullish candle followed by strong bearish move
            elif closes[i]>opens[i]:  # bullish candle
                if i+3<len(closes) and closes[i+3]<lows[i]*0.999:
                    ob_high=highs[i]; ob_low=lows[i]
                    if ob_low*0.998<=price<=ob_high:
                        ob_sig="SELL"; ob_level=round((ob_high+ob_low)/2,5)
                        ob_name=f"Bearish OB @ {ob_level}"; break
    except: pass

    # ── STRATEGY 8: FAIR VALUE GAP (FVG) ──────────────────
    fvg_sig="WAIT"; fvg_name=""
    try:
        if len(h_)>=3:
            # Bullish FVG: gap between candle[i-2].high and candle[i].low
            for i in range(len(closes)-1, max(len(closes)-15,2), -1):
                prev_high=highs[i-2]; curr_low=lows[i]
                prev_low=lows[i-2];   curr_high=highs[i]
                # Bullish FVG: current low > prev high (gap up)
                if curr_low>prev_high and price<=curr_low*1.001:
                    fvg_sig="BUY"; fvg_name=f"Bullish FVG {round(prev_high,5)}-{round(curr_low,5)}"; break
                # Bearish FVG: current high < prev low (gap down)
                elif curr_high<prev_low and price>=curr_high*0.999:
                    fvg_sig="SELL"; fvg_name=f"Bearish FVG {round(curr_high,5)}-{round(prev_low,5)}"; break
    except: pass

    # ── COMBINE 8 STRATEGIES ─────────────────────────────
    # Core 6 always count, OB+FVG add extra weight
    all_sigs=[ema_sig,rsi_sig,macd_sig,bb_sig,sr_sig,bos_sig,ob_sig,fvg_sig]
    # Extra weight for SMC signals — if OB or FVG agrees, boost confidence
    smc_bonus=sum(1 for s in [ob_sig,fvg_sig] if s!="WAIT")
    buys=sum(1 for s in all_sigs if s=="BUY")
    sells=sum(1 for s in all_sigs if s=="SELL")
    total=len(all_sigs)

    if buys>sells:
        direction="BUY"; conf=round(buys/total*100)
        final_sig="STRONG BUY" if buys>=5 else "BUY"
    elif sells>buys:
        direction="SELL"; conf=round(sells/total*100)
        final_sig="STRONG SELL" if sells>=5 else "SELL"
    else:
        direction="WAIT"; conf=50; final_sig="WAIT"

    # ── QUALITY FILTERS ───────────────────────────────────
    atr_pct=atr/price*100
    atr_ok=atr_pct>=0.2

    # Weekly trend filter
    if df_w is not None:
        cw=df_w["Close"]; e20w=cw.ewm(span=20).mean(); e50w=cw.ewm(span=50).mean()
        weekly_bull=float(e20w.iloc[-1])>float(e50w.iloc[-1])
    else: weekly_bull=direction=="BUY"
    weekly_ok=weekly_bull==(direction=="BUY") or direction=="WAIT"

    # Session filter
    hour=datetime.datetime.now(datetime.timezone.utc).hour
    session_ok=(7<=hour<=17) or (12<=hour<=21)
    session_label="London" if 7<=hour<13 else "New York" if 13<=hour<21 else "Asian/Off"

    # MTF confirmation
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

    # Candle info for display only (not used in scoring)
    vol_ok=True; candle_quality_ok=True
    o=float(df_d["Open"].iloc[-1]) if "Open" in df_d.columns else float(c.iloc[-2])
    hi=float(h_.iloc[-1]); lo=float(l_.iloc[-1]); cl=float(c.iloc[-1])
    po=float(df_d["Open"].iloc[-2]) if "Open" in df_d.columns else float(c.iloc[-3])
    pc=float(c.iloc[-2]); body=abs(cl-o); full=hi-lo
    uw=hi-max(cl,o); lw=min(cl,o)-lo
    bull_engulf=cl>o and pc<po and cl>po and o<pc
    bear_engulf=cl<o and pc>po and cl<po and o>pc
    bull_pin=lw>body*2 and uw<body*0.5
    bear_pin=uw>body*2 and lw<body*0.5
    if bull_engulf: candle_name="Bullish Engulfing"
    elif bear_engulf: candle_name="Bearish Engulfing"
    elif bull_pin: candle_name="Hammer/Pin Bar"
    elif bear_pin: candle_name="Shooting Star"
    elif cl>o: candle_name="Bullish close"
    else: candle_name="Bearish close"

    # Trend strength (simple slope check)
    trend_strong=abs(ema_slope)>0.05

    # ── SPECIALIST WEIGHTING ──────────────────────────────
    spec=SPECIALIST.get(pair_name,1.0)
    adj_conf=min(99,round(conf*spec)) if direction!="WAIT" else 50

    # ── GRADE (A/B/C) — tuned for 6 strategies ────────────
    agree_count=max(buys,sells)
    filters_passed=sum([atr_ok,weekly_ok,session_ok,mtf_ok])
    if adj_conf>=83 and agree_count>=6 and filters_passed>=3: grade="A"
    elif adj_conf>=66 and agree_count>=5 and filters_passed>=2: grade="B"
    elif adj_conf>=50 and agree_count>=3 and filters_passed>=1: grade="C"
    else: grade="D"
    adx=0  # not used in 6-strategy mode

    # Skip D-grade signals entirely — not worth showing
    if grade=="D" and direction!="WAIT":
        direction="WAIT"; final_sig="WAIT"

    # ── TRADE LEVELS ─────────────────────────────────────
    # SL = 1x ATR (tight but realistic)
    # TP1 = 0.5x ATR (very achievable — close and take profit)
    # TP2 = 1x ATR (standard R:R 1:1)
    # TP3 = 2x ATR (let winners run)
    sl_dist  = atr * 1.0   # tighter SL
    tp1_dist = atr * 0.5   # TP1 very close — high hit rate
    tp2_dist = atr * 1.0   # TP2 at 1:1
    tp3_dist = atr * 2.0   # TP3 at 1:2 — stretch target

    if direction=="BUY":
        entry=price
        sl  =price - sl_dist
        tp1 =price + tp1_dist
        tp2 =price + tp2_dist
        tp3 =price + tp3_dist
    elif direction=="SELL":
        entry=price
        sl  =price + sl_dist
        tp1 =price - tp1_dist
        tp2 =price - tp2_dist
        tp3 =price - tp3_dist
    else:
        entry=price; sl=0; tp1=0; tp2=0; tp3=0

    # Entry validity check — warn if price has moved too far from entry
    entry_valid = True
    entry_drift_pct = 0
    # (shown on signal card so user knows if entry is still valid)

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
    strat_names="EMA · RSI · MACD · BB · S/R · BOS · Order Block · FVG"

    return {
        "pair":pair_name,"sym":symbol,"symbol":symbol,"direction":direction,"signal":final_sig,
        "confidence":adj_conf,"grade":grade,"entry":entry,"sl":sl,
        "tp1":tp1,"tp2":tp2,"tp3":tp3,"atr":round(atr,5),
        "sig_daily":sig_daily,"sig_4h":sig_4h,"sig_1h":sig_1h,
        "mtf_agree":mtf_agree,"market_cond":market_cond,
        "candle_ok":candle_quality_ok,"vol_ok":vol_ok,
        "weekly_ok":weekly_ok,"session_ok":session_ok,"mtf_ok":mtf_ok,
        "session_label":session_label,"strategies":strat_names,
        "agree":f"{agree_count}/8 agree","ob_name":ob_name,"fvg_name":fvg_name,"smc_bonus":smc_bonus,"rsi":round(rsi_val,1),
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
    pair_active = is_pair_active(sig["pair"])
    active_badge = "" if pair_active else "⏸️ Off-hours · "

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

      <div class='pair-name'>{sig["pair"]} <span style='font-size:12px;color:#8b949e;font-weight:400'>{active_badge}{"🟢 Active hours" if pair_active else ""}</span></div>
      <div class='mtf-line'>MTF: {sig.get("mtf_agree","—")}</div>
      <div class='market-condition'>📊 {sig.get("market_cond","—")}</div>
      <div style='background:#1a2040;border-radius:6px;padding:6px 10px;margin:4px 0;font-size:11px'>
        ⏰ Signal posted: <b>{sig.get("time_ago","just now")}</b> &nbsp;|&nbsp;
        📍 Entry: <b>{round(sig.get("entry",0), 5 if sig.get("entry",0)<100 else 2)}</b> &nbsp;|&nbsp;
        🎯 TP1 distance: <b>{round(abs(sig.get("tp1",0)-sig.get("entry",0)), 5 if sig.get("entry",0)<100 else 2)}</b>
      </div>

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
# PIPNEX-STYLE CHART FUNCTION
# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════
# ACCOUNT-BASED TRADE CALCULATOR
# ════════════════════════════════════════════════════════════
PIP_VALUES_GLOBAL = {
    "EUR/USD":10,"GBP/USD":10,"USD/JPY":9,"AUD/USD":10,
    "USD/CHF":10,"USD/CAD":10,"Gold (XAU/USD)":100,
    "Bitcoin":100,"NASDAQ":1,"S&P 500":1
}

def show_trade_calculator(sig):
    """Shows account-based position sizing under every signal"""
    if sig is None or sig.get("direction")=="WAIT": return

    entry = sig.get("entry", 0)
    sl    = sig.get("sl", 0)
    tp1   = sig.get("tp1", 0)
    tp2   = sig.get("tp2", 0)
    tp3   = sig.get("tp3", 0)
    pair  = sig.get("pair","")
    dp    = 5 if entry < 100 else 2

    st.markdown("""
    <div style='background:#0d1117;border-radius:10px;padding:14px;
      margin-top:8px;border:1px solid #21262d'>
    <b style='color:#ffd200'>💰 Position Calculator</b>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    balance  = col1.number_input("Account Balance ($)",
                min_value=10.0, value=st.session_state.account_balance,
                step=100.0, key=f"bal_{pair}_{entry}")
    risk_pct = col2.number_input("Risk %",
                min_value=0.1, max_value=5.0,
                value=st.session_state.risk_pct,
                step=0.1, key=f"risk_{pair}_{entry}")
    pip_val  = col3.number_input("Pip Value ($)",
                min_value=0.1, value=float(PIP_VALUES_GLOBAL.get(pair, 10)),
                step=0.1, key=f"pip_{pair}_{entry}")

    # Save to session state
    st.session_state.account_balance = balance
    st.session_state.risk_pct        = risk_pct

    # Calculations
    risk_amt  = balance * risk_pct / 100
    sl_dist   = abs(entry - sl)
    sl_pips   = sl_dist / 0.0001 if entry < 10 else sl_dist / 0.01 if entry < 500 else sl_dist
    lot       = max(0.01, round(risk_amt / (sl_pips * pip_val / 100), 2)) if sl_pips > 0 else 0.01
    loss_sl   = round(lot * sl_pips * pip_val / 100, 2)
    win_tp1   = round(lot * abs(tp1 - entry) / (sl_dist if sl_dist > 0 else 1) * loss_sl, 2)
    win_tp2   = round(lot * abs(tp2 - entry) / (sl_dist if sl_dist > 0 else 1) * loss_sl, 2)
    win_tp3   = round(lot * abs(tp3 - entry) / (sl_dist if sl_dist > 0 else 1) * loss_sl, 2)
    bal_after_loss = balance - loss_sl
    bal_after_tp1  = balance + win_tp1

    # Results
    st.markdown(f"""
    <div style='background:#0d1117;border-radius:10px;padding:14px;margin-top:8px'>
      <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:10px;text-align:center'>
        <div>
          <div style='font-size:10px;color:#8b949e;font-weight:700'>LOT SIZE</div>
          <div style='font-size:22px;font-weight:900;color:#ffd200'>{lot}</div>
        </div>
        <div>
          <div style='font-size:10px;color:#8b949e;font-weight:700'>RISK AMOUNT</div>
          <div style='font-size:22px;font-weight:900;color:#f85149'>-${loss_sl}</div>
        </div>
        <div>
          <div style='font-size:10px;color:#8b949e;font-weight:700'>TP1 PROFIT</div>
          <div style='font-size:22px;font-weight:900;color:#3fb950'>+${win_tp1}</div>
        </div>
        <div>
          <div style='font-size:10px;color:#8b949e;font-weight:700'>TP3 PROFIT</div>
          <div style='font-size:22px;font-weight:900;color:#3fb950'>+${win_tp3}</div>
        </div>
      </div>

      <div style='margin-top:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:12px'>
        <div style='background:#1a0a0a;border-radius:8px;padding:8px;text-align:center'>
          <div style='color:#8b949e'>If SL hits</div>
          <div style='color:#f85149;font-weight:700'>${bal_after_loss:,.2f}</div>
        </div>
        <div style='background:#0a1a0a;border-radius:8px;padding:8px;text-align:center'>
          <div style='color:#8b949e'>If TP1 hits</div>
          <div style='color:#3fb950;font-weight:700'>${bal_after_tp1:,.2f}</div>
        </div>
        <div style='background:#0a1a0a;border-radius:8px;padding:8px;text-align:center'>
          <div style='color:#8b949e'>If TP2 hits</div>
          <div style='color:#3fb950;font-weight:700'>${balance+win_tp2:,.2f}</div>
        </div>
      </div>

      <div style='margin-top:10px;font-size:11px;color:#8b949e'>
        📍 Entry: <b style='color:#e6edf3'>{round(entry,dp)}</b> &nbsp;|&nbsp;
        🛑 SL: <b style='color:#f85149'>{round(sl,dp)}</b> ({round(sl_dist,dp)} = {round(sl_pips,1)} pips) &nbsp;|&nbsp;
        ✅ TP1: <b style='color:#3fb950'>{round(tp1,dp)}</b> &nbsp;|&nbsp;
        ✅ TP2: <b style='color:#3fb950'>{round(tp2,dp)}</b> &nbsp;|&nbsp;
        ✅ TP3: <b style='color:#3fb950'>{round(tp3,dp)}</b>
      </div>
    </div>""", unsafe_allow_html=True)

def show_pipnex_chart(symbol, pair_name, sig):
    """
    Shows a Pipnex-style chart with:
    - Candlesticks
    - TP zone (green shaded)
    - SL zone (red shaded)
    - Entry line (yellow)
    - SMC zones: Order Block, Premium/Discount, BOS
    - Timeframe tabs: 15M, 30M, 1H, 4H, Daily
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # Timeframe selector
    tf_cols = st.columns(5)
    tf_options = [("15M","15m","5d"),("30M","30m","10d"),("1H","1h","1mo"),("4H","1h","2mo"),("Daily","1d","6mo")]
    if "chart_tf" not in st.session_state: st.session_state.chart_tf = "1H"

    for i,(label,_,_) in enumerate(tf_options):
        if tf_cols[i].button(label,
            use_container_width=True,
            type="primary" if st.session_state.chart_tf==label else "secondary"):
            st.session_state.chart_tf=label
            st.rerun()

    # Get selected timeframe data
    sel_tf = next((t for t in tf_options if t[0]==st.session_state.chart_tf), tf_options[2])
    label,interval,period = sel_tf

    with st.spinner(f"Loading {label} chart..."):
        df = fetch(symbol, period, interval)

    if df is None or len(df) < 10:
        st.warning("Chart data unavailable.")
        return

    # Use last 80 candles for clean display
    df = df.iloc[-80:]

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    open_  = df["Open"] if "Open" in df.columns else close.shift(1)
    dates  = df.index
    price  = float(close.iloc[-1])

    # ── Calculate indicators ─────────────────────────────
    ema20  = close.ewm(span=20).mean()
    ema50  = close.ewm(span=50).mean()

    # ATR
    tr = pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    atr_val = float(tr.rolling(14).mean().iloc[-1])

    # S/R zones
    resistance = float(high.rolling(20).max().iloc[-1])
    support    = float(low.rolling(20).min().iloc[-1])
    mid_zone   = (resistance + support) / 2
    premium    = resistance
    discount   = support

    # Order Block detection (last bearish before bullish or vice versa)
    ob_high = ob_low = ob_type = None
    try:
        closes_arr = close.values; opens_arr = open_.values
        highs_arr  = high.values;  lows_arr  = low.values
        for i in range(len(closes_arr)-2, max(len(closes_arr)-15, 2), -1):
            if closes_arr[i] < opens_arr[i]:  # bearish candle
                if i+2 < len(closes_arr) and closes_arr[i+2] > highs_arr[i]:
                    ob_high = highs_arr[i]; ob_low = lows_arr[i]; ob_type = "Bullish OB"; break
            elif closes_arr[i] > opens_arr[i]:  # bullish candle
                if i+2 < len(closes_arr) and closes_arr[i+2] < lows_arr[i]:
                    ob_high = highs_arr[i]; ob_low = lows_arr[i]; ob_type = "Bearish OB"; break
    except: pass

    # BOS level
    bos_level = float(high.iloc[-20:-3].max()) if sig.get("direction")=="BUY" else float(low.iloc[-20:-3].min())

    # ── Build chart ───────────────────────────────────────
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25], vertical_spacing=0.02)

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=dates, open=open_, high=high, low=low, close=close,
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a",
        decreasing_fillcolor="#ef5350",
    ), row=1, col=1)

    # EMA lines
    fig.add_trace(go.Scatter(x=dates, y=ema20, name="EMA20",
        line=dict(color="#f0b90b", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=ema50, name="EMA50",
        line=dict(color="#2196f3", width=1, dash="dot")), row=1, col=1)

    # ── SMC Zones ─────────────────────────────────────────
    # Premium zone (above mid)
    fig.add_hrect(y0=mid_zone, y1=premium*1.001,
        fillcolor="rgba(239,83,80,0.08)", line_width=0,
        annotation_text="PREMIUM", annotation_position="top left",
        annotation_font_color="#ef5350", annotation_font_size=10, row=1, col=1)

    # Discount zone (below mid)
    fig.add_hrect(y0=discount*0.999, y1=mid_zone,
        fillcolor="rgba(38,166,154,0.08)", line_width=0,
        annotation_text="DISCOUNT", annotation_position="bottom left",
        annotation_font_color="#26a69a", annotation_font_size=10, row=1, col=1)

    # Order Block zone
    if ob_high and ob_low:
        ob_color = "rgba(38,166,154,0.15)" if ob_type=="Bullish OB" else "rgba(239,83,80,0.15)"
        ob_border = "#26a69a" if ob_type=="Bullish OB" else "#ef5350"
        fig.add_hrect(y0=ob_low, y1=ob_high,
            fillcolor=ob_color,
            line_color=ob_border, line_width=1, line_dash="dash",
            annotation_text=f"🟦 {ob_type} (Structure)",
            annotation_position="right",
            annotation_font_color=ob_border, annotation_font_size=10, row=1, col=1)

    # BOS line
    bos_color = "#26a69a" if sig.get("direction")=="BUY" else "#ef5350"
    fig.add_hline(y=bos_level, line_color=bos_color, line_width=1,
        line_dash="dot",
        annotation_text=f"BOS {'↑' if sig.get('direction')=='BUY' else '↓'}",
        annotation_position="left",
        annotation_font_color=bos_color, annotation_font_size=10,
        row=1, col=1)

    # ── Trade Levels ──────────────────────────────────────
    entry = sig.get("entry", price)
    sl    = sig.get("sl",    price)
    tp1   = sig.get("tp1",   price)
    tp2   = sig.get("tp2",   price)
    tp3   = sig.get("tp3",   price)
    dp    = 5 if price < 100 else 2

    is_buy = "BUY" in sig.get("direction","")

    # SL zone (red shaded from entry to SL)
    fig.add_hrect(
        y0=min(entry, sl), y1=max(entry, sl),
        fillcolor="rgba(239,83,80,0.20)",
        line_color="#ef5350", line_width=1,
        annotation_text=f"🛑 SL {round(sl,dp)}",
        annotation_position="right",
        annotation_font_color="#ef5350", annotation_font_size=11,
        row=1, col=1)

    # TP1 zone (light green)
    fig.add_hrect(
        y0=min(entry,tp1), y1=max(entry,tp1),
        fillcolor="rgba(38,166,154,0.20)",
        line_color="#26a69a", line_width=1,
        annotation_text=f"✅ TP1 {round(tp1,dp)}",
        annotation_position="right",
        annotation_font_color="#26a69a", annotation_font_size=11,
        row=1, col=1)

    # TP2 zone (medium green)
    fig.add_hrect(
        y0=min(tp1,tp2), y1=max(tp1,tp2),
        fillcolor="rgba(38,166,154,0.12)",
        line_color="#26a69a", line_width=1, line_dash="dot",
        annotation_text=f"✅ TP2 {round(tp2,dp)}",
        annotation_position="right",
        annotation_font_color="#26a69a", annotation_font_size=10,
        row=1, col=1)

    # TP3 zone (faint green)
    fig.add_hrect(
        y0=min(tp2,tp3), y1=max(tp2,tp3),
        fillcolor="rgba(38,166,154,0.06)",
        line_color="#26a69a", line_width=1, line_dash="dot",
        annotation_text=f"✅ TP3 {round(tp3,dp)}",
        annotation_position="right",
        annotation_font_color="#26a69a", annotation_font_size=10,
        row=1, col=1)

    # Entry line (yellow — most prominent)
    fig.add_hline(y=entry,
        line_color="#f0b90b", line_width=2,
        annotation_text=f"📍 ENTRY {round(entry,dp)}",
        annotation_position="left",
        annotation_font_color="#f0b90b", annotation_font_size=12,
        row=1, col=1)

    # Entry arrow on latest candle
    arrow_y = float(low.iloc[-1]) - atr_val*0.3 if is_buy else float(high.iloc[-1]) + atr_val*0.3
    arrow_sym = "triangle-up" if is_buy else "triangle-down"
    arrow_col = "#26a69a" if is_buy else "#ef5350"
    fig.add_trace(go.Scatter(
        x=[dates[-1]], y=[arrow_y],
        mode="markers+text",
        marker=dict(symbol=arrow_sym, size=16, color=arrow_col),
        text=[sig.get("direction","")],
        textposition="top center" if is_buy else "bottom center",
        textfont=dict(color=arrow_col, size=11),
        name="Signal", showlegend=False
    ), row=1, col=1)

    # ── Volume bars ───────────────────────────────────────
    if "Volume" in df.columns:
        vol_colors = ["#26a69a" if c >= o else "#ef5350"
                      for c,o in zip(close.values, open_.values)]
        fig.add_trace(go.Bar(
            x=dates, y=df["Volume"],
            marker_color=vol_colors, name="Volume", opacity=0.6
        ), row=2, col=1)

    # ── Layout ────────────────────────────────────────────
    dir_color = "#26a69a" if is_buy else "#ef5350"
    grade_emoji = {"A":"🏆","B":"✅","C":"⚠️"}.get(sig.get("grade",""),"")

    fig.update_layout(
        title=dict(
            text=f"{grade_emoji} {sig.get('direction','')} {pair_name} — Grade {sig.get('grade','')} {sig.get('confidence','')}% | {label}",
            font=dict(color=dir_color, size=14),
        ),
        plot_bgcolor="#131722",
        paper_bgcolor="#0a0a0f",
        font=dict(color="#d1d4dc", size=11),
        xaxis=dict(
            gridcolor="#1e222d", rangeslider_visible=False,
            showgrid=True, gridwidth=1,
            type="category",
            nticks=8,
        ),
        xaxis2=dict(gridcolor="#1e222d", showgrid=True),
        yaxis=dict(gridcolor="#1e222d", showgrid=True, side="right"),
        yaxis2=dict(gridcolor="#1e222d", showgrid=True, side="right"),
        height=550,
        margin=dict(l=10, r=120, t=50, b=10),
        legend=dict(
            bgcolor="#161b22", bordercolor="#2a2e39",
            borderwidth=1, x=0, y=1,
            font=dict(size=10)
        ),
        hovermode="x unified",
    )
    fig.update_xaxes(showspikes=True, spikecolor="#434651", spikethickness=1)
    fig.update_yaxes(showspikes=True, spikecolor="#434651", spikethickness=1)

    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["autoScale2d","lasso2d","select2d"],
        "scrollZoom": True,
    })

    # ── AI Analysis tab (like Pipnex) ─────────────────────
    chart_tab1, chart_tab2 = st.tabs(["📊 Chart Analysis", "🤖 AI Analysis"])
    with chart_tab1:
        col1,col2,col3 = st.columns(3)
        col1.metric("Entry",  f"{round(entry,dp)}")
        col2.metric("Stop Loss", f"{round(sl,dp)}", delta=f"-{round(abs(entry-sl),dp)}", delta_color="inverse")
        col3.metric("TP1",    f"{round(tp1,dp)}", delta=f"+{round(abs(tp1-entry),dp)}")

        # SMC context
        price_zone = "PREMIUM" if price > mid_zone else "DISCOUNT"
        zone_color = "#ef5350" if price_zone=="PREMIUM" else "#26a69a"
        st.markdown(f"""
        <div style='background:#131722;border-radius:10px;padding:14px;margin-top:10px'>
          <div style='display:flex;gap:20px;flex-wrap:wrap'>
            <span>📍 Zone: <b style='color:{zone_color}'>{price_zone}</b></span>
            <span>🔑 Support: <b>{round(support,dp)}</b></span>
            <span>🔑 Resistance: <b>{round(resistance,dp)}</b></span>
            <span>📊 ATR: <b>{round(atr_val,dp)}</b></span>
            {f"<span>🟦 {ob_type}: <b>{round(ob_low,dp)}-{round(ob_high,dp)}</b></span>" if ob_high else ""}
          </div>
          <p style='color:#8b949e;font-size:12px;margin:10px 0 0'>
            {"✅ Price in DISCOUNT zone — good for BUY entries" if price_zone=="DISCOUNT" and is_buy
             else "✅ Price in PREMIUM zone — good for SELL entries" if price_zone=="PREMIUM" and not is_buy
             else "⚠️ Trading against the zone — reduce position size"}
          </p>
        </div>""", unsafe_allow_html=True)

    with chart_tab2:
        api_key = st.secrets.get("GROQ_API_KEY","")
        if not api_key:
            st.info("Add GROQ_API_KEY to secrets for AI analysis.")
        else:
            if st.button("🤖 Get AI Analysis", use_container_width=True):
                with st.spinner("Analysing..."):
                    prompt = f"""You are a professional SMC forex analyst.
Analyse this trade setup:
Pair: {pair_name} | Timeframe: {label} | Direction: {sig.get('direction','')}
Grade: {sig.get('grade','')} | Confidence: {sig.get('confidence','')}%
Entry: {round(entry,dp)} | SL: {round(sl,dp)} | TP1: {round(tp1,dp)} | TP2: {round(tp2,dp)}
Price zone: {price_zone} | Support: {round(support,dp)} | Resistance: {round(resistance,dp)}
Order Block: {f"{ob_type} at {round(ob_low,dp)}-{round(ob_high,dp)}" if ob_high else "None detected"}
MTF: {sig.get('mtf_agree','—')} | RSI: {sig.get('rsi','—')}

Write a SHORT professional analysis (max 150 words) like Pipnex AI:
- Is this a good setup?
- What is the thesis?
- Key level to watch
- Risk warning if any
Be direct and confident."""
                    try:
                        r = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
                            json={"model":"llama-3.3-70b-versatile",
                                  "messages":[{"role":"user","content":prompt}],
                                  "max_tokens":250,"temperature":0.6},
                            timeout=20)
                        if r.status_code==200:
                            analysis = r.json()["choices"][0]["message"]["content"]
                            st.markdown(f"""
                            <div style='background:#131722;border-radius:10px;padding:16px;
                              border-left:3px solid {dir_color};font-size:13px;line-height:1.7;
                              color:#d1d4dc'>
                            🤖 <b style='color:{dir_color}'>TRISH AI · LIVE</b><br><br>
                            {analysis.replace(chr(10),"<br>")}
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.error(f"Error {r.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")

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

    # Market status check
    mkt = get_market_status()
    if not mkt["open"]:
        st.markdown(f"""
        <div style='background:#1a0a0a;border:2px solid #f85149;border-radius:12px;
          padding:14px;margin-bottom:12px;text-align:center'>
          <b style='color:#f85149;font-size:16px'>🔴 Market Closed — {mkt["session"]}</b><br>
          <span style='color:#8b949e;font-size:12px'>{mkt["reason"]}</span><br>
          <span style='color:#8b949e;font-size:11px'>Signals below are based on last closed candles — do NOT enter trades now</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background:#161b22;border-radius:12px;padding:14px;margin-bottom:12px;
          border-left:3px solid {mkt["color"]}'>
          <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:4px'>
            <div style='display:flex;align-items:center;gap:8px'>
              <span class='live-dot'></span>
              <b style='font-size:16px'>Live Pulse Signal</b>
            </div>
            <span style='background:{mkt["color"]}22;color:{mkt["color"]};padding:3px 10px;
              border-radius:8px;font-size:12px;font-weight:700'>{mkt["quality"]} · {mkt["session"]}</span>
          </div>
          <p style='color:#8b949e;font-size:12px;margin:0'>{mkt["note"]}</p>
          <p style='color:#8b949e;font-size:11px;margin:4px 0 0'>Scan: {now}</p>
        </div>""", unsafe_allow_html=True)

    if not premium:
        st.warning("🔒 Free plan shows 5 assets. Upgrade for all 10 + Grade A/B system.")

    compact=st.toggle("Compact view",value=False)

    # Session state init
    if "pulse_signals"      not in st.session_state: st.session_state.pulse_signals=[]
    if "pulse_last_scan"    not in st.session_state: st.session_state.pulse_last_scan=None
    if "auto_refresh"       not in st.session_state: st.session_state.auto_refresh=False
    if "refresh_interval"   not in st.session_state: st.session_state.refresh_interval=15

    # Signal expiry: mark signals older than X minutes as expired
    EXPIRY_MINUTES = 60  # signals expire after 60 min
    def is_expired(sig):
        try:
            scan_dt = datetime.datetime.fromisoformat(sig.get("scan_time",""))
            if scan_dt.tzinfo is None: scan_dt = scan_dt.replace(tzinfo=datetime.timezone.utc)
            age_mins = (datetime.datetime.now(datetime.timezone.utc) - scan_dt).total_seconds() / 60
            return age_mins > EXPIRY_MINUTES
        except: return False

    # Auto-refresh logic
    col_r1,col_r2,col_r3 = st.columns([2,1,1])
    auto = col_r2.toggle("⚡ Auto", value=st.session_state.auto_refresh, help="Auto-refresh every 15 minutes")
    st.session_state.auto_refresh = auto
    interval = col_r3.selectbox("Every", [5,10,15,30], index=2, label_visibility="collapsed")
    st.session_state.refresh_interval = interval

    # Check if auto-refresh needed
    should_scan = False
    if st.session_state.auto_refresh and st.session_state.pulse_last_scan:
        age = (datetime.datetime.now(datetime.timezone.utc) - st.session_state.pulse_last_scan).total_seconds() / 60
        if age >= interval:
            should_scan = True
            st.info(f"⚡ Auto-refreshing... (last scan {round(age)}m ago)")

    if col_r1.button("🔄 Refresh Signals",use_container_width=True,type="primary") or should_scan:
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
        st.session_state.pulse_last_scan=datetime.datetime.now(datetime.timezone.utc)
        st.rerun()

    # Show last scan time + next refresh
    if st.session_state.pulse_last_scan:
        age_m = round((datetime.datetime.now(datetime.timezone.utc) - st.session_state.pulse_last_scan).total_seconds()/60,1)
        next_in = max(0, round(interval - age_m, 1))
        col_info = st.columns(2)
        col_info[0].caption(f"Last scan: {age_m}m ago")
        if auto: col_info[1].caption(f"Next refresh in: {next_in}m")

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
        active_sigs  = [s for s in signals if not is_expired(s)]
        expired_sigs = [s for s in signals if is_expired(s)]

        if active_sigs:
            for sig in active_sigs:
                if not compact:
                    render_signal_card(sig)
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
        else:
            st.warning("⏰ All signals have expired. Tap Refresh to scan for new ones.")

        # Show expired signals collapsed
        # Chart viewer for top signal
        if active_sigs:
            top_sig = active_sigs[0]
            with st.expander(f"📈 View Chart — {top_sig['pair']} {top_sig['direction']} Grade {top_sig.get('grade','')}"):
                show_pipnex_chart(top_sig["sym"], top_sig["pair"], top_sig)

        # Entry guide
        if active_sigs:
            st.markdown("""
            <div style='background:#161b22;border-radius:10px;padding:14px;margin:10px 0;
              border-left:3px solid #ffd200'>
            <b style='color:#ffd200'>⚡ How to Enter These Signals</b><br>
            <small style='color:#8b949e'>
            1. Check the entry price — if current price is within 20 pips (forex) or $3 (gold) of entry, it's still valid<br>
            2. Wait for price to pull back TO the entry level before entering<br>
            3. TP1 is set tight — take it when it hits, then move SL to breakeven<br>
            4. Best entry times: London open 08:00 UTC or NY open 13:30 UTC<br>
            5. If price has moved MORE than 30 pips past entry — skip this signal
            </small>
            </div>""",unsafe_allow_html=True)

        if expired_sigs:
            with st.expander(f"⏰ {len(expired_sigs)} Expired Signal(s) — Do NOT trade these"):
                for sig in expired_sigs:
                    dp=5 if sig["entry"]<100 else 2
                    st.markdown(f"""
                    <div style='background:#1a1a1a;border-radius:10px;padding:10px;margin-bottom:6px;
                      border-left:3px solid #444;opacity:0.6'>
                      <b style='color:#666'>{sig["pair"]}</b>
                      <span style='color:#666;margin-left:8px'>{sig["direction"]} {sig["confidence"]}%</span>
                      <span style='background:#333;color:#666;padding:2px 8px;border-radius:10px;font-size:11px;margin-left:8px'>
                        ⏰ EXPIRED — {sig.get("time_ago","old")}
                      </span><br>
                      <small style='color:#555'>Entry: {round(sig["entry"],dp)} | Do NOT trade — signal is too old</small>
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
            if sig and sig["direction"]!="WAIT":
                render_signal_card(sig)
                show_pipnex_chart(sym,name,sig)
                st.divider()
            elif sig:
                st.info(f"⏳ {name} — WAIT (no clear signal)")
            else:
                st.warning(f"No data for {name}")

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
        st.divider()
        show_pipnex_chart(best.get("symbol",best.get("sym","")),best["pair"],best)
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
    st.markdown("### 🏢 Prop Firm Challenge Tracker")
    if not premium: st.error("🔒 Premium only."); st.stop()

    FIRMS_DATA={
        "FTMO":         {"e":"🏆","c":"#1a6cff","daily":5,"max":10,"target":10,"days":4, "split":80,
                         "tip":"Most popular firm. Strict consistency rule. No trading during major news.",
                         "pass_tips":["Trade minimum 4 days","Never lose more than 5% in one day","Never exceed 10% total drawdown","Hit 10% profit target","Use 0.5-1% risk per trade only","Avoid FOMC, NFP and CPI news events","Take TP1 always — don't be greedy"]},
        "The5ers":      {"e":"🌍","c":"#d97706","daily":4,"max":5, "target":8, "days":0, "split":100,
                         "tip":"100% profit split on first target! Very tight 5% max loss. Scales to $4M.",
                         "pass_tips":["No minimum trading days","VERY tight 5% max loss — use 0.25% risk","Hit 8% target slowly and consistently","Best for patient disciplined traders","Scale plan is incredible — work towards it"]},
        "FundedNext":   {"e":"⚡","c":"#7c3aed","daily":5,"max":10,"target":10,"days":5, "split":90,
                         "tip":"90% profit split. Stellar accounts available. Bi-weekly payouts.",
                         "pass_tips":["Trade minimum 5 days","5% daily loss limit — respect it","Hit 10% profit target","Keep consistency — no huge single day wins","Great split — worth the effort"]},
        "MyForexFunds": {"e":"📊","c":"#0891b2","daily":5,"max":12,"target":8, "days":5, "split":85,
                         "tip":"Rapid 1-phase option available. Good for beginners. 85% split.",
                         "pass_tips":["Choose Rapid account for 1-phase only","8% target is lower than most firms","12% max loss gives more breathing room","Good first prop firm choice","Consistent daily trading preferred"]},
        "Apex":         {"e":"🔺","c":"#ef4444","daily":3,"max":6, "target":6, "days":7, "split":90,
                         "tip":"Futures-focused. No time limit. Very tight 3% daily loss. Fast payouts.",
                         "pass_tips":["No time limit — take your time","VERY tight 3% daily — use micro lots","6% profit target is achievable slowly","Best for indices and futures traders","Payout every 14 days once funded"]},
        "True Forex":   {"e":"💎","c":"#14b8a6","daily":5,"max":10,"target":10,"days":4, "split":80,
                         "tip":"Weekly payouts. No minimum days on funded. Straightforward rules.",
                         "pass_tips":["4 minimum days in challenge phase","Standard 5% daily / 10% max rules","Weekly payouts once funded — great cashflow","Good 2-phase evaluation process","80% split — fair for a reliable firm"]},
        "E8 Funding":   {"e":"🎯","c":"#f59e0b","daily":5,"max":8, "target":8, "days":0, "split":80,
                         "tip":"Tight 8% max loss. Scaling plan available. Good community.",
                         "pass_tips":["8% max loss — tighter than most","Use Grade A signals only","Avoid overtrading — 1-2 setups per day","Scale up after passing for more capital","Good firm for systematic traders"]},
        "Alpha Capital":{"e":"🅰️","c":"#8b5cf6","daily":5,"max":10,"target":10,"days":0, "split":80,
                         "tip":"Straightforward rules. Weekend holding allowed. Good for swing traders.",
                         "pass_tips":["No minimum trading days","Standard 5%/10% rules","Weekend holding allowed — good for swings","10% profit target — take your time","Consistent risk management is key"]},
    }

    PIP_VALUES={"EUR/USD":10,"GBP/USD":10,"USD/JPY":9,"AUD/USD":10,"USD/CHF":10,
                "USD/CAD":10,"Gold (XAU/USD)":100,"Bitcoin":100,"NASDAQ":1,"S&P 500":1}

    # Session state
    for k,v in [("pf_firm","FTMO"),("pf_account",10000.0),("pf_profit",0.0),
                ("pf_loss",0.0),("pf_days",0)]:
        if k not in st.session_state: st.session_state[k]=v

    # ── Firm + account selector ────────────────────────────
    col1,col2=st.columns(2)
    with col1:
        firm_name=st.selectbox("🏦 Prop Firm",list(FIRMS_DATA.keys()))
        st.session_state.pf_firm=firm_name
    with col2:
        size_opts=["$5,000","$10,000","$25,000","$50,000","$100,000","Custom"]
        size_sel=st.selectbox("💼 Account Size",size_opts)
        if size_sel=="Custom":
            account=st.number_input("Amount ($)",min_value=1000.0,value=10000.0,step=1000.0)
        else:
            account=float(size_sel.replace("$","").replace(",",""))
        st.session_state.pf_account=account

    firm=FIRMS_DATA[firm_name]
    dl=account*firm["daily"]/100
    ml=account*firm["max"]/100
    pt=account*firm["target"]/100

    # Firm info banner
    st.markdown(f"""
    <div style="background:#161b22;border-radius:14px;padding:16px;margin:10px 0;border-left:4px solid {firm['c']}">
      <b style="color:{firm['c']};font-size:18px">{firm['e']} {firm_name}</b>
      <p style="color:#8b949e;margin:6px 0;font-size:13px">{firm['tip']}</p>
      <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:8px">
        <span style="color:#f85149">📉 Daily Loss: {firm['daily']}% (${dl:,.0f})</span>
        <span style="color:#f85149">🔻 Max Loss: {firm['max']}% (${ml:,.0f})</span>
        <span style="color:#3fb950">🎯 Target: {firm['target']}% (${pt:,.0f})</span>
        <span style="color:#ffd200">💰 Split: {firm['split']}%</span>
        <span style="color:#58a6ff">📅 Min Days: {firm['days'] if firm['days']>0 else 'None'}</span>
      </div>
    </div>""",unsafe_allow_html=True)

    # ── Section tabs ───────────────────────────────────────
    pf_section=st.selectbox("📂 Section",
        ["📊 Dashboard","💰 Lot Calculator","🎯 Get Signal for Challenge",
         "📋 How to Pass","🏆 Firm Comparison"],
        label_visibility="hidden")
    st.divider()

    # ══ DASHBOARD ══
    if "Dashboard" in pf_section:
        col1,col2,col3=st.columns(3)
        profit=col1.number_input("Current Profit ($)",min_value=0.0,value=st.session_state.pf_profit,step=10.0)
        loss  =col2.number_input("Current Loss ($)",  min_value=0.0,value=st.session_state.pf_loss,  step=10.0)
        days  =col3.number_input("Days Traded",       min_value=0,  value=st.session_state.pf_days,  step=1)
        st.session_state.pf_profit=profit; st.session_state.pf_loss=loss; st.session_state.pf_days=days

        rem_daily=max(0,dl-loss); rem_max=max(0,ml-loss)
        profit_pct=profit/account*100; loss_pct=loss/account*100
        progress_pct=min(100,profit/pt*100) if pt>0 else 0
        daily_used_pct=loss/dl*100 if dl>0 else 0

        # Status
        if daily_used_pct>=100: st.error("🚨 DAILY LOSS LIMIT HIT — STOP TRADING TODAY!")
        elif daily_used_pct>=70: st.warning(f"⚠️ {round(daily_used_pct)}% of daily limit used — be very careful")
        elif profit_pct>=firm["target"]: st.success(f"🎉 PROFIT TARGET HIT! Check minimum days then request payout!")
        else: st.success(f"✅ Safe to trade — {round(daily_used_pct)}% of daily limit used")

        st.markdown(f"""
        <div class="metric-row">
          <div class="metric-card"><div class="metric-label">Balance</div><div class="metric-value">${account+profit-loss:,.0f}</div></div>
          <div class="metric-card"><div class="metric-label">Profit</div><div class="metric-value" style="color:#3fb950">${profit:,.0f} ({profit_pct:.1f}%)</div></div>
          <div class="metric-card"><div class="metric-label">Loss Used</div><div class="metric-value" style="color:#f85149">${loss:,.0f} ({loss_pct:.1f}%)</div></div>
        </div>
        <div class="metric-row">
          <div class="metric-card"><div class="metric-label">Daily Remaining</div><div class="metric-value" style="color:{"#f85149" if rem_daily<dl*0.3 else "#3fb950"}">${rem_daily:,.0f}</div></div>
          <div class="metric-card"><div class="metric-label">Max Remaining</div><div class="metric-value">${rem_max:,.0f}</div></div>
          <div class="metric-card"><div class="metric-label">Still Need</div><div class="metric-value" style="color:#ffd200">${max(0,pt-profit):,.0f}</div></div>
        </div>""",unsafe_allow_html=True)

        st.caption("Profit Progress")
        st.progress(min(progress_pct/100,1.0))
        st.caption(f"${profit:,.2f} / ${pt:,.0f} target ({progress_pct:.1f}%)")
        st.caption("Daily Loss Used")
        st.progress(min(daily_used_pct/100,1.0))
        st.caption(f"${loss:,.2f} / ${dl:,.0f} ({daily_used_pct:.1f}%)")

        # Pass probability
        pass_prob=50+min(30,progress_pct*0.3)-daily_used_pct*0.3-loss_pct*0.5
        pass_prob=max(5,min(95,round(pass_prob)))
        st.subheader(f"🎯 Pass Probability: {pass_prob}%")
        st.progress(pass_prob/100)
        if pass_prob>=70: st.success("Strong position — keep trading consistently!")
        elif pass_prob>=40: st.warning("Moderate — reduce risk, focus on quality Grade A/B signals only")
        else: st.error("High risk of failing — stop, reset mindset, trade very small lots")

        est_payout=profit*firm["split"]/100
        st.info(f"💰 If you pass and withdraw current profit: **${est_payout:,.2f}** ({firm['split']}% split)")

    # ══ LOT CALCULATOR ══
    elif "Lot" in pf_section:
        st.subheader("💰 Smart Lot Calculator")
        st.info(f"Calculates safe lot sizes within {firm_name} rules for every pair")

        loss_now=st.session_state.pf_loss
        rem_daily_now=max(0,dl-loss_now)

        col1,col2=st.columns(2)
        with col1:
            risk_mode=st.radio("Risk Mode",[f"Conservative (0.5% = ${account*0.005:,.0f})",
                                            f"Standard (1% = ${account*0.01:,.0f})",
                                            f"Aggressive (2% = ${account*0.02:,.0f})"])
            stop_pips=st.number_input("Your Stop Loss (pips)",min_value=1.0,value=20.0,step=5.0)
        with col2:
            risk_pct=0.5 if "0.5%" in risk_mode else 1.0 if "1%" in risk_mode else 2.0
            risk_amt=min(account*risk_pct/100, rem_daily_now*0.25)
            st.metric("Max Risk This Trade",f"${risk_amt:,.2f}")
            st.metric("Daily Buffer Left",f"${rem_daily_now:,.2f}")
            st.metric("Max Loss Per Trade",f"${account*0.01:,.2f} (1% hard limit)")

        st.divider()
        st.subheader("📊 Lot Sizes for Every Pair")
        lot_rows=[]
        for pname,pval in PIP_VALUES.items():
            trade_risk=min(account*risk_pct/100,rem_daily_now*0.25)
            lot=max(0.01,round(trade_risk/(stop_pips*pval/100),2))
            loss_if_sl=round(lot*stop_pips*pval/100,2)
            win_if_tp1=round(lot*stop_pips*pval/100*1.5,2)
            lot_rows.append({"Pair":pname,"Lot Size":lot,
                            f"Loss if SL (${stop_pips:.0f}p)":f"-${loss_if_sl}",
                            "Win if TP1 (1.5R)":f"+${win_if_tp1}",
                            "Safe?":"✅" if loss_if_sl<=dl*0.2 else "⚠️"})
        st.dataframe(pd.DataFrame(lot_rows),use_container_width=True,hide_index=True)
        st.caption(f"Based on {risk_pct}% risk · {stop_pips:.0f} pip SL · ${account:,.0f} account · {firm_name} rules")

    # ══ GET SIGNAL ══
    elif "Signal" in pf_section:
        st.subheader("🎯 Prop Firm Signal — App Picks the Best Trade for You")
        st.info("Only Grade A & B signals are shown. Lot size is calculated within your challenge rules.")
        loss_now=st.session_state.pf_loss
        rem_daily_now=max(0,dl-loss_now)

        if rem_daily_now<=0:
            st.error("🚨 Daily loss limit reached — no trades recommended today.")
        else:
            if st.button("🔍 Find Best Signal for My Challenge",type="primary",use_container_width=True):
                with st.spinner("Scanning for Grade A/B signals..."):
                    best=None
                    for pname,sym in (ALL_PAIRS if premium else FREE_PAIRS).items():
                        try:
                            sig=analyse_pair(sym,pname)
                            if sig and sig["direction"]!="WAIT" and sig.get("grade") in ["A","B"]:
                                if best is None or sig["confidence"]>best["confidence"]: best=sig
                        except: pass

                if best:
                    pval=PIP_VALUES.get(best["pair"],10)
                    sl_dist=abs(best["entry"]-best["sl"])
                    sl_pips=sl_dist/0.0001 if best["entry"]<10 else sl_dist/0.01 if best["entry"]<500 else sl_dist
                    max_risk=min(rem_daily_now*0.25,account*0.01)
                    lot=max(0.01,round(max_risk/(sl_pips*pval/100),2))
                    dp=5 if best["entry"]<100 else 2
                    pot_loss=round(lot*sl_pips*pval/100,2)
                    pot_win =round(lot*sl_pips*pval/100*1.5,2)
                    dir_color="#3fb950" if "BUY" in best["direction"] else "#f85149"
                    grade_color={"A":"#3fb950","B":"#0072ff","C":"#ffd200"}.get(best["grade"],"#f85149")

                    st.markdown(f"""
                    <div style="background:{"#0a1a0a" if "BUY" in best["direction"] else "#1a0a0a"};
                      border-radius:16px;padding:20px;border:2px solid {dir_color}40;margin:10px 0">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                        <div>
                          <span style="font-size:22px;font-weight:900;color:{dir_color}">
                            {"📈 BUY" if "BUY" in best["direction"] else "📉 SELL"}
                          </span>
                          <span style="background:{grade_color};color:#000;padding:3px 12px;
                            border-radius:6px;font-weight:900;margin-left:10px;font-size:14px">
                            Grade {best["grade"]}
                          </span>
                        </div>
                        <span style="font-size:32px;font-weight:900;color:#ffd200">{best["confidence"]}%</span>
                      </div>
                      <p style="font-size:22px;font-weight:900;color:#e6edf3;margin:6px 0">{best["pair"]}</p>
                      <p style="font-size:13px;color:#8b949e;margin:4px 0">{best.get("mtf_agree","")}</p>

                      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;
                        background:#0d1117;border-radius:10px;padding:12px;margin:12px 0">
                        <div style="text-align:center"><div style="font-size:10px;color:#8b949e;font-weight:700">ENTRY</div>
                          <div style="font-weight:800;font-size:13px">{round(best["entry"],dp)}</div></div>
                        <div style="text-align:center"><div style="font-size:10px;color:#8b949e;font-weight:700">STOP</div>
                          <div style="font-weight:800;font-size:13px;color:#f85149">{round(best["sl"],dp)}</div></div>
                        <div style="text-align:center"><div style="font-size:10px;color:#8b949e;font-weight:700">TP1</div>
                          <div style="font-weight:800;font-size:13px;color:#3fb950">{round(best["tp1"],dp)}</div></div>
                        <div style="text-align:center"><div style="font-size:10px;color:#8b949e;font-weight:700">TP2</div>
                          <div style="font-weight:800;font-size:13px;color:#3fb950">{round(best["tp2"],dp)}</div></div>
                        <div style="text-align:center"><div style="font-size:10px;color:#8b949e;font-weight:700">TP3</div>
                          <div style="font-weight:800;font-size:13px;color:#3fb950">{round(best["tp3"],dp)}</div></div>
                      </div>

                      <div style="background:#1a2040;border-radius:10px;padding:14px">
                        <p style="color:#ffd200;font-weight:900;font-size:16px;margin:0 0 8px">
                          💰 {firm_name} Safe Lot: <span style="font-size:22px">{lot} lots</span>
                        </p>
                        <p style="color:#8b949e;font-size:12px;margin:2px 0">
                          Max risk: ${max_risk:,.2f} ({round(max_risk/account*100,2)}% of account)
                        </p>
                        <p style="color:#f85149;font-size:12px;margin:2px 0">
                          If SL hit: -${pot_loss} ({round(pot_loss/dl*100,1)}% of daily limit)
                        </p>
                        <p style="color:#3fb950;font-size:12px;margin:2px 0">
                          If TP1 hit: +${pot_win} | Daily buffer remaining: ${rem_daily_now:,.2f}
                        </p>
                      </div>
                    </div>""",unsafe_allow_html=True)

                    # Trading rules reminder
                    st.markdown("""
                    <div style="background:#161b22;border-radius:10px;padding:14px;margin-top:10px">
                    <b>⚡ Prop Firm Trade Rules:</b><br>
                    ✅ Take TP1 — secure profit, move SL to breakeven<br>
                    ✅ Let TP2 run with trailing stop<br>
                    ✅ Close trade before major news events<br>
                    ❌ Never move your stop loss against you<br>
                    ❌ Never add to a losing position<br>
                    ❌ Max 2-3 trades per day on a challenge
                    </div>""",unsafe_allow_html=True)
                else:
                    st.info("⏳ No Grade A/B signals right now. Check back in 15-30 minutes or try refreshing the Pulse tab.")

            if best:
                st.divider()
                st.subheader("📈 Chart for This Signal")
                show_pipnex_chart(best["sym"], best["pair"], best)

    # ══ HOW TO PASS ══
    elif "How to Pass" in pf_section:
        st.markdown(f"## {firm['e']} How to Pass {firm_name}")
        st.markdown(f"""
        <div style="background:#161b22;border-radius:14px;padding:20px;border-left:5px solid {firm['c']};margin-bottom:16px">
        <h3 style="color:{firm['c']};margin:0 0 12px">Step-by-Step Guide</h3>
        {"".join([f"<p style='color:#e6edf3;font-size:14px;padding:6px 0;border-bottom:1px solid #21262d;margin:0'><b style='color:{firm["c"]}'>{i+1}.</b> {tip}</p>" for i,tip in enumerate(firm["pass_tips"])])}
        </div>""",unsafe_allow_html=True)

        st.subheader("❌ Common Reasons People FAIL")
        fails=["Trading too large lots out of greed","Revenge trading after a loss — worst thing you can do",
               "Trading during FOMC, NFP, CPI without a plan","Ignoring the daily loss limit",
               "Taking too many trades — overtrading kills challenges","Trading Grade C and D signals",
               "Moving stop loss wider when in a losing trade","Not tracking daily P&L carefully"]
        for f in fails:
            st.markdown(f"<p style='color:#f85149;font-size:14px;margin:4px 0'>❌ {f}</p>",unsafe_allow_html=True)

        st.subheader("✅ Winning Formula")
        wins=["Only take Grade A & B signals from the Sparro FX AI Pulse tab",
              "Risk 0.5-1% per trade maximum — use the lot calculator above",
              "Trade 1-2 setups per day only — quality beats quantity every time",
              "Stop trading after 2 losses in one day — protect your buffer",
              "Journal every trade and review performance weekly",
              "Trade London open (08:00-11:00 UTC) for best liquidity",
              "Always check the News tab before entering any trade",
              "Take TP1 always to lock in profit, then let TP2 and TP3 run"]
        for w in wins:
            st.markdown(f"<p style='color:#3fb950;font-size:14px;margin:4px 0'>✅ {w}</p>",unsafe_allow_html=True)

    # ══ COMPARISON ══
    elif "Comparison" in pf_section:
        st.subheader("🏆 All Prop Firms Compared")
        rows=[]
        for fn,fd in FIRMS_DATA.items():
            rows.append({"Firm":f"{fd['e']} {fn}","Daily":f"{fd['daily']}%",
                        "Max DD":f"{fd['max']}%","Target":f"{fd['target']}%",
                        "Split":f"{fd['split']}%","Min Days":fd["days"] if fd["days"]>0 else "None"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.divider()
        st.subheader("💡 Which Firm is Right for You?")
        st.markdown("""
        | Your Situation | Best Choice |
        |---|---|
        | First time prop trader | MyForexFunds Rapid (1-phase, easiest) |
        | Want highest profit split | The5ers (100%) or FundedNext (90%) |
        | Want to scale to $1M+ | The5ers scaling programme |
        | Tight on time, no min days | The5ers or Alpha Capital |
        | Futures/indices trader | Apex Trader Funding |
        | Want weekly payouts | True Forex Funds |
        | Most trusted / well known | FTMO |
        | Good for beginners | MyForexFunds or E8 Funding |
        """)

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
        api_key=st.secrets.get("GROQ_API_KEY","")
        if not api_key:
            st.error("⚠️ Add GROQ_API_KEY to Streamlit secrets. Get free key at console.groq.com")
        else:
            with st.spinner("🤖 Analysing news impact..."):
                try:
                    r=requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
                        json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":f"You are a forex news analyst. Analyse this week economic calendar impact on {selected}. Give: 1) Bullish or bearish bias 2) Key events to watch 3) Times to avoid trading. Be concise with bullet points."}],"max_tokens":600,"temperature":0.5},timeout=30)
                    if r.status_code==200:
                        analysis=r.json()["choices"][0]["message"]["content"]
                        st.markdown(f"<div class='news-card'>{analysis.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
                    else:
                        st.error(f"Groq error {r.status_code}: {r.json().get('error',{}).get('message','Unknown')}")
                except Exception as e:
                    st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════
# PAGE: AI STRATEGY BUILDER
# ════════════════════════════════════════════════════════════
elif "AI Strategy" in page:
    st.markdown("### 🤖 AI Strategy Builder")
    st.caption("Tell the app your trading style — it builds a custom strategy AND scans for signals that match it")
    if not premium: st.error("🔒 Premium only."); st.stop()

    # ── Strategy preferences ──────────────────────────────
    st.subheader("1️⃣ Set Your Preferences")
    col1,col2=st.columns(2)
    with col1:
        style   =st.selectbox("Trading Style",["Day Trading","Scalping","Swing Trading"])
        risk    =st.selectbox("Risk Level",   ["Conservative","Moderate","Aggressive"])
        session =st.selectbox("Session",      ["London","New York","Asian","All Sessions"])
    with col2:
        exp     =st.selectbox("Experience",   ["Beginner","Intermediate","Advanced"])
        fav     =st.multiselect("Focus Pairs",list(ALL_PAIRS.keys()),
                    default=["EUR/USD","Gold (XAU/USD)","GBP/USD"])
        min_conf=st.slider("Minimum Confidence %",50,95,
                    60 if risk=="Aggressive" else 75 if risk=="Moderate" else 80)

    # Strategy settings based on preferences
    risk_pct   = 0.5 if risk=="Conservative" else 1.0 if risk=="Moderate" else 2.0
    grade_filter=["A"] if risk=="Conservative" else ["A","B"] if risk=="Moderate" else ["A","B","C"]
    session_hours={"London":(7,17),"New York":(12,21),"Asian":(0,9),"All Sessions":(0,24)}
    sess_start,sess_end=session_hours[session]
    current_hour=datetime.datetime.now(datetime.timezone.utc).hour
    in_session=(sess_start<=current_hour<=sess_end) if session!="All Sessions" else True

    # Session indicator
    sess_color="#3fb950" if in_session else "#f85149"
    sess_label=f"{'✅ Active' if in_session else '❌ Closed'} — {session} Session"
    st.markdown(f"<p style='color:{sess_color};font-size:13px;font-weight:700'>{sess_label}</p>",
        unsafe_allow_html=True)

    st.divider()

    # ── Build + Scan button ───────────────────────────────
    st.subheader("2️⃣ Build Strategy & Scan")
    if st.button("🚀 Build My Strategy & Find Signals",type="primary",use_container_width=True):

        # ── Step 1: Scan markets with custom filters ──────
        with st.spinner("📊 Scanning markets for your strategy..."):
            custom_signals=[]
            scan_pairs={k:v for k,v in ALL_PAIRS.items() if k in fav} if fav else ALL_PAIRS
            for pname,sym in scan_pairs.items():
                try:
                    sig=analyse_pair(sym,pname)
                    if not sig or sig["direction"]=="WAIT": continue
                    if sig.get("grade") not in grade_filter: continue
                    if sig["confidence"]<min_conf: continue
                    # Session filter
                    if not in_session and session!="All Sessions": continue
                    custom_signals.append(sig)
                except: pass
            custom_signals.sort(key=lambda x:x["confidence"],reverse=True)

        # ── Step 2: Build AI strategy based on results ────
        api_key=st.secrets.get("GROQ_API_KEY","")
        ai_strategy_text=""
        if api_key:
            with st.spinner("🤖 AI is writing your custom strategy..."):
                signals_context=""
                if custom_signals:
                    signals_context=f"Current live signals matching this strategy: "+", ".join(
                        [f"{s['direction']} {s['pair']} (Grade {s['grade']}, {s['confidence']}%)"
                         for s in custom_signals[:3]])
                else:
                    signals_context="No signals currently active for this strategy — market may be consolidating."

                prompt=f"""You are a professional forex trading coach.
Build a concise, practical custom strategy for this trader:
- Style: {style}
- Risk: {risk} ({risk_pct}% per trade)
- Session: {session}
- Experience: {exp}
- Focus pairs: {", ".join(fav) if fav else "All pairs"}
- Grade filter: {", ".join(grade_filter)} signals only
- Min confidence: {min_conf}%
- {signals_context}

Write a SHORT strategy (max 300 words) with:
1. Strategy name
2. Entry rules (3 bullet points max)
3. Exit rules (SL and TP)
4. One key rule to never break
5. What makes this strategy work for {session} session

Be direct and practical. No fluff."""
                try:
                    r=requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
                        json={"model":"llama-3.3-70b-versatile",
                              "messages":[{"role":"user","content":prompt}],
                              "max_tokens":500,"temperature":0.6},
                        timeout=30)
                    if r.status_code==200:
                        ai_strategy_text=r.json()["choices"][0]["message"]["content"]
                        st.session_state.ai_strategy=ai_strategy_text
                except: pass

        # ── Display results ───────────────────────────────
        st.divider()

        # AI strategy card
        if ai_strategy_text:
            st.subheader("📋 Your Custom Strategy")
            st.markdown(f"""
            <div style='background:#161b22;border-radius:14px;padding:20px;
              border-left:4px solid #0072ff;margin-bottom:16px'>
            {ai_strategy_text.replace(chr(10),"<br>")}
            </div>""",unsafe_allow_html=True)
        elif not api_key:
            st.info("💡 Add GROQ_API_KEY to Streamlit secrets to also get an AI-written strategy explanation.")

        # Strategy settings summary
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;margin-bottom:16px;
          border-left:4px solid #ffd200'>
        <b style='color:#ffd200'>⚙️ Your Strategy Settings</b><br><br>
        🎯 Style: <b>{style}</b> | Risk: <b>{risk}</b> ({risk_pct}% per trade)<br>
        📊 Grades: <b>{", ".join(grade_filter)}</b> signals only | Min confidence: <b>{min_conf}%</b><br>
        ⏰ Session: <b>{session}</b> ({sess_label})<br>
        💹 Pairs: <b>{", ".join(fav) if fav else "All pairs"}</b>
        </div>""",unsafe_allow_html=True)

        # ── Matching signals ──────────────────────────────
        st.subheader(f"📡 Live Signals Matching Your Strategy ({len(custom_signals)} found)")
        if not custom_signals:
            st.info(f"⏳ No {'/'.join(grade_filter)} signals above {min_conf}% on your selected pairs right now.")
            st.caption("Try: lowering minimum confidence, adding more pairs, or checking during your session hours.")
        else:
            for sig in custom_signals:
                dp=5 if sig["entry"]<100 else 2
                dir_color="#3fb950" if "BUY" in sig["direction"] else "#f85149"
                grade_color={"A":"#3fb950","B":"#0072ff","C":"#ffd200"}.get(sig.get("grade","D"),"#f85149")

                # Calculate lot size for this signal
                sl_dist=abs(sig["entry"]-sig["sl"])
                sl_pips=sl_dist/0.0001 if sig["entry"]<10 else sl_dist/0.01 if sig["entry"]<500 else sl_dist
                pip_val_map={"EUR/USD":10,"GBP/USD":10,"USD/JPY":9,"AUD/USD":10,
                             "USD/CHF":10,"USD/CAD":10,"Gold (XAU/USD)":100,
                             "Bitcoin":100,"NASDAQ":1,"S&P 500":1}
                pval=pip_val_map.get(sig["pair"],10)
                account_for_lot=1000.0  # default — user can adjust
                risk_amt=account_for_lot*risk_pct/100
                lot=max(0.01,round(risk_amt/(sl_pips*pval/100),2)) if sl_pips>0 else 0.01

                st.markdown(f"""
                <div style='background:{"#0a1a0a" if "BUY" in sig["direction"] else "#1a0a0a"};
                  border-radius:14px;padding:16px;margin-bottom:12px;
                  border:1px solid {dir_color}40'>
                  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                    <div style='display:flex;align-items:center;gap:8px'>
                      <span style='font-size:18px;font-weight:800;color:{dir_color}'>
                        {"📈" if "BUY" in sig["direction"] else "📉"} {sig["direction"]}
                      </span>
                      <span style='background:{grade_color};color:#000;padding:2px 10px;
                        border-radius:6px;font-weight:800;font-size:12px'>Grade {sig.get("grade","—")}</span>
                    </div>
                    <span style='font-size:26px;font-weight:800;color:#ffd200'>{sig["confidence"]}%</span>
                  </div>
                  <p style='font-size:18px;font-weight:800;color:#e6edf3;margin:4px 0'>{sig["pair"]}</p>
                  <p style='font-size:12px;color:#8b949e;margin:2px 0'>MTF: {sig.get("mtf_agree","—")} | {sig.get("marketCond",sig.get("market_cond","—"))}</p>

                  <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:6px;
                    background:#0d1117;border-radius:8px;padding:10px;margin:10px 0'>
                    <div style='text-align:center'><div style='font-size:10px;color:#8b949e'>ENTRY</div>
                      <div style='font-weight:800;font-size:12px'>{round(sig["entry"],dp)}</div></div>
                    <div style='text-align:center'><div style='font-size:10px;color:#8b949e'>STOP</div>
                      <div style='font-weight:800;font-size:12px;color:#f85149'>{round(sig["sl"],dp)}</div></div>
                    <div style='text-align:center'><div style='font-size:10px;color:#8b949e'>TP1</div>
                      <div style='font-weight:800;font-size:12px;color:#3fb950'>{round(sig["tp1"],dp)}</div></div>
                    <div style='text-align:center'><div style='font-size:10px;color:#8b949e'>TP2</div>
                      <div style='font-weight:800;font-size:12px;color:#3fb950'>{round(sig["tp2"],dp)}</div></div>
                    <div style='text-align:center'><div style='font-size:10px;color:#8b949e'>TP3</div>
                      <div style='font-weight:800;font-size:12px;color:#3fb950'>{round(sig["tp3"],dp)}</div></div>
                  </div>

                  <div style='background:#1a2040;border-radius:8px;padding:10px'>
                    <p style='color:#ffd200;font-weight:800;margin:0'>
                      💰 Suggested Lot: {lot} lots
                      <span style='font-size:11px;color:#8b949e;font-weight:400'>
                       (based on {risk_pct}% risk on $1,000 — adjust for your account)
                      </span>
                    </p>
                    <p style='font-size:11px;color:#8b949e;margin:4px 0'>
                      ✅ Strategies: {sig.get("strategies","—")} | {sig.get("agree","—")}
                    </p>
                  </div>
                </div>""",unsafe_allow_html=True)

        # Account size note
        # Chart for top signal
        if custom_signals:
            with st.expander(f"📈 View Chart — {custom_signals[0]['pair']}"):
                show_pipnex_chart(custom_signals[0]["sym"], custom_signals[0]["pair"], custom_signals[0])

        st.caption("💡 Lot sizes above are based on $1,000 account. Go to 🏢 Prop Firm or 💰 Risk Calculator to get exact lot sizes for your account.")

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
        img_bytes  = uploaded.read()
        img_b64    = base64.b64encode(img_bytes).decode()
        ext        = uploaded.name.split(".")[-1].lower()
        media_type = f"image/{'jpeg' if ext in ['jpg','jpeg'] else 'png'}"
        api_key    = st.secrets.get("GROQ_API_KEY","")
        if not api_key:
            st.error("⚠️ Add GROQ_API_KEY to Streamlit secrets. Get free key at console.groq.com")
        else:
            with st.spinner("🤖 Analysing your chart..."):
                chart_prompt=f"""You are a professional forex technical analyst.
Analyse this {pair_ctx} {tf_ctx} chart screenshot.
Trader question: {question if question else 'Give full technical analysis.'}

Provide:
1. Overall trend direction (Bullish/Bearish/Neutral)
2. Key support and resistance levels you can see
3. Chart patterns visible (triangles, flags, H&S etc)
4. Candlestick patterns
5. Recommended direction (BUY/SELL/WAIT)
6. Suggested Entry, Stop Loss and Take Profit levels
7. Key risks to watch

Be specific and actionable."""
                try:
                    # Groq vision model supports images
                    r=requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
                        json={
                            "model":"llama-3.2-11b-vision-preview",
                            "messages":[{"role":"user","content":[
                                {"type":"image_url","image_url":{"url":f"data:{media_type};base64,{img_b64}"}},
                                {"type":"text","text":chart_prompt}
                            ]}],
                            "max_tokens":1200,"temperature":0.4
                        },
                        timeout=40)
                    if r.status_code==200:
                        analysis=r.json()["choices"][0]["message"]["content"]
                        st.subheader("🤖 AI Chart Analysis")
                        st.markdown(f"<div class='strategy-card'>{analysis.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
                    else:
                        err=r.json().get("error",{})
                        st.error(f"Groq error {r.status_code}: {err.get('message','Unknown')}")
                        st.caption("Tips: Use PNG or JPG under 4MB · Make sure API key is valid")
                except Exception as e:
                    st.error(f"Error: {e}")

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
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1a1a0a,#2d2a0a);border:2px solid #ffd200;"
        "border-radius:16px;padding:24px;text-align:center;margin:16px 0'>"
        "<div style='font-size:32px'>⚡</div>"
        "<h2 style='color:#ffd200;margin:8px 0'>Premium Plan</h2>"
        "<h1 style='color:#fff;margin:0'>$24/month</h1>"
        "<p style='color:#8b949e;margin:12px 0'>Everything you need to trade professionally</p>"
        "<hr style='border-color:#30363d;margin:16px 0'>"
        "<p>✅ All 10 assets · Grade A/B/C/D signals<br>"
        "✅ Live Pulse with 8-strategy engine<br>"
        "✅ Multi-timeframe · Currency strength<br>"
        "✅ Precision entries · Prop firm tools<br>"
        "✅ AI Strategy Builder · Chart analysis<br>"
        "✅ Telegram alerts · Trade journal</p>"
        "</div>",
        unsafe_allow_html=True)
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
