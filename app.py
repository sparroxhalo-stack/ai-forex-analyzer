import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib

# ─── APP CONFIGURATION ────────────────────────────────────────────────────────
st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")

# Mobile-Optimized Dark UI Styling
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

# ─── SPEED & CACHING OPTIMIZATION ──────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache market data for 5 minutes to prevent mobile lag
def get_df(sym, period="6mo", interval="1d"):
    try:
        df = yf.download(sym, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# ─── TELEGRAM SIGNALS BROADCASTER (MONETIZATION UPSELL) ───────────────────────
def broadcast_to_telegram(asset, signal, confidence, entry, sl, tp1):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    emoji = "🚀" if "BUY" in signal else "📉"
    text = (
        f"{emoji} **SPARRO FX AI SIGNAL** {emoji}\n\n"
        f"🎯 **Asset:** {asset}\n"
        f"🚦 **Action:** {signal}\n"
        f"🔥 **Confidence:** {confidence}%\n\n"
        f"🟢 **Entry Zone:** {round(entry, 4)}\n"
        f"🔴 **Stop Loss:** {round(sl, 4)}\n"
        f"🔵 **Take Profit 1:** {round(tp1, 4)}\n\n"
        f"📱 Check the dashboard for full multi-timeframe alignment analysis."
    )
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass

# ─── SUPABASE INTEGRATED AUTHENTICATION ────────────────────────────────────────
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
    # Fallback to standard admin check if Supabase secrets are empty
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

# Initialize Session States
DEFS = {"logged_in": False, "account_type": None, "trial_start": None, "email": "", "journal": [], "subscribers": [], "sig_history": [], "page": "Dashboard", "_loaded": False}
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

# ─── REFINED SCALPING & STRUCTURE STRATEGIES ──────────────────────────────────
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
        pv, nv = float(pdi.iloc[-1]), float(ndi.iloc[-1])
        if adx >= 25 and pv > nv: return "BUY", f"ADX Momentum active ({round(adx,1)}) — Expansion Upward"
        if adx >= 25 and nv > pv: return "SELL", f"ADX Momentum active ({round(adx,1)}) — Expansion Downward"
        return "NEUTRAL", f"ADX choppy ({round(adx,1)}) — Accumulation phase"
    except: return "NEUTRAL", "ADX error"

def s_rsi(df):
    try:
        c = df["Close"]; d = c.diff()
        g = d.where(d > 0, 0).rolling(14).mean()
        l = (-d.where(d < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (g / l)))
        rv = float(rsi.iloc[-1])
        prices, rsis = c.iloc[-20:].values, rsi.iloc[-20:].values
        ph = [i for i in range(1, len(prices) - 1) if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]]
        pl = [i for i in range(1, len(prices) - 1) if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]]
        if len(ph) >= 2 and prices[ph[-1]] > prices[ph[-2]] and rsis[ph[-1]] < rsis[ph[-2]]:
            return "SELL", f"RSI={round(rv,1)} — Structural Bearish Divergence (Reversal Engine Triggered)"
        if len(pl) >= 2 and prices[pl[-1]] < prices[pl[-2]] and rsis[pl[-1]] > rsis[pl[-2]]:
            return "BUY", f"RSI={round(rv,1)} — Structural Bullish Divergence (Reversal Engine Triggered)"
        if rv > 60: return "BUY", "Aggressive Buying pressure building"
        if rv < 40: return "SELL", "Aggressive Liquidations active"
        return "NEUTRAL", "Oscillator resting at Equilibrium"
    except: return "NEUTRAL", "RSI error"

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
            if lo <= cp <= hi * 1.003: return "BUY", f"SMC Order Block ({round(lo,2)}-{round(hi,2)}) — Institutional Mitigation Active"
        for lo, hi in sobs[:3]:
            if lo * 0.997 <= cp <= hi: return "SELL", f"SMC Order Block ({round(lo,2)}-{round(hi,2)}) — Institutional Mitigation Active"
        return "NEUTRAL", "Institutional liquidity pools unmitigated"
    except: return "NEUTRAL", "SMC OB error"

def s_fvg(df):
    # Specialized 50% Premium/Discount Equilibrium Strategy Update
    try:
        h, l, c = df["High"], df["Low"], df["Close"]
        cp = float(c.iloc[-1]); bfvg, sfvg = [], []
        for i in range(2, min(50, len(df) - 3)):
            idx = -i
            ph, nl = float(h.iloc[idx - 1]), float(l.iloc[idx + 1])
            if nl > ph: bfvg.append((ph, nl, ph + (nl - ph) * 0.5))  # Includes 50% discount equilibrium level
            pl, nh = float(l.iloc[idx - 1]), float(h.iloc[idx + 1])
            if pl > nh: sfvg.append((nh, pl, nh + (pl - nh) * 0.5))
        for lo, hi, eq in bfvg[:5]:
            if lo <= cp <= hi:
                lbl = "Discount Area Entry" if cp <= eq else "Premium Entry"
                return "BUY", f"SMC FVG Imbalance Active ({round(lo,2)}-{round(hi,2)}) — {lbl} at Equilibrium: {round(eq,2)}"
        for lo, hi, eq in sfvg[:5]:
            if lo <= cp <= hi:
                lbl = "Premium Area Entry" if cp >= eq else "Discount Entry"
                return "SELL", f"SMC FVG Imbalance Active ({round(lo,2)}-{round(hi,2)}) — {lbl} at Equilibrium: {round(eq,2)}"
        return "NEUTRAL", "Fair value price delivery stabilized"
    except: return "NEUTRAL", "SMC FVG error"

def s_sr(df):
    # Upgraded to scan daily major structural extreme boundaries
    try:
        h, l, c = df["High"], df["Low"], df["Close"]
        p = float(c.iloc[-1])
        res, sup = float(h.rolling(50).max().iloc[-1]), float(l.rolling(50).min().iloc[-1])
        zone = (res - sup) * 0.08
        if p >= res - zone: return "SELL", f"Testing Daily Macro Liquidity Resistance ({round(res,2)}) — Watch rejection wicks"
        if p <= sup + zone: return "BUY", f"Testing Daily Macro Liquidity Support ({round(sup,2)}) — Watch compression bounces"
        return "NEUTRAL", f"Price running inside intermediate range. Sup: {round(sup,2)} | Res: {round(res,2)}"
    except: return "NEUTRAL", "S/R error"

STRATS = {
    "EMA Trend": (s_ema, "📈", "Trend Structure"),
    "ADX Strength": (s_adx, "💪", "Momentum Filter"),
    "RSI + Divergence": (s_rsi, "⚡", "Reversal Oscillator"),
    "SMC Order Blocks": (s_ob, "🏦", "Mitigation Pools"),
    "SMC Fair Value Gap": (s_fvg, "🕳️", "Imbalance Fill"),
    "Support/Resistance": (s_sr, "🧱", "Macro Extremes")
}

# ─── STRATEGY SCORING ENGINE ──────────────────────────────────────────────────
SPECIALISTS = {
    "Gold (XAU/USD)": {"sym": "GC=F", "icon": "🥇", "badge": "gold-badge", "label": "GOLD", "color": "#ffd200", "best": ["SMC Order Blocks", "Support/Resistance", "EMA Trend"], "why": "Gold maps perfectly to physical liquidity pools and Daily high/low extremes.", "period": "6mo", "tf_best": "Daily + 4H"},
    "Bitcoin": {"sym": "BTC-USD", "icon": "₿", "badge": "btc-badge", "label": "BTC", "color": "#f7931a", "best": ["SMC Fair Value Gap", "RSI + Divergence", "Support/Resistance"], "why": "Bitcoin fills market imbalances cleanly and drives heavy divergence prints on exhaustion sweeps.", "period": "3mo", "tf_best": "4H + Daily"},
    "EUR/USD": {"sym": "EURUSD=X", "icon": "€", "badge": "eur-badge", "label": "EUR/USD", "color": "#4488ff", "best": ["EMA Trend", "ADX Strength", "SMC Fair Value Gap"], "why": "Extremely liquid trend follower; respects EMA stack alignments through London/NY overlaps.", "period": "6mo", "tf_best": "1H + 4H"}
}
ALL_PAIRS = {"Gold (XAU/USD)": "GC=F", "Bitcoin": "BTC-USD", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X", "NASDAQ": "^IXIC", "S&P 500": "^GSPC"}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:3])
pairs = ALL_PAIRS if is_pro() else FREE_PAIRS

def run_strats(sym, period="6mo", asset_name=None):
    df = get_df(sym, period)
    if df is None or len(df) < 50: return {}, 0, "ERROR"
    spec = SPECIALISTS.get(asset_name, None)
    best_strats = spec["best"] if spec else []
    res = {}
    for name, (fn, _, _) in STRATS.items():
        try: res[name] = fn(df)
        except: res[name] = ("NEUTRAL", "Calculation error")
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

def run_mtf(sym, asset_name=None):
    tfs = {}
    for label, period, interval in [("Daily", "6mo", "1d"), ("4H", "60d", "4h"), ("1H", "5d", "1h")]:
        df = get_df(sym, period, interval)
        if df is None or len(df) < 30: tfs[label] = ("WAIT", 0); continue
        res = {}
        spec = SPECIALISTS.get(asset_name, None)
        best_strats = spec["best"] if spec else []
        for name, (fn, _, __) in STRATS.items():
            try: res[name] = fn(df)
            except: res[name] = ("NEUTRAL", "Error")
        bs, ss, tw = 0, 0, 0
        for name, (sg, _) in res.items():
            w = 2.0 if name in best_strats else 1.0
            tw += w
            if sg == "BUY": bs += w
            if sg == "SELL": ss += w
        if bs > ss and bs / tw >= 0.65: tfs[label] = ("BUY", round(bs / tw * 100))
        elif ss > bs and ss / tw >= 0.65: tfs[label] = ("SELL", round(ss / tw * 100))
        else: tfs[label] = ("WAIT", 50)
    sigs = [s for s, _ in tfs.values() if s != "WAIT"]
    bc, sc = sum(1 for s in sigs if s == "BUY"), sum(1 for s in sigs if s == "SELL")
    if bc == 3: ms, mn = "STRONG BUY", "All 3 higher timeframes completely aligned ✅"
    elif bc == 2: ms, mn = "BUY", "2/3 timeframes structural agreement"
    elif sc == 3: ms, mn = "STRONG SELL", "All 3 higher timeframes completely aligned ✅"
    elif sc == 2: ms, mn = "SELL", "2/3 timeframes structural agreement"
    else: ms, mn = "WAIT", "Timeframe conflict — structure distribution messy"
    return tfs, ms, mn

def get_setup(sym, direction, asset_name=None):
    # Specialized contract sizing risk calculator adjustments
    try:
        df = get_df(sym, "3mo"); c = df["Close"]; h = df["High"]; l = df["Low"]; p = float(c.iloc[-1])
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        
        # Adjust risk padding for highly volatile gold wicks vs indices
        multiplier = 2.0 if asset_name == "Gold (XAU/USD)" else 1.5
        risk = atr * multiplier
        
        if "BUY" in direction: return p, p - risk, p + risk, p + risk * 2, p + risk * 3
        else: return p, p + risk, p - risk, p - risk * 2, p - risk * 3
    except: return None, None, None, None, None

def get_fibs(sym):
    try:
        df = get_df(sym, "3mo")
        hi, lo = float(df["High"].iloc[-20:].max()), float(df["Low"].iloc[-20:].min()); d = hi - lo
        return {"0.786": hi - d * 0.214, "0.618": hi - d * 0.382, "0.5": hi - d * 0.5, "0.382": hi - d * 0.618}
    except: return {}

def get_pivots(sym):
    try:
        df = get_df(sym, "5d"); prev = df.iloc[-2]
        hi, lo, cl = float(prev["High"]), float(prev["Low"]), float(prev["Close"])
        pp = (hi + lo + cl) / 3
        return {"R1": 2 * pp - lo, "PP": pp, "S1": 2 * pp - hi}
    except: return {}

def auto_ticket(asset, sig, conf, entry, sl, tp1, tp2, tp3, src="Auto"):
    today = str(datetime.date.today())
    dup = [t for t in st.session_state.journal if t.get("Asset") == asset and t.get("Date") == today and t.get("Signal") == sig]
    if dup: return False
    st.session_state.journal.append({"Date": today, "Time": datetime.datetime.now().strftime("%H:%M"), "Asset": asset, "Signal": sig, "Entry": round(entry, 5), "SL": round(sl, 5), "TP1": round(tp1, 5), "TP2": round(tp2, 5), "TP3": round(tp3, 5), "Confidence": conf, "Result": "Open", "Source": src})
    st.session_state.sig_history.append({"DateTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "Asset": asset, "Signal": sig, "Confidence": conf, "Entry": round(entry, 5), "Result": "Pending"})
    
    # Monetization broadcast engine trigger
    if conf >= 80:
        broadcast_to_telegram(asset, sig, conf, entry, sl, tp1)
    return True

# ─── AI DEEP GENERATIVE ENGINE ───────────────────────────────────────────────
def ai_call(prompt, max_tokens=500):
    if not AI_KEY: return "Enter dynamic ANTHROPIC_API_KEY in secrets to route system execution."
    try:
        # Corrected production Claude 3.5 Sonnet stable model API string identifier
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": AI_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-3-5-sonnet-20241022", "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}, timeout=25)
        if r.status_code == 200: return r.json()["content"][0]["text"]
        return f"AI execution routing down. Status: {r.status_code}"
    except Exception as e: return f"Routing Error: {e}"

def get_news():
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=8)
        if r.status_code == 200:
            return pd.DataFrame([{"Time": e.get("date", "")[:16].replace("T", " "), "Currency": e.get("currency", ""), "Event": e.get("title", ""), "Impact": e.get("impact", ""), "Forecast": e.get("forecast", "—"), "Previous": e.get("previous", "—")} for e in r.json()[:15]])
    except: pass
    return pd.DataFrame([{"Time": "Macro Wave Today", "Currency": "USD", "Event": "Core Capital Markets Injection", "Impact": "High", "Forecast": "Volatile", "Previous": "Stable"}])

# ─── FRONT END VISUALIZATION SUITE ────────────────────────────────────────────
def specialist_header(name):
    spec = SPECIALISTS.get(name)
    if not spec: return
    st.markdown(f"""<div style='background:linear-gradient(135deg,#161b22,#0d1117);border:2px solid {spec["color"]};border-radius:12px;padding:14px;margin-bottom:14px'><div style='display:flex;align-items:center;gap:12px'><div style='font-size:32px'>{spec["icon"]}</div><div><div style='font-weight:900;font-size:18px;color:{spec["color"]}'>{name} Specialist Structural Framework</div><div style='font-size:12px;color:#8b949e;margin-top:3px'>Core Engines: <b style='color:{spec["color"]}'>{" · ".join(spec["best"])}</b> &nbsp;|&nbsp; Target Window: <b>{spec["tf_best"]}</b></div><div style='font-size:12px;color:#8b949e;margin-top:3px'>{spec["why"]}</div></div></div></div>""", unsafe_allow_html=True)

def banner(sig, asset, conf):
    spec = SPECIALISTS.get(asset)
    spec_tag = f"&nbsp;<span class='{spec['badge']}'>{spec['icon']} {spec['label']} SPEC</span>" if spec else ""
    if "STRONG" in sig:
        col, bg = ("#3fb950", "linear-gradient(135deg,#0d5c2e,#1a7a3e)") if "BUY" in sig else ("#f85149", "linear-gradient(135deg,#5c0d0d,#7a1a1a)")
        st.markdown(f"""<div style='background:{bg};border:2px solid {col};border-radius:14px;padding:20px;text-align:center;margin-bottom:12px;box-shadow:0 0 20px {col}44'><div style='font-size:24px;font-weight:900;color:{col}'>🔥 {sig} RUNNING {spec_tag}</div><div style='font-size:14px;color:#e6edf3;margin-top:5px'>{asset} | Confluence Match: {conf}%</div></div>""", unsafe_allow_html=True)
    elif sig in ("BUY", "SELL"):
        col, bg = ("#3fb950", "#0d2b1a") if "BUY" in sig else ("#f85149", "#2b0d0d")
        st.markdown(f"""<div style='background:{bg};border:2px solid {col};border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'><div style='font-size:18px;font-weight:800;color:{col}'>🟢 {sig} SETUP DEPLOYED {spec_tag}</div><div style='font-size:13px;color:#e6edf3;margin-top:4px'>{asset} | Matrix Matching: {conf}%</div></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#161b22;border:1px solid #30363d;border-radius:14px;padding:14px;text-align:center;margin-bottom:12px'><div style='font-size:15px;color:#8b949e'>⏳ STAND ASIDE — {asset} Structure out of parameter range</div></div>""", unsafe_allow_html=True)

def chart(sym, name, sig, entry, sl, tp1, tp2, ckey="chart", asset_name=None):
    df = get_df(sym, "3mo", "1d")
    if df is None: st.warning("Execution engine chart stream disconnected"); return
    cl = df["Close"]; e20, e50, e200 = cl.ewm(20).mean(), cl.ewm(50).mean(), cl.ewm(200).mean()
    dates = df.index; fig = go.Figure()
    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(x=dates, open=df["Open"], high=df["High"], low=df["Low"], close=cl, name="Price Delivery", increasing_line_color="#3fb950", decreasing_line_color="#f85149"))
    else:
        fig.add_trace(go.Scatter(x=dates, y=cl, name="Price Line", line=dict(color="#58a6ff", width=2)))
    
    # Enhanced specialist execution styling parameters
    ema200_color = "#ffd200" if asset_name == "Gold (XAU/USD)" else "#da70d6"
    ema200_width = 2.5 if asset_name == "Gold (XAU/USD)" else 1.2
    fig.add_trace(go.Scatter(x=dates, y=e20, name="EMA20 Structural", line=dict(color="#ffd700", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=dates, y=e200, name="EMA200 Macro Base", line=dict(color={ema200_color}, width=ema200_width, dash="dash")))
    
    if entry:
        col = "#3fb950" if "BUY" in sig else "#f85149"
        fig.add_hline(y=entry, line_color=col, line_width=2, annotation_text=f"ENTRY {round(entry,4)}")
        fig.add_hline(y=sl, line_color="#f85149", line_dash="dash", annotation_text=f"INVALIDATION {round(sl,4)}")
        fig.add_hline(y=tp1, line_color="#3fb950", line_dash="dash", annotation_text=f"TP1 TARGET {round(tp1,4)}")
    
    for lv, pr in get_fibs(sym).items():
        fig.add_hline(y=pr, line_color="#9b59b6" if lv=="0.618" else "#444", line_width=1, line_dash="dot")
        
    fig.update_layout(plot_bgcolor="#0d1117", paper_bgcolor="#0d1117", font=dict(color="#e6edf3"), height=400, xaxis=dict(gridcolor="#21262d", rangeslider_visible=False), yaxis=dict(gridcolor="#21262d"), margin=dict(l=40, r=40, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True, key=ckey)

# ─── CORE AUTHENTICATION UI GUARD ────────────────────────────────────────────
def login_page():
    st.markdown("""<div style='text-align:center;padding:40px 0 20px'><div style='font-size:50px'>🚀</div><div style='font-size:32px;font-weight:900;background:linear-gradient(90deg,#00c6ff,#0072ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent'>Sparro FX AI Terminal</div><div style='color:#8b949e;font-size:13px;margin-top:6px'>High-Performance Institutional Structural Edge Scanner</div></div>""", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        t1, t2 = st.tabs(["🔐 Secure Gateway Access", "🎁 Request Trial Credentials"])
        with t1:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            em = st.text_input("User Identity Handle (Email)")
            pw = st.text_input("Security Access Phrase (Password)", type="password")
            if st.button("Unlock Core Engines", use_container_width=True, type="primary"):
                at = verify_user(em, pw)
                if at:
                    st.session_state.update(logged_in=True, account_type=at, email=em)
                    save_session(at, em); st.rerun()
                else: st.error("Access rejected. Cryptographic handshake signature failed.")
            st.markdown("</div>", unsafe_allow_html=True)
        with t2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            te = st.text_input("Target Delivery Email")
            tn = st.text_input("First Name")
            if st.button("Generate 48hr Trial Token", use_container_width=True):
                if "@" not in te or not tn.strip(): st.error("Valid authentication registration fields required.")
                else:
                    ts = datetime.datetime.now()
                    st.session_state.update(logged_in=True, account_type="trial", trial_start=ts, email=te)
                    save_session("trial", te, ts.isoformat()); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.logged_in: login_page(); st.stop()
if st.session_state.account_type == "trial" and hours_left() == 0:
    st.error("⏰ System Sandbox Trial Expired. Establish regular subscription ledger allocation access ($15/mo).")
    st.stop()

# ─── NAVIGATION APPLICATION PANEL CONTROL VIA SIDEBAR ─────────────────────────
with st.sidebar:
    st.markdown("<h3 style='text-align:center;color:#00c6ff'>🚀 Sparro Engine</h3>", unsafe_allow_html=True)
    st.caption(f"Identity: {st.session_state.email} [{st.session_state.account_type.upper()}]")
    if st.session_state.account_type == "trial": st.warning(f"Sandbox Window: {hours_left()}h remaining")
    st.divider()
    navs = [("🏠 Scanner Core Matrix", "Dashboard"), ("🎫 Open Ticket Management", "Tickets"), ("📓 Structural Ledger Journal", "Journal"), ("💰 Matrix Risk Size Modeler", "Risk")]
    for lbl, k in navs:
        if st.button(lbl, use_container_width=True, type="primary" if st.session_state.page == k else "secondary"):
            st.session_state.page = k; st.rerun()
    st.divider()
    if st.button("Purge System Allocation Memory (Logout)", use_container_width=True):
        st.session_state.clear(); st.query_params.clear(); st.rerun()

pg = st.session_state.page

# ─── RENDER INTERFACE WINDOW: DASHBOARD ───────────────────────────────────────
if pg == "Dashboard":
    st.markdown("### 🏠 Matrix Scanning Interface Core")
    t1, t2, t3 = st.tabs(["⚡ Live Confluence Pulse", "🔬 Deep Granular Breakdown", "🗞️ Macro Flow Strategy"])
    
    with t1:
        st.markdown("<div style='margin-bottom:10px'><span class='pulse-dot'></span><b>Real-time Engine Structural Scans</b></div>", unsafe_allow_html=True)
        with st.spinner("Decoding algorithmic trends..."):
            hits = []
            for name, sym in pairs.items():
                res, conf, sig = run_strats(sym, asset_name=name)
                if sig != "WAIT" and conf >= 65:
                    entry, sl, tp1, tp2, tp3 = get_setup(sym, sig, asset_name=name)
                    if entry:
                        tfs, ms, mn = run_mtf(sym, asset_name=name)
                        hits.append({"name": name, "sym": sym, "sig": sig, "conf": conf, "entry": entry, "sl": sl, "tp1": tp1, "res": res, "mtf_ok": ("BUY" in ms and "BUY" in sig) or ("SELL" in ms and "SELL" in sig), "is_spec": name in SPECIALISTS})
            hits.sort(key=lambda x: (x["is_spec"], x["conf"]), reverse=True)
            
        if not hits:
            st.info("Market pricing stabilized in structural range. Scanning continuous liquidity patterns...")
        else:
            for idx, h in enumerate(hits):
                col = "#3fb950" if "BUY" in h["sig"] else "#f85149"
                st.markdown(f"""<div class='card' style='border-left:5px solid {col}'><h4>{h['name']} — {h['sig']} ({h['conf']}% Engine Match)</h4><p>Entry Window Target: <b>{round(h['entry'],4)}</b> | Invalidation Level: <b style='color:#f85149'>{round(h['sl'],4)}</b> | Structural Expansion Point: <b style='color:#3fb950'>{round(h['tp1'],4)}</b></p></div>""", unsafe_allow_html=True)
                if st.button(f"Inject Invalidation Ledger Entry Token #{idx}", key=f"t_{idx}"):
                    auto_ticket(h['name'], h['sig'], h['conf'], h['entry'], h['sl'], h['tp1'], h['tp1']*1.02, h['tp1']*1.05, "Pulse Engine")
                    st.success("Ledger Entry Saved.")

    with t2:
        sel = st.selectbox("Select Asset Framework Index", list(pairs.keys()))
        sym = pairs[sel]
        if sel in SPECIALISTS: specialist_header(sel)
        res, conf, sig = run_strats(sym, asset_name=sel)
        banner(sig, sel, conf)
        chart(sym, sel, sig, *get_setup(sym, sig, asset_name=sel)[:3], ckey="deep", asset_name=sel)

    with t3:
        st.markdown("#### Macro Sentiment Strategy Guide Engine")
        if not is_pro(): st.error("Upgrade pipeline access to mount automated AI generative summaries.")
        else:
            if st.button("Generate AI Market Intelligence Brief"):
                with st.spinner("Structuring intelligence payload..."):
                    ctx = get_news().to_string()
                    briefing = ai_call(f"Write a hyper-focused 3-bullet micro scalping strategy for Gold, BTC, and EURUSD. Base context on tracking institutional order blocks and liquidity voids. Context feed:\n{ctx}", max_tokens=300)
                    st.write(briefing)

# ─── RENDER INTERFACE WINDOW: TICKETS ─────────────────────────────────────────
elif pg == "Tickets":
    st.markdown("### 🎫 Open Pipeline Liquidity Ledgers")
    open_t = [t for t in st.session_state.journal if t.get("Result") == "Open"]
    if not open_t: st.info("No unmitigated active ticket profiles currently registered inside database storage.")
    for idx, tr in enumerate(open_t):
        st.markdown(f"""<div class='card'><b>{tr['Asset']} ({tr['Signal']})</b><br>Track Entry Base: {tr['Entry']} | Stop Level: {tr['SL']}</div>""", unsafe_allow_html=True)
        if st.button(f"Close Ticket #{idx} with Profit Take", key=f"c_p_{idx}"):
            tr["Result"] = "Win"; st.rerun()

# ─── RENDER INTERFACE WINDOW: JOURNAL ─────────────────────────────────────────
elif pg == "Journal":
    st.markdown("### 📓 Database Historical Performance Ledger")
    if st.session_state.journal:
        st.dataframe(pd.DataFrame(st.session_state.journal), use_container_width=True)
    else: st.info("Performance historical transaction logging layer clean.")

# ─── RENDER INTERFACE WINDOW: RISK MODELER ────────────────────────────────────
elif pg == "Risk":
    st.markdown("### 💰 Risk Profile Matrix Calculator Engine")
    c1, c2 = st.columns(2)
    with c1:
        bal = st.number_input("Account Balance Equity Allocations ($)", min_value=10.0, value=2000.0)
        risk_p = st.slider("Max Capital Invalidation Ceiling Percent (%)", 0.25, 5.0, 1.0, 0.25)
        sl_pips = st.number_input("Invalidation Range (Pips/Points Offset)", min_value=1.0, value=30.0)
    
    risk_cash = bal * (risk_p / 100.0)
    calculated_lots = round(risk_cash / (sl_pips * 1.0), 2)  # Base asset unit scaling formula
    
    with c2:
        st.metric("Absolute Maximum Loss Allocation Limit", f"${risk_cash:.2f}")
        st.metric("Mathematical Position Sizing Target Volume", f"{calculated_lots} standard contracts")
