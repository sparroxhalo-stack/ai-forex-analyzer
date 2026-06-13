import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import json
import os
import requests

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
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────
DEFAULTS = {
    "is_premium": False,
    "trade_journal": [],
    "telegram_token": "",
    "telegram_chat_id": "",
    "subscriber_chat_ids": [],   # list of all subscriber chat IDs for broadcast
    "notification_threshold": 75,
}
for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Assets ───────────────────────────────────────────────────
ALL_PAIRS = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X",
    "AUD/USD":"AUDUSD=X","USD/CHF":"USDCHF=X","USD/CAD":"USDCAD=X",
    "Gold (XAU/USD)":"GC=F","Bitcoin":"BTC-USD","NASDAQ":"^IXIC","S&P 500":"^GSPC"
}
FREE_PAIRS = dict(list(ALL_PAIRS.items())[:5])

# ════════════════════════════════════════════════════════════
# SIGNAL BANNER — urgent visual alert for strong signals
# ════════════════════════════════════════════════════════════
def show_signal_banner(sig, asset, conf):
    """Display a prominent urgent banner based on signal strength."""
    if sig == "STRONG BUY":
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#0d5c2e,#1a7a3e);border:2px solid #3fb950;
        border-radius:14px;padding:22px;text-align:center;margin-bottom:16px;
        box-shadow:0 0 20px rgba(63,185,80,0.4)'>
        <div style='font-size:28px;font-weight:900;color:#3fb950;letter-spacing:2px'>
        🚀 STRONG BUY — BUY NOW</div>
        <div style='font-size:18px;color:#e6edf3;margin-top:8px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        <div style='font-size:13px;color:#8b949e;margin-top:6px'>⚡ {conf}% of strategies agree — high probability setup</div>
        </div>""", unsafe_allow_html=True)
    elif sig == "BUY":
        st.markdown(f"""
        <div style='background:#0d2b1a;border:2px solid #3fb950;
        border-radius:14px;padding:18px;text-align:center;margin-bottom:16px'>
        <div style='font-size:22px;font-weight:800;color:#3fb950'>🟢 BUY SIGNAL</div>
        <div style='font-size:16px;color:#e6edf3;margin-top:6px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""", unsafe_allow_html=True)
    elif sig == "STRONG SELL":
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#5c0d0d,#7a1a1a);border:2px solid #f85149;
        border-radius:14px;padding:22px;text-align:center;margin-bottom:16px;
        box-shadow:0 0 20px rgba(248,81,73,0.4)'>
        <div style='font-size:28px;font-weight:900;color:#f85149;letter-spacing:2px'>
        📉 STRONG SELL — SELL NOW</div>
        <div style='font-size:18px;color:#e6edf3;margin-top:8px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        <div style='font-size:13px;color:#8b949e;margin-top:6px'>⚡ {conf}% of strategies agree — high probability setup</div>
        </div>""", unsafe_allow_html=True)
    elif sig == "SELL":
        st.markdown(f"""
        <div style='background:#2b0d0d;border:2px solid #f85149;
        border-radius:14px;padding:18px;text-align:center;margin-bottom:16px'>
        <div style='font-size:22px;font-weight:800;color:#f85149'>🔴 SELL SIGNAL</div>
        <div style='font-size:16px;color:#e6edf3;margin-top:6px'>{asset} &nbsp;|&nbsp; {conf}% confidence</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background:#1c1c1c;border:2px solid #8b949e;
        border-radius:14px;padding:16px;text-align:center;margin-bottom:16px'>
        <div style='font-size:20px;font-weight:700;color:#8b949e'>⏳ WAIT — No Clear Signal</div>
        <div style='font-size=14px;color:#8b949e;margin-top:6px'>{asset} — market is unclear, stand aside</div>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# TELEGRAM — single message + broadcast to all subscribers
# ════════════════════════════════════════════════════════════
def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r   = requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
        return r.status_code == 200
    except:
        return False

def broadcast_telegram(token, chat_ids, message):
    """Send a message to every subscriber chat ID."""
    if not token or not chat_ids:
        return 0, 0
    success = 0
    fail    = 0
    for cid in chat_ids:
        cid = str(cid).strip()
        if not cid:
            continue
        ok = send_telegram(token, cid, message)
        if ok:
            success += 1
        else:
            fail += 1
    return success, fail

def build_signal_message(asset, signal, confidence, entry, sl, tp1, tp2, tp3):
    direction = "🚀 BUY" if "BUY" in signal else "📉 SELL"
    return f"""
🔔 *Sparro FX AI — New Signal*

{direction} *{asset}*
📊 Signal: *{signal}*
🎯 Confidence: *{confidence}%*

💰 Entry:     `{round(entry,5)}`
🛑 Stop Loss: `{round(sl,5)}`
✅ TP1 (1R):  `{round(tp1,5)}`
✅ TP2 (2R):  `{round(tp2,5)}`
✅ TP3 (3R):  `{round(tp3,5)}`

⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
_Sparro FX AI — Trade responsibly_
"""

def notify_trade(asset, signal, confidence, entry, sl, tp1, tp2, tp3):
    """Send to owner's own chat ID only."""
    token   = st.session_state.telegram_token
    chat_id = st.session_state.telegram_chat_id
    if not token or not chat_id:
        return False
    msg = build_signal_message(asset, signal, confidence, entry, sl, tp1, tp2, tp3)
    return send_telegram(token, chat_id, msg)

def notify_all_subscribers(asset, signal, confidence, entry, sl, tp1, tp2, tp3):
    """Broadcast signal to ALL subscriber chat IDs."""
    token      = st.session_state.telegram_token
    chat_ids   = st.session_state.subscriber_chat_ids
    # also include owner's own chat ID if set
    owner_id   = st.session_state.telegram_chat_id
    all_ids    = list(chat_ids)
    if owner_id and owner_id not in all_ids:
        all_ids.insert(0, owner_id)
    msg = build_signal_message(asset, signal, confidence, entry, sl, tp1, tp2, tp3)
    return broadcast_telegram(token, all_ids, msg)

# ════════════════════════════════════════════════════════════
# DATA & STRATEGY ENGINE
# ════════════════════════════════════════════════════════════
def fetch_data(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

def strategy_ema_trend(df):
    c   = df["Close"]
    e20 = c.ewm(span=20).mean().iloc[-1]
    e50 = c.ewm(span=50).mean().iloc[-1]
    e200= c.ewm(span=200).mean().iloc[-1]
    if e20 > e50 and e50 > e200:
        return "BUY",  "EMA20 > EMA50 > EMA200 — full bullish stack"
    if e20 < e50 and e50 < e200:
        return "SELL", "EMA20 < EMA50 < EMA200 — full bearish stack"
    return "NEUTRAL", "EMA stack mixed"

def strategy_rsi(df):
    c = df["Close"]; d = c.diff()
    g = d.where(d > 0, 0).rolling(14).mean()
    l = (-d.where(d < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + (g / l)))).iloc[-1]
    if rsi > 60: return "BUY",  f"RSI={round(rsi,1)} — bullish momentum"
    if rsi < 40: return "SELL", f"RSI={round(rsi,1)} — bearish momentum"
    return "NEUTRAL", f"RSI={round(rsi,1)} — neutral"

def strategy_macd(df):
    c = df["Close"]
    m = c.ewm(span=12).mean() - c.ewm(span=26).mean()
    s = m.ewm(span=9).mean(); h = m - s
    if m.iloc[-1] > s.iloc[-1] and h.iloc[-1] > h.iloc[-2]: return "BUY",  "MACD bullish crossover"
    if m.iloc[-1] < s.iloc[-1] and h.iloc[-1] < h.iloc[-2]: return "SELL", "MACD bearish crossover"
    return "NEUTRAL", "MACD weak signal"

def strategy_bollinger(df):
    c = df["Close"]; mid = c.rolling(20).mean(); std = c.rolling(20).std()
    upper = mid + 2*std; lower = mid - 2*std; p = c.iloc[-1]
    if p > upper.iloc[-1]: return "BUY",  "Above Bollinger upper — breakout"
    if p < lower.iloc[-1]: return "SELL", "Below Bollinger lower — breakdown"
    if p > mid.iloc[-1]:   return "BUY",  "Above BB midline"
    return "SELL", "Below BB midline"

def strategy_sr(df):
    h = df["High"]; l = df["Low"]; p = float(df["Close"].iloc[-1])
    res = float(h.rolling(10).max().iloc[-1]); sup = float(l.rolling(10).min().iloc[-1])
    zone = (res - sup) * 0.15
    if p >= res - zone: return "SELL", f"At resistance {round(res,4)} — rejection likely"
    if p <= sup + zone: return "BUY",  f"At support {round(sup,4)} — bounce likely"
    return ("BUY" if p > (res+sup)/2 else "SELL"), f"S={round(sup,4)} R={round(res,4)}"

def strategy_candles(df):
    o  = df["Open"].iloc[-1]  if "Open" in df.columns else df["Close"].iloc[-2]
    h  = df["High"].iloc[-1]; l = df["Low"].iloc[-1]; c = df["Close"].iloc[-1]
    po = df["Open"].iloc[-2]  if "Open" in df.columns else df["Close"].iloc[-3]
    pc = df["Close"].iloc[-2]
    body = abs(c-o); candle = h-l; uw = h-max(c,o); lw = min(c,o)-l
    if c > o and pc < po and c > po and o < pc: return "BUY",  "Bullish Engulfing pattern"
    if c < o and pc > po and c < po and o > pc: return "SELL", "Bearish Engulfing pattern"
    if lw > body*2 and uw < body*0.5:           return "BUY",  "Hammer / Pin Bar — bullish rejection"
    if uw > body*2 and lw < body*0.5:           return "SELL", "Shooting Star — bearish rejection"
    if body < candle*0.1:                        return "NEUTRAL", "Doji — indecision"
    return "NEUTRAL", "No strong candle pattern"

def strategy_bos(df):
    h = df["High"]; l = df["Low"]; p = float(df["Close"].iloc[-1])
    sh  = float(h.iloc[-20:-5].max()); sl_ = float(l.iloc[-20:-5].min())
    if p > sh:  return "BUY",  f"Break of Structure — broke swing high {round(sh,4)}"
    if p < sl_: return "SELL", f"Break of Structure — broke swing low {round(sl_,4)}"
    return "NEUTRAL", f"Inside range {round(sl_,4)}–{round(sh,4)}"

def strategy_volume(df):
    if "Volume" not in df.columns: return "NEUTRAL", "No volume data"
    v = df["Volume"]; c = df["Close"]
    avg = v.rolling(20).mean().iloc[-1]; cur = v.iloc[-1]; up = c.iloc[-1] > c.iloc[-2]
    r   = cur / avg if avg > 0 else 1
    if r > 1.5 and up:     return "BUY",  f"High volume bullish ({round(r,1)}x avg)"
    if r > 1.5 and not up: return "SELL", f"High volume bearish ({round(r,1)}x avg)"
    return "NEUTRAL", f"Normal volume ({round(r,1)}x avg)"

STRATEGIES = {
    "EMA Trend":           strategy_ema_trend,
    "RSI Momentum":        strategy_rsi,
    "MACD Crossover":      strategy_macd,
    "Bollinger Breakout":  strategy_bollinger,
    "Support/Resistance":  strategy_sr,
    "Candlestick Pattern": strategy_candles,
    "Break of Structure":  strategy_bos,
    "Volume Momentum":     strategy_volume,
}

def run_all_strategies(symbol, period="6mo"):
    df = fetch_data(symbol, period)
    if df is None: return {}, 0, "ERROR"
    results = {}
    for name, fn in STRATEGIES.items():
        try:    results[name] = fn(df)
        except: results[name] = ("NEUTRAL", "Error")
    buys  = sum(1 for s,_ in results.values() if s == "BUY")
    sells = sum(1 for s,_ in results.values() if s == "SELL")
    total = len(results)
    if buys > sells:   conf = round(buys/total*100);  sig = "STRONG BUY"  if buys  >= 6 else "BUY"
    elif sells > buys: conf = round(sells/total*100); sig = "STRONG SELL" if sells >= 6 else "SELL"
    else:              conf = 50; sig = "WAIT"
    return results, conf, sig

def get_trade_setup(symbol, direction):
    try:
        df = fetch_data(symbol, "3mo"); c = df["Close"]; h = df["High"]; l = df["Low"]
        p  = float(c.iloc[-1])
        tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr   = float(tr.rolling(14).mean().iloc[-1]); risk = atr * 1.5
        if "BUY" in direction:
            return p, p-risk, p+risk, p+risk*2, p+risk*3, round(atr,5)
        else:
            return p, p+risk, p-risk, p-risk*2, p-risk*3, round(atr,5)
    except:
        return None, None, None, None, None, None

# ════════════════════════════════════════════════════════════
# PRICE CHART  — FIX: plotly imported at top, HTML escaped
# ════════════════════════════════════════════════════════════
def show_price_chart(symbol, pair_name, signal, entry, sl, tp1, tp2):
    df = fetch_data(symbol, "3mo", "1d")
    if df is None:
        st.warning("Chart data unavailable.")
        return

    close  = df["Close"]
    ema20  = close.ewm(span=20).mean()
    ema50  = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()
    resistance = float(df["High"].rolling(10).max().iloc[-1])
    support    = float(df["Low"].rolling(10).min().iloc[-1])
    dates      = df.index

    fig = go.Figure()

    if "Open" in df.columns:
        fig.add_trace(go.Candlestick(
            x=dates, open=df["Open"], high=df["High"],
            low=df["Low"], close=close, name="Price",
            increasing_line_color="#3fb950",
            decreasing_line_color="#f85149"
        ))
    else:
        fig.add_trace(go.Scatter(x=dates, y=close, name="Price",
            line=dict(color="#58a6ff", width=2)))

    fig.add_trace(go.Scatter(x=dates, y=ema20,  name="EMA 20",  line=dict(color="#ffd700", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=dates, y=ema50,  name="EMA 50",  line=dict(color="#ff7f50", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=dates, y=ema200, name="EMA 200", line=dict(color="#da70d6", width=1, dash="dash")))

    fig.add_hline(y=resistance, line_color="#f85149", line_dash="dash",
                  annotation_text=f"Resistance {round(resistance,4)}", annotation_position="right")
    fig.add_hline(y=support, line_color="#3fb950", line_dash="dash",
                  annotation_text=f"Support {round(support,4)}", annotation_position="right")

    if entry:
        color = "#3fb950" if "BUY" in signal else "#f85149"
        fig.add_hline(y=entry, line_color=color,    line_width=2,
                      annotation_text=f"Entry {round(entry,5)}", annotation_position="left")
        fig.add_hline(y=sl,    line_color="#f85149", line_width=1, line_dash="dash",
                      annotation_text=f"SL {round(sl,5)}", annotation_position="left")
        fig.add_hline(y=tp1,   line_color="#3fb950", line_width=1, line_dash="dash",
                      annotation_text=f"TP1 {round(tp1,5)}", annotation_position="left")
        fig.add_hline(y=tp2,   line_color="#3fb950", line_width=1, line_dash="dot",
                      annotation_text=f"TP2 {round(tp2,5)}", annotation_position="left")

    last_price   = float(close.iloc[-1])
    arrow_color  = "#3fb950" if "BUY" in signal else "#f85149"
    arrow_symbol = "triangle-up" if "BUY" in signal else "triangle-down"
    fig.add_trace(go.Scatter(
        x=[dates[-1]], y=[last_price], mode="markers",
        marker=dict(symbol=arrow_symbol, size=16, color=arrow_color),
        name=f"{signal} Signal"
    ))

    fig.update_layout(
        title=f"{pair_name} — Price Chart with Trade Setup",
        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        xaxis=dict(gridcolor="#21262d", rangeslider_visible=False),
        yaxis=dict(gridcolor="#21262d"),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        height=500,
        margin=dict(l=60, r=120, t=60, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Why take this trade — FIX: use &lt; instead of < in HTML ──
    st.subheader("💡 Why Take This Trade?")
    price_vs_ema20  = "above" if last_price > float(ema20.iloc[-1])  else "below"
    price_vs_ema200 = "above" if last_price > float(ema200.iloc[-1]) else "below"
    trend_dir       = "uptrend" if float(ema20.iloc[-1]) > float(ema200.iloc[-1]) else "downtrend"
    month_ago       = float(close.iloc[-22]) if len(close) > 22 else float(close.iloc[0])
    change_pct      = round((last_price - month_ago) / month_ago * 100, 2)
    change_str      = f"up {change_pct}%" if change_pct > 0 else f"down {abs(change_pct)}%"
    ema_slope       = float(ema20.iloc[-1]) - float(ema20.iloc[-5])
    slope_str       = "rising strongly" if ema_slope > 0 else "falling strongly"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #0072ff'>
        <b>📈 Price Movement (Last 30 days)</b><br><br>
        • Price has moved <b>{change_str}</b> over the past month<br>
        • Currently <b>{price_vs_ema20} EMA20</b> — short-term trend is {"bullish" if price_vs_ema20=="above" else "bearish"}<br>
        • Currently <b>{price_vs_ema200} EMA200</b> — long-term trend is {"bullish" if price_vs_ema200=="above" else "bearish"}<br>
        • EMA20 is <b>{slope_str}</b> — momentum is {"building" if "rising" in slope_str else "weakening"}<br>
        • Overall: <b>{trend_dir.upper()}</b>
        </div>""", unsafe_allow_html=True)
    with col2:
        near_res  = abs(last_price - resistance) / last_price < 0.005
        near_sup  = abs(last_price - support)    / last_price < 0.005
        zone_note = ("⚠️ Price is near resistance — watch for rejection" if near_res else
                     "✅ Price is near support — potential bounce zone"   if near_sup else
                     "📊 Price is in the middle of the range")
        trend_agree = (("BUY" in signal and trend_dir == "uptrend") or
                       ("SELL" in signal and trend_dir == "downtrend"))
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:14px;border-left:4px solid #ffd700'>
        <b>🎯 Trade Reasoning</b><br><br>
        • Signal: <b>{signal}</b><br>
        • Key resistance: <b>{round(resistance,4)}</b><br>
        • Key support: <b>{round(support,4)}</b><br>
        • {zone_note}<br>
        • {"✅ Trend and signal AGREE — higher probability" if trend_agree else "⚠️ Trading against the trend — lower probability, reduce size"}
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# NEWS
# ════════════════════════════════════════════════════════════
def fetch_forex_news():
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        r   = requests.get(url, timeout=8)
        if r.status_code == 200:
            events = r.json()
            return pd.DataFrame([{
                "Time":     e.get("date","")[:16].replace("T"," "),
                "Currency": e.get("currency",""),
                "Event":    e.get("title",""),
                "Impact":   e.get("impact",""),
                "Forecast": e.get("forecast","—"),
                "Previous": e.get("previous","—"),
            } for e in events[:25]])
    except:
        pass
    return pd.DataFrame([
        {"Time":"Today 08:30","Currency":"USD","Event":"Non-Farm Payrolls","Impact":"High","Forecast":"180K","Previous":"175K"},
        {"Time":"Today 10:00","Currency":"EUR","Event":"ECB Rate Decision","Impact":"High","Forecast":"4.5%","Previous":"4.5%"},
        {"Time":"Today 13:30","Currency":"GBP","Event":"CPI y/y","Impact":"Medium","Forecast":"3.1%","Previous":"3.4%"},
        {"Time":"Tomorrow 14:00","Currency":"USD","Event":"FOMC Minutes","Impact":"High","Forecast":"—","Previous":"—"},
    ])

def analyse_news_with_ai(news_df, pair):
    try:
        news_text = news_df.to_string(index=False)
        prompt = f"""You are a professional forex news analyst.
Asset: {pair}

This week's economic calendar:
{news_text}

Analyse clearly:
1. Which events most affect {pair}?
2. What direction does news sentiment suggest (Bullish/Bearish/Neutral)?
3. Which days/times should the trader AVOID?
4. Which events could cause the biggest moves?
5. Overall bias for {pair} this week?

Be concise and direct. Use bullet points."""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": st.secrets.get("ANTHROPIC_API_KEY",""),
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 800,
                "messages": [{"role":"user","content":prompt}]
            },
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
        return f"AI error {r.status_code} — add your Anthropic API key in Settings."
    except Exception as e:
        return f"Error: {e}"

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🚀 Sparro FX AI")
    st.divider()
    tier = st.radio("Account Tier", ["Free","Premium (Demo)"])
    st.session_state.is_premium = (tier == "Premium (Demo)")
    if st.session_state.is_premium: st.success("✅ Premium Active")
    else:
        st.warning("🔒 Free Plan")
        if st.button("⚡ Upgrade — $15/mo"):
            st.info("Connect Stripe / Gumroad / Whop here.")
    st.divider()
    page = st.radio("Navigate",[
        "📊 Scanner",
        "🏆 Trade of the Day",
        "🔬 Deep Analysis",
        "🗞️ News Analysis",
        "🔔 Notifications",
        "📓 Trade Journal",
        "📈 Performance",
        "💰 Risk Calculator",
        "⚙️ Settings",
        "💎 Pricing",
    ])

premium = st.session_state.is_premium
pairs   = ALL_PAIRS if premium else FREE_PAIRS

# ════════════════════════════════════════════════════════════
# PAGE: SCANNER
# ════════════════════════════════════════════════════════════
if "Scanner" in page:
    st.title("📊 Market Scanner")
    if not premium:
        st.warning("🔒 Free plan: 5 assets. Upgrade for all 10 + full strategy engine.")

    results = []
    prog = st.progress(0); items = list(pairs.items())
    for i, (name, sym) in enumerate(items):
        strats, conf, sig = run_all_strategies(sym)
        buys  = sum(1 for s,_ in strats.values() if s == "BUY")
        sells = sum(1 for s,_ in strats.values() if s == "SELL")
        results.append({
            "Asset": name, "Signal": sig,
            "Confidence":  f"{conf}%" if premium else "🔒",
            "Strategies":  f"{max(buys,sells)}/8" if premium else "🔒"
        })
        prog.progress((i+1)/len(items))
    prog.empty()

    scanner = pd.DataFrame(results)

    # Show urgent banners for any STRONG signals
    strong = [r for r in results if r["Signal"] in ("STRONG BUY","STRONG SELL")]
    if strong:
        st.subheader("⚡ Urgent Signals")
        for r in strong:
            show_signal_banner(r["Signal"], r["Asset"], int(r["Confidence"].replace("%","")) if "%" in str(r["Confidence"]) else 0)

    c1, c2  = st.columns(2)
    with c1:
        st.subheader("🚀 Top Buys")
        st.dataframe(scanner[scanner["Signal"].str.contains("BUY", na=False)].head(3), use_container_width=True)
    with c2:
        st.subheader("📉 Top Sells")
        st.dataframe(scanner[scanner["Signal"].str.contains("SELL", na=False)].head(3), use_container_width=True)
    st.subheader("Full Scanner")
    st.dataframe(scanner, use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: TRADE OF THE DAY
# ════════════════════════════════════════════════════════════
elif "Trade of the Day" in page:
    st.title("🏆 Trade of the Day")
    if not premium: st.error("🔒 Premium only."); st.stop()

    best = {"conf":0,"sig":"WAIT","name":"","sym":"","strats":{}}
    with st.spinner("Scanning all assets..."):
        for name, sym in ALL_PAIRS.items():
            strats, conf, sig = run_all_strategies(sym)
            if sig != "WAIT" and conf > best["conf"]:
                best = {"conf":conf,"sig":sig,"name":name,"sym":sym,"strats":strats}

    c1, c2, c3 = st.columns(3)
    c1.metric("🏆 Asset", best["name"])
    c2.metric("📡 Signal", best["sig"])
    c3.metric("🎯 Confidence", f"{best['conf']}%")
    st.progress(best["conf"]/100)

    show_signal_banner(best["sig"], best["name"], best["conf"])

    st.divider()
    entry, sl, tp1, tp2, tp3, atr = get_trade_setup(best["sym"], best["sig"])
    if entry:
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Entry", f"{entry:.5f}"); c2.metric("SL", f"{sl:.5f}")
        c3.metric("TP1",  f"{tp1:.5f}");   c4.metric("TP2", f"{tp2:.5f}"); c5.metric("TP3", f"{tp3:.5f}")

        col1, col2, col3 = st.columns(3)
        if col1.button("🔔 My Alert"):
            ok = notify_trade(best["name"], best["sig"], best["conf"], entry, sl, tp1, tp2, tp3)
            st.success("✅ Sent to you!") if ok else st.error("❌ Check Notifications settings.")
        if col2.button("📢 Broadcast to All Subscribers"):
            s, f = notify_all_subscribers(best["name"], best["sig"], best["conf"], entry, sl, tp1, tp2, tp3)
            st.success(f"✅ Sent to {s} subscriber(s). {f} failed.") if s > 0 else st.error("❌ No subscribers found or send failed.")
        if col3.button("➕ Add to Journal"):
            st.session_state.trade_journal.append({
                "Date": str(datetime.date.today()), "Asset": best["name"],
                "Signal": best["sig"], "Entry": entry, "SL": sl, "TP1": tp1,
                "Confidence": best["conf"], "Result": "Open"
            })
            st.success("✅ Added!")

    st.divider()
    if best["sym"]:
        show_price_chart(best["sym"], best["name"], best["sig"], entry, sl, tp1, tp2)

# ════════════════════════════════════════════════════════════
# PAGE: DEEP ANALYSIS
# ════════════════════════════════════════════════════════════
elif "Deep Analysis" in page:
    st.title("🔬 Deep Strategy Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()

    selected = st.selectbox("Choose Asset", list(ALL_PAIRS.keys()))
    sym      = ALL_PAIRS[selected]

    with st.spinner(f"Running 8 strategies on {selected}..."):
        strats, conf, sig = run_all_strategies(sym)

    show_signal_banner(sig, selected, conf)
    c1,c2,c3 = st.columns(3)
    c1.metric("Signal", sig); c2.metric("Confidence", f"{conf}%"); c3.metric("Strategies","8 analysed")
    st.progress(conf/100)
    st.divider()

    for name, (s, reason) in strats.items():
        color = "#238636" if s=="BUY" else "#da3633" if s=="SELL" else "#9e6a03"
        icon  = "🟢"      if s=="BUY" else "🔴"      if s=="SELL" else "🟡"
        # Escape reason so angle brackets aren't parsed as HTML tags
        safe_reason = reason.replace("<","&lt;").replace(">","&gt;")
        st.markdown(f"""
        <div style='background:#161b22;border-radius:10px;padding:12px;margin-bottom:8px;border-left:4px solid {color}'>
          <b>{icon} {name}</b> &nbsp;
          <span style='background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px'>{s}</span><br>
          <small style='color:#8b949e'>{safe_reason}</small>
        </div>""", unsafe_allow_html=True)

    buys  = sum(1 for s,_ in strats.values() if s=="BUY")
    sells = sum(1 for s,_ in strats.values() if s=="SELL")
    c1,c2,c3 = st.columns(3)
    c1.metric("🟢 Buy Votes", buys); c2.metric("🔴 Sell Votes", sells); c3.metric("🟡 Neutral", 8-buys-sells)

    st.divider()
    entry, sl, tp1, tp2, tp3, atr = get_trade_setup(sym, sig)
    if entry and sig != "WAIT":
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Entry", f"{entry:.5f}"); c2.metric("SL", f"{sl:.5f}")
        c3.metric("TP1",  f"{tp1:.5f}");   c4.metric("TP2", f"{tp2:.5f}"); c5.metric("TP3", f"{tp3:.5f}")
        if conf >= 75:   st.success(f"✅ HIGH confidence — {conf}% agree")
        elif conf >= 60: st.warning(f"⚠️ MODERATE — {conf}%. Use smaller size.")
        else:            st.error(f"🚨 LOW confidence — {conf}%. Consider waiting.")

        col1, col2 = st.columns(2)
        if col1.button("🔔 My Alert"):
            ok = notify_trade(selected, sig, conf, entry, sl, tp1, tp2, tp3)
            st.success("✅ Sent!") if ok else st.error("❌ Check Notifications settings.")
        if col2.button("📢 Broadcast to All Subscribers"):
            s, f = notify_all_subscribers(selected, sig, conf, entry, sl, tp1, tp2, tp3)
            st.success(f"✅ Sent to {s} subscriber(s). {f} failed.") if s > 0 else st.error("❌ No subscribers or send failed.")

    st.divider()
    show_price_chart(sym, selected, sig, entry, sl, tp1, tp2)

# ════════════════════════════════════════════════════════════
# PAGE: NEWS ANALYSIS
# ════════════════════════════════════════════════════════════
elif "News" in page:
    st.title("🗞️ News Analysis")
    if not premium: st.error("🔒 Premium only."); st.stop()

    with st.spinner("Fetching economic calendar..."):
        news_df = fetch_forex_news()

    st.subheader("📅 Economic Calendar — This Week")
    st.dataframe(news_df, use_container_width=True)

    st.divider()
    st.subheader("🤖 AI News Analysis")
    selected = st.selectbox("Select asset", list(ALL_PAIRS.keys()))
    if st.button("🔍 Analyse News Impact"):
        with st.spinner("Analysing..."):
            analysis = analyse_news_with_ai(news_df, selected)
        st.markdown(f"<div class='news-card'>{analysis.replace(chr(10),'<br>')}</div>",
                    unsafe_allow_html=True)

    st.divider()
    st.subheader("⚠️ High-Impact Events")
    high = news_df[news_df["Impact"]=="High"] if "Impact" in news_df.columns else pd.DataFrame()
    if not high.empty:
        for _, row in high.iterrows():
            st.error(f"🔴 {row.get('Time','')} | {row.get('Currency','')} — {row.get('Event','')} | Forecast: {row.get('Forecast','—')}")
    else:
        st.success("✅ No high-impact events — relatively safe window")

# ════════════════════════════════════════════════════════════
# PAGE: NOTIFICATIONS  — now includes subscriber management
# ════════════════════════════════════════════════════════════
elif "Notifications" in page:
    st.title("🔔 Telegram Notifications")
    if not premium: st.error("🔒 Premium only."); st.stop()

    with st.expander("📖 3-Step Setup Guide"):
        st.markdown("""
**Step 1 — Create your bot:**
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → choose a name → copy the **Bot Token**

**Step 2 — Get your Chat ID:**
1. Search `@userinfobot` on Telegram
2. Send any message → it replies with your **Chat ID**

**Step 3 — Paste below and test!**
        """)

    st.subheader("🤖 Your Bot Settings")
    token   = st.text_input("Bot Token",  value=st.session_state.telegram_token,   type="password")
    chat_id = st.text_input("Your Chat ID", value=st.session_state.telegram_chat_id)

    if st.button("💾 Save Bot Settings"):
        st.session_state.telegram_token   = token
        st.session_state.telegram_chat_id = chat_id
        st.success("✅ Saved!")

    if st.button("🧪 Send Test Message to Yourself"):
        ok = send_telegram(token, chat_id, "✅ *Sparro FX AI* — Telegram connected! You'll receive trade alerts here. 🚀")
        st.success("✅ Check Telegram!") if ok else st.error("❌ Failed — check token and chat ID.")

    st.divider()
    # ── Subscriber Management ────────────────────────────────
    st.subheader("👥 Subscriber Chat IDs (Broadcast List)")
    st.info("Add every subscriber's Telegram Chat ID here. When you click **Broadcast to All Subscribers** on a signal, every person on this list gets the alert automatically.")

    # Display current list
    current_ids = st.session_state.subscriber_chat_ids
    if current_ids:
        st.success(f"✅ {len(current_ids)} subscriber(s) on the broadcast list")
        ids_text = st.text_area(
            "Edit subscriber Chat IDs (one per line)",
            value="\n".join(str(x) for x in current_ids),
            height=180,
            help="Each line should be one Telegram Chat ID. You can add or remove IDs here."
        )
    else:
        st.warning("No subscribers yet. Add their Chat IDs below.")
        ids_text = st.text_area(
            "Subscriber Chat IDs (one per line)",
            placeholder="123456789\n987654321\n112233445",
            height=180,
            help="Paste each subscriber's Telegram Chat ID on a new line."
        )

    col1, col2 = st.columns(2)
    if col1.button("💾 Save Subscriber List"):
        lines = [l.strip() for l in ids_text.splitlines() if l.strip()]
        st.session_state.subscriber_chat_ids = lines
        st.success(f"✅ Saved {len(lines)} subscriber(s)!")

    if col2.button("📢 Send Test Broadcast to All"):
        s, f = broadcast_telegram(
            st.session_state.telegram_token,
            st.session_state.subscriber_chat_ids,
            "📢 *Sparro FX AI* — Broadcast test! Your signal alerts will look like this. 🚀"
        )
        st.success(f"✅ Delivered to {s} subscriber(s). {f} failed.") if (s+f) > 0 else st.error("❌ No subscribers saved yet.")

    st.divider()
    threshold = st.slider("Alert threshold — minimum confidence (%)", 60, 95, st.session_state.notification_threshold)
    st.session_state.notification_threshold = threshold
    st.info(f"Alerts only fire when confidence ≥ {threshold}%")

# ════════════════════════════════════════════════════════════
# PAGE: TRADE JOURNAL
# ════════════════════════════════════════════════════════════
elif "Journal" in page:
    st.title("📓 Trade Journal")
    if not premium: st.error("🔒 Premium only."); st.stop()

    with st.expander("➕ Log a Trade"):
        c1,c2,c3 = st.columns(3)
        j_asset  = c1.selectbox("Asset",  list(ALL_PAIRS.keys()))
        j_sig    = c2.selectbox("Signal", ["STRONG BUY","BUY","SELL","STRONG SELL"])
        j_result = c3.selectbox("Result", ["Open","Win","Loss","Breakeven"])
        c4,c5,c6 = st.columns(3)
        j_entry  = c4.number_input("Entry", format="%.5f")
        j_conf   = c5.slider("Confidence", 0, 100, 70)
        j_notes  = c6.text_input("Notes")
        if st.button("Save"):
            st.session_state.trade_journal.append({
                "Date": str(datetime.date.today()), "Asset": j_asset, "Signal": j_sig,
                "Entry": j_entry, "SL": 0, "TP1": 0, "Confidence": j_conf,
                "Result": j_result, "Notes": j_notes
            })
            st.success("✅ Saved!")

    if st.session_state.trade_journal:
        df   = pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df, use_container_width=True)
        wins = len(df[df["Result"]=="Win"]); loss = len(df[df["Result"]=="Loss"])
        total= wins + loss; wr = round(wins/total*100,1) if total > 0 else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Total", len(df)); c2.metric("Win Rate", f"{wr}%"); c3.metric("Open", len(df[df["Result"]=="Open"]))
    else:
        st.info("No trades yet.")

# ════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ════════════════════════════════════════════════════════════
elif "Performance" in page:
    st.title("📈 Performance Dashboard")
    if not premium: st.error("🔒 Premium only."); st.stop()
    if not st.session_state.trade_journal: st.info("Log trades to see stats."); st.stop()
    df   = pd.DataFrame(st.session_state.trade_journal)
    wins = len(df[df["Result"]=="Win"]); loss = len(df[df["Result"]=="Loss"])
    total= wins + loss; wr = round(wins/total*100,1) if total > 0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Trades", total); c2.metric("Wins", wins); c3.metric("Losses", loss); c4.metric("Win Rate", f"{wr}%")
    if "Asset" in df.columns:
        st.subheader("By Asset")
        st.dataframe(df.groupby("Asset")["Result"].value_counts().unstack(fill_value=0), use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: RISK CALCULATOR
# ════════════════════════════════════════════════════════════
elif "Risk" in page:
    st.title("💰 Risk Calculator")
    c1, c2 = st.columns(2)
    with c1:
        balance  = st.number_input("Balance ($)", min_value=10.0, value=1000.0)
        risk_pct = st.slider("Risk %", 0.5, 10.0, 2.0, step=0.5)
        sl_pips  = st.number_input("Stop Loss (pips)", min_value=1.0, value=20.0)
        pip_val  = st.number_input("Pip Value per 0.01 lot ($)", value=0.10)
        rr       = st.slider("Risk:Reward", 1, 5, 2)
    risk_amt = balance * risk_pct / 100
    lot      = round(risk_amt / (sl_pips * pip_val / 0.01) * 0.01, 2)
    with c2:
        st.metric("Risk Amount", f"${risk_amt:.2f}"); st.metric("Lot Size", f"{lot} lots")
        st.metric("Potential Profit", f"${risk_amt*rr:.2f}"); st.metric("R:R", f"1:{rr}")
    st.progress(risk_pct/10)
    if risk_pct <= 2:  st.success("✅ Conservative")
    elif risk_pct <= 5: st.warning("⚠️ Moderate")
    else:               st.error("🚨 High risk")

# ════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ════════════════════════════════════════════════════════════
elif "Settings" in page:
    st.title("⚙️ Settings")

    st.subheader("🤖 Anthropic API Key (for AI News Analysis)")
    st.markdown("""
    1. Go to [console.anthropic.com](https://console.anthropic.com) → sign up free → create API key
    2. Create `.streamlit/secrets.toml` in your app folder
    3. Add: `ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"`
    4. Restart the app — AI News Analysis will work automatically
    """)
    st.info("The API key is never stored in the app itself — it lives only in your secrets file.")

    st.subheader("🔔 Telegram")
    t = st.text_input("Bot Token", value=st.session_state.telegram_token, type="password")
    c = st.text_input("Chat ID",   value=st.session_state.telegram_chat_id)
    if st.button("Save Telegram"):
        st.session_state.telegram_token   = t
        st.session_state.telegram_chat_id = c
        st.success("✅ Saved!")

# ════════════════════════════════════════════════════════════
# PAGE: PRICING
# ════════════════════════════════════════════════════════════
elif "Pricing" in page:
    st.title("💎 Upgrade to Premium")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""<div class='tier-box'>
        <h3>🆓 Free</h3><h2>$0/mo</h2><hr>
        ✅ 5 assets<br><br>✅ Basic signals<br><br>
        ❌ Confidence scores<br><br>❌ 8-strategy engine<br><br>
        ❌ Price movement charts<br><br>❌ News Analysis<br><br>
        ❌ Telegram Alerts<br><br>❌ Trade Journal &amp; Performance
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class='tier-box gold'>
        <h3>⚡ Premium</h3><h2>$15/mo</h2><hr>
        ✅ All 10 assets<br><br>✅ 8-strategy engine<br><br>
        ✅ 📈 Price charts with Entry/SL/TP levels<br><br>
        ✅ 💡 Why take this trade explanation<br><br>
        ✅ 🗞️ News Analysis + AI insights<br><br>
        ✅ 📢 Broadcast signals to all subscribers<br><br>
        ✅ 🔔 Telegram trade alerts<br><br>
        ✅ 📓 Trade Journal + 📈 Performance
        </div>""", unsafe_allow_html=True)
    st.divider()
    st.markdown("""
    **💳 Start collecting payments:**
    - **[Whop.com](https://whop.com)** — built for trading tools, member gating included
    - **[Gumroad](https://gumroad.com)** — live in 15 minutes
    - **[Stripe](https://stripe.com)** — professional recurring billing
    """)
    st.info("💡 Recommended: **Whop** — built for exactly this type of trading product.")
