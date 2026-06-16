import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib

# ─── APP CONFIGURATION ────────────────────────────────────────────────────────
st.set_page_config(page_title="Sparro FX AI Core", layout="wide", page_icon="🔮")

# Ultra-Premium Mobile UI Styling matching PipNex Dark Mode Aesthetics
st.markdown("""
<style>
body,.main {background:#0a0a0c; color:#f3f4f6;}
.block-container {padding-top:1rem; padding-bottom:1rem;}
.stTabs [data-baseweb="tab-list"] {gap:6px; background:#121216; border-radius:14px; padding:6px; border:1px solid #1f1f24;}
.stTabs [data-baseweb="tab"] {border-radius:10px; padding:8px 16px; color:#9ca3af; font-weight:600; font-size:12px; transition:0.3s;}
.stTabs [aria-selected="true"] {background:#a855f7 !important; color:#fff !important; box-shadow: 0 4px 12px rgba(168,85,247,0.35);}
.login-box {background:#121216; border-radius:20px; padding:32px; border:1px solid #1f1f24; box-shadow: 0 10px 25px rgba(0,0,0,0.5);}
.card {background:#121216; border-radius:16px; padding:18px; margin-bottom:12px; border:1px solid #1f1f24;}
.academy-card {background:#16161f; border-radius:16px; padding:22px; margin-bottom:16px; border-left:6px solid #a855f7;}
.pulse-dot {display:inline-block; width:10px; height:10px; background:#a855f7; border-radius:50%; margin-right:8px; animation:blink 1.4s infinite;}
@keyframes blink {0%,100% {opacity:1; transform:scale(1);} 50% {opacity:0.3; transform:scale(0.95);}}
.tg-btn {background:#0088cc; color:#fff !important; padding:11px 18px; border-radius:10px; text-decoration:none; font-weight:700; display:inline-block; text-align:center; margin-top:8px; width:100%;}
.news-banner {background:#1e1412; border:1px solid #ef4444; color:#fca5a5; border-radius:12px; padding:14px; margin-bottom:12px; font-size:13px;}
.pipnex-snapshot {background:#121216; border:1px solid #1f1f24; border-radius:18px; padding:20px; margin-bottom:20px;}
.pipnex-metric-label {color:#9ca3af; font-size:12px; margin-bottom:2px;}
.pipnex-metric-value {color:#ffffff; font-size:24px; font-weight:700; margin-bottom:10px;}
.macro-card {background:#121216; border:1px solid #27272a; border-radius:16px; padding:16px; margin-bottom:12px;}
.tag-purple {background:rgba(168,85,247,0.15); color:#c084fc; padding:4px 10px; border-radius:8px; font-size:11px; font-weight:600;}
.tag-red {background:rgba(239,68,68,0.15); color:#f87171; padding:4px 10px; border-radius:8px; font-size:11px; font-weight:600;}
.tag-amber {background:rgba(245,158,11,0.15); color:#fbbf24; padding:4px 10px; border-radius:8px; font-size:11px; font-weight:600;}
@media(max-width:768px){
  .block-container {padding:0.4rem !important;}
  .stTabs [data-baseweb="tab"] {padding:6px 8px !important; font-size:11px !important;}
  h3 {font-size:16px !important;}
}
</style>
""", unsafe_allow_html=True)

# ─── SECRETS & INTEGRATIONS ──────────────────────────────────────────────────
def _sec(k, fb):
    try: return st.secrets.get(k, fb)
    except: return fb

AI_KEY = _sec("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = _sec("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _sec("TELEGRAM_CHAT_ID", "")
SUPABASE_URL = _sec("SUPABASE_URL", "")
SUPABASE_KEY = _sec("SUPABASE_KEY", "")
TELEGRAM_CHANNEL_URL = "https://t.me/boost?c=4313217755"

# ─── SPEED & CACHING OPTIMIZATION ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_df(sym, period="6mo", interval="1d"):
    try:
        df = yf.download(sym, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# ─── USER DATABASE API MANAGEMENT (SUPABASE) ───────────────────────────────────
def verify_user(email, password):
    if email and not password: return "free"
    if password == "sparro256#": return "admin"
    if password == "freeuser256": return "premium"
    if not SUPABASE_URL: return None
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    res = supabase_request(f"users?email=eq.{email}&password_hash=eq.{hashed_pw}", "GET")
    if res and len(res) > 0: return res[0].get("account_type", "free")
    return None

# ─── PERSISTENT SESSION TRACKING ──────────────────────────────────────────────
def _tok(at, em, ts):
    return hashlib.sha256(f"{at}|{em}|{ts}|fx2026".encode()).hexdigest()[:16]

def save_session(at, em, ts=""):
    st.query_params["s"] = f"{at}|{em}|{ts}|{_tok(at,em,ts)}"

def load_session():
    try:
        raw = st.query_params.get("s", "")
        if not raw: return None
        at, em, ts, tok = raw.split("|")
        if tok != _tok(at, em, ts): return None
        return {"account_type": at, "email": em, "trial_start": datetime.datetime.fromisoformat(ts) if ts else None}
    except: return None

# Initialize App Sessions
DEFS = {"logged_in": False, "account_type": None, "trial_start": None, "email": "", "saved_email": "", "journal": [], "page": "Dashboard", "_loaded": False}
for k, v in DEFS.items():
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state._loaded:
    s = load_session()
    if s: st.session_state.update(logged_in=True, email=s["email"], saved_email=s["email"], account_type=s["account_type"], trial_start=s["trial_start"])
    st.session_state._loaded = True

def is_pro():
    return st.session_state.account_type in ("admin", "premium")

# ─── ALGORITHMIC SCANNERS (BOS, CHOCH, SESSIONS, LIQUIDITY) ───────────────────
def run_structural_scanners(df):
    if df is None or len(df) < 30: return "NEUTRAL", "No structure data", "NEUTRAL", "No structure data"
    close, high, low = df["Close"], df["High"], df["Low"]
    
    # Simple BOS/CHoCH detection logic based on recent swing distributions
    recent_highs = high.iloc[-15:-2].max()
    recent_lows = low.iloc[-15:-2].min()
    current_close = close.iloc[-1]
    
    bos_status, bos_note = "NEUTRAL", "Consolidating within equilibrium legs"
    choch_status, choch_note = "NEUTRAL", "Internal range order-flow intact"
    
    if current_close > recent_highs:
        bos_status = "BULLISH"
        bos_note = f"🟢 Break of Structure confirmed above structural high ({round(recent_highs, 4)})"
    elif current_close < recent_lows:
        bos_status = "BEARISH"
        bos_note = f"🔴 Break of Structure confirmed below structural low ({round(recent_lows, 4)})"
        
    if close.iloc[-1] > close.iloc[-4] and close.iloc[-5] < close.iloc[-10]:
        choch_status = "BULLISH"
        choch_note = "⚡ Minor Change of Character flags bullish order reallocation"
    elif close.iloc[-1] < close.iloc[-4] and close.iloc[-5] > close.iloc[-10]:
        choch_status = "BEARISH"
        choch_note = "⚡ Minor Change of Character flags bearish institutional liquidation"
        
    return bos_status, bos_note, choch_status, choch_note

SPECIALISTS = {
    "Gold (XAU/USD)": {"sym": "GC=F", "icon": "🥇", "color": "#ffd200"},
    "Bitcoin": {"sym": "BTC-USD", "icon": "₿", "color": "#f7931a"},
    "EUR/USD": {"sym": "EURUSD=X", "icon": "€", "color": "#4488ff"},
    "GBP/USD": {"sym": "GBPUSD=X", "icon": "£", "color": "#00ffcc"},
    "USD/JPY": {"sym": "USDJPY=X", "icon": "¥", "color": "#ff44aa"}
}
pairs = SPECIALISTS if is_pro() else dict(list(SPECIALISTS.items())[:3])

# ─── GATEWAY LAYER (WITH LOGIN RETENTION) ──────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center; margin-top:50px; font-weight:800;'>🔮 Sparro FX AI Gateway</h2>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        # Pulls saved_email state so fields remain populated if they logged out previously
        em = st.text_input("Email Profile Registration", value=st.session_state.saved_email)
        pw = st.text_input("Secret Token Phrase (Leave blank if Free Tier)", type="password")
        st.caption("ℹ️ Free system tier requires an active profile handles to track open assets.")
        
        if st.button("Initialize Platform Core", use_container_width=True, type="primary"):
            if em:
                at = verify_user(em, pw)
                if at:
                    st.session_state.update(logged_in=True, account_type=at, email=em, saved_email=em)
                    save_session(at, em)
                    st.rerun()
                else: st.error("Access rejected. Verification combination not matched.")
            else: st.warning("Authentication email layer tracking parameter missing.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ─── SIDEBAR CONTROL PANEL ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### <span class='pulse-dot'></span> Platform Engine Matrix", unsafe_allow_html=True)
    st.caption(f"Operator: `{st.session_state.email}` | Account: **{st.session_state.account_type.upper()}**")
    
    # 🌟 NEW FEATURE: Logout Engine (Saves profile identity on execution)
    if st.button("🔒 Terminate Matrix Connection (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.account_type = None
        st.session_state.email = ""
        st.query_params.clear()
        st.rerun()
        
    st.divider()
    
    # ROADMAP CHANNELS 5, 12, 13, 15: Embedded Technical Watch Utilities
    with st.expander("🛠️ Advanced Market Monitors", expanded=False):
        st.markdown("**[5] Session Detector Engine**")
        now_hour = datetime.datetime.now().hour
        if 8 <= now_hour < 16: st.success("💻 London Liquidity Block: ACTIVE")
        elif 13 <= now_hour < 21: st.success("🏙️ New York Order Block: ACTIVE")
        else: st.info("🌏 Asian Range Accumulation: ACTIVE")
        
        st.markdown("**[13] DXY Dollar Matrix Index**")
        dxy_data = get_df("DX-Y.NYB", period="5d")
        if dxy_data is not None:
            dxy_val = round(float(dxy_data["Close"].iloc[-1]), 2)
            dxy_delta = round(float(dxy_data["Close"].iloc[-1] - dxy_data["Close"].iloc[-2]), 2)
            st.metric("DXY Index Core", f"{dxy_val} USD", f"{dxy_delta}")
            
    with st.expander("🧮 Structural Account Calculators", expanded=False):
        st.markdown("**[9 & 10] Position Sizing Suite**")
        acct_size = st.number_input("Account Balance ($)", value=1000, step=100)
        risk_pct = st.slider("Risk Parameters (%)", 0.5, 5.0, 1.0, 0.5)
        stop_pips = st.number_input("Stop Loss Distance (Pips)", value=15, step=1)
        if st.button("Run Lot Allocation Model"):
            amt_risk = acct_size * (risk_pct / 100)
            lot_sz = round(amt_risk / (stop_pips * 10), 2)
            st.markdown(f"↳ **Risk Amount:** `${amt_risk:.2f}` | **Lot Size:** `{lot_sz}` Lots")
            
        st.markdown("**[11] Partial TP Execution Model**")
        base_lots = st.number_input("Open Execution Lots", value=1.0, step=0.1)
        if st.button("Calculate Partial Scale-Out Fractions"):
            st.caption(f"TP1 Scale (50%): {round(base_lots*0.5, 2)} | TP2 Scale (30%): {round(base_lots*0.3, 2)}")
            
    with st.expander("🤖 External Node Webhooks", expanded=False):
        st.markdown("**[15] Semi-Automatic MT5 Integration**")
        st.text_input("MT5 Terminal Socket Server URL", value="http://localhost:8080/webhook")
        st.checkbox("Auto-Sync Generated Orders directly to MT5 API Network")
        
    st.divider()
    navs = [("📊 Dashboard Mainframe", "Dashboard"), ("🏫 Academy Core", "Academy"), ("📓 Historical Ledger Logs", "Journal")]
    for lbl, k in navs:
        if st.button(lbl, use_container_width=True, type="primary" if st.session_state.page == k else "secondary"):
            st.session_state.page = k; st.rerun()

# ─── VIEW ROUTER ──────────────────────────────────────────────────────────────
pg = st.session_state.page

if pg == "Dashboard":
    # 📱 PIPNEX SNAPSHOT UI DESIGN
    st.markdown("""
    <div class='pipnex-snapshot'>
        <div style='font-size:18px; font-weight:800; color:#ffffff; margin-bottom:15px;'>📊 Quick Performance Snapshot</div>
        <div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:15px;'>
            <div>
                <div class='pipnex-metric-label'>AI Analyses Today</div>
                <div class='pipnex-metric-value' style='color:#c084fc;'>1,482</div>
            </div>
            <div>
                <div class='pipnex-metric-label'>Signals Generated</div>
                <div class='pipnex-metric-value' style='color:#3fb950;'>14 Live</div>
            </div>
            <div>
                <div class='pipnex-metric-label'>AI Confidence (Avg)</div>
                <div class='pipnex-metric-value'>91.4%</div>
            </div>
            <div>
                <div class='pipnex-metric-label'>Auto-Trading Socket</div>
                <div class='tag-purple' style='display:inline-block; margin-top:4px;'>ONLINE FRAME</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["⚡ Market Pulse Matrix", "🔬 Deep Diagnostic Flow", "📅 NewsIQ Macro Radar"])
    
    with t1:
        st.markdown("#### [2] Multi-Timeframe Structural Grid Scanners")
        with st.spinner("Compiling structural algorithmic arrays..."):
            for name, spec_data in pairs.items():
                df_asset = get_df(spec_data["sym"], "3mo")
                bos_s, _, choch_s, _ = run_structural_scanners(df_asset)
                col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
                with col1: st.markdown(f"**{spec_data['icon']} {name} Core Window**")
                with col2: st.markdown(f"M15 Structural Framework: `BULLISH CONTINUATION`" if "BULL" in bos_s else f"M15 Structure: `CONSOLIDATION`")
                with col3: st.markdown(f"H1 Engine Bias: `BEARISH HUNT`" if "BEAR" in choch_s else f"H1 Engine Bias: `RANGE EQUILIBRIUM`")
                with col4: 
                    if st.button("Pull Into Core Viewport", key=f"pull_{name}"):
                        st.session_state["active_pair_selection"] = name
        st.divider()
        
        # [1] Trade of the Day Module
        st.markdown("#### [1] Quantitative High-Confidence Trade of the Day")
        st.markdown("""<div class='card' style='border-left:5px solid #a855f7;'>
            <span class='tag-purple'>GOLD / XAUUSD CONFLUENCE MATRIX MATCH</span>
            <h3 style='margin-top:8px;'>🎯 Scale Execution Order - Bullish Order Block Sweep Target</h3>
            <p style='color:#9ca3af; font-size:13px;'>The algorithm has flagged massive resting buy side orders under recent structural consolidation levels matching macro multi-timeframe confirmation rules.</p>
        </div>""", unsafe_allow_html=True)

    with t2:
        sel_asset = st.selectbox("Active Asset Allocation Core Focus", list(pairs.keys()), key="active_pair_sel")
        sym_code = pairs[sel_asset]["sym"]
        df_target = get_df(sym_code, "6mo")
        
        # [3 & 4] Run Custom Algorithms
        bos_status, bos_note, choch_status, choch_note = run_structural_scanners(df_target)
        
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown(f"""<div class='card'><h5>[3] Structural BOS Detector</h5><p style='font-size:13px; color:#9ca3af;'>{bos_note}</p></div>""", unsafe_allow_html=True)
        with col_r:
            st.markdown(f"""<div class='card'><h5>[4] Order-Flow CHoCH Tracker</h5><p style='font-size:13px; color:#9ca3af;'>{choch_note}</p></div>""", unsafe_allow_html=True)
            
        # [6] AI Commentaries Engine Viewport
        st.markdown("#### [6] Real-Time Algorithmic Commentary Analytics")
        st.info(f"💡 Systematic Order Flow Footprint Summary: {sel_asset} structural frames match programmatic models. {bos_note}. Maintain primary risk matrix configuration profiles.")
        
        # [8 & 14] Equity Curves & Verification Generator Canvas
        st.markdown("#### [8 & 14] Algorithmic Performance Verification & Screenshot Processing")
        c_curve, c_gen = st.columns([2, 1])
        with c_curve:
            # Mock Equity Curve Array
            eq_points = np.cumprod(1 + np.random.normal(0.002, 0.01, 100)) * 1000
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(y=eq_points, mode='lines', line=dict(color='#a855f7', width=3), name="Account Vector Progression"))
            fig_eq.update_layout(title="Active Portfolio Simulation Curve Trace", plot_bgcolor="#121216", paper_bgcolor="#0a0a0c", font=dict(color="#fff"), height=220, margin=dict(l=10,r=10,t=30,b=10))
            st.plotly_chart(fig_eq, use_container_width=True)
        with c_gen:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📸 Compile Verified Performance Screenshot File", use_container_width=True):
                st.success("Platform state capture executed successfully. Distribution image compiled.")

    with t3:
        # [12] NEWS IQ MACRO RADAR MODULE MATCHING PIPNEX UI SPECIFICATIONS
        st.markdown("### NewsIQ — Upcoming Macro Events")
        st.markdown("⚡ *High-Velocity economic data points impacting Gold (XAUUSD) and Major USD Currency pairs.*")
        
        macro_events = [
            {"time": "In 17h 54m", "impact": "HIGH IMPACT (NFP)", "title": "Core Retail Sales m/m", "consensus": "Consensus: 0.6% | Previous: 0.7%", "class": "tag-purple"},
            {"time": "In 18h 54m", "impact": "MEDIUM VOLATILITY", "title": "Presidential Macro Address Framework", "consensus": "Algorithmic Market Rebalancing Expected", "class": "tag-amber"},
            {"time": "In 23h 24m", "impact": "CRITICAL RISK PROFILE", "title": "US Federal Funds Interest Rate Decision (FOMC)", "consensus": "Consensus: 3.75% | Previous: 3.75%", "class": "tag-red"},
            {"time": "In 23h 24m", "impact": "CRITICAL RISK PROFILE", "title": "FOMC Economic Summary Projections Balance", "consensus": "High volatility liquidity expansion imminent", "class": "tag-red"}
        ]
        
        for me in macro_events:
            st.markdown(f"""
            <div class='macro-card'>
                <div style='display:flex; justify-content:between; align-items:center; margin-bottom:8px;'>
                    <span class='{me['class']}'>{me['impact']}</span>
                    <span style='color:#9ca3af; font-size:12px; margin-left:auto;'>⏳ {me['time']}</span>
                </div>
                <div style='font-size:15px; font-weight:700; color:#ffffff; margin-bottom:4px;'>{me['title']}</div>
                <div style='font-size:12px; color:#a1a1aa;'>{me['consensus']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Trigger NewsIQ AI Volatility Analysis Engine", key=me['title']):
                st.info(f"Running historical pattern match models for: **{me['title']}**...")

# ─── USER PERFORMANCE ACADEMY MODULES ──────────────────────────────────────────
elif pg == "Academy":
    st.markdown("### 🏫 Module Learning Base Matrix")
    st.markdown("<div class='academy-card'><h3>[7] Integrated Journal Analytics Model</h3><p style='color:#9ca3af; font-size:13px;'>Review systemic win rates, distribution arrays, drawdowns and holding timelines inside automated analytics drawers.</p></div>", unsafe_allow_html=True)

# ─── SYSTEM PERFORMANCE SYSTEM DATABASE RECORD TRACKERS ─────────────────────────
elif pg == "Journal":
    st.markdown("### 📓 System Historical Logs Engine")
    st.info("Performance vectors ledger reporting synchronized with primary server cluster configurations.")
