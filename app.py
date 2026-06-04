import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="AI Forex Analyzer", layout="wide")

st.title("📈 AI Forex Analyzer")

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CHF": "USDCHF=X",
    "USD/CAD": "USDCAD=X",
    "Gold (XAU/USD)": "GC=F"
}

pair = st.selectbox("Select Pair", list(PAIRS.keys()))
symbol = PAIRS[pair]


def get_signal(symbol):
    try:
        data = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if data.empty:
            return "NO DATA"

        close = data["Close"]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        if ema20 > ema50:
            return "BUY"
        else:
            return "SELL"

    except Exception as e:
    st.error(str(e))
    return "ERROR"


signal = get_signal(symbol)

st.subheader("Current Signal")

if signal == "BUY":
    st.success("BUY")

elif signal == "SELL":
    st.error("SELL")

else:
    st.warning(signal)

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

st.divider()

st.subheader("Market Scanner")

results = []

for name, sym in PAIRS.items():

    sig = get_signal(sym)

    results.append({
        "Pair": name,
        "Signal": sig
    })

scanner = pd.DataFrame(results)

st.dataframe(
    scanner,
    use_container_width=True
)

st.info(
    "This version uses a simple EMA20 vs EMA50 trend system."
)
