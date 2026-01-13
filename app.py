import streamlit as st
import yfinance as yf
import pandas as pd

# 頁面基本設定
st.set_page_config(page_title="穩定收入投資工具", layout="wide")

st.title("📈 穩定收入投資者儀表板")
st.write("監控港股及美股，計算手續費並檢查派息穩定性。")

# 側邊欄設定
st.sidebar.header("搜尋設定")
ticker_input = st.sidebar.text_input("輸入股票代號 (例如: 0005.HK, 2800.HK, AAPL, SCHD):", "0005.HK").upper()
broker_fee_rate = st.sidebar.number_input("券商佣金百分比 % (例如: 0.03)", value=0.03, format="%.3f") / 100

# 抓取資料的函式 (已移除會報錯的 cache)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 嘗試抓取 currentPrice 來驗證資料是否存在
        if ticker.info and 'currentPrice' in ticker.info:
            return ticker
        return None
    except:
        return None

# 執行抓取
tk = get_stock_data(ticker_input)

if tk:
    info = tk.info
    curr = info.get('currency', 'USD')
    price = info.get('currentPrice')
    
    # 建立三欄佈局顯示基本資訊
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("當前股價", f"{price} {curr}")
        st.write(f"**公司名稱:** {info.get('longName', '未知')}")

    with col2:
        # 計算股息率
        div_yield = info.get('dividendYield', 0) * 100
        st.metric("股息率 (Yield)", f"{div_yield:.2f}%")
        st.write(f"**每股派息:** {info.get('dividendRate', 0)} {curr}")

    with col3:
        # 每手股數 (港股特有，美股預設為 1)
        lot_size = info.get('sharesPerLot', 1) if ".HK" in ticker_input else 1
        min_invest = lot_size * price
        st.metric("最低入場費", f"{min_invest:,.2f} {curr}")
        st.caption(f"基於每手 {lot_size} 股計算")

    st.divider()

    # 手續費計算器
    st.subheader("📊 交易及持倉成本估算")
    buy_shares = st.number_input("預計買入股數:", min_value=int(lot_size), step=int(lot_size), value=int(lot_size))
    total_value = buy_shares * price

    calc_col1, calc_col2 = st.columns(2)
    
    with calc_col1:
        st.write(f"**總成交金額:** {total_value:,.2f} {curr}")
        if ".HK" in ticker_input:
            stamp_duty = total_value * 0.001  # 印花稅 0.1%
            trading_fee = total_value * 0.0000565 # 交易費
            broker_comm = total_value * broker_fee_rate
            total_fee = stamp_duty + trading_fee + broker_comm
            st.write(f"🔹 估計買入手續費: {total_fee:.2f} HKD")
            st.caption("(含印花稅、證監會徵費及券商佣金)")
        else:
            broker_comm = total_value * broker_fee_rate
            st.write(f"🔹 估計買入手續費: {broker_comm:.2f} USD")
            st.warning("⚠️ 注意：美股股息對香港居民通常有 30% 的代扣稅。")

    # 顯示最新公告/新聞
    st.subheader("🔔 相關新聞與公告")
    try:
        news = tk.news[:5]
        for item in news:
            st.write(f"• [{item['title']}]({item['link']})")
    except:
        st.write("暫時無法取得新聞。")

else:
    st.error("找不到該股票代號。提示：港股請加 '.HK' (如 0005.HK)，美股請直接輸入 (如 AAPL)。")
