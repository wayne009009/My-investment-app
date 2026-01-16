import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 核心邏輯：預測派息月份與除淨倒數 ---
def get_dividend_info(symbol):
    try:
        tk = yf.Ticker(symbol)
        divs = tk.dividends
        if divs.empty:
            return [], "N/A", 999
        
        # 預測月份
        recent_months = sorted(list(set(divs.index.month[-4:])))
        
        # 尋找最近或下一個除淨日
        last_ex_date = divs.index[-1].date()
        today = datetime.date.today()
        
        # 估計下一次除淨日 (簡單邏輯：去年同期的除淨日)
        # 找到去年最近一次派息大約在什麼時候
        target_date_last_year = today - datetime.timedelta(days=365)
        upcoming_divs = divs[divs.index.date >= target_date_last_year]
        
        if not upcoming_divs.empty:
            # 找去年最接近今天的日期，推算今年
            next_est_date = upcoming_divs.index[0].date() + datetime.timedelta(days=365)
            countdown = (next_est_date - today).days
            return recent_months, next_est_date.strftime('%Y-%m-%d'), countdown
        else:
            return recent_months, "確認中", 999
    except:
        return [], "N/A", 999

# --- 2. 數據分析引擎 ---
def get_comprehensive_data(symbol, budget, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        price = tk.fast_info.get('last_price')
        if price is None or price == 0: return None

        info = tk.info
        divs = tk.dividends
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        exch_rate = 1.0 if is_hk else 7.8
        
        # 一手股數定義
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
                   "0700.HK": 100, "1398.HK": 1000, "0011.HK": 100, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        cost_hkd = price * exch_rate * lot_size
        
        # 預算策略
        strategy = f"✅ 買 {int(budget // cost_hkd)} 手" if budget >= cost_hkd else f"❌ 缺 ${cost_hkd - budget:,.0f}"
        
        # 獲取除淨日與倒數
        months, next_date, countdown = get_dividend_info(symbol)
        
        # 倒數說明
        if countdown < 0: countdown_str = "已過除淨日"
        elif countdown <= 14: countdown_str = f"🔥 僅剩 {countdown} 天"
        else: countdown_str = f"{countdown} 天"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "除淨日倒數": countdown_str,
            "預估下個除淨": next_date,
            "實戰策略": strategy,
            "一手成本": f"${cost_hkd:,.0f}",
            "估值": "💎 特價" if (info.get('fiveYearAvgDividendYield', 0)/100.0) > 0 and price <= (div_rate / (info.get('fiveYearAvgDividendYield', 0)/100.0 * 1.05)) else "⚠️ 溢價",
            "股息率%": round((div_rate/price)*100, 2),
            "派息月份": months
        }
    except: return None

# --- UI 介面 ---
st.title("🛡️ 5萬元收息：發錢倒數計時戰情室")

with st.sidebar:
    st.header("💰 本金設定")
    user_budget = st.number_input("您的投資本金 (HKD):", value=50000)
    st.info("💡 **除淨日倒數**：顯示距離下次收息資格還有幾天。若是『🔥 僅剩 14 天內』，代表您需盡快決定。")

TARGET_STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "0011.HK", "0823.HK"]

if st.button("🚀 啟動全方位掃描 (含倒數計時)"):
    results = []
    progress = st.progress(0)
    for i, s in enumerate(TARGET_STOCKS):
        data = get_comprehensive_data(s, user_budget, True)
        if data: results.append(data)
        progress.progress((i+1)/len(TARGET_STOCKS))

    if results:
        df = pd.DataFrame(results)
        
        # --- 顯示倒數關鍵表 ---
        st.subheader("⏰ 下一次派息資格倒數")
        st.dataframe(
            df[["代碼", "公司", "除淨日倒數", "預估下個除淨", "實戰策略", "估值"]],
            use_container_width=True, hide_index=True
        )

        # --- 1-12月月份表 ---
        st.subheader("🗓️ 全年派息月份預測")
        month_data = []
        for _, row in df.iterrows():
            m_list = [""] * 12
            for m in row['派息月份']: m_list[m-1] = "💰"
            month_data.append([row['公司']] + m_list)
        st.table(pd.DataFrame(month_data, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

st.divider()
st.subheader("🔍 個股深度查詢")
search = st.text_input("輸入代碼 (例 0005.HK):").strip().upper()
if search:
    tk = yf.Ticker(search)
    st.write(tk.dividends.tail(10).sort_index(ascending=False))
