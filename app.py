import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import json
import random

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Sparro FX AI",
    layout="wide",
    page_icon="🚀"
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
  body, .main { background-color: #0d1117; color: #e6edf3; }
  .stMetric  { background: #161b22; border-radius: 10px; padding: 12px; }
  .stProgress > div > div { background: linear-gradient(90deg,#00c6ff,#0072ff); }
  .premium-badge {
    background: linear-gradient(135deg,#f7971e,#ffd200);
    color: #000; font-weight: 700; font-size: 11px;
    padding: 2px 8px; border-radius: 20px; margin-left: 6px;
  }
  .free-badge {
    background: #238636; color: #fff; font-weight: 700;
    font-size: 11px; padding: 2px 8px; border-radius: 20px; margin-left: 6px;
  }
  .signal-card {
    background: #161b22; border-radius: 12px;
    padding: 16px; margin-bottom: 10px;
    border-left: 4px solid #0072ff;
  }
  .tier-box {
    background: #161b22; border-radius: 14px;
    padding: 20px; text-align: center;
    border: 2px solid #30363d;
  }
  .tier-box.gold { border-color: #ffd200; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []
if "page" not in st.session_state:
    st.session_state.page = "Scanner"

# ── Assets ───────────────────────────────────────────────────
ALL_PAIRS = {
    "EUR/USD":        "EURUSD=X",
    "GBP/USD":        "GBPUSD=X",
    "USD/JPY":        "USDJPY=X",
    "AUD/USD":        "AUDUSD=X",
    "USD/CHF":        "USDCHF=X",
    "USD/CAD":        "USDCAD=X",
    "Gold (XAU/USD)": "GC=F",
    "Bitcoin":        "BTC-USD",
    "NASDAQ":         "^IXIC",
    "S&P 500":        "^GSPC"
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])

# ── Core Functions ────────────────────────────────────────────
def get_signal(symbol, period="6mo"):
    try:
        data = yf.download(symbol, period=period, interval="1d",
                           progress=False, auto_adjust=True)
        if data.empty:
            return "WAIT", None, None, None
        close  = data.iloc[:, 0]
        ema20  = close.ewm(span=20).mean().iloc[-1]
        ema50  = close.ewm(span=50).mean().iloc[-1]
        ema200 = close.ewm(span=200).mean().iloc[-1]
        delta  = close.diff()
        gain   = delta.where(delta > 0, 0).rolling(14).mean()
        loss   = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs     = gain / loss
        rsi    = (100 - (100 / (1 + rs))).iloc[-1]

        if ema20 > ema50 and ema50 > ema200 and rsi > 55:
            sig = "STRONG BUY"
        elif ema20 < ema50 and ema50 < ema200 and rsi < 45:
            sig = "STRONG SELL"
        elif ema20 > ema50:
            sig = "BUY"
        elif ema20 < ema50:
            sig = "SELL"
        else:
            sig = "WAIT"
        return sig, round(ema20, 5), round(rsi, 1), round(float(close.iloc[-1]), 5)
    except:
        return "ERROR", None, None, None

def calculate_confidence(d, s, t):
    conf = 50
    if d == s:        conf += 10
    if s == t:        conf += 10
    if d == t:        conf += 10
    if "STRONG" in d: conf += 5
    if "STRONG" in s: conf += 5
    if "STRONG" in t: conf += 5
    return min(conf, 99)

def get_trade_setup(symbol, direction):
    try:
        data = yf.download(symbol, period="3mo", interval="1d",
                           progress=False, auto_adjust=True)
        close = data.iloc[:, 0]
        high  = data.iloc[:, 1]
        low   = data.iloc[:, 2]
        price = float(close.iloc[-1])
        tr    = pd.concat([high-low, (high-close.shift()).abs(),
                           (low-close.shift()).abs()], axis=1).max(axis=1)
        atr   = tr.rolling(14).mean().iloc[-1]
        risk  = atr * 1.5
        if "BUY" in direction:
            return price, price-risk, price+risk, price+risk*2, price+risk*3, round(atr,5)
        else:
            return price, price+risk, price-risk, price-risk*2, price-risk*3, round(atr,5)
    except:
        return None,None,None,None,None,None

def ai_explanation(asset, signal, confidence, d, s, t):
    lines = []
    if "BUY" in signal:
        lines.append(f"**{asset}** is showing bullish momentum across multiple timeframes.")
        if d == s == t:
            lines.append("✅ All 3 timeframes aligned — Daily, Swing and Trend all agree.")
        if "STRONG" in signal:
            lines.append("🔥 EMA stack is fully bullish (EMA20 > EMA50 > EMA200) and RSI confirms strength above 55.")
        lines.append(f"📊 Confidence is **{confidence}%** — {'very high conviction' if confidence >= 85 else 'moderate conviction'}.")
        lines.append("🎯 Look for pullbacks to EMA20 as a low-risk entry opportunity.")
    elif "SELL" in signal:
        lines.append(f"**{asset}** is showing bearish pressure across timeframes.")
        if d == s == t:
            lines.append("✅ All 3 timeframes aligned — full bearish agreement.")
        if "STRONG" in signal:
            lines.append("🔻 EMA stack is fully bearish (EMA20 < EMA50 < EMA200) and RSI below 45.")
        lines.append(f"📊 Confidence is **{confidence}%** — {'very high conviction' if confidence >= 85 else 'moderate conviction'}.")
        lines.append("🎯 Look for bounces to EMA20 as a low-risk short entry.")
    else:
        lines.append(f"**{asset}** timeframes are mixed — no clear edge right now.")
        lines.append("⏳ Wait for alignment before entering a trade.")
    return "\n\n".join(lines)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.image("https://em-content.zobj.net/source/twitter/376/rocket_1f680.png", width=50)
    st.title("Sparro FX AI")
    st.divider()

    # Tier toggle (demo — replace with real auth)
    tier = st.radio("Account Tier", ["Free", "Premium (Demo)"])
    st.session_state.is_premium = (tier == "Premium (Demo)")

    if st.session_state.is_premium:
        st.success("✅ Premium Active")
    else:
        st.warning("🔒 Free Plan")
        if st.button("⚡ Upgrade to Premium — $24/mo"):
            st.info("👉 Connect Stripe or Gumroad here to take payment.")

    st.divider()
    page = st.radio("Navigate", [
        "📊 Scanner",
        "🏆 Trade of the Day",
        "🤖 AI Explanation",
        "📓 Trade Journal",
        "📈 Performance",
        "💰 Risk Calculator",
        "💎 Pricing"
    ])
    st.session_state.page = page

premium = st.session_state.is_premium
pairs   = ALL_PAIRS if premium else FREE_PAIRS

# ═════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ═════════════════════════════════════════════════════════════
if "Scanner" in page:
    st.title("📊 Market Scanner")
    if not premium:
        st.warning("🔒 Free plan shows 5 assets. Upgrade for all 10 + full confidence scores.")

    results = []
    with st.spinner("Scanning markets..."):
        for pair_name, pair_symbol in pairs.items():
            d, ema, rsi, price = get_signal(pair_symbol, "6mo")
            s, _,   _,   _    = get_signal(pair_symbol, "1y")
            t, _,   _,   _    = get_signal(pair_symbol, "2y")

            buys  = sum(1 for x in [d,s,t] if "BUY"  in x)
            sells = sum(1 for x in [d,s,t] if "SELL" in x)

            if buys  == 3: sig = "STRONG BUY"
            elif sells == 3: sig = "STRONG SELL"
            elif buys  >= 2: sig = "BUY"
            elif sells >= 2: sig = "SELL"
            else:            sig = "WAIT"

            conf = calculate_confidence(d, s, t) if premium else "🔒"
            results.append({
                "Asset": pair_name, "Signal": sig,
                "Daily": d, "Swing": s, "Trend": t,
                "Confidence": conf, "Price": price
            })

    scanner = pd.DataFrame(results)
    if premium:
        scanner = scanner.sort_values("Confidence", ascending=False)

    col1, col2 = st.columns(2)
    top_buys  = scanner[scanner["Signal"].str.contains("BUY",  na=False)]
    top_sells = scanner[scanner["Signal"].str.contains("SELL", na=False)]

    with col1:
        st.subheader("🚀 Top Buys")
        st.dataframe(top_buys[["Asset","Signal","Confidence"]].head(3), use_container_width=True)
    with col2:
        st.subheader("📉 Top Sells")
        st.dataframe(top_sells[["Asset","Signal","Confidence"]].head(3), use_container_width=True)

    st.subheader("Full Scanner")
    st.dataframe(scanner[["Asset","Signal","Daily","Swing","Trend","Confidence","Price"]],
                 use_container_width=True)

    # Store scanner in session for other pages
    st.session_state.scanner = scanner.to_dict("records")

# ═════════════════════════════════════════════════════════════
# PAGE: TRADE OF THE DAY
# ═════════════════════════════════════════════════════════════
elif "Trade of the Day" in page:
    st.title("🏆 Trade of the Day")
    if not premium:
        st.error("🔒 Trade of the Day is a Premium feature. Upgrade to unlock.")
        st.stop()

    results = []
    with st.spinner("Finding best opportunity..."):
        for pair_name, pair_symbol in ALL_PAIRS.items():
            d, _, _, price = get_signal(pair_symbol, "6mo")
            s, _, _, _     = get_signal(pair_symbol, "1y")
            t, _, _, _     = get_signal(pair_symbol, "2y")
            buys  = sum(1 for x in [d,s,t] if "BUY"  in x)
            sells = sum(1 for x in [d,s,t] if "SELL" in x)
            if buys  == 3: sig = "STRONG BUY"
            elif sells == 3: sig = "STRONG SELL"
            elif buys  >= 2: sig = "BUY"
            elif sells >= 2: sig = "SELL"
            else:            sig = "WAIT"
            conf = calculate_confidence(d, s, t)
            results.append({"Asset": pair_name, "Symbol": pair_symbol,
                             "Signal": sig, "Confidence": conf,
                             "Daily": d, "Swing": s, "Trend": t, "Price": price})

    best = max(results, key=lambda x: x["Confidence"])
    sym  = best["Symbol"]

    col1, col2, col3 = st.columns(3)
    col1.metric("🏆 Asset",      best["Asset"])
    col2.metric("📡 Signal",     best["Signal"])
    col3.metric("🎯 Confidence", f"{best['Confidence']}%")

    st.progress(best["Confidence"] / 100)

    if "BUY" in best["Signal"]:
        st.success(f"🚀 {best['Asset']} is today's strongest buy opportunity at {best['Confidence']}% confidence")
    else:
        st.error(f"📉 {best['Asset']} is today's strongest sell opportunity at {best['Confidence']}% confidence")

    st.divider()
    st.subheader("🎯 Full Trade Setup")
    entry, sl, tp1, tp2, tp3, atr = get_trade_setup(sym, best["Signal"])
    if entry:
        col1,col2,col3,col4,col5 = st.columns(5)
        col1.metric("Entry",     f"{entry:.5f}")
        col2.metric("Stop Loss", f"{sl:.5f}")
        col3.metric("TP1 (1R)",  f"{tp1:.5f}")
        col4.metric("TP2 (2R)",  f"{tp2:.5f}")
        col5.metric("TP3 (3R)",  f"{tp3:.5f}")
        st.caption(f"ATR(14): {atr} — Stop distance based on 1.5× ATR")

        st.divider()
        st.subheader("🤖 Why This Trade?")
        explanation = ai_explanation(best["Asset"], best["Signal"],
                                     best["Confidence"], best["Daily"],
                                     best["Swing"], best["Trend"])
        st.markdown(explanation)

        st.divider()
        st.subheader("📓 Log This Trade")
        if st.button("➕ Add to Journal"):
            st.session_state.trade_journal.append({
                "Date":       str(datetime.date.today()),
                "Asset":      best["Asset"],
                "Signal":     best["Signal"],
                "Entry":      entry,
                "SL":         sl,
                "TP1":        tp1,
                "Confidence": best["Confidence"],
                "Result":     "Open"
            })
            st.success("✅ Trade added to journal!")

# ═════════════════════════════════════════════════════════════
# PAGE: AI EXPLANATION
# ═════════════════════════════════════════════════════════════
elif "AI Explanation" in page:
    st.title("🤖 AI Trade Explanation")
    if not premium:
        st.error("🔒 AI Explanations are a Premium feature.")
        st.stop()

    selected = st.selectbox("Choose an asset to analyse", list(ALL_PAIRS.keys()))
    sym = ALL_PAIRS[selected]

    with st.spinner("Analysing..."):
        d, ema, rsi, price = get_signal(sym, "6mo")
        s, _,   _,   _    = get_signal(sym, "1y")
        t, _,   _,   _    = get_signal(sym, "2y")

    buys  = sum(1 for x in [d,s,t] if "BUY"  in x)
    sells = sum(1 for x in [d,s,t] if "SELL" in x)
    if buys  == 3: sig = "STRONG BUY"
    elif sells == 3: sig = "STRONG SELL"
    elif buys  >= 2: sig = "BUY"
    elif sells >= 2: sig = "SELL"
    else:            sig = "WAIT"
    conf = calculate_confidence(d, s, t)

    col1,col2,col3 = st.columns(3)
    col1.metric("Signal",      sig)
    col2.metric("Confidence",  f"{conf}%")
    col3.metric("Current RSI", f"{rsi}" if rsi else "N/A")

    st.progress(conf / 100)
    st.divider()
    st.markdown(ai_explanation(selected, sig, conf, d, s, t))

    st.divider()
    st.subheader("📐 Timeframe Breakdown")
    tf_df = pd.DataFrame({
        "Timeframe": ["Daily (6mo)", "Swing (1yr)", "Trend (2yr)"],
        "Signal":    [d, s, t],
        "Aligned":   ["✅" if x == sig or (("BUY" in x) == ("BUY" in sig)) else "⚠️" for x in [d,s,t]]
    })
    st.dataframe(tf_df, use_container_width=True)

# ═════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ═════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium:
        st.error("🔒 Trade Journal is a Premium feature.")
        st.stop()

    st.subheader("➕ Log a Trade Manually")
    with st.expander("Add New Trade"):
        c1,c2,c3 = st.columns(3)
        j_asset  = c1.selectbox("Asset",  list(ALL_PAIRS.keys()))
        j_signal = c2.selectbox("Signal", ["STRONG BUY","BUY","SELL","STRONG SELL"])
        j_result = c3.selectbox("Result", ["Open","Win","Loss","Breakeven"])
        c4,c5    = st.columns(2)
        j_entry  = c4.number_input("Entry Price", value=0.0, format="%.5f")
        j_notes  = c5.text_input("Notes", "")
        if st.button("Save Trade"):
            st.session_state.trade_journal.append({
                "Date": str(datetime.date.today()),
                "Asset": j_asset, "Signal": j_signal,
                "Entry": j_entry, "SL": 0, "TP1": 0,
                "Confidence": 0, "Result": j_result, "Notes": j_notes
            })
            st.success("✅ Trade saved!")

    st.divider()
    if st.session_state.trade_journal:
        df = pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df, use_container_width=True)

        wins   = len(df[df["Result"] == "Win"])
        losses = len(df[df["Result"] == "Loss"])
        total  = wins + losses
        wr     = round(wins/total*100, 1) if total > 0 else 0

        col1,col2,col3 = st.columns(3)
        col1.metric("Total Trades", len(df))
        col2.metric("Win Rate",     f"{wr}%")
        col3.metric("Open Trades",  len(df[df["Result"]=="Open"]))
    else:
        st.info("No trades logged yet. Use Trade of the Day to auto-log setups.")

# ═════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ═════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.title("📈 Performance Dashboard")
    if not premium:
        st.error("🔒 Performance Dashboard is a Premium feature.")
        st.stop()

    if not st.session_state.trade_journal:
        st.info("Log some trades in the Trade Journal to see your performance stats.")
    else:
        df = pd.DataFrame(st.session_state.trade_journal)
        wins   = len(df[df["Result"]=="Win"])
        losses = len(df[df["Result"]=="Loss"])
        be     = len(df[df["Result"]=="Breakeven"])
        total  = wins + losses + be
        wr     = round(wins/total*100,1) if total > 0 else 0

        col1,col2,col3,col4 = st.columns(4)
        col1.metric("Total Trades",  total)
        col2.metric("Wins",          wins)
        col3.metric("Losses",        losses)
        col4.metric("Win Rate",      f"{wr}%")

        st.divider()
        if "Asset" in df.columns:
            asset_perf = df.groupby("Asset")["Result"].value_counts().unstack(fill_value=0)
            st.subheader("Performance by Asset")
            st.dataframe(asset_perf, use_container_width=True)

# ═════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ═════════════════════════════════════════════════════════════
elif "Risk" in page:
    st.title("💰 Risk Calculator")
    st.info("Calculate your position size based on your account and risk tolerance.")

    col1, col2 = st.columns(2)
    with col1:
        balance      = st.number_input("Account Balance ($)", min_value=10.0, value=1000.0)
        risk_percent = st.slider("Risk Per Trade (%)", 0.5, 10.0, 2.0, step=0.5)
        stop_pips    = st.number_input("Stop Loss (pips)", min_value=1.0, value=20.0)
        pip_value    = st.number_input("Pip Value per 0.01 lot ($)", value=0.10)

    risk_amount = balance * risk_percent / 100
    lot_size    = round(risk_amount / (stop_pips * pip_value / 0.01) * 0.01, 2)
    rr          = st.slider("Risk:Reward Ratio", 1, 5, 2)

    with col2:
        st.metric("💵 Risk Amount",     f"${risk_amount:.2f}")
        st.metric("📦 Lot Size",        f"{lot_size} lots")
        st.metric("🎯 Potential Profit", f"${risk_amount * rr:.2f}")
        st.metric("📊 Risk:Reward",     f"1:{rr}")

    st.divider()
    st.progress(risk_percent / 10)
    if risk_percent <= 2:
        st.success("✅ Conservative risk — good for consistency")
    elif risk_percent <= 5:
        st.warning("⚠️ Moderate risk — manage carefully")
    else:
        st.error("🚨 High risk — only for experienced traders")

# ═════════════════════════════════════════════════════════════
# PAGE: PRICING
# ═════════════════════════════════════════════════════════════
elif "Pricing" in page:
    st.title("💎 Upgrade to Premium")
    st.subheader("Unlock the full power of Sparro FX AI")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class='tier-box'>
        <h3>🆓 Free</h3>
        <h2>$0 / month</h2>
        <hr/>
        ✅ 5 assets (Forex pairs)<br><br>
        ✅ Basic Buy/Sell signals<br><br>
        ✅ Single timeframe view<br><br>
        ❌ Confidence scores locked<br><br>
        ❌ Trade of the Day locked<br><br>
        ❌ AI Explanations locked<br><br>
        ❌ Trade Journal locked<br><br>
        ❌ Risk Calculator (basic only)<br><br>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='tier-box gold'>
        <h3>⚡ Premium</h3>
        <h2>$24 / month</h2>
        <hr/>
        ✅ All 10 assets (Forex, Gold, Crypto, Indices)<br><br>
        ✅ Real confidence scores (not guesses)<br><br>
        ✅ 3-timeframe alignment analysis<br><br>
        ✅ 🏆 Trade of the Day (auto-selected)<br><br>
        ✅ 🤖 AI Trade Explanation<br><br>
        ✅ 📓 Trade Journal<br><br>
        ✅ 📈 Performance Dashboard<br><br>
        ✅ 💰 Full Risk Calculator<br><br>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("🚀 Ready to upgrade?")
    st.markdown("""
    Connect one of these payment providers to start collecting subscriptions:

    - **[Stripe](https://stripe.com)** — best for recurring billing, card payments
    - **[Gumroad](https://gumroad.com)** — easiest to set up, great for indie products
    - **[LemonSqueezy](https://lemonsqueezy.com)** — modern Stripe alternative
    - **[Whop](https://whop.com)** — built for trading communities & signal groups
    """)
    st.info("💡 Tip: Start with Gumroad or Whop — both let you launch in under 30 minutes with zero coding.")
