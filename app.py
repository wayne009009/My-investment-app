import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="高息股自動掃描儀", layout="wide")

st.title("🚀 穩健高息股：每日自動掃描排名 (Top 10)")
st.write("自動從港美股穩健清單中篩選當前股息率最高的 10 隻標的。")

# --- 1. 定義穩健候選名單 (您可以隨時在代碼中修改這組清單) ---
# 包含港股藍籌、美股 ETF 及配息名股
CANDIDATES = [
    "0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK",
    "SCHD", "O", "VICI", "JEPI", "JEPQ", "VIG", "VYM", "AAPL", "MSFT", "KO", "PEP", "MO", "T", "PFE"
]

# --- 數據處理函式 ---
@st.cache_data(ttl=43200) # 每12小時更新一次數據，節省加載時間
def scan_high_yield_top10(symbols):
    all_data = []
    progress_bar = st.progress(0)
    for i, s in enumerate(symbols):
        try:
            tk = yf.Ticker(s)
            info = tk.info
            div_yield = info.get('dividendYield', 0)
            if div_yield:
                all_data.append({
                    "代碼": s,
                    "公司": info.get('shortName'),
                    "現價": info.get('currentPrice'),
                    "幣種": info.get('currency'),
                    "股息率": div_yield,
                    "每股派息": info.get('dividendRate', 0),
                    "每手股數": info.get('sharesPerLot', 1) if ".HK" in s else 1,
                    "object": tk
                })
        except:
            continue
        progress_bar.progress((i + 1) / len(symbols))
    
    # 根據股息率排序並取前 10 名
    full_df = pd.DataFrame(all_data)
    top_10 = full_df.sort_values(by="股息率", ascending=False).head(10)
    return top_10

# --- 2. 執行自動掃描 ---
st.subheader("📊 今日即時高息排名 (Top 10)")
with st.spinner('正在掃描全球市場數據...'):
    top_10_df = scan_high_yield_top10(CANDIDATES)

# 格式化顯示
display_df = top_10_df.copy()
display_df['股息率'] = display_df['股息率'].apply(lambda x: f"{x*100:.2f}%")
st.table(display_df.drop(columns=['object']))

# --- 3. 詳細分析與披露易連結 ---
st.divider()
st.subheader("🔍 詳細分析與官方公告")
tabs = st.tabs([f"{r['代碼']}" for _, r in top_10_df.iterrows()])

for i, (idx, res) in enumerate(top_10_df.iterrows()):
    with tabs[i]:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write(f"### {res['公司']} ({res['代碼']})")
            # 歷史派息趨勢
            hist_div = res['object'].dividends
            if not hist_div.empty:
                utc = pytz.UTC
                cutoff = utc.localize(datetime.datetime.now() - datetime.timedelta(days=5*365))
                last_5y = hist_div[hist_div.index > cutoff]
                if not last_5y.empty:
                    st.line_chart(last_5y)
                    months = last_5y.index.month.value_counts().index[:4].tolist()
                    st.success(f"📅 歷史派息月份: {', '.join([f'{m}月' for m in sorted(months)])}")

        with c2:
            st.write("**💰 投資計算**")
            lot = st.number_input(f"手動校正每手股數:", value=int(res['每手股數']), key=f"lot_{res['代碼']}")
            st.metric("最低入場費", f"{res['現價'] * lot:,.2f} {res['幣種']}")
            
            if ".HK" in res['代碼']:
                clean_code = res['代碼'].replace('.HK','').zfill(5)
                hkex_url = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={clean_code}"
                st.link_button("🔍 披露易：查看官方公告", hkex_url)
            else:
                st.warning("🇺🇸 美股注意 30% 股息稅")

# --- 4. 自定義對比功能 ---
st.sidebar.divider()
st.sidebar.header("➕ 手動加入對比 (最多10隻)")
manual_input = st.sidebar.text_input("輸入代碼 (逗號分隔):", "")
if manual_input:
    st.info("手動輸入的代碼將顯示在下方或更新排名。")
