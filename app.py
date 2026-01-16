import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 核心邏輯：1年數據分析引擎 ---
@st.cache_data(ttl=600) # 緩存10分鐘，避免頻繁請求導致封鎖
def get_clean_data(symbol, budget):
    try:
        tk = yf.Ticker(symbol)
        # 僅獲取最核心的快照數據
        fast = tk.fast_info
        price = fast.get('last_price')
        if not price or price <= 0: return None
        
        # 抓取 1 年內的派息紀錄 (366天以確保涵蓋年配)
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=366)
        divs = tk.dividends[tk.dividends.index.date >= start_date]
        
        # 估算年化股息 (若1年內無派息，則嘗試抓取 info 的數據)
        info = tk.info
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        
        # A. 1-12月派息月份 (💰)
        months = sorted(list(set(divs.index.month))) if not divs.empty else []
        
        # B. 除淨倒數 (🔥)
        countdown_label = "確認中"
        if not divs.empty:
            # 預測：去年除淨日 + 365天
            last_ex = divs.index[-1].date()
            est_next = last_ex + datetime.timedelta(days=365)
            diff = (est_next - today).days
            if diff < 0: countdown_label = "已過除淨"
            elif diff <= 21: countdown_label = f"🔥 {diff}天"
            else: countdown_label = f"{diff}天"

        # C. 5萬預算策略
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
                   "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100)
        cost_per_lot = price * lot_size
        
        if budget >= cost_per_lot:
            lots = int(budget // cost_per_lot)
            strategy = f"✅ 買 {lots} 手"
            rem_cash = budget - (lots * cost_per_lot)
            est_income = div_rate * lots * lot_size
        else:
            strategy = f"❌ 缺 ${cost_per_lot - budget:,.0f}"
            rem_cash = budget
            est_income = 0

        # D. 估值狀態 (💎)
        avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "策略": strategy,
            "估值": val,
            "倒數": countdown_label,
            "股息率%": round((div_rate/price)*100, 2) if price > 0 else 0,
            "一手成本": f"${cost_per_lot:,.0f}",
            "剩餘現金": f"${rem_cash:,.0f}",
            "年息預期": f"${est_income:,.0f}",
            "months": months,
            "history": divs
        }
    except: return None

# --- UI 佈局 ---
st.title("🛡️ 收息戰情室 (1年數據+穩定修復版)")

with st.sidebar:
    st.header("💰 本金")
    budget = st.number_input("HKD:", value=50000)
    if st.button("🔄 清除緩存"):
        st.cache_data.clear()
        st.rerun()

STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

# --- 自動執行掃描 ---
results = []
for s in STOCKS:
    data = get_clean_data(s, budget)
    if data: results.append(data)

if results:
    df = pd.DataFrame(results)
    
    # 功能 1: 1-12月月份表
    st.subheader("🗓️ 1-12月 派息月份預測")
    m_data = []
    for _, r in df.iterrows():
        row = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
        m_data.append(row)
    st.table(pd.DataFrame(m_data, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

    # 功能 2: 綜合分析大表
    st.subheader("📊 5萬預算實戰策略")
    display_cols = ["代碼", "公司", "策略", "估值", "倒數", "股息率%", "一手成本", "剩餘現金", "年息預期"]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

st.divider()

# 功能 3: 深度溯源 (1年紀錄)
st.subheader("🔍 個股 1 年派息紀錄溯源")
search = st.text_input("輸入代碼 (例: 0700.HK):").strip().upper()
if search:
    res = get_clean_data(search, budget)
    if res:
        st.write(f"### {search} 近 1 年紀錄")
        st.write(res['history'].sort_index(ascending=False))
    else:
        st.error("查無資料，請確認代碼含 .HK")
