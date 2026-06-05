import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="AI Forex Analyzer", layout="wide")

st.title("📈 AI Forex Analyzer")

pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CHF": "USDCHF=X",
    "USD/CAD": "USDCAD=X",
    "Gold (XAU/USD)": "GC=F"
}

selected_pair = st.selectbox(
    "Select Pair",
    list(pairs.keys())
)

symbol = pairs[selected_pair]


def get_signal(symbol):
    try:
        data = yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if data.empty:
            return "NO DATA"

        if "Close" not in data.columns:
            return "NO DATA"

        close = data["Close"]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        if ema20 > ema50:
            return "BUY"
        else:
            return "SELL"

    except Exception as e:
        return f"ERROR"


signal = get_signal(symbol)

st.subheader("Current Signal")
st.write(signal)

st.divider()

st.subheader("Risk Calculator")

balance = st.number_input(
    "Account Balance ($)",
    min_value=10.0,
    value=100.0
)

risk_percent = st.slider(
    "Risk Per Trade (%)",
    min_value=1,
    max_value=10,
    value=2
)

risk_amount = balance * risk_percent / 100

st.write(f"Risk Amount: ${risk_amount:.2f}")

st.divider()

st.subheader("Market Scanner")

results = []

for pair_name, pair_symbol in pairs.items():
    sig = get_signal(pair_symbol)

    results.append({
        "Pair": pair_name,
        "Signal": sig
    })

scanner_df = pd.DataFrame(results)

st.dataframe(
    scanner_df,
    use_container_width=True
)

st.info(
    "Simple EMA20 vs EMA50 trend scanner."
)
