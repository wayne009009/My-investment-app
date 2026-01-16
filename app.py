import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 核心邏輯：數據抓取與2年分析 ---
def get_stock_data(symbol, budget):
    try:
        tk = yf.Ticker(symbol)
        # 使用 fast_info 確保基礎價格獲取不卡死
        price = tk.fast_info.get('last_price')
        if not price or price <= 0: return None
        
        info = tk.info
        # 抓取 2 年內的派息紀錄
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=730)
        divs = tk.dividends[tk.dividends.index.date >= start_date]
        
        # A. 基礎股息指標
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        yield_pct = (div_rate / price) * 100
        
        # B. 5萬實戰預算策略 (保留)
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

        # C. 派息月份與除淨倒數 (保留)
        months = sorted(list(set(divs.index.month))) if not divs.empty else []
        countdown_label = "確認中"
        next_ex_date = "N/A"
        
        if not divs.empty:
            last_ex = divs.index[-1].date()
            # 預測下一次：去年同期 + 365天
            target_date_last_year = end_date - datetime.timedelta(days=350)
            past_record = divs[divs.index.date >= target_date_last_year]
            if not past_record.empty:
                est_next = past_record.index[0].date() + datetime.timedelta(days=365)
                days_diff = (est_next - end_date).days
                next_ex_date = est_next.strftime('%Y-%m-%d')
                if days_diff < 0: countdown_label = "已過除淨"
                elif days_diff <= 21: countdown_label = f"🔥 {days_diff}天"
                else: countdown_label = f"{days_diff}天"

        # D. 估值狀態 (保留)
        avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "策略": strategy,
            "估值": val,
            "倒數": countdown_label,
            "股息率%": round(yield_pct, 2),
            "一手成本": f"${cost_per_lot:,.0f}",
            "剩餘現金": f"${rem_cash:,.0f}",
            "年息預期": f"${est_income:,.0f}",
            "預估除淨日": next_ex_date,
            "months": months,
            "raw_divs": divs
        }
    except: return None

# --- 2. UI 界面 ---
st.title("🛡️ 5萬元收息終極戰情室 (2年追溯功能全保留版)")

with st.sidebar:
    st.header("💰 實戰預算")
    user_budget = st.number_input("本金 (HKD):", value=50000)
    st.divider()
    st.write("**💎 特價**：股價低於歷史平均")
    st.write("**🔥 倒數**：21天內除淨（收錢倒計時）")

STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

# 執行掃描並保留所有數據
results = []
for s in STOCKS:
    data = get_stock_data(s, user_budget)
    if data: results.append(data)

if results:
    df = pd.DataFrame(results)

    # 功能 A: 1-12月月份表
    st.subheader("🗓️ 1-12月 派息月份預測")
    m_data = []
    for _, r in df.iterrows():
        row = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
        m_data.append(row)
    st.table(pd.DataFrame(m_data, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

    # 功能 B: 綜合分析大表 (包含所有之前的功能)
    st.subheader("📊 實戰策略與倒數計時")
    display_cols = ["代碼", "公司", "策略", "估值", "倒數", "股息率%", "一手成本", "剩餘現金", "年息預期", "預估除淨日"]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

st.divider()

# 功能 C: 2年歷史派息溯源 (修復 0700.HK 問題)
st.subheader("🔍 2年歷史派息與股價溯源")
search = st.text_input("輸入代碼查詢歷史 (例: 0700.HK):").strip().upper()
if search:
    res = get_stock_data(search, user_budget)
    if res is not None:
        st.success(f"成功抓取 {search} 過去 2 年派息紀錄")
        st.write(res['raw_divs'].sort_index(ascending=False))
    else:
        st.error("查無資料，請確認代碼包含 .HK")
