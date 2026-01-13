import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="高息股自動掃描儀", layout="wide")

st.title("🚀 穩健高息股：每日自動掃描排名 (Top 10)")
st.write("自動從港美股穩健清單中篩選當前股息率最高的 10 隻標的。")

# --- 1. 定義穩健候選名單 ---
CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK",
    "SCHD", "O", "VICI", "JEPI", "JEPQ", "VIG", "VYM", "KO", "PEP", "MO", "T", "PFE"
]

# --- 2. 執行自動掃描 (完全移除 st.cache) ---
def get_top_10(symbols):
    all_data = []
    # 建立一個進度條，讓用戶知道正在抓取
    progress_text = "正在掃描全球市場數據，請稍候..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            # 確保有抓到基本價格和股息數據
            if info and 'currentPrice' in info:
                div_yield = info.get('dividendYield', 0)
                all_data.append({
                    "代碼": s,
                    "公司": info.get('shortName', s),
                    "現價": info.get('currentPrice'),
                    "幣種": info.get('currency'),
                    "股息率": div_yield,
                    "每股派息": info.get('dividendRate', 0),
                    "每手股數": info.get('sharesPerLot', 1) if ".HK" in s else 1,
                    "ticker_obj": tk # 存儲物件供後續繪圖使用
                })
        except:
            continue
        my_bar.progress((i + 1) / len(symbols))
    
    my_bar.empty() # 完成後隱藏進度條
    
    if not all_data:
        return pd.DataFrame()
        
    full_df = pd.DataFrame(all_data)
    # 按股息率從高到低排序並取前 10
    top_10 = full_df.sort_values(by="股息率", ascending=False).head(10)
    return top_10

# 執行掃描
top_10_df = get_top_10(CANDIDATES)

if not top_10_df.empty:
    # --- 顯示對比表格 ---
    st.subheader("📊 今日即時高息排名 (Top 10)")
    
    # 格式化顯示用表格 (隱藏物件欄位)
    display_df = top_10_df.copy()
    display_df['股息率'] = display_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
    st.dataframe(display_df.drop(columns=['ticker_obj']), use_container_width=True)

    # --- 詳細分析分頁 ---
    st.divider()
    st.subheader("🔍 詳細分析與官方公告")
    
    # 建立分頁
    tabs = st.tabs([f"{r['代碼']}" for _, r in top_10_df.iterrows()])

    for i, (idx, res) in enumerate(top_10_df.iterrows()):
        with tabs[i]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                
                # 歷史派息圖表 (修正時區問題)
                hist_div = res['ticker_obj'].dividends
                if not hist_div.empty:
                    utc = pytz.UTC
                    cutoff = utc.localize(datetime.datetime.now() - datetime.timedelta(days=5*365))
                    last_5y = hist_div[hist_div.index > cutoff]
                    if not last_5y.empty:
                        st.line_chart(last_5y)
                        months = last_5y.index.month.value_counts().index[:4].tolist()
                        st.success(f"📅 歷史主要派息月份: {', '.join([f'{m}月' for m in sorted(months)])}")
                else:
                    st.write("暫無歷史派息紀錄。")

            with c2:
                st.write("**💰 投資計算**")
                # 港股每手股數校正
                lot = st.number_input(f"每手股數校正:", value=int(res['每手股數']), key=f"lot_{res['代碼']}")
                st.metric("最低入場費", f"{res['現價'] * lot:,.2f} {res['幣種']}")
                
                if ".HK" in res['代碼']:
                    clean_code = res['代碼'].replace('.HK','').zfill(5)
                    hkex_url = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={clean_code}"
                    st.link_button("🔍 披露易：查看官方公告", hkex_url)
                else:
                    st.warning("🇺🇸 美股注意 30% 股息代扣稅")
else:
    st.warning("掃描完成，但未發現有效的股票數據。請檢查網路連線或稍後再試。")

# 側邊欄：手動增加搜尋
st.sidebar.divider()
st.sidebar.write("💡 提示：App 會自動從預設清單中找出最強 10 隻。")
