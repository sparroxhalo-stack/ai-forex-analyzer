import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import json
import hashlib

st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")

st.markdown("""
<style>
  body,.main{background:#0d1117;color:#e6edf3}
  .stMetric{background:#161b22;border-radius:10px;padding:12px}
  .stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}
  .tier-box{background:#161b22;border-radius:14px;padding:20px;text-align:center;border:2px solid #30363d}
  .tier-box.gold{border-color:#ffd200}
  .news-card{background:#161b22;border-radius:10px;padding:14px;margin-bottom:8px;border-left:4px solid #f78166}
  .login-box{background:#161b22;border-radius:16px;padding:30px 26px;border:1px solid #30363d}
  .pulse-card{border-radius:14px;padding:18px;margin-bottom:12px;animation:pulse 2s infinite}
  @keyframes pulse{0%{opacity:1}50%{opacity:0.7}100%{opacity:1}}
</style>
""", unsafe_allow_html=True)

# ════════ PERSISTENT LOGIN via query params ════════
# We store a hashed session token in the URL so login survives refresh
def make_token(account_type, email, trial_start_str):
    raw = f"{account_type}|{email}|{trial_start_str}|sparro_salt_2024"
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
        expected = make_token(account_type, email, ts)
        if token != expected: return None
        trial_start = datetime.datetime.fromisoformat(ts) if ts else None
        return {"account_type": account_type, "email": email, "trial_start": trial_start}
    except: return None

def clear_login():
    st.query_params.clear()

# ════════ SESSION STATE ════════
DEFAULTS = {
    "logged_in": False, "account_type": None, "trial_start": None,
    "user_email": "", "trade_journal": [],
    "notification_threshold": 75, "session_loaded": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Auto-restore login from URL on first load
if not st.session_state.session_loaded:
    saved = load_login()
    if saved:
        st.session_state.logged_in    = True
        st.session_state.account_type = saved["account_type"]
        st.session_state.user_email   = saved["email"]
        st.session_state.trial_start  = saved["trial_start"]
    st.session_state.session_loaded = True

# ════════ CREDENTIALS ════════
def _secret(key, fallback):
    try:    return st.secrets.get(key, fallback)
    except: return fallback

ADMIN_PASSWORD   = _secret("ADMIN_PASSWORD",   "sparro_admin_2024")
PREMIUM_PASSWORD = _secret("PREMIUM_PASSWORD", "sparro_pro_2024")
FREE_PASSWORD    = _secret("FREE_PASSWORD",    "sparro_free")
TRIAL_DAYS = 2

def trial_days_left():
    if st.session_state.trial_start is None: return 0
    return max(0, TRIAL_DAYS - (datetime.datetime.now() - st.session_state.trial_start).days)

def trial_hours_left():
    if st.session_state.trial_start is None: return 0
    elapsed = datetime.datetime.now() - st.session_state.trial_start
    return max(0, TRIAL_DAYS * 24 - int(elapsed.total_seconds() / 3600))

def is_premium_access():
    if st.session_state.account_type in ("premium", "admin"): return True
    if st.session_state.account_type == "trial" and trial_hours_left() > 0: return True
    return False

# ════════ LOGIN PAGE ════════
def show_login_page():
    st.markdown("""
    <div style='max-width:480px;margin:40px auto'>
      <div style='text-align:center;font-size:60px;margin-bottom:4px'>🚀</div>
      <div style='text-align:center;font-size:36px;font-weight:900;
        background:linear-gradient(90deg,#00c6ff,#0072ff);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent'>Sparro FX AI</div>
      <div style='text-align:center;color:#8b949e;font-size:15px;margin-bottom:28px'>
        Professional AI-Powered Forex Signal Platform</div>
    </div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        tab1, tab2, tab3 = st.tabs(["🔑 Login", "🎁 Free 2-Day Trial", "ℹ️ About"])

        with tab1:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.markdown("#### Welcome back 👋")
            email    = st.text_input("Email", placeholder="you@email.com", key="li_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="li_pass")
            remember = st.checkbox("Keep me logged in", value=True)
            if st.button("🔓 Login", use_container_width=True, type="primary"):
                pw = password.strip()
                atype = None
                if pw == ADMIN_PASSWORD:   atype = "admin"
                elif pw == PREMIUM_PASSWORD: atype = "premium"
                elif pw == FREE_PASSWORD:    atype = "free"
                if atype:
                    st.session_state.update(logged_in=True, account_type=atype, user_email=email)
                    if remember: save_login(atype, email)
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Start a free trial or contact us to upgrade.")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:#8b949e;font-size:13px;margin-top:12px'>No account? Try the <b>Free 2-Day Trial</b> tab above.</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;margin-bottom:16px'>
              <span style='background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;
              border-radius:20px;padding:6px 18px;font-weight:700;font-size:14px'>
              🎁 2 Days FREE — Full Premium Access</span></div>""", unsafe_allow_html=True)
            st.markdown("#### Start your free trial")
            st.markdown("""No credit card needed. Get full access for 48 hours:
- ✅ All 10 assets live
- ✅ 8-strategy AI engine
- ✅ Pulse Signal — live strong trade alerts
- ✅ Charts with Entry / SL / TP
- ✅ AI News Analysis
- ✅ Trade Journal""")
            trial_email = st.text_input("Your email", placeholder="you@email.com", key="tr_email")
            trial_name  = st.text_input("Your name",  placeholder="First name",    key="tr_name")
            if st.button("🚀 Start Free Trial", use_container_width=True, type="primary"):
                if not trial_email or "@" not in trial_email:
                    st.error("❌ Enter a valid email.")
                elif not trial_name.strip():
                    st.error("❌ Enter your name.")
                else:
                    ts = datetime.datetime.now()
                    st.session_state.update(logged_in=True, account_type="trial",
                                            trial_start=ts, user_email=trial_email)
                    save_login("trial", trial_email, ts)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:#8b949e;font-size:13px;margin-top:12px'>After trial, upgrade for <b>$15/mo</b>.</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("""<div class='login-box'>
            <h4 style='margin-top:0'>What is Sparro FX AI?</h4>
            <p style='color:#8b949e'>Professional forex signal platform powered by 8 simultaneous
            technical strategies and real-time AI analysis.</p><br>
            <b>🆓 Free Plan</b> — 5 assets, basic signals<br><br>
            <b>🎁 Free Trial (48 hours)</b> — full premium, no card needed<br><br>
            <b>⚡ Premium ($15/mo)</b> — all 10 assets, 8 strategies, charts,
            Pulse Signal, AI news, trade journal<br><br>
            <hr style='border-color:#30363d'>
            <span style='color:#8b949e;font-size:12px'>Trade responsibly. Past signals do not guarantee future results.</span>
            </div>""", unsafe_allow_html=True)

# ════════ ACCESS GATE ════════
if not st.session_state.logged_in:
    show_login_page()
    st.stop()

if st.session_state.account_type == "trial" and trial_hours_left() == 0:
    st.error("⏰ Your 48-hour free trial has ended.")
    st.markdown("### Upgrade to keep full access — $15/mo")
    st.markdown("Contact us to receive your premium password.")
    col1, col2 = st.columns(2)
    if col1.button("🔓 I have a premium password"):
        clear_login()
        st.session_state.logged_in = False
        st.rerun()
    if col2.button("🔄 Back to Login"):
        clear_login()
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

# ════════ SIGNAL BANNER ════════
def show_signal_banner(sig, asset, conf):
    if sig == "STRONG BUY":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#0d5c2e,#1a7a3e);
        border:2px solid #3fb950;border-radius:14px;padding:22px;text-align:center;
        margin-bottom:16px;box-shadow:0 0 24px rgba(63,185,80,0.5)'>
        <div style='font-size:28px;font-weight:900;color:#3fb950;letter-spacing:2px'>🚀 STRONG BUY — BUY NOW</div>
        <div style='font-size:18px;color:#e6edf3;margin-top:8px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        <div style='font-size:13px;color:#8b949e;margin-top:6px'>⚡ {conf}% of strategies agree — high probability</div>
        </div>""", unsafe_allow_html=True)
    elif sig == "BUY":
        st.markdown(f"""<div style='background:#0d2b1a;border:2px solid #3fb950;
        border-radius:14px;padding:18px;text-align:center;margin-bottom:16px'>
        <div style='font-size:22px;font-weight:800;color:#3fb950'>🟢 BUY SIGNAL</div>
        <div style='font-size:16px;color:#e6edf3;margin-top:6px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""", unsafe_allow_html=True)
    elif sig == "STRONG SELL":
        st.markdown(f"""<div style='background:linear-gradient(135deg,#5c0d0d,#7a1a1a);
        border:2px solid #f85149;border-radius:14px;padding:22px;text-align:center;
        margin-bottom:16px;box-shadow:0 0 24px rgba(248,81,73,0.5)'>
        <div style='font-size:28px;font-weight:900;color:#f85149;letter-spacing:2px'>📉 STRONG SELL — SELL NOW</div>
        <div style='font-size:18px;color:#e6edf3;margin-top:8px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        <div style='font-size:13px;color:#8b949e;margin-top:6px'>⚡ {conf}% of strategies agree — high probability</div>
        </div>""", unsafe_allow_html=True)
    elif sig == "SELL":
        st.markdown(f"""<div style='background:#2b0d0d;border:2px solid #f85149;
        border-radius:14px;padding:18px;text-align:center;margin-bottom:16px'>
        <div style='font-size:22px;font-weight:800;color:#f85149'>🔴 SELL SIGNAL</div>
        <div style='font-size:16px;color:#e6edf3;margin-top:6px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#1c1c1c;border:2px solid #8b949e;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:16px'>
        <div style='font-size:20px;font-weight:700;color:#8b949e'>⏳ WAIT — No Clear Signal</div>
        <div style='color:#8b949e;margin-top:6px;font-size:14px'>{asset} — market unclear, stand aside</div>
        </div>""", unsafe_allow_html=True)

# ════════ ASSETS ════════
ALL_PAIRS = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])

# ════════ STRATEGIES ════════
def fetch_data(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def strategy_ema_trend(df):
    c=df["Close"]; e20=c.ewm(span=20).mean().iloc[-1]; e50=c.ewm(span=50).mean().iloc[-1]; e200=c.ewm(span=200).mean().iloc[-1]
    if e20>e50 and e50>e200: return "BUY",  "EMA20 > EMA50 > EMA200 — full bullish stack"
    if e20<e50 and e50<e200: return "SELL", "EMA20 < EMA50 < EMA200 — full bearish stack"
    return "NEUTRAL","EMA stack mixed"

def strategy_rsi(df):
    c=df["Close"]; d=c.diff()
    g=d.where(d>0,0).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean()
    rsi=(100-(100/(1+(g/l)))).iloc[-1]
    if rsi>60: return "BUY",  f"RSI={round(rsi,1)} — bullish momentum"
    if rsi<40: return "SELL", f"RSI={round(rsi,1)} — bearish momentum"
    return "NEUTRAL",f"RSI={round(rsi,1)} — neutral"

def strategy_macd(df):
    c=df["Close"]; m=c.ewm(span=12).mean()-c.ewm(span=26).mean(); s=m.ewm(span=9).mean(); h=m-s
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2]: return "BUY",  "MACD bullish crossover"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2]: return "SELL", "MACD bearish crossover"
    return "NEUTRAL","MACD weak signal"

def strategy_bollinger(df):
    c=df["Close"]; mid=c.rolling(20).mean(); std=c.rolling(20).std()
    upper=mid+2*std; lower=mid-2*std; p=c.iloc[-1]
    if p>upper.iloc[-1]: return "BUY",  "Above Bollinger upper — breakout"
    if p<lower.iloc[-1]: return "SELL", "Below Bollinger lower — breakdown"
    if p>mid.iloc[-1]:   return "BUY",  "Above BB midline"
    return "SELL","Below BB midline"

def strategy_sr(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    res=float(h.rolling(10).max().iloc[-1]); sup=float(l.rolling(10).min().iloc[-1]); zone=(res-sup)*0.15
    if p>=res-zone: return "SELL",f"At resistance {round(res,4)} — rejection likely"
    if p<=sup+zone: return "BUY", f"At support {round(sup,4)} — bounce likely"
    return ("BUY" if p>(res+sup)/2 else "SELL"),f"S={round(sup,4)} R={round(res,4)}"

def strategy_candles(df):
    o=df["Open"].iloc[-1] if "Open" in df.columns else df["Close"].iloc[-2]
    h=df["High"].iloc[-1]; l=df["Low"].iloc[-1]; c=df["Close"].iloc[-1]
    po=df["Open"].iloc[-2] if "Open" in df.columns else df["Close"].iloc[-3]; pc=df["Close"].iloc[-2]
    body=abs(c-o); candle=h-l; uw=h-max(c,o); lw=min(c,o)-l
    if c>o and pc<po and c>po and o<pc: return "BUY",  "Bullish Engulfing pattern"
    if c<o and pc>po and c<po and o>pc: return "SELL", "Bearish Engulfing pattern"
    if lw>body*2 and uw<body*0.5:       return "BUY",  "Hammer / Pin Bar — bullish rejection"
    if uw>body*2 and lw<body*0.5:       return "SELL", "Shooting Star — bearish rejection"
    if body<candle*0.1:                 return "NEUTRAL","Doji — indecision"
    return "NEUTRAL","No strong candle pattern"

def strategy_bos(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    sh=float(h.iloc[-20:-5].max()); sl_=float(l.iloc[-20:-5].min())
    if p>sh:  return "BUY",  f"Break of Structure — broke swing high {round(sh,4)}"
    if p<sl_: return "SELL", f"Break of Structure — broke swing low {round(sl_,4)}"
    return "NEUTRAL",f"Inside range {round(sl_,4)}-{round(sh,4)}"

def strategy_volume(df):
    if "Volume" not in df.columns: return "NEUTRAL","No volume data"
    v=df["Volume"]; c=df["Close"]
    avg=v.rolling(20).mean().iloc[-1]; cur=v.iloc[-1]; up=c.iloc[-1]>c.iloc[-2]; r=cur/avg if avg>0 else 1
    if r>1.5 and up:     return "BUY",  f"High volume bullish ({round(r,1)}x avg)"
    if r>1.5 and not up: return "SELL", f"High volume bearish ({round(r,1)}x avg)"
    return "NEUTRAL",f"Normal volume ({round(r,1)}x avg)"

STRATEGIES = {
    "EMA Trend":strategy_ema_trend,"RSI Momentum":strategy_rsi,
    "MACD Crossover":strategy_macd,"Bollinger Breakout":strategy_bollinger,
    "Support/Resistance":strategy_sr,"Candlestick Pattern":strategy_candles,
    "Break of Structure":strategy_bos,"Volume Momentum":strategy_volume,
}

def run_all_strategies(symbol, period="6mo"):
    df=fetch_data(symbol,period)
    if df is None: return {},0,"ERROR"
    results={}
    for name,fn in STRATEGIES.items():
        try:    results[name]=fn(df)
        except: results[name]=("NEUTRAL","Error")
    buys=sum(1 for s,_ in results.values() if s=="BUY"); sells=sum(1 for s,_ in results.values() if s=="SELL")
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

# ════════ PRICE CHART ════════
def show_price_chart(symbol, pair_name, signal, entry, sl, tp1, tp2):
    df=fetch_data(symbol,"3mo","1d")
    if df is None: st.warning("Chart data unavailable."); return
    close=df["Close"]; ema20=close.ewm(span=20).mean(); ema50=close.ewm(span=50).mean(); ema200=close.ewm(span=200).mean()
    res=float(df["High"].rolling(10).max().iloc[-1]); sup=float(df["Low"].rolling(10).min().iloc[-1])
    dates=df.index; fig=go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],low=df["Low"],close=close,
            name="Price",increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates,y=close,name="Price",line=dict(color="#58a6ff",width=2)))
    fig.add_trace(go.Scatter(x=dates,y=ema20, name="EMA 20", line=dict(color="#ffd700",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema50, name="EMA 50", line=dict(color="#ff7f50",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema200,name="EMA 200",line=dict(color="#da70d6",width=1,dash="dash")))
    fig.add_hline(y=res,line_color="#f85149",line_dash="dash",annotation_text=f"Resistance {round(res,4)}",annotation_position="right")
    fig.add_hline(y=sup,line_color="#3fb950",line_dash="dash",annotation_text=f"Support {round(sup,4)}",annotation_position="right")
    if entry:
        color="#3fb950" if "BUY" in signal else "#f85149"
        fig.add_hline(y=entry,line_color=color,   line_width=2,annotation_text=f"Entry {round(entry,5)}",annotation_position="left")
        fig.add_hline(y=sl,   line_color="#f85149",line_width=1,line_dash="dash",annotation_text=f"SL {round(sl,5)}",annotation_position="left")
        fig.add_hline(y=tp1,  line_color="#3fb950",line_width=1,line_dash="dash",annotation_text=f"TP1 {round(tp1,5)}",annotation_position="left")
        fig.add_hline(y=tp2,  line_color="#3fb950",line_width=1,line_dash="dot", annotation_text=f"TP2 {round(tp2,5)}",annotation_position="left")
    lp=float(close.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[lp],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in signal else "triangle-down",size=16,
                    color="#3fb950" if "BUY" in signal else "#f85149"),name=f"{signal} Signal"))
    fig.update_layout(title=f"{pair_name} — Price Chart",plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
        height=500,margin=dict(l=60,r=120,t=60,b=40))
    st.plotly_chart(fig,use_container_width=True)

    st.subheader("💡 Why Take This Trade?")
    pve20="above" if lp>float(ema20.iloc[-1]) else "below"
    pve200="above" if lp>float(ema200.iloc[-1]) else "below"
    trend="uptrend" if float(ema20.iloc[-1])>float(ema200.iloc[-1]) else "downtrend"
    ma=float(close.iloc[-22]) if len(close)>22 else float(close.iloc[0])
    cp=round((lp-ma)/ma*100,2); cs=f"up {cp}%" if cp>0 else f"down {abs(cp)}%"
    slope="rising" if float(ema20.iloc[-1])-float(ema20.iloc[-5])>0 else "falling"
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
        <b>📈 Price Movement (Last 30 days)</b><br><br>
        Moved <b>{cs}</b> over past month<br>
        Short-term trend: <b>{"bullish" if pve20=="above" else "bearish"}</b> (price {pve20} EMA20)<br>
        Long-term trend: <b>{"bullish" if pve200=="above" else "bearish"}</b> (price {pve200} EMA200)<br>
        EMA20 is <b>{slope}</b> — momentum {"building" if slope=="rising" else "weakening"}<br>
        Overall: <b>{trend.upper()}</b></div>""", unsafe_allow_html=True)
    with c2:
        nr=abs(lp-res)/lp<0.005; ns=abs(lp-sup)/lp<0.005
        zn="⚠️ Near resistance — watch for rejection" if nr else "✅ Near support — bounce zone" if ns else "📊 Mid range"
        ta=(("BUY" in signal and trend=="uptrend") or ("SELL" in signal and trend=="downtrend"))
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
        <b>🎯 Trade Reasoning</b><br><br>
        Signal: <b>{signal}</b><br>
        Key resistance: <b>{round(res,4)}</b><br>
        Key support: <b>{round(sup,4)}</b><br>
        {zn}<br>
        {"✅ Trend and signal AGREE — higher probability" if ta else "⚠️ Against trend — reduce position size"}</div>""", unsafe_allow_html=True)

# ════════ NEWS ════════
def fetch_forex_news():
    try:
        r=requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",timeout=8)
        if r.status_code==200:
            return pd.DataFrame([{"Time":e.get("date","")[:16].replace("T"," "),"Currency":e.get("currency",""),
                "Event":e.get("title",""),"Impact":e.get("impact",""),"Forecast":e.get("forecast","—"),"Previous":e.get("previous","—"),
            } for e in r.json()[:25]])
    except: pass
    return pd.DataFrame([
        {"Time":"Today 08:30","Currency":"USD","Event":"Non-Farm Payrolls","Impact":"High","Forecast":"180K","Previous":"175K"},
        {"Time":"Today 10:00","Currency":"EUR","Event":"ECB Rate Decision","Impact":"High","Forecast":"4.5%","Previous":"4.5%"},
        {"Time":"Today 13:30","Currency":"GBP","Event":"CPI y/y","Impact":"Medium","Forecast":"3.1%","Previous":"3.4%"},
        {"Time":"Tomorrow 14:00","Currency":"USD","Event":"FOMC Minutes","Impact":"High","Forecast":"—","Previous":"—"},
    ])

def analyse_news_with_ai(news_df, pair):
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":_secret("ANTHROPIC_API_KEY",""),"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":800,"messages":[{"role":"user","content":
                f"You are a professional forex analyst. Asset: {pair}\n\nCalendar:\n{news_df.to_string(index=False)}\n\n"
                "Analyse: 1) Which events affect this pair most? 2) Bullish/Bearish/Neutral? "
                "3) Times to AVOID trading? 4) Biggest move events? 5) Overall bias this week? Use bullet points."}]},timeout=30)
        if r.status_code==200: return r.json()["content"][0]["text"]
        return f"AI error {r.status_code}"
    except Exception as e: return f"Error: {e}"

# ════════ SIDEBAR ════════
premium = is_premium_access()
pairs   = ALL_PAIRS if premium else FREE_PAIRS
atype   = st.session_state.account_type

with st.sidebar:
    st.title("🚀 Sparro FX AI")
    st.divider()

    if atype=="admin":     st.success("👑 Admin")
    elif atype=="premium": st.success("⚡ Premium Active")
    elif atype=="trial":
        h=trial_hours_left()
        st.warning(f"🎁 Trial — {h}h left")
        if h<=12: st.error("⏰ Upgrade now to keep access!")
    elif atype=="free":
        st.info("🆓 Free Plan")
        if st.button("⚡ Upgrade — $15/mo"): st.info("Contact us for your premium password.")

    if st.session_state.user_email: st.caption(f"👤 {st.session_state.user_email}")
    st.divider()

    # Build nav based on account type
    nav_options = ["⚡ Pulse Signal","📊 Scanner","🏆 Trade of the Day",
                   "🔬 Deep Analysis","🗞️ News Analysis",
                   "📓 Trade Journal","📈 Performance","💰 Risk Calculator","💎 Pricing"]

    if atype == "admin":
        nav_options += ["👑 Admin Panel"]

    page = st.radio("Navigate", nav_options)
    st.divider()
    if st.button("🚪 Logout"):
        clear_login()
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: PULSE SIGNAL
# ════════════════════════════════════════════════════════════
if "Pulse Signal" in page:
    st.title("⚡ Pulse Signal")
    st.markdown("<div style='color:#8b949e;margin-bottom:20px'>Live feed of the strongest active trade setups right now. Only high-confidence signals appear here.</div>", unsafe_allow_html=True)

    if not premium:
        st.warning("🔒 Upgrade to see live Pulse Signals.")
        st.stop()

    with st.spinner("🔍 Scanning all markets for strong signals..."):
        pulse_signals = []
        for name, sym in ALL_PAIRS.items():
            strats, conf, sig = run_all_strategies(sym)
            if sig in ("STRONG BUY", "STRONG SELL") and conf >= 70:
                entry, sl, tp1, tp2, tp3, atr = get_trade_setup(sym, sig)
                if entry:
                    pulse_signals.append({
                        "name": name, "sym": sym, "sig": sig,
                        "conf": conf, "entry": entry, "sl": sl,
                        "tp1": tp1, "tp2": tp2, "tp3": tp3,
                        "strats": strats
                    })
        pulse_signals.sort(key=lambda x: x["conf"], reverse=True)

    st.caption(f"🕐 Last scanned: {datetime.datetime.now().strftime('%H:%M:%S UTC')}  —  {len(pulse_signals)} strong signal(s) found")
    if st.button("🔄 Refresh Pulse"):
        st.rerun()

    if not pulse_signals:
        st.markdown("""<div style='background:#161b22;border:1px solid #30363d;border-radius:14px;
        padding:40px;text-align:center'>
        <div style='font-size:40px'>😴</div>
        <div style='font-size:20px;color:#8b949e;margin-top:12px'>No strong signals right now</div>
        <div style='color:#8b949e;margin-top:8px;font-size:14px'>The market is quiet. Check back soon or browse the Scanner.</div>
        </div>""", unsafe_allow_html=True)
    else:
        for p in pulse_signals:
            is_buy = "BUY" in p["sig"]
            border = "#3fb950" if is_buy else "#f85149"
            bg     = "linear-gradient(135deg,#0d5c2e,#0d2b1a)" if is_buy else "linear-gradient(135deg,#5c0d0d,#2b0d0d)"
            icon   = "🚀" if is_buy else "📉"
            direction = "BUY NOW" if is_buy else "SELL NOW"

            # Confidence bar
            conf_color = "#3fb950" if p["conf"] >= 80 else "#ffd700" if p["conf"] >= 65 else "#f85149"

            st.markdown(f"""
            <div style='background:{bg};border:2px solid {border};border-radius:14px;
            padding:20px;margin-bottom:16px;box-shadow:0 0 16px {border}55'>
              <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div>
                  <span style='font-size:22px;font-weight:900;color:{border}'>{icon} {p["sig"]} — {direction}</span><br>
                  <span style='font-size:18px;color:#e6edf3;font-weight:700'>{p["name"]}</span>
                </div>
                <div style='text-align:right'>
                  <div style='font-size:28px;font-weight:900;color:{conf_color}'>{p["conf"]}%</div>
                  <div style='font-size:12px;color:#8b949e'>confidence</div>
                </div>
              </div>
              <div style='display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px'>
                <div style='background:#00000033;border-radius:8px;padding:8px;text-align:center'>
                  <div style='font-size:11px;color:#8b949e'>ENTRY</div>
                  <div style='font-size:13px;font-weight:700;color:#e6edf3'>{round(p["entry"],5)}</div>
                </div>
                <div style='background:#00000033;border-radius:8px;padding:8px;text-align:center'>
                  <div style='font-size:11px;color:#8b949e'>STOP LOSS</div>
                  <div style='font-size:13px;font-weight:700;color:#f85149'>{round(p["sl"],5)}</div>
                </div>
                <div style='background:#00000033;border-radius:8px;padding:8px;text-align:center'>
                  <div style='font-size:11px;color:#8b949e'>TP1</div>
                  <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp1"],5)}</div>
                </div>
                <div style='background:#00000033;border-radius:8px;padding:8px;text-align:center'>
                  <div style='font-size:11px;color:#8b949e'>TP2</div>
                  <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp2"],5)}</div>
                </div>
                <div style='background:#00000033;border-radius:8px;padding:8px;text-align:center'>
                  <div style='font-size:11px;color:#8b949e'>TP3</div>
                  <div style='font-size:13px;font-weight:700;color:#3fb950'>{round(p["tp3"],5)}</div>
                </div>
              </div>
              <div style='font-size:12px;color:#8b949e'>
                Strategies agreeing: {", ".join(n for n,(s,_) in p["strats"].items() if s==("BUY" if is_buy else "SELL"))}
              </div>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"📊 View {p['name']} Chart"):
                show_price_chart(p["sym"], p["name"], p["sig"], p["entry"], p["sl"], p["tp1"], p["tp2"])

# ════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ════════════════════════════════════════════════════════════
elif "Scanner" in page:
    st.title("📊 Market Scanner")
    if not premium: st.warning("🔒 Free plan: 5 assets. Upgrade for all 10.")
    results=[]; prog=st.progress(0); items=list(pairs.items())
    for i,(name,sym) in enumerate(items):
        strats,conf,sig=run_all_strategies(sym)
        buys=sum(1 for s,_ in strats.values() if s=="BUY"); sells=sum(1 for s,_ in strats.values() if s=="SELL")
        results.append({"Asset":name,"Signal":sig,
            "Confidence":f"{conf}%" if premium else "🔒","Strategies":f"{max(buys,sells)}/8" if premium else "🔒"})
        prog.progress((i+1)/len(items))
    prog.empty()
    scanner=pd.DataFrame(results)
    strong=[r for r in results if r["Signal"] in ("STRONG BUY","STRONG SELL")]
    if strong:
        st.subheader("⚡ Urgent Signals")
        for r in strong:
            cv=int(r["Confidence"].replace("%","")) if "%" in str(r["Confidence"]) else 0
            show_signal_banner(r["Signal"],r["Asset"],cv)
    c1,c2=st.columns(2)
    with c1:
        st.subheader("🚀 Top Buys")
        st.dataframe(scanner[scanner["Signal"].str.contains("BUY",na=False)].head(3),use_container_width=True)
    with c2:
        st.subheader("📉 Top Sells")
        st.dataframe(scanner[scanner["Signal"].str.contains("SELL",na=False)].head(3),use_container_width=True)
    st.subheader("Full Scanner"); st.dataframe(scanner,use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: TRADE OF THE DAY
# ════════════════════════════════════════════════════════════
elif "Trade of the Day" in page:
    st.title("🏆 Trade of the Day")
    if not premium: st.error("🔒 Premium only."); st.stop()
    best={"conf":0,"sig":"WAIT","name":"","sym":"","strats":{}}
    with st.spinner("Scanning all assets..."):
        for name,sym in ALL_PAIRS.items():
            strats,conf,sig=run_all_strategies(sym)
            if sig!="WAIT" and conf>best["conf"]: best={"conf":conf,"sig":sig,"name":name,"sym":sym,"strats":strats}
    show_signal_banner(best["sig"],best["name"],best["conf"])
    c1,c2,c3=st.columns(3)
    c1.metric("🏆 Asset",best["name"]); c2.metric("📡 Signal",best["sig"]); c3.metric("🎯 Confidence",f"{best['conf']}%")
    st.progress(best["conf"]/100); st.divider()
    entry,sl,tp1,tp2,tp3,atr=get_trade_setup(best["sym"],best["sig"])
    if entry:
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        if st.button("➕ Add to Journal"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),"Asset":best["name"],
                "Signal":best["sig"],"Entry":entry,"SL":sl,"TP1":tp1,"Confidence":best["conf"],"Result":"Open"})
            st.success("✅ Added to journal!")
    st.divider()
    if best["sym"]: show_price_chart(best["sym"],best["name"],best["sig"],entry,sl,tp1,tp2)

# ════════════════════════════════════════════════════════════
# PAGE: DEEP ANALYSIS
# ════════════════════════════════════════════════════════════
elif "Deep Analysis" in page:
    st.title("🔬 Deep Strategy Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    selected=st.selectbox("Choose Asset",list(ALL_PAIRS.keys())); sym=ALL_PAIRS[selected]
    with st.spinner(f"Running 8 strategies on {selected}..."):
        strats,conf,sig=run_all_strategies(sym)
    show_signal_banner(sig,selected,conf)
    c1,c2,c3=st.columns(3)
    c1.metric("Signal",sig); c2.metric("Confidence",f"{conf}%"); c3.metric("Strategies","8 analysed")
    st.progress(conf/100); st.divider()
    for name,(s,reason) in strats.items():
        color="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
        icon ="🟢"      if s=="BUY" else "🔴"      if s=="SELL" else "🟡"
        sr=reason.replace("<","&lt;").replace(">","&gt;")
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:12px;margin-bottom:8px;border-left:4px solid {color}'>
          <b>{icon} {name}</b> &nbsp;
          <span style='background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px'>{s}</span><br>
          <small style='color:#8b949e'>{sr}</small></div>""",unsafe_allow_html=True)
    buys=sum(1 for s,_ in strats.values() if s=="BUY"); sells=sum(1 for s,_ in strats.values() if s=="SELL")
    c1,c2,c3=st.columns(3)
    c1.metric("🟢 Buy Votes",buys); c2.metric("🔴 Sell Votes",sells); c3.metric("🟡 Neutral",8-buys-sells)
    st.divider()
    entry,sl,tp1,tp2,tp3,atr=get_trade_setup(sym,sig)
    if entry and sig!="WAIT":
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        if conf>=75:   st.success(f"✅ HIGH confidence — {conf}% agree")
        elif conf>=60: st.warning(f"⚠️ MODERATE — {conf}%. Use smaller size.")
        else:          st.error(f"🚨 LOW — {conf}%. Consider waiting.")
    st.divider(); show_price_chart(sym,selected,sig,entry,sl,tp1,tp2)

# ════════════════════════════════════════════════════════════
# PAGE: NEWS ANALYSIS
# ════════════════════════════════════════════════════════════
elif "News" in page:
    st.title("🗞️ News Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.spinner("Fetching calendar..."): news_df=fetch_forex_news()
    st.subheader("📅 Economic Calendar — This Week"); st.dataframe(news_df,use_container_width=True)
    st.divider(); st.subheader("🤖 AI News Analysis")
    selected=st.selectbox("Select asset",list(ALL_PAIRS.keys()))
    if st.button("🔍 Analyse News Impact"):
        with st.spinner("Analysing..."): analysis=analyse_news_with_ai(news_df,selected)
        st.markdown(f"<div class='news-card'>{analysis.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
    st.divider(); st.subheader("⚠️ High-Impact Events")
    high=news_df[news_df["Impact"]=="High"] if "Impact" in news_df.columns else pd.DataFrame()
    if not high.empty:
        for _,row in high.iterrows():
            st.error(f"🔴 {row.get('Time','')} | {row.get('Currency','')} — {row.get('Event','')} | Forecast: {row.get('Forecast','—')}")
    else: st.success("✅ No high-impact events — safe window")

# ════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("➕ Log a Trade"):
        c1,c2,c3=st.columns(3)
        ja=c1.selectbox("Asset",list(ALL_PAIRS.keys())); js=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"])
        jr=c3.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c4,c5,c6=st.columns(3)
        je=c4.number_input("Entry",format="%.5f"); jc=c5.slider("Confidence",0,100,70); jn=c6.text_input("Notes")
        if st.button("Save Trade"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),"Asset":ja,"Signal":js,
                "Entry":je,"SL":0,"TP1":0,"Confidence":jc,"Result":jr,"Notes":jn})
            st.success("✅ Saved!")
    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal); st.dataframe(df,use_container_width=True)
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
    if not st.session_state.trade_journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); tot=wins+loss
    wr=round(wins/tot*100,1) if tot>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Trades",tot); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")
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
        balance=st.number_input("Balance ($)",min_value=10.0,value=1000.0)
        rp=st.slider("Risk %",0.5,10.0,2.0,step=0.5)
        slp=st.number_input("Stop Loss (pips)",min_value=1.0,value=20.0)
        pv=st.number_input("Pip Value per 0.01 lot ($)",value=0.10)
        rr=st.slider("Risk:Reward",1,5,2)
    ra=balance*rp/100; lot=round(ra/(slp*pv/0.01)*0.01,2)
    with c2:
        st.metric("Risk Amount",f"${ra:.2f}"); st.metric("Lot Size",f"{lot} lots")
        st.metric("Potential Profit",f"${ra*rr:.2f}"); st.metric("R:R",f"1:{rr}")
    st.progress(rp/10)
    if rp<=2:  st.success("✅ Conservative — good risk management")
    elif rp<=5: st.warning("⚠️ Moderate — be careful")
    else:       st.error("🚨 High risk — reduce position size")

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
        5 assets &nbsp;·&nbsp; Basic signals<br><br>
        ❌ Pulse Signal<br>❌ Confidence scores<br>❌ 8-strategy engine<br>
        ❌ Price charts<br>❌ News Analysis<br>❌ Trade Journal
        </div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$15/mo</h2><hr>
        ✅ <b>⚡ Pulse Signal</b> — live strong trades<br>
        ✅ All 10 assets<br>✅ 8-strategy engine<br>
        ✅ Charts with Entry/SL/TP<br>
        ✅ Why take this trade<br>✅ News Analysis + AI<br>
        ✅ Trade Journal + Performance
        </div>""",unsafe_allow_html=True)
    st.divider()
    st.markdown("""**💳 Collect payments via:**
- **[Whop.com](https://whop.com)** — built for trading tools
- **[Gumroad](https://gumroad.com)** — live in 15 minutes
- **[Stripe](https://stripe.com)** — professional billing""")
    st.info("💡 Tip: Start on **Whop** — perfect for trading signal products.")

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ════════════════════════════════════════════════════════════
elif "Admin" in page:
    if atype != "admin":
        st.error("🔒 Admin only."); st.stop()

    st.title("👑 Admin Panel")
    st.markdown(f"<div style='color:#8b949e'>Logged in as admin — {st.session_state.user_email}</div><br>", unsafe_allow_html=True)

    # ── Password Management ──────────────────────────────────
    st.subheader("🔐 Password Management")
    st.info("""Passwords are stored in `.streamlit/secrets.toml` on Streamlit Cloud.

To update them:
1. Go to your app on **share.streamlit.io**
2. Click **Settings → Secrets**
3. Edit the values and save — app restarts automatically

```toml
ADMIN_PASSWORD   = "your-admin-password"
PREMIUM_PASSWORD = "your-premium-password"
FREE_PASSWORD    = "sparro_free"
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```""")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div style='background:#161b22;border-radius:10px;padding:16px;border-left:4px solid #ffd700'>
        <b>👑 Admin Password</b><br>
        <span style='color:#8b949e;font-size:13px'>Only you should know this. Never share it.</span>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div style='background:#161b22;border-radius:10px;padding:16px;border-left:4px solid #3fb950'>
        <b>⚡ Premium Password</b><br>
        <span style='color:#8b949e;font-size:13px'>Share with paying subscribers. Change anytime to revoke access from non-payers.</span>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Subscriber Management ────────────────────────────────
    st.subheader("👥 Subscriber Management")
    st.markdown("Track your paying subscribers below. This is stored locally in your session — keep a copy in a spreadsheet or Notion.")

    if "subscribers" not in st.session_state:
        st.session_state.subscribers = []

    with st.expander("➕ Add New Subscriber"):
        c1, c2, c3 = st.columns(3)
        sub_name  = c1.text_input("Name",  key="sub_name")
        sub_email = c2.text_input("Email", key="sub_email")
        sub_plan  = c3.selectbox("Plan", ["Premium ($15/mo)", "Trial", "Free"])
        sub_date  = st.date_input("Start Date", datetime.date.today())
        sub_notes = st.text_input("Notes (optional)", key="sub_notes")
        if st.button("➕ Add Subscriber"):
            if sub_name and sub_email:
                st.session_state.subscribers.append({
                    "Name": sub_name, "Email": sub_email,
                    "Plan": sub_plan, "Start Date": str(sub_date),
                    "Notes": sub_notes, "Status": "Active"
                })
                st.success(f"✅ {sub_name} added!")
            else:
                st.error("Name and email required.")

    if st.session_state.subscribers:
        df_sub = pd.DataFrame(st.session_state.subscribers)
        st.dataframe(df_sub, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Subscribers", len(df_sub))
        premium_count = len(df_sub[df_sub["Plan"].str.contains("Premium", na=False)])
        c2.metric("Premium", premium_count)
        c3.metric("Monthly Revenue", f"${premium_count * 15}")
    else:
        st.info("No subscribers yet. Add your first one above.")

    st.divider()

    # ── App Stats ────────────────────────────────────────────
    st.subheader("📊 Quick Stats")
    c1, c2, c3, c4 = st.columns(4)
    sub_count = len(st.session_state.get("subscribers", []))
    revenue   = sub_count * 15
    c1.metric("Subscribers", sub_count)
    c2.metric("Monthly Revenue", f"${revenue}")
    c3.metric("Trial Length", "48 hours")
    c4.metric("Plan Price", "$15/mo")

    st.divider()
    st.subheader("🔗 Useful Links")
    st.markdown("""
    - 🌐 [Your Streamlit App](https://share.streamlit.io) — manage deployment & secrets
    - 💳 [Whop.com](https://whop.com) — accept payments
    - 📊 [GitHub Repo](https://github.com/sparroxhalo-stack/ai-forex-analyzer) — update code
    - 🤖 [Anthropic Console](https://console.anthropic.com) — manage AI API key
    """)
