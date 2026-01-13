import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import io

st.set_page_config(page_title="全球收息佈局大師", layout="wide")

# --- 側邊欄：資訊提示 ---
st.sidebar.header("🔍 股票查詢")
search_symbol = st.sidebar.text_input("⭐ 輸入代碼強行加入 (例: 0005.HK):", "").strip().upper()
st.sidebar.info("💡 提示：本版本已取消強制過濾，所有標的均會顯示，請自行留意紅字風險警告。")

# --- 核心運算函式 ---
def get_details(tk_obj):
    divs = tk_obj.dividends
    if divs.empty: return 0, {}
    # 連續增長計算
    yearly = divs.groupby(divs.index.year).sum().sort_index(ascending=False)
    streak = 0
    years = yearly.index.tolist()
    for i in range(len(years) - 1):
        if yearly.iloc[i] >= yearly.iloc[i+1]: streak += 1
        else: break
    # 過去 12 個月月份映射
    last_12m = divs[divs.index > (datetime.datetime.now() - datetime.timedelta(days=365))]
    m_map = last_12m.groupby(last_12m.index.month).sum().to_dict()
    return streak, m_map

# --- 主頁面 ---
st.title("🏆 全球收息佈局：月度派息與風險掃描")

CANDIDATES = ["0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "SCHD", "O", "VICI", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV"]

def fetch_all_data(symbols, custom_s):
    all_res = []
    target_list = list(set(symbols + ([custom_s] if custom_s else [])))
    prog = st.progress(0, text="正在獲取全球數據...")
    
    for i, s in enumerate(target_list):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if not info or 'currentPrice' not in info: continue
            
            streak, m_map = get_details(tk)
            net_inc = info.get('netIncomeToCommon', 0)
            price = info.get('currentPrice')
            div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            
            # 風險判定：不再過濾，只做紀錄
            risk_tag = "正常"
            if net_inc <= 0: risk_tag = "⚠️ 虧損中"
            
            all_res.append({
                "代碼": s,
                "公司": info.get('shortName', s),
                "現價": price,
                "股息率": (div_rate / price) if price > 0 else 0,
                "連續增長": streak,
                "狀態": risk_tag,
                "m_map": m_map,
                "is_custom": (s == custom_s),
                "幣種": info.get('currency', 'USD')
            })
        except: continue
        prog.progress((i + 1) / len(target_list))
    prog.empty()
    return pd.DataFrame(all_res)

df = fetch_all_data(CANDIDATES, search_symbol)

if not df.empty:
    # 排序：自定義置頂，其餘按股息率
    df['sort_key'] = df['is_custom'].apply(lambda x: 0 if x else 1)
    final_df = df.sort_values(by=['sort_key', '股息率'], ascending=[True, False]).head(15)

    # --- 1. 月份對比表 ---
    st.subheader("📅 過去 12 個月派息金額紀錄 (按月份)")
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

    # --- 2. 數據導出 ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        table_df.to_excel(writer, sheet_name='MonthlyDividends')
    st.download_button("📥 導出 Excel 紀錄", data=buffer, file_name="dividend_report.xlsx")

    # --- 3. 詳細風險清單 ---
    st.subheader("📊 完整對比清單 (含風險標籤)")
    view_df = final_df.copy()
    view_df['股息率'] = view_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    
    # 使用顏色高亮顯示風險
    st.dataframe(view_df[["代碼", "公司", "現價", "股息率", "連續增長", "狀態", "幣種"]].reset_index(drop=True), use_container_width=True)

else:
    st.warning("請在左側輸入正確的股票代碼。")
