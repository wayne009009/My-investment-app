import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

st.set_page_config(page_title="全球收息終極監控系統", layout="wide")

# --- 1. 計算工具 ---
def get_final_data(symbol, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        if not info or 'currentPrice' not in info: return None
        
        price = info.get('currentPrice', 0)
        payout = info.get('payoutRatio', 0)
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        # 5年平均股息率 (估值核心)
        five_year_avg_yield = info.get('fiveYearAvgDividendYield', 0) / 100.0 if info.get('fiveYearAvgDividendYield') else (div_rate / price if price > 0 else 0)
        
        # 目標買入價計算: 假設我們要獲得比歷史平均更好的收益 (溢價 5% 安全邊際)
        # 公式: 目標價 = 每股股息 / (歷史平均殖利率 * 1.05)
        target_price = div_rate / (five_year_avg_yield * 1.05) if five_year_avg_yield > 0 else price * 0.9
        
        # 業績與 RSI
        fin = tk.financials
        is_safe_3y = "✅ 穩健"
        if fin is not None and not fin.empty and 'Net Income' in fin.index:
            if (fin.loc['Net Income'].head(3) <= 0).any(): is_safe_3y = "🚨 波動"

        hist = tk.history(period="3mo")
        rsi = 50
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + (gain.iloc[-1]/loss.iloc[-1])))

        status = "💎 特價中" if price <= target_price else "⚠️ 溢價中"
        
        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "現價": round(price, 2),
            "目標買入價": round(target_price, 2),
            "估值狀態": status,
            "Payout(派息比)": payout,
            "D/E(債務比)": round(de_ratio, 2),
            "股息率%": round((div_rate/price)*100, 2),
            "3年業績": is_safe_3y,
            "RSI時機": round(rsi, 1),
            "link": f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={symbol.replace('.HK','').lstrip('0')}" if is_hk else f"https://www.sec.gov/edgar/browse/?CIK={symbol}"
        }
    except: return None

# --- 2. 指標說明 ---
with st.sidebar:
    st.header("📖 估值邏輯")
    st.write("**目標買入價計算：**")
    st.latex(r"Target = \frac{Dividend}{5YrAvgYield \times 1.05}")
    st.write("我們在歷史平均殖利率基礎上，再要求 5% 的折扣作為**安全邊際**。")
    st.divider()
    st.info("💎 **特價中**: 現價 < 目標價 (適合建倉)\n\n⚠️ **溢價中**: 現價 > 目標價 (建議等待回調)")

# --- 3. 畫面顯示 ---
st.title("🛡️ 2026 全球收息防禦與估值系統")

HK_LIST = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "1398.HK", "3988.HK", "0011.HK", "0003.HK", "0823.HK", "1171.HK"]
US_LIST = ["MO", "T", "PFE", "VZ", "EPD", "O", "ABBV", "KO", "SCHD", "VYM"]

if st.button("🚀 啟動全方位估值掃描"):
    t1, t2 = st.tabs(["🇭🇰 港股估值榜", "🇺🇸 美股估值榜"])
    
    for tab, stocks, is_hk in zip([t1, t2], [HK_LIST, US_LIST], [True, False]):
        with tab:
            res = []
            bar = st.progress(0)
            for i, s in enumerate(stocks):
                data = get_final_data(s, is_hk)
                if data: res.append(data)
                bar.progress((i+1)/len(stocks))
            
            if res:
                df = pd.DataFrame(res).sort_values("Payout(派息比)").reset_index(drop=True)
                df.index += 1
                # 格式化
                df_show = df.copy()
                df_show["Payout(派息比)"] = df_show["Payout(派息比)"].apply(lambda x: f"{x*100:.1f}%")
                st.table(df_show.drop(columns=["link"]))
                
                for _, row in df.iterrows():
                    st.link_button(f"🔗 查看 {row['公司']} 官方新聞", row['link'])

st.divider()
st.subheader("🕰️ 派息歷史查詢")
search = st.text_input("輸入代碼 (例: 0941.HK):").strip().upper()
if search:
    tk = yf.Ticker(search)
    divs = tk.dividends.tail(8).sort_index(ascending=False)
    if not divs.empty:
        st.write(divs)
    else: st.error("查無紀錄")
