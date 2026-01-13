import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="全球收息大師", layout="wide")

# --- 側邊欄：自定義股票查驗 ---
st.sidebar.header("🔍 自定義股票查驗")
search_symbol = st.sidebar.text_input("輸入代碼 (例: 0005.HK 或 O):", "").strip().upper()

if search_symbol:
    tk_s = yf.Ticker(search_symbol)
    s_info = tk_s.info
    if s_info and 'currentPrice' in s_info:
        st.sidebar.success(f"已找到: {s_info.get('shortName')}")
        s_price = s_info.get('currentPrice')
        s_div = s_info.get('trailingAnnualDividendRate', 0) or s_info.get('dividendRate', 0)
        
        # 讓用戶在側邊欄直接設定該股的手數
        default_lot = s_info.get('sharesPerLot', 1) if ".HK" in search_symbol else 1
        s_user_lot = st.sidebar.number_input(f"設定 {search_symbol} 每手股數:", value=int(default_lot), step=1)
        
        if s_div > 0:
            st.sidebar.write(f"💰 一手 ({s_user_lot}股) 預計年收息:")
            st.sidebar.subheader(f"{s_div * s_user_lot:.2f} {s_info.get('currency')}")
        else:
            st.sidebar.warning("此股票目前不派息。")

# --- 主頁面 ---
st.title("🏆 全球高息股 Top 10 掃描器")
st.info("💡 港股每手股數若不準，請點選下方分頁進行『手動校正』。")

CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK",
    "SCHD", "O", "VICI", "JEPI", "JEPQ", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE"
]

def get_data(symbols):
    all_data = []
    for s in symbols:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            price = info.get('currentPrice')
            div = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            if div > 0:
                all_data.append({
                    "代碼": s,
                    "公司": info.get('shortName', s),
                    "現價": price,
                    "幣種": info.get('currency'),
                    "真實股息率": (div / price) if price else 0,
                    "每股派息": div,
                    "每手股數": info.get('sharesPerLot', 1) if ".HK" in s else 1,
                    "obj": tk
                })
        except: continue
    return pd.DataFrame(all_data).sort_values(by="真實股息率", ascending=False).head(10)

top_10 = get_data(CANDIDATES)

if not top_10.empty:
    # --- 表格顯示 ---
    display_df = top_10.copy()
    display_df['真實股息率'] = display_df['真實股息率'].apply(lambda x: f"{x*100:.2f}%")
    st.dataframe(display_df[["代碼", "公司", "現價", "真實股息率", "每手股數", "幣種"]], use_container_width=True)

    # --- 分頁校正與查證 ---
    st.divider()
    tabs = st.tabs([f"{r['代碼']}" for _, r in top_10.iterrows()])
    for i, (idx, res) in enumerate(top_10.iterrows()):
        with tabs[i]:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                # 讓用戶手動輸入正確的手數 (解決數據不準問題)
                user_lot = st.number_input(f"手動校正 {res['代碼']} 每手股數:", value=int(res['每手股數']), key=f"main_{res['代碼']}")
                annual_income = res['每股派息'] * user_lot
                st.metric("一手年度收息額", f"{annual_income:,.2f} {res['幣種']}")
                st.write(f"最低入場費: {res['現價'] * user_lot:,.2f} {res['幣種']}")

            with col2:
                st.write("**🔗 官方權威查證**")
                if ".HK" in res['代碼']:
                    code = res['代碼'].replace('.HK','').zfill(5)
                    st.link_button("📊 點此打開『披露易』查手數與股息", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={code}")
                else:
                    st.link_button("🇺🇸 點此打開『SEC』查詢美股情況", f"https://www.sec.gov/edgar/browse/?CIK={res['代碼']}")
