import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="全球高息股掃描儀", layout="wide")

st.title("🚀 全球高息 Top 10：含除淨日與官方查證")
st.write("自動掃描港美股清單，顯示最新股息率及官方公告連結。")

# --- 1. 擴充候選名單 (在此加入更多標的) ---
CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK",
    "0001.HK", "0002.HK", "0012.HK", "0016.HK", "0388.HK", "0857.HK", "2318.HK", "2628.HK", "3968.HK",
    "SCHD", "O", "VICI", "JEPI", "JEPQ", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV", "XOM"
]

# --- 2. 數據抓取邏輯 ---
def get_stock_data(symbols):
    all_data = []
    my_bar = st.progress(0, text="正在同步全球交易所數據...")
    
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if info and 'currentPrice' in info:
                # 提取股息率
                div_yield = info.get('dividendYield', 0)
                
                # 提取除淨日 (從 calendar 抓取較準確)
                ex_div_date = "N/A"
                try:
                    cal = tk.calendar
                    if cal is not None and 'Dividend Date' in cal:
                        ex_date = cal['Dividend Date']
                        if isinstance(ex_date, (datetime.date, datetime.datetime)):
                            ex_div_date = ex_date.strftime('%Y-%m-%d')
                except:
                    pass
                
                all_data.append({
                    "代碼": s,
                    "公司": info.get('shortName', s),
                    "現價": info.get('currentPrice'),
                    "幣種": info.get('currency'),
                    "股息率": div_yield,
                    "每股派息": info.get('dividendRate', 0),
                    "除淨日": ex_div_date,
                    "每手股數": info.get('sharesPerLot', 1) if ".HK" in s else 1,
                    "ticker_obj": tk
                })
        except:
            continue
        my_bar.progress((i + 1) / len(symbols))
    
    my_bar.empty()
    if not all_data: return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    # 依股息率排序並取前 10
    return df.sort_values(by="股息率", ascending=False).head(10)

# 執行掃描
top_10_df = get_stock_data(CANDIDATES)

if not top_10_df.empty:
    # --- 顯示 Top 10 對比表格 ---
    st.subheader("📊 今日即時高息排名 (Top 10)")
    display_df = top_10_df.copy()
    display_df['股息率'] = display_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    # 將除淨日排在顯眼位置
    cols = ["代碼", "公司", "現價", "股息率", "除淨日", "幣種"]
    st.dataframe(display_df[cols], use_container_width=True)

    # --- 詳細分析分頁 ---
    st.divider()
    tabs = st.tabs([f"{r['代碼']}" for _, r in top_10_df.iterrows()])

    for i, (idx, res) in enumerate(top_10_df.iterrows()):
        with tabs[i]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                hist_div = res['ticker_obj'].dividends
                if not hist_div.empty:
                    utc = pytz.UTC
                    cutoff = utc.localize(datetime.datetime.now() - datetime.timedelta(days=5*365))
                    last_5y = hist_div[hist_div.index > cutoff]
                    st.line_chart(last_5y)

            with c2:
                st.write("**🏛️ 官方數據查證**")
                
                if ".HK" in res['代碼']:
                    # 港股：披露易
                    clean_code = res['代碼'].replace('.HK','').zfill(5)
                    url = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={clean_code}"
                    st.link_button("🔍 進入披露易 (查看最新公告)", url)
                else:
                    # 美股：SEC EDGAR 官方查詢
                    symbol_only = res['代碼']
                    sec_url = f"https://www.sec.gov/edgar/browse/?CIK={symbol_only}"
                    st.link_button("🇺🇸 進入 SEC EDGAR (官方財務報告)", sec_url)
                
                st.divider()
                st.write("**💰 成本計算**")
                lot = st.number_input(f"每手股數:", value=int(res['每手股數']), key=f"lot_{res['代碼']}")
                st.metric("預計入場費", f"{res['現價'] * lot:,.2f} {res['幣種']}")
                st.info(f"該標的前次除淨日參考: {res['除淨日']}")
else:
    st.error("暫時無法抓取數據，請重整網頁。")
