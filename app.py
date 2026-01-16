import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="全球高息股掃描儀", layout="wide")

st.title("🚀 全球高息 Top 10：修正股息率與一手派息估計")
st.write("手動計算真實股息率，並顯示每一手可獲得的派息金額。")

# --- 1. 候選名單 ---
CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK",
    "0001.HK", "0002.HK", "0012.HK", "0016.HK", "0388.HK", "0857.HK", "2318.HK", "2628.HK", "3968.HK",
    "SCHD", "O", "VICI", "JEPI", "JEPQ", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE", "VZ", "ABBV", "XOM"
]

# --- 2. 核心數據抓取與精確計算 ---
def get_refined_data(symbols):
    all_data = []
    my_bar = st.progress(0, text="正在計算真實股息收益...")
    
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            if not info or 'currentPrice' not in info: continue
            
            price = info.get('currentPrice')
            # 使用 Trailing Annual Dividend Rate (過去12個月總派息) 計算真實股息率
            actual_div_rate = info.get('trailingAnnualDividendRate', 0)
            if actual_div_rate == 0: 
                actual_div_rate = info.get('dividendRate', 0) # 備用方案
            
            real_yield = (actual_div_rate / price) if price > 0 else 0
            lot_size = info.get('sharesPerLot', 1) if ".HK" in s else 1
            
            # --- 新增：計算一手派息額 ---
            dividend_per_lot = actual_div_rate * lot_size
            
            # 提取除淨日
            ex_div_date = "N/A"
            try:
                cal = tk.calendar
                if cal is not None and 'Dividend Date' in cal:
                    ex_date = cal['Dividend Date']
                    if isinstance(ex_date, (datetime.date, datetime.datetime)):
                        ex_div_date = ex_date.strftime('%Y-%m-%d')
            except: pass
            
            all_data.append({
                "代碼": s,
                "公司": info.get('shortName', s),
                "現價": price,
                "幣種": info.get('currency'),
                "真實股息率": real_yield,
                "每股派息": actual_div_rate,
                "每手股數": lot_size,
                "一手派息額": dividend_per_lot,
                "除淨日": ex_div_date,
                "ticker_obj": tk
            })
        except: continue
        my_bar.progress((i + 1) / len(symbols))
    
    my_bar.empty()
    if not all_data: return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    # 按手動計算的真實股息率排序
    return df.sort_values(by="真實股息率", ascending=False).head(10)

# 執行
top_10_df = get_refined_data(CANDIDATES)

if not top_10_df.empty:
    # --- 3. 簡潔表格顯示 ---
    st.subheader("📊 今日即時高息排名 (Top 10)")
    
    display_df = top_10_df.copy()
    display_df['真實股息率'] = display_df['真實股息率'].apply(lambda x: f"{x*100:.2f}%")
    display_df['一手派息額'] = display_df.apply(lambda r: f"{r['一手派息額']:,.2f} {r['幣種']}", axis=1)
    
    # 重新排列欄位，讓用戶最關心的資訊在前
    cols = ["代碼", "公司", "現價", "真實股息率", "一手派息額", "除淨日", "每手股數"]
    st.dataframe(display_df[cols], use_container_width=True)
    st.info("💡 『一手派息額』係根據過去12個月派息總額計算之參考值。")

    # --- 4. 詳細查證分頁 ---
    st.divider()
    tabs = st.tabs([f"{r['代碼']}" for _, r in top_10_df.iterrows()])
    for i, (idx, res) in enumerate(top_10_df.iterrows()):
        with tabs[i]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                st.write(f"**💰 買入一手 ({res['每手股數']}股) 的預期年收息：{res['一手派息額']}**")
                # 繪製趨勢圖
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
                
                # 手動校正（針對港股每手股數不準的情況）
                st.divider()
                new_lot = st.number_input(f"校正每手股數:", value=int(res['每手股數']), key=f"adj_{res['代碼']}")
                st.metric("校正後一手派息", f"{(res['每股派息'] * new_lot):,.2f} {res['幣種']}")

else:
    st.error("掃描失敗，請檢查網路後重整。")
