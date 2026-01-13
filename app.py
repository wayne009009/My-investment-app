import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="全球高息股掃描儀", layout="wide")

st.title("🚀 全球高息 Top 10：即時掃描與自定義查詢")

# --- 1. 側邊欄：自定義股票查驗 (新功能) ---
st.sidebar.header("🔍 自定義股票查驗")
search_symbol = st.sidebar.text_input("輸入代碼 (例如 0941.HK 或 TSLA):", "").strip().upper()

if search_symbol:
    try:
        tk_search = yf.Ticker(search_symbol)
        s_info = tk_search.info
        if s_info and 'currentPrice' in s_info:
            st.sidebar.success(f"✅ 已找到: {s_info.get('shortName')}")
            s_price = s_info.get('currentPrice')
            s_div = s_info.get('trailingAnnualDividendRate', 0) or s_info.get('dividendRate', 0)
            s_lot = s_info.get('sharesPerLot', 1) if ".HK" in search_symbol else 1
            
            if s_div > 0:
                st.sidebar.metric("真實股息率", f"{(s_div/s_price)*100:.2f}%")
                st.sidebar.write(f"💰 一手 ({s_lot}股) 派息: **{s_div * s_lot:.2f} {s_info.get('currency')}**")
            else:
                st.sidebar.warning("⚠️ 該標的目前不派發股息 (Growth Stock)。")
        else:
            st.sidebar.error("找不到該代碼，請檢查格式。")
    except:
        st.sidebar.error("抓取失敗，請稍後再試。")

# --- 2. 候選名單 ---
CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK",
    "0001.HK", "0002.HK", "0012.HK", "0016.HK", "0388.HK", "0857.HK", "2318.HK", "2628.HK", "3968.HK",
    "SCHD", "O", "VICI", "JEPI", "JEPQ", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV", "XOM"
]

# --- 3. 核心數據抓取與 Top 10 計算 ---
def get_refined_data(symbols):
    all_data = []
    my_bar = st.progress(0, text="正在同步全球 Top 10 數據...")
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if not info or 'currentPrice' not in info: continue
            price = info.get('currentPrice')
            actual_div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
            real_yield = (actual_div_rate / price) if price > 0 else 0
            lot_size = info.get('sharesPerLot', 1) if ".HK" in s else 1
            
            all_data.append({
                "代碼": s,
                "公司": info.get('shortName', s),
                "現價": price,
                "幣種": info.get('currency'),
                "真實股息率": real_yield,
                "每股派息": actual_div_rate,
                "每手股數": lot_size,
                "一手派息額": actual_div_rate * lot_size,
                "ticker_obj": tk
            })
        except: continue
        my_bar.progress((i + 1) / len(symbols))
    my_bar.empty()
    if not all_data: return pd.DataFrame()
    return pd.DataFrame(all_data).sort_values(by="真實股息率", ascending=False).head(10)

top_10_df = get_refined_data(CANDIDATES)

if not top_10_df.empty:
    st.subheader("📊 今日即時高息排名 (Top 10)")
    display_df = top_10_df.copy()
    display_df['真實股息率'] = display_df['真實股息率'].apply(lambda x: f"{x*100:.2f}%")
    display_df['一手派息額'] = display_df.apply(lambda r: f"{r['一手派息額']:,.2f} {r['幣種']}", axis=1)
    st.dataframe(display_df[["代碼", "公司", "現價", "真實股息率", "一手派息額", "每手股數"]], use_container_width=True)

    st.divider()
    tabs = st.tabs([f"{r['代碼']}" for _, r in top_10_df.iterrows()])
    for i, (idx, res) in enumerate(top_10_df.iterrows()):
        with tabs[i]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                st.write(f"**💰 買入一手 ({res['每手股數']}股) 年收息：{res['一手派息額']}**")
                hist_div = res['ticker_obj'].dividends
                if not hist_div.empty:
                    utc = pytz.UTC
                    cutoff = utc.localize(datetime.datetime.now() - datetime.timedelta(days=5*365))
                    st.line_chart(hist_div[hist_div.index > cutoff])
            with c2:
                st.write("**🏛️ 官方數據查證**")
                if ".HK" in res['代碼']:
                    clean_code = res['代碼'].replace('.HK','').zfill(5)
                    st.link_button("🔍 進入披露易 (核對股息)", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={clean_code}")
                else:
                    st.link_button("🇺🇸 進入 SEC EDGAR (官方報告)", f"https://www.sec.gov/edgar/browse/?CIK={res['代碼']}")
