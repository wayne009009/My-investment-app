import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="專業穩健投資工具", layout="wide")

st.title("🏆 專業穩健投資者分析儀表板")
st.write("集成港美股對比、派息歷史、真實收益計算及披露易追蹤。")

# --- 側邊欄設定 ---
st.sidebar.header("🔍 全球股票搜尋")
user_input = st.sidebar.text_input("輸入多個代碼 (用逗號分隔):", "0005.HK, 2800.HK, SCHD, O")
broker_fee_rate = st.sidebar.number_input("券商佣金 %", value=0.03, format="%.3f") / 100
invest_amount = st.sidebar.number_input("預計投入金額 (每隻股票)", value=100000)

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
        lot_size = info.get('sharesPerLot', 1) if ".HK" in symbol else 1
        
        # 披露易連結 (僅限港股)
        hkex_url = f"https://www.hkexnews.hk/sdsearch/searchcas.aspx?shareholder={symbol.replace('.HK','')}" if ".HK" in symbol else "N/A"
        
        return {
            "代碼": symbol,
            "公司": info.get('shortName'),
            "現價": price,
            "幣種": curr,
            "股息率": f"{div_yield*100:.2f}%",
            "每股派息": div_rate,
            "每手股數": lot_size,
            "最低入場費": price * lot_size,
            "披露易": hkex_url,
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
    df = pd.DataFrame(results)
    
    # --- 選項 A: 多股票橫向對比 ---
    st.subheader("📊 多股票橫向對比")
    st.dataframe(df.drop(columns=['object', '披露易']), use_container_width=True)

    # --- 選項 B & C: 詳細分析 ---
    st.divider()
    tabs = st.tabs([f"分析: {r['代碼']}" for r in results])
    
    for i, tab in enumerate(tabs):
        res = results[i]
        tk_obj = res['object']
        
        with tab:
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.write(f"### {res['公司']} ({res['代碼']})")
                # 歷史派息圖表 (選項 B)
                st.write("**📅 過去五年派息趨勢**")
                hist_div = tk_obj.dividends
                if not hist_div.empty:
                    last_5y = hist_div[hist_div.index > (datetime.datetime.now() - datetime.timedelta(days=5*365))]
                    st.line_chart(last_5y)
                    
                    # 預測派息月份
                    months = last_5y.index.month.value_counts().index[:4].tolist()
                    months_str = ", ".join([f"{m}月" for m in sorted(months)])
                    st.success(f"💡 歷史慣常派息月份: {months_str}")
                else:
                    st.write("無法取得派息歷史。")

            with c2:
                # 真實收益計算 (選項 C)
                st.write("**💰 真實年度收益估算**")
                shares = invest_amount / res['現價']
                gross_div = shares * res['每股派息']
                
                if ".HK" in res['代碼']:
                    net_div = gross_div - 30 # 假設代收費 30 HKD
                    tax_info = "已扣除估計代收費 $30"
                else:
                    net_div = gross_div * 0.7 # 美股 30% 稅
                    tax_info = "已扣除 30% 股息代扣稅"
                
                st.metric("預計年領現金", f"{net_div:,.2f} {res['幣種']}")
                st.caption(tax_info)
                
                # 披露易連結
                if res['披露易'] != "N/A":
                    st.link_button("🔍 前往披露易查看官方公告", res['披露易'])
                
                st.info("🔄 策略提示: 派息後如欲轉倉，可參考同表內 Yield 較高且派息月份接續的股票。")

else:
    st.error("請在左側輸入正確的股票代碼。")
