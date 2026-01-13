import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Conservative Investor Tool", layout="wide")

st.title("📈 Stable Income Investor Dashboard")
st.write("Monitor HK & US stocks, calculate fees, and check dividend stability.")

# Sidebar for Input
st.sidebar.header("Search Settings")
ticker_input = st.sidebar.text_input("Enter Ticker (e.g., 0005.HK, 2800.HK, SCHD, O):", "0005.HK")
broker_fee_rate = st.sidebar.number_input("Broker Commission % (e.g., 0.03)", value=0.03, format="%.3f") / 100

# Fetch Data
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 我們檢查一下是否真的抓到了價格，來確認代碼有效
        if ticker.info.get('currentPrice'):
            return ticker
        return None
    except:
        return None

tk = get_data(ticker_input)

if tk and tk.info.get('currentPrice'):
    info = tk.info
    curr = info.get('currency', 'USD')
    price = info.get('currentPrice')
    
    # Layout Columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Price", f"{price} {curr}")
        st.write(f"**Company:** {info.get('longName')}")

    with col2:
        div_yield = info.get('dividendYield', 0) * 100
        st.metric("Dividend Yield", f"{div_yield:.2f}%")
        st.write(f"**Payout Frequency:** {info.get('dividendRate', 0)} per share")

    with col3:
        # Minimum Investment Logic
        # HK stocks usually have lot sizes, US is 1 share
        lot_size = info.get('sharesPerLot', 1) if ".HK" in ticker_input else 1
        min_invest = lot_size * price
        st.metric("Min. Entry Amount", f"{min_invest:,.2f} {curr}")
        st.caption(f"Based on {lot_size} share(s) per lot")

    st.divider()

    # Fee Calculator
    st.subheader("📊 Transaction & Holding Fee Estimator")
    buy_shares = st.number_input("Number of shares to buy:", min_value=int(lot_size), step=int(lot_size))
    total_value = buy_shares * price

    if ".HK" in ticker_input:
        stamp_duty = total_value * 0.001 # 0.1% Stamp Duty
        trading_fee = total_value * 0.0000565 # Approx HKEX fees
        est_total_fee = stamp_duty + trading_fee + (total_value * broker_fee_rate)
        
        st.write(f"**Estimated Buy Fees:** {est_total_fee:.2f} HKD")
        st.info("Note: HK dividends may incur 'Scrip Dividend' or 'Collection Fees' by your broker (usually ~$30 HKD).")
    else:
        withholding_tax = div_yield * 0.30
        st.write(f"**US Dividend Tax:** ~30% withholding tax applies to your dividends.")
        st.write(f"**Estimated Buy Fees:** {(total_value * broker_fee_rate):.2f} USD (plus platform fixed fees)")

    # News/Announcements
    st.subheader("🔔 Recent Announcements")
    news = tk.news[:5]
    for item in news:
        st.write(f"**[{item['title']}]({item['link']})**")

else:
    st.error("Ticker not found. Please use '.HK' for Hong Kong stocks (e.g., 0005.HK) and symbols like 'AAPL' for US.")
