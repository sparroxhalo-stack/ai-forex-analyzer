import streamlit as st
import yfinance as yf

st.title("Yahoo Finance Test")

try:
    data = yf.download(
        "EURUSD=X",
        period="1mo",
        progress=False
    )

    st.write("Data downloaded successfully")
    st.write(data.tail())

except Exception as e:
    st.error(str(e))
