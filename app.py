import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 核心邏輯：派息月份、除淨日與倒數 ---
def get_div_analysis(symbol, divs):
    if divs.empty:
        return [], "N/A", 999
    
    # 預測月份
    months = sorted(list(set(divs.index.month[-4:])))
    
    # 計算倒數 (邏輯：參考去年同期的除淨日)
    today = datetime.date.today()
    try:
        # 尋找去年此時之後最接近的派息紀錄
        last_year_date = today - datetime.timedelta(days=350)
        past_divs = divs[divs.index.date >= last_year_date]
        
        if not past_divs.empty:
            # 預測下一次：去年日期 + 365天
            est_next_date = past_divs.index[0].date() + datetime.timedelta(days=365)
            countdown = (est_next_date - today).days
            return months, est_next_date.strftime('%Y-%m-%d'), countdown
    except:
        pass
    return months, "確認中", 999

# --- 2. 核心數據掃描器 ---
def scan_stock(symbol, budget, is_hk=True):
    try:
        tk = yf.Ticker(symbol)
        # 使用 fast_info 避免系統崩潰
        price = tk.fast_info.get('last_price')
        if price is None or price <= 0: return None
        
        info = tk.info
        divs = tk.dividends
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        
        # 港股一手股數定義
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, "0700.HK": 100, 
                   "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0003.HK": 1000, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        
        # 成本與預算 (5萬元實戰)
        one_lot_hkd = price * lot_size
        if budget >= one_lot_hkd:
            max_lots = int(budget // one_lot_hkd)
            strategy = f"✅ 買 {max_lots} 手"
            rem_cash = budget - (max_lots * one_lot_hkd)
            est_income = (div_rate) * (max_lots * lot_size)
        else:
            strategy = f"❌ 缺 ${one_lot_hkd - budget:,.0f}"
            rem_cash = budget
            est_income = 0
            
        # 派息分析
        months, next_ex_date, countdown = get_div_analysis(symbol, divs)
        
        # 倒數警告標籤
        if countdown < 0: countdown_label = "已過期"
        elif countdown <= 21: countdown_label = f"🔥 僅剩 {countdown}天"
        else: countdown_label = f"{countdown}天"

        # 估值 (💎特價判斷)
        avg_yield = info.get('fiveYearAvgDividendYield', 0) / 100.0
        target_price = div_rate / (avg_yield * 1.05) if avg_yield > 0 else 0
        val_status = "💎 特價" if target_price > 0 and price <= target_price else "⚠️ 溢價"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "估值": val_status,
            "除淨倒數": countdown_label,
            "實戰策略": strategy,
            "一手成本": f"${one_lot_hkd:,.0f}",
            "剩餘現金": f"${rem_cash:,.0f}",
            "預計年息": f"${est_income:,.0f}",
            "股息率%": round((div_rate/price)*100, 2),
            "預估下回": next_ex_date,
            "months": months
        }
    except: return None

# --- UI 介面 ---
st.title("🛡️ 全球收息終極戰情室 (全功能修復版)")

with st.sidebar:
    st.header("💰 實戰預算")
    budget = st.number_input("本金 (HKD):", value=50000)
    st.divider()
    st.write("**💎 特價**：現價 < 目標價 (5年平均)")
    st.write("**🔥 倒數**：21天內除淨，請儘速決策")

STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0003.HK", "0823.HK"]

if st.button("🚀 執行全方位掃描 (恢復所有功能)"):
    results = []
    bar = st.progress(0)
    for i, s in enumerate(STOCKS):
        data = scan_stock(s, budget)
        if data: results.append(data)
        bar.progress((i+1)/len(STOCKS))
    
    if results:
        df = pd.DataFrame(results)
        
        # 1. 1-12月月份表
        st.subheader("🗓️ 1-12月 派息預期表")
        m_rows = []
        for _, r in df.iterrows():
            m_data = [""] * 12
            for m in r['months']: m_data[m-1] = "💰"
            m_rows.append([r['公司']] + m_data)
        st.table(pd.DataFrame(m_rows, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

        # 2. 實戰清單 (包含所有重要指標)
        st.subheader("📊 實戰策略分析清單")
        st.dataframe(df.drop(columns=["months"]), use_container_width=True, hide_index=True)

st.divider()
st.subheader("🔍 個股深度溯源 (含 0700.HK)")
search = st.text_input("輸入代碼 (例: 0700.HK):").strip().upper()
if search:
    tk = yf.Ticker(search)
    try:
        st.write(f"### {search} 歷史派息紀錄")
        st.write(tk.dividends.tail(10).sort_index(ascending=False))
    except: st.error("查無紀錄")
