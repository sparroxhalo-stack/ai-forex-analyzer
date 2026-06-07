import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="AI Forex Analyzer Pro", layout="wide")

st.title("📈 AI Forex Analyzer Pro")

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
            return "NO DATA"

        close = data.iloc[:, 0]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        if ema20 > ema50:
            return "BUY"
        else:
            return "SELL"

    except:
        return "ERROR"


daily_signal = get_signal(symbol, "6mo")
swing_signal = get_signal(symbol, "1y")
trend_signal = get_signal(symbol, "2y")

buy_count = [daily_signal, swing_signal, trend_signal].count("BUY")
sell_count = [daily_signal, swing_signal, trend_signal].count("SELL")

if buy_count == 3:
    final_signal = "STRONG BUY"
    confidence = 95

elif sell_count == 3:
    final_signal = "STRONG SELL"
    confidence = 95

elif buy_count >= 2:
    final_signal = "BUY"
    confidence = 75

elif sell_count >= 2:
    final_signal = "SELL"
    confidence = 75

else:
    final_signal = "WAIT"
    confidence = 50


st.subheader("Current Analysis")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Daily", daily_signal)

with col2:
    st.metric("Swing", swing_signal)

with col3:
    st.metric("Trend", trend_signal)

st.divider()

st.header(final_signal)

st.progress(confidence / 100)

st.write(f"Confidence: {confidence}%")

if "BUY" in final_signal:
    st.success("Bullish Market Structure")

elif "SELL" in final_signal:
    st.error("Bearish Market Structure")

st.divider()

st.subheader("Market Scanner")

results = []

for pair_name, pair_symbol in pairs.items():

    d = get_signal(pair_symbol, "6mo")
    s = get_signal(pair_symbol, "1y")
    t = get_signal(pair_symbol, "2y")

    buys = [d, s, t].count("BUY")
    sells = [d, s, t].count("SELL")

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

st.dataframe(
    scanner,
    use_container_width=True
)

st.divider()

st.subheader("Risk Calculator")

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

st.info(
    "Use Daily for day trading. Use Swing + Trend alignment for swing trades."
)
