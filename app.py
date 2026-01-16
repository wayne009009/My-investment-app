import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 核心數據抓取引擎 (帶緩存，防止系統卡死) ---
@st.cache_data(ttl=3600)
def get_stock_raw_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        # 獲取基礎價格 (使用 fast_info 最穩定)
        price = tk.fast_info.get('last_price')
        if not price or price <= 0: return None
        
        # 抓取 2 年派息紀錄 (應用戶要求)
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=730)
        divs = tk.dividends[tk.dividends.index.date >= start_date]
        
        return {
            "price": price,
            "info": tk.info,
            "divs": divs,
            "currency": tk.fast_info.get('currency', 'HKD')
        }
    except:
        return None

# --- 2. 核心分析邏輯 ---
def analyze_stock(symbol, budget, is_hk=True):
    data = get_stock_raw_data(symbol)
    if not data: return None
    
    price = data['price']
    info = data['info']
    divs = data['divs']
    
    # A. 派息數據與 1-12 月份表
    div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
    months = sorted(list(set(divs.index.month))) if not divs.empty else []
    
    # B. 除淨日倒數 (🔥)
    countdown_label = "確認中"
    next_ex_est = "N/A"
    if not divs.empty:
        today = datetime.date.today()
        # 預估邏輯：參考去年最接近今天的派息日
        last_year_approx = today - datetime.timedelta(days=350)
        recent_records = divs[divs.index.date >= last_year_approx]
        if not recent_records.empty:
            est_date = recent_records.index[0].date() + datetime.timedelta(days=365)
            days_left = (est_date - today).days
            next_ex_est = est_date.strftime('%Y-%m-%d')
            if days_left < 0: countdown_label = "已過除淨"
            elif days_left <= 21: countdown_label = f"🔥 {days_left}天"
            else: countdown_label = f"{days_left}天"

    # C. 5萬預算實戰策略 (核心功能)
    lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
               "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
    lot_size = lot_map.get(symbol, 100) if is_hk else 1
    exch_rate = 1.0 if is_hk else 7.8
    cost_per_lot = price * exch_rate * lot_size
    
    if budget >= cost_per_lot:
        lots = int(budget // cost_per_lot)
        strategy = f"✅ 買 {lots} 手"
        rem_cash = budget - (lots * cost_per_lot)
        est_income = div_rate * exch_rate * lots * lot_size
    else:
        strategy = f"❌ 缺 ${cost_per_lot - budget:,.0f}"
        rem_cash = budget
        est_income = 0

    # D. 估值判斷 (💎)
    avg_yield = info.get('fiveYearAvgDividendYield', 0) / 100.0
    val_status = "💎 特價" if avg_yield > 0 and price <= (div_rate / (avg_yield * 1.05)) else "⚠️ 溢價"

    return {
        "代碼": symbol,
        "公司": info.get('shortName', symbol),
        "實戰策略": strategy,
        "估值": val_status,
        "除淨倒數": countdown_label,
        "股息率%": round((div_rate/price)*100, 2) if price > 0 else 0,
        "一手成本": f"${cost_per_lot:,.0f}",
        "剩餘現金": f"${rem_cash:,.0f}",
        "預計年息": f"${est_income:,.0f}",
        "months": months,
        "raw_divs": divs
    }

# --- 3. UI 界面 ---
st.title("🛡️ 全球收息終極戰情室 (2年追溯修復版)")

with st.sidebar:
    st.header("💰 本金設定")
    user_budget = st.number_input("您的投資本金 (HKD):", value=50000)
    st.divider()
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()
    st.info("系統現已改為追溯 2 年數據，並保留所有實戰分析功能。")

# 預設掃描名單
STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

if st.button("🚀 啟動掃描 (保證功能完整)"):
    results = []
    progress_bar = st.progress(0, text="正在同步全球派息數據...")
    
    for i, s in enumerate(STOCKS):
        data = analyze_stock(s, user_budget)
        if data: results.append(data)
        progress_bar.progress((i + 1) / len(STOCKS))

    if results:
        df = pd.DataFrame(results)
        
        # 功能 1: 1-12月派息月份表
        st.subheader("🗓️ 1-12月 派息預期表 (💰 代表入帳月份)")
        m_rows = []
        for _, r in df.iterrows():
            m_data = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
            m_rows.append(m_data)
        st.table(pd.DataFrame(m_rows, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

        # 功能 2: 綜合分析清單 (包含倒數、策略、估值)
        st.subheader("📊 5萬預算實戰清單")
        show_cols = ["代碼", "公司", "實戰策略", "估值", "除淨倒數", "股息率%", "一手成本", "剩餘現金", "預計年息"]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

st.divider()

# 功能 3: 深度溯源 (解決 0700.HK 顯示問題)
st.subheader("🔍 2年歷史派息詳細溯源")
search_code = st.text_input("輸入代碼查詢 (例: 0700.HK):").strip().upper()
if search_code:
    res = analyze_stock(search_code, user_budget)
    if res:
        st.success(f"成功抓取 {search_code} 過去 2 年派息紀錄")
        st.write(res['raw_divs'].sort_index(ascending=False))
    else:
        st.error("查無資料，港股請記得加 .HK (例如 0700.HK)")
