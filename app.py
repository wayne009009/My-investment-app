import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 定義一手股數 (港股核心資料) ---
LOT_MAP = {
    "0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
    "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100
}

# --- 2. 核心引擎：1年數據分析 ---
@st.cache_data(ttl=600)
def get_full_analysis(symbol, budget):
    try:
        tk = yf.Ticker(symbol)
        fast = tk.fast_info
        price = fast.get('last_price')
        if not price or price <= 0: return None
        
        # A. 抓取 1 年內的派息紀錄 (確保 0700.HK 年配息能抓到)
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=366)
        divs = tk.dividends[tk.dividends.index.date >= start_date]
        
        info = tk.info
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        
        # B. 12個月派息預測 (💰)
        months = sorted(list(set(divs.index.month))) if not divs.empty else []
        
        # C. 發錢倒數計時 (🔥)
        countdown_label = "確認中"
        next_ex_est = "N/A"
        if not divs.empty:
            last_ex = divs.index[-1].date()
            est_next = last_ex + datetime.timedelta(days=365)
            diff = (est_next - today).days
            next_ex_est = est_next.strftime('%Y-%m-%d')
            if diff < 0: countdown_label = "已過除淨"
            elif diff <= 21: countdown_label = f"🔥 {diff}天"
            else: countdown_label = f"{diff}天"

        # D. 5萬元實戰預算 (買幾手、剩多少錢)
        lot_size = LOT_MAP.get(symbol, 100)
        one_lot_cost = price * lot_size
        
        if budget >= one_lot_cost:
            lots = int(budget // one_lot_cost)
            strategy = f"✅ 買 {lots} 手"
            rem_cash = budget - (lots * one_lot_cost)
            est_income = div_rate * lots * lot_size
        else:
            strategy = f"❌ 缺 ${one_lot_cost - budget:,.0f}"
            rem_cash = budget
            est_income = 0

        # E. 估值狀態 (💎 特價)
        avg_yield = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val_status = "💎 特價" if avg_yield > 0 and price <= (div_rate / (avg_yield * 1.05)) else "⚠️ 溢價"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "實戰策略": strategy,
            "估值": val_status,
            "倒數": countdown_label,
            "股息率%": round((div_rate/price)*100, 2) if price > 0 else 0,
            "一手成本": f"${one_lot_cost:,.0f}",
            "剩餘現金": f"${rem_cash:,.0f}",
            "預計年息": f"${est_income:,.0f}",
            "months": months,
            "next_date": next_ex_est,
            "raw_divs": divs
        }
    except: return None

# --- UI 介面佈局 ---
st.title("🛡️ 收息戰情室 (1年穩定+全功能恢復版)")

with st.sidebar:
    st.header("💰 實戰預算")
    user_budget = st.number_input("本金 (HKD):", value=50000)
    st.divider()
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

# 掃描名單
STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

# 執行分析
results = []
progress = st.progress(0, text="正在恢復所有功能模組...")
for i, s in enumerate(STOCKS):
    data = get_full_analysis(s, user_budget)
    if data: results.append(data)
    progress.progress((i + 1) / len(STOCKS))

if results:
    df = pd.DataFrame(results)
    
    # 1. 功能回歸：1-12月 💰 月份表
    st.subheader("🗓️ 1-12月 派息月份預期")
    m_rows = []
    for _, r in df.iterrows():
        m_data = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
        m_rows.append(m_data)
    st.table(pd.DataFrame(m_rows, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

    # 2. 功能回歸：綜合實戰大表 (策略、倒數、估值、成本、剩餘現金)
    st.subheader("📊 5萬預算實戰分析")
    show_cols = ["代碼", "公司", "實戰策略", "估值", "倒數", "股息率%", "一手成本", "剩餘現金", "預計年息"]
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

st.divider()

# 3. 功能回歸：歷史溯源查詢
st.subheader("🔍 個股 1 年派息紀錄溯源 (含 0700.HK)")
search = st.text_input("輸入代碼 (例: 0700.HK):").strip().upper()
if search:
    res = get_full_analysis(search, user_budget)
    if res:
        st.write(f"### {search} 近 1 年紀錄 (預估下回: {res['next_date']})")
        st.write(res['raw_divs'].sort_index(ascending=False))
    else:
        st.error("查無資料，請確認代碼含 .HK")
