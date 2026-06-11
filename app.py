import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Sparro FX AI",
    layout="wide"
)

st.title("🚀 Sparro FX AI")

st.caption(
    "AI-Powered Forex, Gold, Crypto & Index Analysis"
)
st.divider()

st.subheader("📊 Market Overview")

st.info(
    "Professional AI market scanner for Forex, Gold, Crypto and Indices."
)

st.divider()

pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CHF": "USDCHF=X",
    "USD/CAD": "USDCAD=X",
    "Gold (XAU/USD)": "GC=F",
    "Bitcoin": "BTC-USD",
    "NASDAQ": "^IXIC",
    "S&P 500": "^GSPC"
}

selected_pair = st.selectbox(
    "Select Asset",
    list(pairs.keys())
)

symbol = pairs[selected_pair]


def get_signal(symbol, period="6mo"):
    try:
        data = yf.download(
            symbol,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if data.empty:
            return "WAIT"

        close = data.iloc[:, 0]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        ema200 = close.ewm(span=200).mean().iloc[-1]

        delta = close.diff()

        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

        rs = gain / loss

        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        if (
            ema20 > ema50 and
            ema50 > ema200 and
            rsi > 55
        ):
            return "STRONG BUY"

        elif (
            ema20 < ema50 and
            ema50 < ema200 and
            rsi < 45
        ):
            return "STRONG SELL"

        elif ema20 > ema50:
            return "BUY"

        elif ema20 < ema50:
            return "SELL"

        else:
            return "WAIT"

    except:
        return "ERROR"

daily_signal = get_signal(symbol, "6mo")
swing_signal = get_signal(symbol, "1y")
trend_signal = get_signal(symbol, "2y")

st.subheader("Current Analysis")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Daily", daily_signal)

with col2:
    st.metric("Swing", swing_signal)

with col3:
    st.metric("Trend", trend_signal)

st.divider()

if "BUY" in final_signal:
    st.success(f"🚀 {final_signal}")

elif "SELL" in final_signal:
    st.error(f"📉 {final_signal}")

else:
    st.warning("⏳ WAIT")

st.progress(confidence / 100)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Signal", final_signal)

with col2:
    st.metric("Confidence", f"{confidence}%")

with col3:
    st.metric("Asset", selected_pair)

st.write(f"Confidence: {confidence}%")

if "BUY" in final_signal:
    st.success("Bullish Market Structure")

elif "SELL" in final_signal:
    st.error("Bearish Market Structure")

st.divider()

st.subheader("🔥 Top Market Opportunities")

results = []

results = []

for pair_name, pair_symbol in pairs.items():

    d = get_signal(pair_symbol, "6mo")
    s = get_signal(pair_symbol, "1y")
    t = get_signal(pair_symbol, "2y")

    buys = sum(
        1 for x in [d, s, t]
        if "BUY" in x
    )

    sells = sum(
        1 for x in [d, s, t]
        if "SELL" in x
    )

    if buys == 3:
        signal = "STRONG BUY"
        score = 95

    elif sells == 3:
        signal = "STRONG SELL"
        score = 95

    elif buys >= 2:
        signal = "BUY"
        score = 75

    elif sells >= 2:
        signal = "SELL"
        score = 75

    else:
        signal = "WAIT"
        score = 50

    results.append(
        {
            "Asset": pair_name,
            "Signal": signal,
            "Score": score
        }
    )

scanner = pd.DataFrame(results)

scanner = scanner.sort_values(
    by="Score",
    ascending=False
)

top_buys = scanner[
    scanner["Signal"].str.contains("BUY", na=False)
].head(3)

top_sells = scanner[
    scanner["Signal"].str.contains("SELL", na=False)
].head(3)

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚀 Top Buys")
    st.dataframe(top_buys, use_container_width=True)

with col2:
    st.subheader("📉 Top Sells")
    st.dataframe(top_sells, use_container_width=True)

st.subheader("📊 Full Market Scanner")

st.dataframe(
    scanner,
    use_container_width=True
)
st.divider()

st.subheader("💰 Risk Management")

balance = st.number_input(
    "Account Balance ($)",
    min_value=10.0,
    value=100.0
)

risk_percent = st.slider(
    "Risk Per Trade (%)",
    1,
    10,
    2
)

risk_amount = balance * risk_percent / 100

st.write(f"Risk Amount: ${risk_amount:.2f}")

if risk_amount <= 5:
    lot_size = 0.01
elif risk_amount <= 20:
    lot_size = 0.02
elif risk_amount <= 50:
    lot_size = 0.05
else:
    lot_size = 0.10

st.write(f"Suggested Lot Size: {lot_size}")

st.divider()

st.subheader("Trade Setup")

try:
    data = yf.download(
        symbol,
        period="3mo",
        interval="1d",
        progress=False,
        auto_adjust=True
    )

    close = data.iloc[:, 0]
    current_price = float(close.iloc[-1])

    high = data.iloc[:, 1]
    low = data.iloc[:, 2]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(14).mean().iloc[-1]

    risk = atr * 1.5

    if "BUY" in final_signal:

        sl = current_price - risk

        tp1 = current_price + risk
        tp2 = current_price + (risk * 2)
        tp3 = current_price + (risk * 3)

    else:

        sl = current_price + risk

        tp1 = current_price - risk
        tp2 = current_price - (risk * 2)
        tp3 = current_price - (risk * 3)

    st.write(f"Current Price: {current_price:.5f}")
    st.write(f"Stop Loss: {sl:.5f}")
    st.write(f"TP1: {tp1:.5f}")
    st.write(f"TP2: {tp2:.5f}")
    st.write(f"TP3: {tp3:.5f}")

except:
    st.warning("Trade setup unavailable")
st.info(
    "Use Daily for day trading. Use Swing + Trend alignment for swing trades."
)
