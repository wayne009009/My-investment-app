import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import io

# 1. 初始化頁面設定
st.set_page_config(page_title="全球收息佈局終極版", layout="wide")

# 2. 側邊欄：整合所有功能 (查詢 + 風險 + 下載)
st.sidebar.header("🔍 股票查詢與設定")
search_symbol = st.sidebar.text_input("⭐ 輸入代碼強行對比 (例: 0005.HK):", "").strip().upper()
min_growth_years = st.sidebar.slider("最低連續增長年數", 0, 10, 0)
min_profit_only = st.sidebar.checkbox("僅顯示盈利公司 (不影響⭐)", value=False)

# 核心運算：計算連續增長與月份映射
def get_stock_details(tk_obj):
    try:
        divs = tk_obj.dividends
        if divs.empty: return 0, {}
        # 連續增長計算
        yearly = divs.groupby(divs.index.year).sum().sort_index(ascending=False)
        streak, years = 0, yearly.index.tolist()
        for i in range(len(years) - 1):
            if yearly.iloc[i] >= yearly.iloc[i+1]: streak += 1
            else: break
        # 月份映射 (過去 12 個月)
        last_12m = divs[divs.index > (datetime.datetime.now() - datetime.timedelta(days=365))]
        m_map = last_12m.groupby(last_12m.index.month).sum().to_dict()
        return streak, m_map
    except: return 0, {}

# 3. 數據抓取邏輯
st.title("🏆 全球高息 Top 10 與全功能收息表")
CANDIDATES = ["0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "SCHD", "O", "VICI", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV"]

def fetch_data(symbols, custom_s):
    all_res = []
    target_list = list(set(symbols + ([custom_s] if custom_s else [])))
    prog = st.progress(0, text="正在同步數據...")
    for i, s in enumerate(target_list):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if not info or 'currentPrice' not in info: continue
            
            streak, m_map = get_stock_details(tk)
            net_inc = info.get('netIncomeToCommon', 0)
            
            # 過濾邏輯：自定義不被過濾
            if s != custom_s:
                if min_profit_only and net_inc <= 0: continue
                if streak < min_growth_years: continue
            
            price = info.get('currentPrice')
            div = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            
            # 除淨日處理
            ex_date_str, days_to_ex = "N/A", 999
            try:
                cal = tk.calendar
                if cal is not None and 'Dividend Date' in cal:
                    ex_date = cal['Dividend Date']
                    ex_date_str = ex_date.strftime('%Y-%m-%d')
                    days_to_ex = (ex_date - datetime.datetime.now().date()).days
            except: pass

            all_res.append({
                "代碼": s, "公司": info.get('shortName', s), "現價": price,
                "股息率": (div / price) if price > 0 else 0, "連續增長": streak,
                "除淨日": ex_date_str, "倒數(天)": days_to_ex,
                "狀態": "✅ 盈利" if net_inc > 0 else "⚠️ 虧損",
                "m_map": m_map, "is_custom": (s == custom_s), "幣種": info.get('currency', 'USD')
            })
        except: continue
        prog.progress((i + 1) / len(target_list))
    prog.empty()
    return pd.DataFrame(all_res)

df = fetch_data(CANDIDATES, search_symbol)

if not df.empty:
    df['sort_key'] = df['is_custom'].apply(lambda x: 0 if x else 1)
    final_df = df.sort_values(by=['sort_key', '股息率'], ascending=[True, False]).head(12)

    # --- 功能 1: 月份對比表 ---
    st.subheader("📅 過去 12 個月派息月份歷史紀錄")
    m_records = []
    for _, row in final_df.iterrows():
        prefix = "⭐ " if row['is_custom'] else ""
        m_row = {"代碼": prefix + row['代碼']}
        for m in range(1, 13):
            val = row['m_map'].get(m, 0)
            m_row[f"{m}月"] = f"{val:.2f}" if val > 0 else "-"
        m_records.append(m_row)
    table_df = pd.DataFrame(m_records).set_index("代碼")
    st.table(table_df)

    # --- 功能 2: Excel 下載 (含錯誤處理) ---
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            table_df.to_excel(writer, sheet_name='MonthlyDividends')
        st.download_button("📥 導出月份紀錄 Excel", data=buffer, file_name="dividend_report.xlsx")
    except: st.warning("Excel 引擎載入中，請確保 requirements.txt 已包含 xlsxwriter")

    # --- 功能 3: 詳細列表 (含除淨日、增長、風險狀態) ---
    st.subheader("📊 實時風險掃描與除淨提醒")
    view_df = final_df.copy()
    view_df['股息率'] = view_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    cols = ["代碼", "公司", "現價", "股息率", "連續增長", "除淨日", "倒數(天)", "狀態", "幣種"]
    st.dataframe(view_df[cols].reset_index(drop=True), use_container_width=True)

else:
    st.warning("請調整篩選器或檢查代碼。")
