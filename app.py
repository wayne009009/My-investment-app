import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 核心數據引擎 (優化速度，減少崩潰) ---
@st.cache_data(ttl=3600) # 快取一小時，避免重複請求導致封鎖
def fetch_stock_basic(symbol):
    try:
        tk = yf.Ticker(symbol)
        # 僅抓取最核心數據
        fast = tk.fast_info
        price = fast.get('last_price')
        if not price: return None
        
        info = tk.info
        divs = tk.dividends
        
        return {"price": price, "info": info, "divs": divs}
    except: return None

def get_analysis(symbol, budget, is_hk=True):
    data = fetch_stock_basic(symbol)
    if not data: return None
    
    price = data['price']
    info = data['info']
    divs = data['divs']
    
    # A. 基礎股息
    div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
    yield_pct = (div_rate / price) * 100 if price > 0 else 0
    
    # B. 5萬實戰策略 (保留功能)
    lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
               "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
    lot_size = lot_map.get(symbol, 100) if is_hk else 1
    cost_per_lot = price * lot_size
    
    if budget >= cost_per_lot:
        lots = int(budget // cost_per_lot)
        strategy = f"✅ 買 {lots} 手"
        income = div_rate * lots * lot_size
        rem_cash = budget - (lots * cost_per_lot)
    else:
        strategy = f"❌ 缺 ${cost_per_lot - budget:,.0f}"
        income = 0
        rem_cash = budget

    # C. 派息月份與倒數 (保留功能)
    months = sorted(list(set(divs.index.month[-4:]))) if not divs.empty else []
    countdown_str = "查詢中"
    if not divs.empty:
        today = datetime.date.today()
        # 預測邏輯：去年同期日期 + 365
        last_year = today - datetime.timedelta(days=365)
        recent_divs = divs[divs.index.date >= last_year]
        if not recent_divs.empty:
            est_next = recent_divs.index[0].date() + datetime.timedelta(days=365)
            diff = (est_next - today).days
            countdown_str = f"🔥 {diff}天" if 0 < diff <= 21 else f"{diff}天" if diff > 0 else "已過除淨"

    # D. 估值狀態 (保留功能)
    avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
    val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"

    return {
        "代碼": symbol,
        "公司": info.get('shortName', symbol),
        "策略": strategy,
        "估值": val,
        "倒數": countdown_str,
        "股息率%": round(yield_pct, 2),
        "一手成本": f"${cost_per_lot:,.0f}",
        "剩餘現金": f"${rem_cash:,.0f}",
        "年息預期": f"${income:,.0f}",
        "months": months
    }

# --- 2. UI 界面 ---
st.title("🛡️ 收息終極戰情室 (全功能修復版)")

with st.sidebar:
    st.header("💰 設定")
    user_budget = st.number_input("本金 (HKD):", value=50000)
    if st.button("🔄 清除快取並刷新"):
        st.cache_data.clear()
        st.rerun()

STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

# 執行掃描
results = []
for s in STOCKS:
    res = get_analysis(s, user_budget)
    if res: results.append(res)

if results:
    df = pd.DataFrame(results)
    
    # 功能 1: 1-12月月份表 (💰)
    st.subheader("🗓️ 1-12月 派息月份表")
    m_data = []
    for _, r in df.iterrows():
        row = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
        m_data.append(row)
    st.table(pd.DataFrame(m_data, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

    # 功能 2: 綜合分析表 (倒數、策略、成本、估值)
    st.subheader("📊 5萬預算實戰分析")
    st.dataframe(df.drop(columns=["months"]), use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ 數據加載中或伺服器忙碌，請點擊左側『刷新』按鈕。")

st.divider()

# 功能 3: 深度溯源 (解決 0700.HK 顯示問題)
st.subheader("🔍 個股深度溯源")
search = st.text_input("輸入代碼 (例: 0700.HK):").strip().upper()
if search:
    data = fetch_stock_basic(search)
    if data:
        st.write(f"### {search} 近期派息歷史")
        st.write(data['divs'].tail(10).sort_index(ascending=False))
    else: st.error("查無資料，請確認代碼包含 .HK")
