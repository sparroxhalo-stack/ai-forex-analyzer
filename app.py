import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="AI Forex Analyzer", layout="wide")

st.title("📈 AI Forex Analyzer Pro")

pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CHF": "USDCHF=X",
    "USD/CAD": "USDCAD=X",
    "EUR/GBP": "EURGBP=X"
}

selected_pair = st.selectbox("Select Forex Pair", list(pairs.keys()))
symbol = pairs[selected_pair]


def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def analyze_timeframe(symbol, interval):

    try:
        data = yf.download(
            symbol,
            period="90d",
            interval=interval,
            progress=False,
            auto_adjust=True
        )

        if len(data) < 60:
            return "WAIT", 50

        close = data["Close"]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        rsi = calculate_rsi(close).iloc[-1]

        if ema20 > ema50 and rsi > 55:
            signal = "BUY"

        elif ema20 < ema50 and rsi < 45:
            signal = "SELL"

        else:
            signal = "WAIT"

        return signal, round(float(rsi), 2)

    except:
        return "WAIT", 50


st.subheader("Multi-Timeframe Analysis")

col1, col2, col3 = st.columns(3)

h1_signal, h1_rsi = analyze_timeframe(symbol, "1h")
h4_signal, h4_rsi = analyze_timeframe(symbol, "4h")
d1_signal, d1_rsi = analyze_timeframe(symbol, "1d")

with col1:
    st.metric("1 Hour", h1_signal)
    st.write(f"RSI: {h1_rsi}")

with col2:
    st.metric("4 Hour", h4_signal)
    st.write(f"RSI: {h4_rsi}")

with col3:
    st.metric("Daily", d1_signal)
    st.write(f"RSI: {d1_rsi}")

buy_count = [h1_signal, h4_signal, d1_signal].count("BUY")
sell_count = [h1_signal, h4_signal, d1_signal].count("SELL")

if buy_count == 3:
    final_signal = "🔥 STRONG BUY"
    confidence = 95

elif sell_count == 3:
    final_signal = "🔥 STRONG SELL"
    confidence = 95

elif buy_count >= 2:
    final_signal = "✅ BUY"
    confidence = 75

elif sell_count >= 2:
    final_signal = "✅ SELL"
    confidence = 75

else:
    final_signal = "⏳ WAIT"
    confidence = 50

st.divider()

st.header(final_signal)
st.progress(confidence / 100)
st.write(f"Confidence: {confidence}%")

st.divider()

st.subheader("Risk Management")

balance = st.number_input(
    "Account Balance ($)",
    min_value=10.0,
    value=100.0
)

risk_percent = st.slider(
    "Risk Per Trade (%)",
    1,
    10,
    5
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

st.info(
    "Use the Daily trend for swing trading and the 1H + 4H trend alignment for day trading."
)
