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

        # Handle Yahoo multi-index columns
        close = data.iloc[:, 0]

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
st.header(signal)

st.divider()

st.subheader("Market Scanner")

results = []

for pair_name, pair_symbol in pairs.items():

    sig = get_signal(pair_symbol)

    results.append({
        "Pair": pair_name,
        "Signal": sig
    })

scanner = pd.DataFrame(results)

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
