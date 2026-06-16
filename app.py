import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib

# ─── APP CONFIGURATION ────────────────────────────────────────────────────────
st.set_page_config(page_title="Sparro FX AI Core", layout="wide", page_icon="🚀")

# Premium Mobile-Optimized Dark UI Styling
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
.academy-card{background:#1f2937;border-radius:12px;padding:20px;margin-bottom:15px;border-left:5px solid #7c3aed}
.pulse-dot{display:inline-block;width:9px;height:9px;background:#3fb950;border-radius:50%;margin-right:6px;animation:blink 1.2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.tg-btn{background:#0088cc;color:#fff !important;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;text-align:center;margin-top:10px}
.smc-badge{background:#7c3aed;color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.news-banner{background:#4d1b00;border:1px solid #ff5500;color:#ffaa66;border-radius:8px;padding:10px;margin-bottom:12px;font-size:13px}
@media(max-width:768px){
  .block-container{padding:0.5rem !important}
  .stTabs [data-baseweb="tab"]{padding:5px 7px !important;font-size:10px !important}
  h1{font-size:20px !important}
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

# ─── AUTOMATED TELEGRAM SIGNALS BROADCASTER ────────────────────────────────────
def broadcast_to_telegram(asset, signal, confidence, entry, sl, tp1):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    emoji = "🚀" if "BUY" in signal else "📉"
    text = (
        f"{emoji} **SPARRO FX AI PREMIUM SIGNAL** {emoji}\n\n"
        f"🎯 **Asset:** {asset}\n"
        f"🚦 **Action:** {signal}\n"
        f"🔥 **Matrix Match:** {confidence}%\n\n"
        f"🟢 **Entry Target:** {round(entry, 4)}\n"
        f"🔴 **Stop Loss:** {round(sl, 4)}\n"
        f"🔵 **Take Profit 1:** {round(tp1, 4)}\n\n"
        f"📱 Premium Dashboard Monitoring: {TELEGRAM_CHANNEL_URL}"
    )
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass

# ─── USER DATABASE API MANAGEMENT (SUPABASE) ───────────────────────────────────
def supabase_request(endpoint, method="GET", payload=None):
    if not SUPABASE_URL or not SUPABASE_KEY: return None
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    try:
        if method == "GET": r = requests.get(url, headers=headers, timeout=10)
        elif method == "POST": r = requests.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code in [200, 201]: return r.json()
    except: pass
    return None

def verify_user(email, password):
    if not SUPABASE_URL:
        if password == _sec("ADMIN_PASSWORD", "sparro_admin_2026"): return "admin"
        if password == _sec("PREMIUM_PASSWORD", "sparro_pro_2026"): return "premium"
        return None
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    res = supabase_request(f"users?email=eq.{email}&password_hash=eq.{hashed_pw}", "GET")
    if res and len(res) > 0:
        return res[0].get("account_type", "free")
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
DEFS = {"logged_in": False, "account_type": None, "trial_start": None, "email": "", "journal": [], "page": "Dashboard", "_loaded": False}
for k, v in DEFS.items():
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state._loaded:
    s = load_session()
    if s: st.session_state.update(logged_in=True, email=s["email"], account_type=s["account_type"], trial_start=s["trial_start"])
    st.session_state._loaded = True

TRIAL_H = 48
def hours_left():
    if not st.session_state.trial_start: return 0
    return max(0, TRIAL_H - int((datetime.datetime.now() - st.session_state.trial_start).total_seconds() / 3600))

def is_pro():
    at = st.session_state.account_type
    if at in ("admin", "premium"): return True
    if at == "trial" and hours_left() > 0: return True
    return False

# ─── HIGH-POWER SMC LOGIC & STRUCTURAL SCANNERS ───────────────────────────────
def s_liquidity_sweep(df):
    try:
        h, l, c = df["High"], df["Low"], df["Close"]
        cp = float(c.iloc[-1])
        lookback = df.iloc[-25:-1]
        highest_pool = float(lookback["High"].max())
        lowest_pool = float(lookback["Low"].min())
        if float(h.iloc[-1]) > highest_pool and cp < highest_pool:
            return "SELL", f"SMC Sweep Tracker: Buy-side Hunt Swept ({round(highest_pool,2)})"
        if float(l.iloc[-1]) < lowest_pool and cp > lowest_pool:
            return "BUY", f"SMC Sweep Tracker: Sell-side Hunt Swept ({round(lowest_pool,2)})"
        return "NEUTRAL", "Liquidity expanding within balanced internal ranges"
    except: return "NEUTRAL", "Sweep Analysis Error"

def s_ema(df):
    c = df["Close"]
    e20, e50, e200 = float(c.ewm(20).mean().iloc[-1]), float(c.ewm(50).mean().iloc[-1]), float(c.ewm(200).mean().iloc[-1])
    p = float(c.iloc[-1])
    if e20 > e50 > e200 and p > e20: return "BUY", "Bullish Structural Stack Alignment (20 > 50 > 200)"
    if e20 < e50 < e200 and p < e20: return "SELL", "Bearish Structural Stack Alignment (20 < 50 < 200)"
    return "NEUTRAL", "EMAs crossing inside consolidation range"

def s_adx(df):
    try:
        h, l, c = df["High"], df["Low"], df["Close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        up, dn = h.diff(), -l.diff()
        pdm = up.where((up > dn) & (up > 0), 0)
        ndm = dn.where((dn > up) & (dn > 0), 0)
        atr = tr.ewm(14, min_periods=14).mean()
        pdi = 100 * (pdm.ewm(14, min_periods=14).mean() / atr)
        ndi = 100 * (ndm.ewm(14, min_periods=14).mean() / atr)
        dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
        adx = float(dx.ewm(14, min_periods=14).mean().iloc[-1])
        if adx >= 25 and float(pdi.iloc[-1]) > float(ndi.iloc[-1]): return "BUY", f"ADX Momentum active ({round(adx,1)})"
        if adx >= 25 and float(ndi.iloc[-1]) > float(pdi.iloc[-1]): return "SELL", f"ADX Momentum active ({round(adx,1)})"
        return "NEUTRAL", "ADX accumulation"
    except: return "NEUTRAL", "ADX error"

def s_ob(df):
    try:
        o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
        cp = float(c.iloc[-1]); bobs, sobs = [], []
        for i in range(2, min(60, len(df) - 3)):
            idx = -i
            if c.iloc[idx] < o.iloc[idx] and c.iloc[idx + 1] > o.iloc[idx + 1] and c.iloc[idx + 2] > o.iloc[idx + 2] and c.iloc[idx + 2] > float(h.iloc[idx]):
                bobs.append((float(l.iloc[idx]), float(h.iloc[idx])))
            if c.iloc[idx] > o.iloc[idx] and c.iloc[idx + 1] < o.iloc[idx + 1] and c.iloc[idx + 2] < o.iloc[idx + 2] and c.iloc[idx + 2] < float(l.iloc[idx]):
                sobs.append((float(l.iloc[idx]), float(h.iloc[idx])))
        for lo, hi in bobs[:3]:
            if lo <= cp <= hi * 1.003: return "BUY", f"SMC Order Block ({round(lo,2)}-{round(hi,2)})"
        for lo, hi in sobs[:3]:
            if lo * 0.997 <= cp <= hi: return "SELL", f"SMC Order Block ({round(lo,2)}-{round(hi,2)})"
        return "NEUTRAL", "Institutional liquidity pools unmitigated"
    except: return "NEUTRAL", "SMC OB error"

def s_fvg(df):
    try:
        h, l, c = df["High"], df["Low"], df["Close"]
        cp = float(c.iloc[-1]); bfvg, sfvg = [], []
        for i in range(2, min(50, len(df) - 3)):
            idx = -i
            ph, nl = float(h.iloc[idx - 1]), float(l.iloc[idx + 1])
            if nl > ph: bfvg.append((ph, nl))
            pl, nh = float(l.iloc[idx - 1]), float(h.iloc[idx + 1])
            if pl > nh: sfvg.append((nh, pl))
        for lo, hi in bfvg[:5]:
            if lo <= cp <= hi: return "BUY", f"SMC FVG Imbalance ({round(lo,2)}-{round(hi,2)})"
        for lo, hi in sfvg[:5]:
            if lo <= cp <= hi: return "SELL", f"SMC FVG Imbalance ({round(lo,2)}-{round(hi,2)})"
        return "NEUTRAL", "Fair value price delivery stabilized"
    except: return "NEUTRAL", "SMC FVG error"

STRATS = {
    "SMC Sweep Tracker": (s_liquidity_sweep, "🏹", "Stop Hunt"),
    "EMA Trend Matrix": (s_ema, "📈", "Trend Structure"),
    "ADX Strength": (s_adx, "💪", "Momentum Filter"),
    "SMC Order Blocks": (s_ob, "🏦", "Mitigation Pools"),
    "SMC Fair Value Gap": (s_fvg, "🕳️", "Imbalance Fill")
}

SPECIALISTS = {
    "Gold (XAU/USD)": {"sym": "GC=F", "icon": "🥇", "badge": "gold-badge", "color": "#ffd200", "best": ["SMC Order Blocks", "SMC Sweep Tracker"], "period": "6mo"},
    "Bitcoin": {"sym": "BTC-USD", "icon": "₿", "badge": "btc-badge", "color": "#f7931a", "best": ["SMC Fair Value Gap", "SMC Sweep Tracker"], "period": "3mo"},
    "EUR/USD": {"sym": "EURUSD=X", "icon": "€", "badge": "eur-badge", "color": "#4488ff", "best": ["EMA Trend Matrix", "SMC Fair Value Gap"], "period": "6mo"}
}
ALL_PAIRS = {"Gold (XAU/USD)": "GC=F", "Bitcoin": "BTC-USD", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X"}
pairs = ALL_PAIRS if is_pro() else dict(list(ALL_PAIRS.items())[:3])

def run_strats(sym, period="6mo", asset_name=None):
    df = get_df(sym, period)
    if df is None or len(df) < 50: return {}, 0, "WAIT"
    spec = SPECIALISTS.get(asset_name, None)
    best_strats = spec["best"] if spec else []
    res = {}
    for name, (fn, _, _) in STRATS.items():
        try: res[name] = fn(df)
        except: res[name] = ("NEUTRAL", "Error")
    buy_score, sell_score, total_weight = 0, 0, 0
    for name, (sig, _) in res.items():
        weight = 2.0 if (name in best_strats) else 1.0
        total_weight += weight
        if sig == "BUY": buy_score += weight
        if sig == "SELL": sell_score += weight
    if buy_score > sell_score:
        conf = round(buy_score / total_weight * 100)
        sig = "STRONG BUY" if buy_score / total_weight >= 0.80 else "BUY" if buy_score / total_weight >= 0.65 else "WAIT"
    elif sell_score > buy_score:
        conf = round(sell_score / total_weight * 100)
        sig = "STRONG SELL" if sell_score / total_weight >= 0.80 else "SELL" if sell_score / total_weight >= 0.65 else "WAIT"
    else:
        conf, sig = 50, "WAIT"
    return res, conf, sig

def get_setup(sym, direction, asset_name=None):
    try:
        df = get_df(sym, "3mo"); c = df["Close"]; h = df["High"]; l = df["Low"]; p = float(c.iloc[-1])
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        risk = float(tr.rolling(14).mean().iloc[-1]) * (2.0 if asset_name == "Gold (XAU/USD)" else 1.5)
        if "BUY" in direction: return p, p - risk, p + risk
        else: return p, p + risk, p - risk
    except: return None, None, None

def get_news_events():
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=5)
        if r.status_code == 200:
            return [{"Currency": e.get("currency", ""), "Event": e.get("title", ""), "Impact": e.get("impact", "")} for e in r.json() if e.get("impact") == "High"]
    except: pass
    return [{"Currency": "USD", "Event": "Macro Interest Rate Projection Volatility", "Impact": "High"}]

def auto_ticket(asset, sig, conf, entry, sl, tp1, src="Auto Scanner"):
    id_num = len(st.session_state.journal)
    st.session_state.journal.append({
        "ID": id_num, "Date": str(datetime.date.today()), "Asset": asset, 
        "Signal": sig, "Entry": round(entry, 4), "SL": round(sl, 4), "TP1": round(tp1, 4), 
        "Confidence": conf, "Status": "Open", "Notes": "", "Source": src
    })
    if conf >= 80:
        broadcast_to_telegram(asset, sig, conf, entry, sl, tp1)

# ─── FRONT END VISUAL COMPONENTS ──────────────────────────────────────────────
def specialist_header(name):
    spec = SPECIALISTS.get(name)
    if not spec: return
    st.markdown(f"""<div style='background:#161b22;border:2px solid {spec["color"]};border-radius:12px;padding:14px;margin-bottom:14px'><div style='display:flex;align-items:center;gap:12px'><div style='font-size:32px'>{spec["icon"]}</div><div><div style='font-weight:900;font-size:18px;color:{spec["color"]}'>{name} Specialist Engine</div><div style='font-size:12px;color:#8b949e'>Engines optimized for structural algorithms: <b>{" · ".join(spec["best"])}</b></div></div></div></div>""", unsafe_allow_html=True)

def banner(sig, asset, conf):
    if "STRONG" in sig:
        col, bg = ("#3fb950", "linear-gradient(135deg,#0d5c2e,#1a7a3e)") if "BUY" in sig else ("#f85149", "linear-gradient(135deg,#5c0d0d,#7a1a1a)")
        st.markdown(f"""<div style='background:{bg};border:2px solid {col};border-radius:14px;padding:20px;text-align:center;margin-bottom:12px'><div style='font-size:24px;font-weight:900;color:{col}'>🔥 {sig} ENGINE CONFLUENCE RUNNING</div></div>""", unsafe_allow_html=True)
    elif sig in ("BUY", "SELL"):
        col, bg = ("#3fb950", "#0d2b1a") if "BUY" in sig else ("#f85149", "#2b0d0d")
        st.markdown(f"""<div style='background:{bg};border:2px solid {col};border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'><div style='font-size:18px;font-weight:800;color:{col}'>🟢 {sig} SETUP TRIGGERED ({conf}%)</div></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#161b22;border:1px solid #30363d;border-radius:14px;padding:14px;text-align:center;margin-bottom:12px'><div style='font-size:15px;color:#8b949e'>⏳ STAND ASIDE — Parameters Neutral</div></div>""", unsafe_allow_html=True)

def chart(sym, sig, entry, sl, tp1):
    df = get_df(sym, "3mo")
    if df is None: return
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Candles", increasing_line_color="#3fb950", decreasing_line_color="#f85149"))
    if entry and not np.isnan(entry):
        fig.add_hline(y=entry, line_color="#58a6ff", annotation_text="ENTRY")
        fig.add_hline(y=sl, line_color="#f85149", line_dash="dash", annotation_text="SL")
        fig.add_hline(y=tp1, line_color="#3fb950", line_dash="dash", annotation_text="TP1")
    fig.update_layout(plot_bgcolor="#0d1117", paper_bgcolor="#0d1117", font=dict(color="#e6edf3"), height=360, margin=dict(l=20,r=20,t=20,b=20), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ─── GATEWAY LAYER ────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;margin-top:50px'>🚀 Sparro FX AI Gateway</h2>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        em = st.text_input("Email Profile")
        pw = st.text_input("Secret Token Phrase", type="password")
        if st.button("Access Dashboard Core", use_container_width=True, type="primary"):
            at = verify_user(em, pw)
            if at:
                st.session_state.update(logged_in=True, account_type=at, email=em)
                save_session(at, em); st.rerun()
    st.stop()

# ─── NAVIGATION SIDEBAR ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h3 style='color:#00c6ff'>🚀 Sparro Engine</h3>", unsafe_allow_html=True)
    st.caption(f"Handle: {st.session_state.email} ({st.session_state.account_type.upper()})")
    st.markdown(f"<a href='{TELEGRAM_CHANNEL_URL}' class='tg-btn' target='_blank'>📱 Telegram Signal Link</a>", unsafe_allow_html=True)
    st.divider()
    navs = [("🏠 Scanner Core Matrix", "Dashboard"), ("🏫 Sparro SMC Academy", "Academy"), ("🎫 Open Ticket Dashboard", "Tickets"), ("📓 System History Logs", "Journal")]
    if st.session_state.account_type == "admin": navs.append(("🔐 Admin User Console", "Admin"))
    for lbl, k in navs:
        if st.button(lbl, use_container_width=True, type="primary" if st.session_state.page == k else "secondary"):
            st.session_state.page = k; st.rerun()

# ─── VIEW ROUTER ──────────────────────────────────────────────────────────────
pg = st.session_state.page

if pg == "Dashboard":
    st.markdown("### 🏠 Matrix Scanning Interface Core")
    t1, t2 = st.tabs(["📊 Scanner Feed", "🔬 Technical Analytics Window"])
    
    with t1:
        news_events = get_news_events()
        if news_events:
            with st.expander("🚨 HIGH IMPACT SYSTEM MACRO NEWS DETECTED", expanded=True):
                for ne in news_events[:3]:
                    st.markdown(f"<div class='news-banner'>⚠️ Institutional Volatility Spikes: <b>{ne['Currency']}</b> - {ne['Event']} ({ne['Impact']} Impact)</div>", unsafe_allow_html=True)
                    
        with st.spinner("Analyzing cross-confluences..."):
            hits = []
            for name, sym in pairs.items():
                res, conf, sig = run_strats(sym, asset_name=name)
                if sig != "WAIT":
                    entry, sl, tp1 = get_setup(sym, sig, asset_name=name)
                    if entry: hits.append({"name": name, "sym": sym, "sig": sig, "conf": conf, "entry": entry, "sl": sl, "tp1": tp1})
        if not hits:
            st.info("Continuous liquidity hunting scanning. Standard equilibrium bands stable.")
        for idx, h in enumerate(hits):
            col = "#3fb950" if "BUY" in h["sig"] else "#f85149"
            st.markdown(f"<div class='card' style='border-left:5px solid {col}'><h4>{h['name']} — {h['sig']} ({h['conf']}% Match)</h4><p>Target: {h['entry']} | SL: {h['sl']} | TP1: {h['tp1']}</p></div>", unsafe_allow_html=True)
            if st.button(f"Inject Ledger Token Target #{idx}", key=f"inj_{idx}"):
                auto_ticket(h['name'], h['sig'], h['conf'], h['entry'], h['sl'], h['tp1'])
                st.success("Position pushed to active open pipeline pipeline ledger.")

    with t2:
        sel = st.selectbox("Select Core Frame Index Asset", list(pairs.keys()))
        sym = pairs[sel]
        if sel in SPECIALISTS: specialist_header(sel)
        res, conf, sig = run_strats(sym, asset_name=sel)
        banner(sig, sel, conf)
        
        setup_vals = get_setup(sym, sig, asset_name=sel)
        entry_v, sl_v, tp1_v = (setup_vals[0], setup_vals[1], setup_vals[2]) if setup_vals[0] is not None else (None, None, None)
        chart(sym, sig, entry_v, sl_v, tp1_v)
        
        st.markdown("#### Internal Algorithmic Engine Breakdowns")
        for s_name, (sig_val, notes_val) in res.items():
            st.markdown(f"**{s_name}:** `{sig_val}` — *{notes_val}*")

# ─── ACADEMY WINDOW (NEW EDUCATION SECTION) ───────────────────────────────────
elif pg == "Academy":
    st.markdown("### 🏫 Sparro SMC Academy")
    st.markdown("*Mastering Institutional Order Flow & Liquidity Engineering on Mobile.*")
    st.divider()
    
    lesson = st.selectbox("Select Academy Module", [
        "1. Core Market Structure & Bias", 
        "2. Smart Money Order Blocks (OB)", 
        "3. Liquidity Pools & Stop Hunts"
    ])
    
    if lesson == "1. Core Market Structure & Bias":
        st.markdown("<div class='academy-card'><h3>Module 1: Market Structure & Framework Rules</h3>", unsafe_allow_html=True)
        st.markdown("""
        To scale a trading account, you must stop trading retail chart patterns (like trendlines and triangles) that algorithms easily manipulate. Markets exclusively move via **Market Structure**.
        
        #### 📈 The Two Core Market Phasing Rules:
        1. **Bullish Structure:** Price breaks past old swing highs, producing a sequence of **Higher Highs (HH)** and **Higher Lows (HL)**. 
           * *Trading Rule:* You **ONLY** hunt for buy signals when the market finishes a minor pullback down to a fresh Higher Low.
        2. **Bearish Structure:** Price punches down past old swing lows, producing a sequence of **Lower Lows (LL)** and **Lower Highs (LH)**.
           * *Trading Rule:* You **ONLY** hunt for short execution entries on a temporary relief rally up to a fresh Lower High.
        
        #### 🚨 The Break of Structure (BOS)
        A trend flip is officially confirmed when a candlestick body aggressively closes *outside* the previous valid structural swing high or low. When you see a change of character or BOS, immediately adjust your bias on your scanner tab.
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
    elif lesson == "2. Smart Money Order Blocks (OB)":
        st.markdown("<div class='academy-card'><h3>Module 2: Uncovering Institutional Order Blocks</h3>", unsafe_allow_html=True)
        st.markdown("""
        Central Banks and global institutions do not buy with simple market execution buttons—they trade thousands of lots using hidden limit orders that leave visible tracks on your chart. 
        
        An **Order Block (OB)** is the exact candle footprint left behind right before institutional capital forcefully pushed price in the opposite direction.
        
        #### 🔍 Spotting Valid Blocks on Mobile:
        * **Bullish Order Block:** Locate the *last down-close (bearish) candle* right before an aggressive, explosive structural breakout to the upside.
        * **Bearish Order Block:** Locate the *last up-close (bullish) candle* right before a heavy liquidation market collapse to the downside.
        
        #### 🎯 How to Execute:
        Never chase a runaway market. Wait patiently for price to drift back down into the previous Order Block zone. When price touches the footprint, institutions will inject their remaining open buy orders, resulting in a rapid bounce away from your entry zone.
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
    elif lesson == "3. Liquidity Pools & Stop Hunts":
        st.markdown("<div class='academy-card'><h3>Module 3: Liquidity Sweeps & Stop Hunting Strategy</h3>", unsafe_allow_html=True)
        st.markdown("""
        The market is fundamentally an auction engine that seeks liquidity to match massive institutional volumes. Retail traders are taught to put their stop-losses at identical, obvious technical areas. 
        
        Algorithms aggressively drive price straight into these clusters to absorb those resting orders before reversing back into the actual target direction.
        
        #### 🏦 Major Liquidity Horizons:
        * **Equal Highs (EQH / Double Tops):** Heavy buy-stop resting liquidity sits right above these clean resistance highs.
        * **Equal Lows (EQL / Double Bottoms):** Massive sell-stop clusters sit right underneath these technical supports.
        
        #### 🏹 The Stop Hunt Execution Model:
        When price violently pierces below Equal Lows, sweeps out all retail buy stop-losses, and *immediately snaps back inside the range*, the **SMC Sweep Tracker** indicator in your dashboard flags a buy trigger. You enter the trade immediately following the sweep candle close, placing a tight invalidation stop right below the newly established wick low.
        """)
        st.markdown("</div>", unsafe_allow_html=True)

# ─── TICKETS WINDOW ───────────────────────────────────────────────────────────
elif pg == "Tickets":
    st.markdown("### 🎫 Open Active Pipeline Ledger Management")
    open_t = [t for t in st.session_state.journal if t.get("Status") == "Open"]
    
    if not open_t:
        st.info("No tracking positions active in the live network matrix.")
    else:
        for t in open_t:
            st.markdown(f"""
            <div class='card' style='border:1px dashed #58a6ff'>
                <h4>🏷️ ID #{t['ID']} | {t['Asset']} — Structural {t['Signal']} Setup</h4>
                <p><b>Matrix Stats:</b> Entry Block: <code>{t['Entry']}</code> | SL Level: <code>{t['SL']}</code> | TP1 Zone: <code>{t['TP1']}</code></p>
                <p><i>Logged Tracking Engine Notes:</i> {t['Notes'] if t['Notes'] else 'No manual notes appended.'}</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.container():
                c1, c2, c3 = st.columns([1, 1.5, 0.8])
                with c1:
                    status_update = st.selectbox(
                        "Update Ledger Target", 
                        ["Open", "Hit TP1", "Hit SL", "Closed at BE (Breakeven)", "Manual Close Profit", "Manual Close Loss"], 
                        key=f"stat_{t['ID']}"
                    )
                with c2:
                    notes_update = st.text_input("Append Execution Notes", key=f"note_{t['ID']}")
                with c3:
                    if st.button("Commit Log Update", key=f"commit_{t['ID']}", use_container_width=True):
                        t["Status"] = status_update
                        t["Notes"] = notes_update
                        st.success(f"ID #{t['ID']} profile updated.")
                        st.rerun()
            st.divider()

# ─── DATABASE JOURNAL PERFORMANCE SYSTEM ──────────────────────────────────────
elif pg == "Journal":
    st.markdown("### 📓 System Historical Performance Ledger")
    if st.session_state.journal:
        st.dataframe(pd.DataFrame(st.session_state.journal), use_container_width=True)
    else: st.info("No historical logs recorded inside active tracking instances.")

# ─── HIDDEN USER CONTROL ADMIN DASHBOARD CONSOLE ──────────────────────────────
elif pg == "Admin" and st.session_state.account_type == "admin":
    st.markdown("### 🔐 Secure Database Administration User Matrix")
    st.metric("Total System Cloud Allocations Active", f"{len(st.session_state.journal)} Positions Logged")
    
    mock_users = [
        {"Email": "simon_vip@sparro.com", "Tier": "Premium Pro", "Authorized_Term": "Monthly Sub Active"},
        {"Email": "alpha_scalper@trade.ug", "Tier": "Premium Pro", "Authorized_Term": "Monthly Sub Active"},
        {"Email": "guest_9831@gmail.com", "Tier": "48hr Free Trial", "Authorized_Term": "Expires 12 Hours"}
    ]
    st.table(pd.DataFrame(mock_users))
