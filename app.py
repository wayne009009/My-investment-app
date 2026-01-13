import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="專業穩健投資工具", layout="wide")

st.title("🏆 專業穩健投資者分析儀表板")
st.write("集成港美股對比、派息歷史、真實收益計算及披露易追蹤。")

# --- 側邊欄設定 ---
st.sidebar.header("🔍 全球股票搜尋")
user_input = st.sidebar.text_input("輸入多個代碼 (用逗號分隔):", "0005.HK, 0700.HK, SCHD, O")
broker_fee_rate = st.sidebar.number_input("券商佣金 %", value=0.03, format="%.3f") / 100
invest_amount = st.sidebar.number_input("預計投入金額 (每隻股票)", value=100, step=100) * 1000 # 以千為單位

tickers = [t.strip().upper() for t in user_input.split(",")]

# --- 數據處理函式 ---
def get_stock_metrics(symbol):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        if not info or 'currentPrice' not in info: return None
        
        price = info.get('currentPrice')
        div_rate = info.get('dividendRate', 0)
        div_yield = info.get('dividendYield', 0)
        curr = info.get('currency', 'USD')
        
        # --- 修正每手股數邏輯 ---
        # 如果 yfinance 抓不到或回傳 1 (港股通常不可能是 1)，則給予警告
        lot_size = info.get('sharesPerLot', 1)
        is_hk = ".HK" in symbol
        
        # 披露易精確跳轉：直接導向該股的「股息及權益」公告分類
        hkex_url = "N/A"
        if is_hk:
            clean_code = symbol.replace('.HK','').zfill(5)
            # 這是披露易公告搜尋的深層連結格式
            hkex_url = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={clean_code}"
        
        return {
            "代碼": symbol,
            "公司": info.get('shortName'),
            "現價": price,
            "幣種": curr,
            "股息率": f"{div_yield*100:.2f}%",
            "每股派息": div_rate,
            "每手股數": int(lot_size),
            "hkex": hkex_url,
            "is_hk": is_hk,
            "object": tk
        }
    except:
        return None

# --- 執行抓取 ---
results = []
for t in tickers:
    data = get_stock_metrics(t)
    if data: results.append(data)

if results:
    # --- 選項 A: 多股票橫久對比 ---
    st.subheader("📊 多股票橫向對比")
    display_df = pd.DataFrame(results).drop(columns=['object', 'hkex', 'is_hk'])
    st.dataframe(display_df, use_container_width=True)
    st.warning("⚠️ 提示：若港股『每手股數』顯示為 1，代表數據源暫無該資訊，請以披露易公告為準。")

    # --- 詳細分析 ---
    st.divider()
    tabs = st.tabs([f"分析: {r['代碼']}" for r in results])
    
    for i, tab in enumerate(tabs):
        res = results[i]
        tk_obj = res['object']
        
        with tab:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                # 歷史派息趨勢 (修正時區)
                hist_div = tk_obj.dividends
                if not hist_div.empty:
                    utc = pytz.UTC
                    cutoff = utc.localize(datetime.datetime.now() - datetime.timedelta(days=5*365))
                    last_5y = hist_div[hist_div.index > cutoff]
                    if not last_5y.empty:
                        st.line_chart(last_5y)
                        months = last_5y.index.month.value_counts().index[:4].tolist()
                        st.success(f"💡 歷史慣常派息月份: {', '.join([f'{m}月' for m in sorted(months)])}")

            with c2:
                st.write("**💰 投資成本與收益**")
                # 讓用戶手動校準每手股數
                correct_lot = st.number_input(f"校正 {res['代碼']} 每手股數:", value=res['每手股數'], step=1, key=f"lot_{res['代碼']}")
                min_entry = res['現價'] * correct_lot
                st.metric("最低入場費", f"{min_entry:,.2f} {res['幣種']}")
                
                st.divider()
                if res['is_hk']:
                    st.link_button("🔗 披露易：查看最新股息公告", res['hkex'])
                    st.caption("建議在此確認最新的『每手股數』與『除淨日』")
                else:
                    st.write("🇺🇸 美股通常以 1 股為單位交易。")

else:
    st.error("請確認輸入的代碼格式正確。")
                
              
