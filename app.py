import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import io

st.set_page_config(page_title="全球高息股掃描儀", layout="wide")

# --- 側邊欄：搜尋功能 ---
st.sidebar.header("🔍 股票查詢")
search_symbol = st.sidebar.text_input("⭐ 輸入代碼強行加入對比 (例: 0005.HK):", "").strip().upper()

# --- 核心運算函式 ---
def get_details(tk_obj):
    try:
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
    except:
        return 0, {}

# --- 主頁面 ---
st.title("🏆 全球高息 Top 10 與月度收息表")

# 穩定候選名單
CANDIDATES = ["0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "SCHD", "O", "VICI", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV"]

def fetch_data(symbols, custom_s):
    all_res = []
    target_list = list(set(symbols + ([custom_s] if custom_s else [])))
    
    prog = st.progress(0, text="正在獲取最新股息數據 (如遇阻塞請稍候)...")
    
    for i, s in enumerate(target_list):
        try:
            tk = yf.Ticker(s)
            # 優先嘗試快速獲取價格和基本資訊
            price = tk.fast_info.get('lastPrice') or tk.info.get('currentPrice')
            if price is None: continue
            
            info = tk.info
            streak, m_map = get_details(tk)
            div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            
            # 除淨日處理
            ex_date_str = "N/A"
            days_to_ex = 999
            try:
                cal = tk.calendar
                if cal is not None and 'Dividend Date' in cal:
                    ex_date = cal['Dividend Date']
                    ex_date_str = ex_date.strftime('%Y-%m-%d')
                    days_to_ex = (ex_date - datetime.datetime.now().date()).days
            except: pass
            
            all_res.append({
                "代碼": s,
                "公司": info.get('shortName', s),
                "現價": price,
                "股息率": (div_rate / price) if price > 0 else 0,
                "連續增長": streak,
                "除淨日": ex_date_str,
                "倒數(天)": days_to_ex,
                "m_map": m_map,
                "is_custom": (s == custom_s),
                "幣種": info.get('currency', 'USD')
            })
        except:
            continue
        prog.progress((i + 1) / len(target_list))
    prog.empty()
    return pd.DataFrame(all_res)

# 執行抓取
df = fetch_data(CANDIDATES, search_symbol)

if not df.empty:
    # 排序邏輯：自定義置頂，其餘按股息率排
    df['sort_key'] = df['is_custom'].apply(lambda x: 0 if x else 1)
    final_df = df.sort_values(by=['sort_key', '股息率'], ascending=[True, False]).head(11)

    # --- 1. 月份對比表 ---
    st.subheader("📅 過去 12 個月派息歷史 (按月份分佈)")
    m_records = []
    for _, row in final_df.iterrows():
        prefix = "⭐ " if row['is_custom'] else ""
        m_row = {"代碼": prefix + row['代碼']}
        for m in range(1, 13):
            val = row['m_map'].get(m, 0)
            m_row[f"{m}月"] = f"{val:.2f}" if val > 0 else "-"
        m_records.append(m_row)
    
    st.table(pd.DataFrame(m_records).set_index("代碼"))

    # --- 2. 下載按鈕 ---
    buffer = io.BytesIO()
    pd.DataFrame(m_records).to_excel(buffer, index=False)
    st.download_button("📥 導出 Excel 紀錄", data=buffer, file_name="dividend_history.xlsx")

    # --- 3. 實時排名與除淨提醒 ---
    st.subheader("📊 實時排名與除淨倒數")
    view_df = final_df.copy()
    view_df['股息率'] = view_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    cols = ["代碼", "公司", "現價", "股息率", "除淨日", "倒數(天)", "連續增長", "幣種"]
    st.dataframe(view_df[cols].reset_index(drop=True), use_container_width=True)

else:
    st.warning("🔄 數據加載超時，可能是 Yahoo Finance 接口繁忙。請嘗試點擊右上角「Rerun」或重新整理。")
