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
    if divs.empty: return 0, {}
    
    # 1. 計算連續增長年數 (按年加總)
    yearly_divs = divs.groupby(divs.index.year).sum().sort_index(ascending=False)
    streak = 0
    years = yearly_divs.index.tolist()
    for i in range(len(years) - 1):
        if yearly_divs.iloc[i] >= yearly_divs.iloc[i+1]: streak += 1
        else: break
    
    # 2. 過去 12 個月按月份分類 (製作月份查閱表)
    last_12m = divs[divs.index > (datetime.datetime.now() - datetime.timedelta(days=365))]
    # 轉換為 {月份: 金額} 字典
    monthly_map = last_12m.groupby(last_12m.index.month).sum().to_dict()
    
    return streak, monthly_map

# --- 主頁面 ---
st.title("🏆 全球收息 Top 10 與月度歷史紀錄")

CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", 
    "SCHD", "O", "VICI", "JEPI", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV"
]

def fetch_data(symbols):
    all_data = []
    progress = st.progress(0, text="數據同步中...")
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if not info or 'currentPrice' not in info: continue
            
            streak, monthly_map = get_dividend_details(tk)
            
            # 嚴格過濾邏輯
            if min_profit_only and info.get('netIncomeToCommon', 0) <= 0: continue
            if streak < min_growth_years: continue
            
            price = info.get('currentPrice')
            div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            
            if div_rate > 0:
                all_data.append({
                    "代碼": s,
                    "公司": info.get('shortName', s),
                    "現價": price,
                    "股息率": (div_rate / price) if price else 0,
                    "連續增長": streak,
                    "monthly_map": monthly_map,
                    "幣種": info.get('currency', 'USD'),
                    "obj": tk
                })
        except: continue
        progress.progress((i + 1) / len(symbols))
    progress.empty()
    return pd.DataFrame(all_data)

# 抓取數據
raw_df = fetch_data(CANDIDATES)

# 檢查是否有數據，避免 KeyError
if not raw_df.empty:
    top_10_df = raw_df.sort_values(by="股息率", ascending=False).head(10)

    # --- 1. 月份收息歷史表 (核心需求) ---
    st.subheader("📅 過去 12 個月派息紀錄表 (按月份)")
    
    month_cols = [f"{m}月" for m in range(1, 13)]
    monthly_records = []
    
    for _, row in top_10_df.iterrows():
        m_map = row['monthly_map']
        m_row = {"代碼": row['代碼']}
        for m in range(1, 13):
            val = m_map.get(m, 0)
            m_row[f"{m}月"] = f"{val:.2f}" if val > 0 else "-"
        monthly_records.append(m_row)
    
    st.table(pd.DataFrame(monthly_records).set_index("代碼"))

    # --- 2. 數據對比總覽 ---
    st.subheader("📊 穩健高息排名總覽")
    display_df = top_10_df.copy()
    display_df['股息率'] = display_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    st.dataframe(display_df[["代碼", "公司", "現價", "股息率", "連續增長", "幣種"]], use_container_width=True)

    # --- 3. 個股風險診斷 ---
    st.divider()
    tabs = st.tabs([f"{r['代碼']}" for _, r in top_10_df.iterrows()])
    for i, (idx, res) in enumerate(top_10_df.iterrows()):
        with tabs[i]:
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                st.write(f"🛡️ **連續增長紀錄：** {res['連續增長']} 年")
                st.line_chart(res['obj'].dividends)
            with c2:
                st.write("🔧 **操作與查證**")
                if ".HK" in res['代碼']:
                    st.link_button("🔍 披露易：查看官方公告", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={res['代碼'].replace('.HK','').zfill(5)}")
                else:
                    st.link_button("🇺🇸 SEC：查看美國官方報告", f"https://www.sec.gov/edgar/browse/?CIK={res['代碼']}")
                
                # 手動手數校正
                lot = st.number_input(f"校正 {res['代碼']} 每手股數:", value=100 if ".HK" in res['代碼'] else 1, key=f"lot_{res['代碼']}")
                st.metric("一手派息估算", f"{res['obj'].info.get('dividendRate', 0) * lot:.2f} {res['幣種']}")

else:
    st.error("🚨 找不到符合條件的股票。請在左側降低『連續增長年數』或取消勾選『僅顯示盈利公司』後重試。")
