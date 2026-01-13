import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import io

st.set_page_config(page_title="全球收息佈局大師", layout="wide")

# --- 側邊欄：風險管理與自定義查詢 ---
st.sidebar.header("🔍 自定義與風險設定")
search_symbol = st.sidebar.text_input("⭐ 輸入代碼強行加入對比 (例: 0941.HK):", "").strip().upper()
min_growth_years = st.sidebar.slider("最低連續增長年數", 0, 10, 0)
min_profit_only = st.sidebar.checkbox("僅顯示盈利公司 (不影響自定義股票)", value=False)

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
    # 月份映射 (過去 12 個月)
    last_12m = divs[divs.index > (datetime.datetime.now() - datetime.timedelta(days=365))]
    m_map = last_12m.groupby(last_12m.index.month).sum().to_dict()
    return streak, m_map

# --- 主頁面 ---
st.title("🏆 全球收息 Top 10 與月度歷史對比")
st.write("自定義查詢的股票將以 ⭐ 標註並強行出現在首行，不受風險過濾影響。")

CANDIDATES = ["0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "SCHD", "O", "VICI", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV"]

def fetch_all(symbols, custom_s):
    all_res = []
    # 合併清單並去重
    target_list = list(set(symbols + ([custom_s] if custom_s else [])))
    
    prog = st.progress(0, text="正在同步數據...")
    for i, s in enumerate(target_list):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if not info or 'currentPrice' not in info: continue
            
            streak, m_map = get_details(tk)
            net_inc = info.get('netIncomeToCommon', 0)
            
            # 過濾邏輯：自定義股票 (custom_s) 永遠不被過濾
            if s != custom_s:
                if min_profit_only and net_inc <= 0: continue
                if streak < min_growth_years: continue
            
            price = info.get('currentPrice')
            div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            
            all_res.append({
                "代碼": s,
                "公司": info.get('shortName', s),
                "股息率": (div_rate / price) if price > 0 else 0,
                "連續增長": streak,
                "m_map": m_map,
                "is_custom": (s == custom_s),
                "幣種": info.get('currency', 'USD')
            })
        except: continue
        prog.progress((i + 1) / len(target_list))
    prog.empty()
    return pd.DataFrame(all_res)

df = fetch_all(CANDIDATES, search_symbol)

if not df.empty:
    # 排序邏輯：自定義股票排最前，其餘按股息率排序
    df['sort_key'] = df['is_custom'].apply(lambda x: 0 if x else 1)
    final_df = df.sort_values(by=['sort_key', '股息率'], ascending=[True, False]).head(12)

    # --- 1. 月份對比表 ---
    st.subheader("📅 過去 12 個月派息月份分佈 (含自定義查詢)")
    m_records = []
    for _, row in final_df.iterrows():
        m_row = {"代碼": ("⭐ " + row['代碼'] if row['is_custom'] else row['代碼'])}
        for m in range(1, 13):
            val = row['m_map'].get(m, 0)
            m_row[f"{m}月"] = round(val, 2) if val > 0 else "-"
        m_records.append(m_row)
    
    table_df = pd.DataFrame(m_records).set_index("代碼")
    st.table(table_df)

    # --- 2. 數據導出功能 ---
    st.divider()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        table_df.to_excel(writer, sheet_name='Monthly_Dividends')
    
    st.download_button(
        label="📥 下載月度收息對比表 (Excel)",
        data=buffer,
        file_name=f"dividend_report_{datetime.date.today()}.xlsx",
        mime="application/vnd.ms-excel"
    )

    # --- 3. 詳細排名表 ---
    st.subheader("📊 詳細數據總覽")
    view_df = final_df.copy()
    view_df['股息率'] = view_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    st.dataframe(view_df[["代碼", "公司", "股息率", "連續增長", "幣種"]], use_container_width=True)

else:
    st.error("🚨 找不到符合條件的數據。請調整左側過濾器。")
