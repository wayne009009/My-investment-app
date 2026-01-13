import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="全球收息佈局大師", layout="wide")

# --- 側邊欄設定 ---
st.sidebar.header("🛡️ 風險與時間管理")
min_growth_years = st.sidebar.slider("最低連續派息增長年數", 0, 10, 0)
min_profit_only = st.sidebar.checkbox("僅顯示盈利公司", value=True)

# --- 核心運算函式 ---
def get_dividend_details(tk_obj):
    divs = tk_obj.dividends
    if divs.empty: return 0, pd.DataFrame()
    
    # 1. 計算連續增長年數
    yearly_divs = divs.groupby(divs.index.year).sum().sort_index(ascending=False)
    streak = 0
    years = yearly_divs.index.tolist()
    for i in range(len(years) - 1):
        if yearly_divs.iloc[i] >= yearly_divs.iloc[i+1]: streak += 1
        else: break
    
    # 2. 過去 12 個月按月份分類紀錄
    last_year = divs[divs.index > (datetime.datetime.now() - datetime.timedelta(days=365))]
    monthly_summary = last_year.groupby(last_year.index.month).sum()
    
    return streak, monthly_summary

# --- 主頁面佈局 ---
st.title("🏆 全球收息 Top 10 與月度收息表")

CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", 
    "SCHD", "O", "VICI", "JEPI", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV"
]

def fetch_data(symbols):
    all_data = []
    progress = st.progress(0, text="正在分析派息日曆與財務風險...")
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            streak, monthly_divs = get_dividend_details(tk)
            
            # 篩選邏輯
            if min_profit_only and info.get('netIncomeToCommon', 0) <= 0: continue
            if streak < min_growth_years: continue
            
            price = info.get('currentPrice')
            div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            
            # 獲取下次除淨日
            ex_date = "N/A"
            try:
                cal = tk.calendar
                if cal is not None and 'Dividend Date' in cal:
                    ex_date = cal['Dividend Date'].strftime('%Y-%m-%d')
            except: pass
            
            if div_rate > 0:
                all_data.append({
                    "代碼": s,
                    "公司": info.get('shortName', s),
                    "現價": price,
                    "股息率": (div_rate / price) if price else 0,
                    "除淨日": ex_date,
                    "連續增長": f"{streak}年",
                    "一手股數": info.get('sharesPerLot', 1) if ".HK" in s else 1,
                    "monthly_data": monthly_divs,
                    "obj": tk
                })
        except: continue
        progress.progress((i + 1) / len(symbols))
    progress.empty()
    return pd.DataFrame(all_data).sort_values(by="股息率", ascending=False).head(10)

df_res = fetch_data(CANDIDATES)

if not df_res.empty:
    # --- 1. 即將除淨提醒 ---
    st.subheader("⏰ 近期除淨提醒 (未來 30 天)")
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    upcoming = df_res[df_res['除淨日'] != "N/A"].sort_values(by='除淨日')
    st.table(upcoming[["代碼", "公司", "除淨日", "股息率"]])

    # --- 2. 核心數據表 ---
    st.subheader("📊 穩健高息排名")
    st.dataframe(df_res.drop(columns=['obj', 'monthly_data']), use_container_width=True)

    # --- 3. 月度收息歷史回顧 ---
    st.divider()
    st.subheader("📅 過去 12 個月派息月份分佈")
    
    # 建立橫向月份對比表
    month_list = []
    for _, row in df_res.iterrows():
        m_data = row['monthly_data']
        res_row = {"代碼": row['代碼']}
        for m in range(1, 13):
            val = m_data.get(m, 0)
            res_row[f"{m}月"] = f"{val:.2f}" if val > 0 else "-"
        month_list.append(res_row)
    
    st.table(pd.DataFrame(month_list).set_index("代碼"))

    # --- 4. 個股深度分析 ---
    st.divider()
    tabs = st.tabs([f"{r['代碼']}" for _, r in df_res.iterrows()])
    for i, (idx, res) in enumerate(df_res.iterrows()):
        with tabs[i]:
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                st.write(f"**連續增長：** {res['連續增長']}")
                st.line_chart(res['obj'].dividends)
            with c2:
                st.write("### 查證與計算")
                if ".HK" in res['代碼']:
                    st.link_button("📊 披露易：核對官方公告", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={res['代碼'].replace('.HK','').zfill(5)}")
                else:
                    st.link_button("🇺🇸 SEC：查看 10-K 報表", f"https://www.sec.gov/edgar/browse/?CIK={res['代碼']}")
                
                u_lot = st.number_input(f"校正手數:", value=int(res['一手股數']), key=f"tab_{res['代碼']}")
                st.metric("一手派息金額", f"{res['obj'].info.get('dividendRate', 0) * u_lot:.2f}")

else:
    st.warning("請調整篩選條件或檢查網路連線。")
