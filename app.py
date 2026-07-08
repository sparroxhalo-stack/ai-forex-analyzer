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
  .tier-box{background:#161b22;border-radius:14px;padding:20px;
    text-align:center;border:2px solid #30363d}
  .tier-box.gold{border-color:#ffd200}
  .news-card{background:#161b22;border-radius:10px;padding:14px;
    margin-bottom:8px;border-left:4px solid #f78166}
  .strategy-card{background:#161b22;border-radius:10px;padding:14px;
    margin-bottom:8px;border-left:4px solid #3fb950;font-size:14px;line-height:1.8}
  .login-box{background:#161b22;border-radius:16px;padding:32px;
    max-width:400px;margin:60px auto;border:1px solid #30363d}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# SUPABASE HELPERS
# ════════════════════════════════════════════════════════════
def get_supabase_headers():
    key = st.secrets.get("SUPABASE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

def supabase_url(path):
    base = st.secrets.get("SUPABASE_URL", "")
    return f"{base}/rest/v1/{path}"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(email):
    try:
        r = requests.get(
            supabase_url(f"users?email=eq.{email}&select=*"),
            headers=get_supabase_headers(), timeout=8
        )
        data = r.json()
        return data[0] if data else None
    except: return None

def create_user(email, password, tier="free"):
    try:
        r = requests.post(
            supabase_url("users"),
            headers=get_supabase_headers(),
            json={
                "email": email,
                "password_hash": hash_password(password),
                "tier": tier,
                "is_active": True,
                "created_at": datetime.datetime.now().isoformat()
            }, timeout=8
        )
        return r.status_code in [200, 201]
    except: return False

def update_user_tier(email, tier):
    try:
        r = requests.patch(
            supabase_url(f"users?email=eq.{email}"),
            headers=get_supabase_headers(),
            json={"tier": tier}, timeout=8
        )
        return r.status_code in [200, 204]
    except: return False

def delete_user(email):
    try:
        r = requests.delete(
            supabase_url(f"users?email=eq.{email}"),
            headers=get_supabase_headers(), timeout=8
        )
        return r.status_code in [200, 204]
    except: return False

def get_all_users():
    try:
        r = requests.get(
            supabase_url("users?select=*&order=created_at.desc"),
            headers=get_supabase_headers(), timeout=8
        )
        return r.json()
    except: return []

# ════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════
DEFAULTS = {
    "logged_in": False,
    "user_email": "",
    "user_tier": "free",
    "is_admin": False,
    "trade_journal": [],
    "telegram_token": "",
    "telegram_chat_id": "",
    "notification_threshold": 75,
    "ai_strategy": "",
}
for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ════════════════════════════════════════════════════════════
# LOGIN / REGISTER SCREEN
# ════════════════════════════════════════════════════════════
def show_login():
    st.markdown("""
    <div style='text-align:center;padding:40px 0 20px'>
      <h1>🚀 Sparro FX AI</h1>
      <p style='color:#8b949e'>AI-Powered Forex & Commodity Trading Signals</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        st.subheader("Login to your account")
        email    = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", type="primary", use_container_width=True):
            # Check admin first
            admin_user = st.secrets.get("ADMIN_USERNAME","admin")
            admin_pass = st.secrets.get("ADMIN_PASSWORD","")
            if email == admin_user and password == admin_pass:
                st.session_state.logged_in  = True
                st.session_state.is_admin   = True
                st.session_state.user_email = email
                st.session_state.user_tier  = "admin"
                st.rerun()
            else:
                user = get_user(email)
                if user and user["password_hash"] == hash_password(password):
                    if not user.get("is_active", True):
                        st.error("❌ Account deactivated. Contact support.")
                    else:
                        st.session_state.logged_in  = True
                        st.session_state.is_admin   = False
                        st.session_state.user_email = email
                        st.session_state.user_tier  = user.get("tier","free")
                        st.rerun()
                else:
                    st.error("❌ Invalid email or password.")

        st.divider()
        st.caption("Don't have an account? Switch to the Register tab above.")

    with tab2:
        st.subheader("Create a free account")
        reg_email = st.text_input("Email",            key="reg_email")
        reg_pass  = st.text_input("Password",         key="reg_pass",  type="password")
        reg_pass2 = st.text_input("Confirm Password", key="reg_pass2", type="password")

        if st.button("Create Account", type="primary", use_container_width=True):
            if not reg_email or not reg_pass:
                st.error("Please fill in all fields.")
            elif reg_pass != reg_pass2:
                st.error("❌ Passwords don't match.")
            elif len(reg_pass) < 6:
                st.error("❌ Password must be at least 6 characters.")
            elif get_user(reg_email):
                st.error("❌ Email already registered. Please login.")
            else:
                if create_user(reg_email, reg_pass, "free"):
                    st.success("✅ Account created! Please login.")
                else:
                    st.error("❌ Registration failed. Try again.")

if not st.session_state.logged_in:
    show_login()
    st.stop()

# ════════════════════════════════════════════════════════════
# ASSETS
# ════════════════════════════════════════════════════════════
ALL_PAIRS = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])

premium = st.session_state.user_tier in ["premium","admin"]
is_admin = st.session_state.is_admin
pairs = ALL_PAIRS if premium else FREE_PAIRS

# ════════════════════════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════════════════════════
def send_telegram(token, chat_id, message):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id":chat_id,"text":message,"parse_mode":"Markdown"}, timeout=5
        )
        return r.status_code == 200
    except: return False

def notify_trade(asset, signal, confidence, entry, sl, tp1, tp2, tp3):
    token   = st.session_state.telegram_token
    chat_id = st.session_state.telegram_chat_id
    if not token or not chat_id: return False
    direction = "🚀 BUY" if "BUY" in signal else "📉 SELL"
    msg = f"""
🔔 *Sparro FX AI Signal*
{direction} *{asset}*
📊 {signal} | 🎯 {confidence}%
💰 Entry: `{round(entry,5)}`
🛑 SL: `{round(sl,5)}`
✅ TP1: `{round(tp1,5)}` | TP2: `{round(tp2,5)}` | TP3: `{round(tp3,5)}`
⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
"""
    return send_telegram(token, chat_id, msg)

# ════════════════════════════════════════════════════════════
# STRATEGY ENGINE
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
    c=df["Close"]; e20=c.ewm(span=20).mean().iloc[-1]; e50=c.ewm(span=50).mean().iloc[-1]; e200=c.ewm(span=200).mean().iloc[-1]
    if e20>e50 and e50>e200: return "BUY",  "EMA20>EMA50>EMA200 — full bullish stack"
    if e20<e50 and e50<e200: return "SELL", "EMA20<EMA50<EMA200 — full bearish stack"
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
    if m.iloc[-1]>s.iloc[-1] and h.iloc[-1]>h.iloc[-2]: return "BUY","MACD bullish crossover"
    if m.iloc[-1]<s.iloc[-1] and h.iloc[-1]<h.iloc[-2]: return "SELL","MACD bearish crossover"
    return "NEUTRAL","MACD weak signal"

def strategy_bollinger(df):
    c=df["Close"]; mid=c.rolling(20).mean(); std=c.rolling(20).std()
    upper=mid+2*std; lower=mid-2*std; p=c.iloc[-1]; bw=((upper-lower)/mid).iloc[-1]
    if p>upper.iloc[-1]: return "BUY",  f"Above Bollinger upper — breakout"
    if p<lower.iloc[-1]: return "SELL", f"Below Bollinger lower — breakdown"
    if p>mid.iloc[-1]:   return "BUY",  f"Above BB midline"
    return "SELL","Below BB midline"

def strategy_sr(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    res=float(h.rolling(10).max().iloc[-1]); sup=float(l.rolling(10).min().iloc[-1])
    zone=(res-sup)*0.15
    if p>=res-zone: return "SELL",f"At resistance {round(res,4)}"
    if p<=sup+zone: return "BUY", f"At support {round(sup,4)}"
    return ("BUY" if p>(res+sup)/2 else "SELL"),f"S={round(sup,4)} R={round(res,4)}"

def strategy_candles(df):
    o=df["Open"].iloc[-1] if "Open" in df.columns else df["Close"].iloc[-2]
    h=df["High"].iloc[-1]; l=df["Low"].iloc[-1]; c=df["Close"].iloc[-1]
    po=df["Open"].iloc[-2] if "Open" in df.columns else df["Close"].iloc[-3]; pc=df["Close"].iloc[-2]
    body=abs(c-o); candle=h-l; uw=h-max(c,o); lw=min(c,o)-l
    if c>o and pc<po and c>po and o<pc: return "BUY","Bullish Engulfing"
    if c<o and pc>po and c<po and o>pc: return "SELL","Bearish Engulfing"
    if lw>body*2 and uw<body*0.5:       return "BUY","Hammer / Pin Bar"
    if uw>body*2 and lw<body*0.5:       return "SELL","Shooting Star"
    if body<candle*0.1:                 return "NEUTRAL","Doji — indecision"
    return "NEUTRAL","No strong pattern"

def strategy_bos(df):
    h=df["High"]; l=df["Low"]; p=float(df["Close"].iloc[-1])
    sh=float(h.iloc[-20:-5].max()); sl_=float(l.iloc[-20:-5].min())
    if p>sh: return "BUY",  f"Break of Structure — above {round(sh,4)}"
    if p<sl_:return "SELL", f"Break of Structure — below {round(sl_,4)}"
    return "NEUTRAL",f"Inside range {round(sl_,4)}–{round(sh,4)}"

def strategy_volume(df):
    if "Volume" not in df.columns: return "NEUTRAL","No volume data"
    v=df["Volume"]; c=df["Close"]
    avg=v.rolling(20).mean().iloc[-1]; cur=v.iloc[-1]; up=c.iloc[-1]>c.iloc[-2]; r=cur/avg if avg>0 else 1
    if r>1.5 and up:     return "BUY",  f"High volume bullish ({round(r,1)}×)"
    if r>1.5 and not up: return "SELL", f"High volume bearish ({round(r,1)}×)"
    return "NEUTRAL",f"Normal volume ({round(r,1)}×)"

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
    buys=sum(1 for s,_ in results.values() if s=="BUY")
    sells=sum(1 for s,_ in results.values() if s=="SELL")
    total=len(results)
    if buys>sells:   conf=round(buys/total*100);  sig="STRONG BUY" if buys>=6 else "BUY"
    elif sells>buys: conf=round(sells/total*100); sig="STRONG SELL" if sells>=6 else "SELL"
    else:            conf=50; sig="WAIT"
    return results,conf,sig

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
# PRICE CHART
# ════════════════════════════════════════════════════════════
def show_price_chart(symbol, pair_name, signal, entry, sl, tp1, tp2):
    import plotly.graph_objects as go
    df=fetch_data(symbol,"3mo","1d")
    if df is None: st.warning("Chart unavailable."); return
    close=df["Close"]; ema20=close.ewm(span=20).mean(); ema50=close.ewm(span=50).mean(); ema200=close.ewm(span=200).mean()
    resistance=float(df["High"].rolling(10).max().iloc[-1]); support=float(df["Low"].rolling(10).min().iloc[-1])
    dates=df.index; fig=go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates,open=df["Open"],high=df["High"],low=df["Low"],close=close,
            name="Price",increasing_line_color="#3fb950",decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates,y=close,name="Price",line=dict(color="#58a6ff",width=2)))
    fig.add_trace(go.Scatter(x=dates,y=ema20, name="EMA20", line=dict(color="#ffd700",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema50, name="EMA50", line=dict(color="#ff7f50",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=dates,y=ema200,name="EMA200",line=dict(color="#da70d6",width=1,dash="dash")))
    fig.add_hline(y=resistance,line_color="#f85149",line_dash="dash",annotation_text=f"R {round(resistance,4)}",annotation_position="right")
    fig.add_hline(y=support,   line_color="#3fb950",line_dash="dash",annotation_text=f"S {round(support,4)}",  annotation_position="right")
    if entry:
        color="#3fb950" if "BUY" in signal else "#f85149"
        fig.add_hline(y=entry,line_color=color,   line_width=2,annotation_text=f"Entry {round(entry,5)}",annotation_position="left")
        fig.add_hline(y=sl,   line_color="#f85149",line_width=1,line_dash="dash",annotation_text=f"SL {round(sl,5)}",annotation_position="left")
        fig.add_hline(y=tp1,  line_color="#3fb950",line_width=1,line_dash="dash",annotation_text=f"TP1 {round(tp1,5)}",annotation_position="left")
        fig.add_hline(y=tp2,  line_color="#3fb950",line_width=1,line_dash="dot", annotation_text=f"TP2 {round(tp2,5)}",annotation_position="left")
    last_price=float(close.iloc[-1])
    fig.add_trace(go.Scatter(x=[dates[-1]],y=[last_price],mode="markers",
        marker=dict(symbol="triangle-up" if "BUY" in signal else "triangle-down",size=16,
        color="#3fb950" if "BUY" in signal else "#f85149"),name=f"{signal} Signal"))
    fig.update_layout(title=f"{pair_name} — Price Chart",plot_bgcolor="#0d1117",paper_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),xaxis=dict(gridcolor="#21262d",rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),height=500,margin=dict(l=60,r=120,t=60,b=40),
        legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1))
    st.plotly_chart(fig,use_container_width=True)

    st.subheader("💡 Why Take This Trade?")
    month_ago=float(close.iloc[-22]) if len(close)>22 else float(close.iloc[0])
    change_pct=round((last_price-month_ago)/month_ago*100,2)
    trend_dir="uptrend" if float(ema20.iloc[-1])>float(ema200.iloc[-1]) else "downtrend"
    ema_slope=float(ema20.iloc[-1])-float(ema20.iloc[-5])
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
        <b>📈 Price Movement (30 days)</b><br><br>
        • Price moved <b>{"up" if change_pct>0 else "down"} {abs(change_pct)}%</b> last month<br>
        • EMA20 is <b>{"rising" if ema_slope>0 else "falling"}</b> — momentum {"building" if ema_slope>0 else "weakening"}<br>
        • Overall market: <b>{trend_dir.upper()}</b>
        </div>""",unsafe_allow_html=True)
    with c2:
        agree = ("BUY" in signal and trend_dir=="uptrend") or ("SELL" in signal and trend_dir=="downtrend")
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
        <b>🎯 Trade Reasoning</b><br><br>
        • Signal: <b>{signal}</b><br>
        • Resistance: <b>{round(resistance,4)}</b> | Support: <b>{round(support,4)}</b><br>
        • {"✅ Trading WITH the trend — higher probability" if agree else "⚠️ Trading AGAINST trend — reduce size"}
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
                "Previous":e.get("previous","—")} for e in r.json()[:25]])
    except: pass
    return pd.DataFrame([
        {"Time":"Today 08:30","Currency":"USD","Event":"Non-Farm Payrolls","Impact":"High","Forecast":"180K","Previous":"175K"},
        {"Time":"Today 10:00","Currency":"EUR","Event":"ECB Rate Decision","Impact":"High","Forecast":"4.5%","Previous":"4.5%"},
        {"Time":"Today 13:30","Currency":"GBP","Event":"CPI y/y","Impact":"Medium","Forecast":"3.1%","Previous":"3.4%"},
    ])

def call_ai(prompt):
    try:
        api_key=st.secrets.get("ANTHROPIC_API_KEY","")
        if not api_key: return "⚠️ Add ANTHROPIC_API_KEY to Streamlit secrets."
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":1000,"messages":[{"role":"user","content":prompt}]},
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

    # User info
    tier_label = "👑 Admin" if is_admin else ("⚡ Premium" if premium else "🆓 Free")
    st.markdown(f"**{tier_label}**")
    st.caption(f"📧 {st.session_state.user_email}")

    if not premium and not is_admin:
        st.warning("🔒 Free Plan")
        if st.button("⚡ Upgrade — $24/mo"):
            st.info("Contact admin or pay via Whop/Gumroad.")
    elif premium:
        st.success("✅ Premium Active")

    if st.button("🚪 Logout"):
        for k in ["logged_in","user_email","user_tier","is_admin"]:
            st.session_state[k] = DEFAULTS.get(k, "")
        st.session_state.logged_in = False
        st.rerun()

    st.divider()

    pages = ["📊 Scanner","🏆 Trade of the Day","🔬 Deep Analysis",
             "🗞️ News Analysis","🤖 AI Strategy Builder",
             "🔔 Notifications","📓 Trade Journal","📈 Performance",
             "💰 Risk Calculator","⚙️ Settings","💎 Pricing"]
    if is_admin:
        pages.insert(0,"👑 Admin Panel")

    page = st.radio("Navigate", pages)

# ════════════════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ════════════════════════════════════════════════════════════
if "Admin" in page:
    st.title("👑 Admin Panel")
    st.success(f"Logged in as Admin: {st.session_state.user_email}")
    st.divider()

    # Stats
    all_users = get_all_users()
    premium_users = [u for u in all_users if u.get("tier")=="premium"]
    free_users    = [u for u in all_users if u.get("tier")=="free"]

    c1,c2,c3 = st.columns(3)
    c1.metric("👥 Total Users",   len(all_users))
    c2.metric("⚡ Premium Users", len(premium_users))
    c3.metric("🆓 Free Users",    len(free_users))

    st.divider()
    st.subheader("👥 All Users")
    if all_users:
        df_users = pd.DataFrame(all_users)[["email","tier","is_active","created_at"]]
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("No users yet.")

    st.divider()
    st.subheader("⚡ Upgrade User to Premium")
    ug_email = st.text_input("User email to upgrade")
    col1,col2 = st.columns(2)
    if col1.button("⬆️ Set Premium"):
        if update_user_tier(ug_email,"premium"):
            st.success(f"✅ {ug_email} upgraded to Premium!")
        else:
            st.error("❌ Failed. Check email.")
    if col2.button("⬇️ Set Free"):
        if update_user_tier(ug_email,"free"):
            st.success(f"✅ {ug_email} moved to Free.")
        else:
            st.error("❌ Failed.")

    st.divider()
    st.subheader("➕ Create New User")
    c1,c2,c3 = st.columns(3)
    new_email = c1.text_input("Email")
    new_pass  = c2.text_input("Password", type="password")
    new_tier  = c3.selectbox("Tier", ["free","premium"])
    if st.button("Create User"):
        if create_user(new_email, new_pass, new_tier):
            st.success(f"✅ User {new_email} created as {new_tier}!")
        else:
            st.error("❌ Failed. Email may already exist.")

    st.divider()
    st.subheader("🗑️ Delete User")
    del_email = st.text_input("Email to delete")
    if st.button("Delete User", type="primary"):
        if delete_user(del_email):
            st.success(f"✅ {del_email} deleted.")
        else:
            st.error("❌ Failed.")

# ════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ════════════════════════════════════════════════════════════
elif "Scanner" in page:
    st.title("📊 Market Scanner")
    if not premium:
        st.warning("🔒 Free plan: 5 assets. Upgrade for all 10.")

    results=[]; prog=st.progress(0); items=list(pairs.items())
    for i,(name,sym) in enumerate(items):
        strats,conf,sig=run_all_strategies(sym)
        buys=sum(1 for s,_ in strats.values() if s=="BUY")
        sells=sum(1 for s,_ in strats.values() if s=="SELL")
        results.append({"Asset":name,"Signal":sig,
            "Confidence":f"{conf}%" if premium else "🔒",
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
    st.dataframe(scanner,use_container_width=True)

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
            if sig!="WAIT" and conf>best["conf"]:
                best={"conf":conf,"sig":sig,"name":name,"sym":sym,"strats":strats}

    c1,c2,c3=st.columns(3)
    c1.metric("🏆 Asset",best["name"]); c2.metric("📡 Signal",best["sig"]); c3.metric("🎯 Confidence",f"{best['conf']}%")
    st.progress(best["conf"]/100)
    if "BUY"  in best["sig"]: st.success(f"🚀 {best['name']} — {best['sig']} at {best['conf']}%")
    elif "SELL" in best["sig"]: st.error(f"📉 {best['name']} — {best['sig']} at {best['conf']}%")

    entry,sl,tp1,tp2,tp3,atr=get_trade_setup(best["sym"],best["sig"])
    if entry:
        st.divider()
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        col1,col2=st.columns(2)
        if col1.button("🔔 Telegram Alert"):
            ok=notify_trade(best["name"],best["sig"],best["conf"],entry,sl,tp1,tp2,tp3)
            st.success("✅ Sent!") if ok else st.error("❌ Check Notifications.")
        if col2.button("➕ Add to Journal"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),
                "Asset":best["name"],"Signal":best["sig"],"Entry":entry,
                "SL":sl,"TP1":tp1,"Confidence":best["conf"],"Result":"Open"})
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
        strats,conf,sig=run_all_strategies(sym)
    c1,c2,c3=st.columns(3)
    c1.metric("Signal",sig); c2.metric("Confidence",f"{conf}%"); c3.metric("Strategies","8")
    st.progress(conf/100); st.divider()
    for name,(s,reason) in strats.items():
        color="#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
        icon="🟢" if s=="BUY" else "🔴" if s=="SELL" else "🟡"
        st.markdown(f"""<div style='background:#161b22;border-radius:10px;padding:12px;
          margin-bottom:8px;border-left:4px solid {color}'>
          <b>{icon} {name}</b> <span style='background:{color};color:#fff;padding:2px 8px;
          border-radius:12px;font-size:12px'>{s}</span><br>
          <small style='color:#8b949e'>{reason}</small></div>""",unsafe_allow_html=True)
    buys=sum(1 for s,_ in strats.values() if s=="BUY"); sells=sum(1 for s,_ in strats.values() if s=="SELL")
    c1,c2,c3=st.columns(3)
    c1.metric("🟢 Buys",buys); c2.metric("🔴 Sells",sells); c3.metric("🟡 Neutral",8-buys-sells)
    entry,sl,tp1,tp2,tp3,_=get_trade_setup(sym,sig)
    if entry and sig!="WAIT":
        st.divider()
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Entry",f"{entry:.5f}"); c2.metric("SL",f"{sl:.5f}")
        c3.metric("TP1",f"{tp1:.5f}"); c4.metric("TP2",f"{tp2:.5f}"); c5.metric("TP3",f"{tp3:.5f}")
        if conf>=75: st.success(f"✅ HIGH confidence — {conf}%")
        elif conf>=60: st.warning(f"⚠️ MODERATE — {conf}%")
        else: st.error(f"🚨 LOW — {conf}%")
        if st.button("🔔 Telegram Alert"):
            ok=notify_trade(selected,sig,conf,entry,sl,tp1,tp2,tp3)
            st.success("✅ Sent!") if ok else st.error("❌ Check Notifications.")
    st.divider()
    show_price_chart(sym,selected,sig,entry,sl,tp1,tp2)

# ════════════════════════════════════════════════════════════
# PAGE: NEWS
# ════════════════════════════════════════════════════════════
elif "News" in page:
    st.title("🗞️ News Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.spinner("Fetching calendar..."): news_df=fetch_forex_news()
    st.subheader("📅 Economic Calendar")
    st.dataframe(news_df,use_container_width=True)
    st.divider()
    selected=st.selectbox("Asset to analyse",list(ALL_PAIRS.keys()))
    if st.button("🤖 AI News Analysis"):
        with st.spinner("Analysing..."):
            analysis=call_ai(f"You are a forex analyst. Analyse how this week's news affects {selected}:\n{news_df.to_string()}\nBe concise, use bullet points.")
        st.markdown(f"<div class='news-card'>{analysis.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)
    high=news_df[news_df["Impact"]=="High"] if "Impact" in news_df.columns else pd.DataFrame()
    if not high.empty:
        st.subheader("⚠️ High Impact Events")
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
        fav_pairs =st.multiselect("Pairs",list(ALL_PAIRS.keys()),default=["EUR/USD","Gold (XAU/USD)"])
    with col2:
        session   =st.selectbox("Session",["London","New York","Asian","All"])
        experience=st.selectbox("Experience",["Beginner","Intermediate","Advanced"])
        custom    =st.text_area("Extra requirements",placeholder="e.g. only breakouts, trend following...")
    if st.button("🚀 Build Strategy"):
        prompt=f"""You are a professional forex strategy builder.
Build a complete {style} strategy for {', '.join(fav_pairs)}.
Trader profile: {risk_level} risk, {experience} level, trades {session} session.
Extra: {custom}
Include: 1) Entry rules 2) Stop loss 3) TP1/TP2/TP3 4) Timeframes 5) Risk management 6) What to avoid.
Be specific and practical."""
        with st.spinner("Building..."):
            strategy=call_ai(prompt)
            st.session_state.ai_strategy=strategy
    if st.session_state.ai_strategy:
        st.divider()
        st.subheader("📋 Your Strategy")
        st.markdown(f"<div class='strategy-card'>{st.session_state.ai_strategy.replace(chr(10),'<br>')}</div>",unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: NOTIFICATIONS
# ════════════════════════════════════════════════════════════
elif "Notifications" in page:
    st.title("🔔 Telegram Notifications")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("📖 Setup Guide"):
        st.markdown("""
1. Search `@BotFather` on Telegram → `/newbot` → copy **Bot Token**
2. Search `@userinfobot` → send any message → copy **Chat ID**
3. Paste below and test!
        """)
    token  =st.text_input("Bot Token",  value=st.session_state.telegram_token,  type="password")
    chat_id=st.text_input("Chat ID",    value=st.session_state.telegram_chat_id)
    if st.button("💾 Save"):
        st.session_state.telegram_token=token; st.session_state.telegram_chat_id=chat_id; st.success("✅ Saved!")
    if st.button("🧪 Test"):
        ok=send_telegram(token,chat_id,"✅ *Sparro FX AI* — Telegram connected! 🚀")
        st.success("✅ Check Telegram!") if ok else st.error("❌ Failed — check token and chat ID.")
    threshold=st.slider("Min confidence to alert",60,95,st.session_state.notification_threshold)
    st.session_state.notification_threshold=threshold

# ════════════════════════════════════════════════════════════
# PAGE: JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()
    with st.expander("➕ Log Trade"):
        c1,c2,c3=st.columns(3)
        j_asset=c1.selectbox("Asset",list(ALL_PAIRS.keys())); j_sig=c2.selectbox("Signal",["STRONG BUY","BUY","SELL","STRONG SELL"]); j_result=c3.selectbox("Result",["Open","Win","Loss","Breakeven"])
        c4,c5=st.columns(2); j_entry=c4.number_input("Entry",format="%.5f"); j_notes=c5.text_input("Notes")
        if st.button("Save"):
            st.session_state.trade_journal.append({"Date":str(datetime.date.today()),"Asset":j_asset,
                "Signal":j_sig,"Entry":j_entry,"Result":j_result,"Notes":j_notes}); st.success("✅ Saved!")
    if st.session_state.trade_journal:
        df=pd.DataFrame(st.session_state.trade_journal); st.dataframe(df,use_container_width=True)
        wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); total=wins+loss
        wr=round(wins/total*100,1) if total>0 else 0
        c1,c2,c3=st.columns(3); c1.metric("Total",len(df)); c2.metric("Win Rate",f"{wr}%"); c3.metric("Open",len(df[df["Result"]=="Open"]))
    else: st.info("No trades yet.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.title("📈 Performance")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal: st.info("Log trades to see stats."); st.stop()
    df=pd.DataFrame(st.session_state.trade_journal)
    wins=len(df[df["Result"]=="Win"]); loss=len(df[df["Result"]=="Loss"]); total=wins+loss
    wr=round(wins/total*100,1) if total>0 else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Trades",total); c2.metric("Wins",wins); c3.metric("Losses",loss); c4.metric("Win Rate",f"{wr}%")

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
    if risk_pct<=2: st.success("✅ Conservative")
    elif risk_pct<=5: st.warning("⚠️ Moderate")
    else: st.error("🚨 High risk")

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

# ════════════════════════════════════════════════════════════
# PAGE: PRICING
# ════════════════════════════════════════════════════════════
elif "Pricing" in page:
    st.title("💎 Upgrade to Premium")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'><h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        ✅ 5 assets<br><br>✅ Basic signals<br><br>
        ❌ Full strategy engine<br><br>❌ Price charts<br><br>
        ❌ News & AI Analysis<br><br>❌ Telegram alerts<br><br>
        ❌ Trade Journal</div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'><h3>⚡ Premium</h3><h2>$24/mo</h2><hr>
        ✅ All 10 assets<br><br>✅ 8-strategy engine<br><br>
        ✅ Price charts with Entry/SL/TP<br><br>✅ News Analysis + AI<br><br>
        ✅ AI Strategy Builder<br><br>✅ Telegram alerts<br><br>
        ✅ Trade Journal + Performance</div>""",unsafe_allow_html=True)
    st.divider()
    st.markdown("""
    **Pay & get access:**
    - Pay on **[Whop](https://whop.com)** or **[Gumroad](https://gumroad.com)**
    - Email your receipt to the admin
    - Admin upgrades your account in the Admin Panel
    - Login again and Premium is unlocked ✅
    """)
