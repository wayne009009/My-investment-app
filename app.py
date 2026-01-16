import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import numpy as np

st.set_page_config(page_title="全球收息雙榜大師", layout="wide")

# --- 核心運算：四維防禦系統 ---
def get_security_analysis(symbol, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        
        # 1. 財務健康檢查
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        payout = info.get('payoutRatio', 0)
        
        # 2. 3年業績檢查
        fin = tk.financials
        is_safe_3y = "✅ 穩健"
        if fin is not None and 'Net Income' in fin.index:
            last_3y = fin.loc['Net Income'].head(3)
            if (last_3y <= 0).any() or len(last_3y) < 3: is_safe_3y = "🚨 波動"
        
        # 3. RSI 避險指標
        hist = tk.history(period="3mo")
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain/loss))).iloc[-1]
        
        # 4. 派息與手數計算
        price = info.get('currentPrice', 0)
        div = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        # 港股手數設定 (自定義常見手數)
        lot_map = {"0005.HK": 400, "0011.HK": 100, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, "1398.HK": 1000, "3988.HK": 1000, "0003.HK": 1000, "2638.HK": 500, "0066.HK": 500}
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        
        # 官方鏈接
        link = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={symbol.replace('.HK','').zfill(5)}" if is_hk else f"https://www.sec.gov/edgar/browse/?CIK={symbol}"

        return {
            "公司": info.get('shortName', symbol),
            "股息率%": round((div/price)*100, 2) if price > 0 else 0,
            "一手金金": f"{price * lot_size:,.0f}",
            "一手派息": f"{div * lot_size:,.1f}",
            "D/E(債務)": round(de_ratio, 2),
            "Payout(派息比)": f"{payout*100:.1f}%",
            "3年業績": is_safe_3y,
            "RSI時機": round(rsi, 1),
            "建議": "🟢 持有" if rsi < 65 else "🔴 過熱避開",
            "官方新聞": link
        }
    except: return None

# --- 榜單定義 ---
HK_TOP10 = ["01171.HK", "00883.HK", "00941.HK", "00939.HK", "01398.HK", "03988.HK", "00005.HK", "00011.HK", "02638.HK", "00003.HK"]
US_TOP10 = ["MO", "T", "PFE", "VZ", "EPD", "O", "ABBV", "SCHD", "VYM", "KO"]

st.title("🛡️ 2026 全球收息防禦系統 (港/美各 Top 10)")
st.sidebar.header("🔍 自由查詢")
user_input = st.sidebar.text_input("輸入代碼 (例: 0016.HK):").strip().upper()

if st.button("🚀 啟動四維安全掃描"):
    t1, t2, t3 = st.tabs(["🇭🇰 香港高息 Top 10", "🇺🇸 美國高息 Top 10", "🧐 自由查詢"])
    
    with t1:
        res_hk = [get_security_analysis(s, True) for s in HK_TOP10]
        df_hk = pd.DataFrame([r for r in res_hk if r]).sort_values("股息率%", ascending=False).reset_index(drop=True)
        df_hk.index += 1
        st.table(df_hk.drop(columns=['官方新聞']))
        for i, r in df_hk.iterrows():
            st.link_button(f"第 {i} 名: {r['公司']} 官方新聞", r['官方新聞'])

    with t2:
        res_us = [get_security_analysis(s, False) for s in US_TOP10]
        df_us = pd.DataFrame([r for r in res_us if r]).sort_values("股息率%", ascending=False).reset_index(drop=True)
        df_us.index += 1
        st.table(df_us.drop(columns=['官方新聞']))
        for i, r in df_us.iterrows():
            st.link_button(f"第 {i} 名: {r['公司']} SEC 公告", r['官方新聞'])

    with t3:
        if user_input:
            res = get_security_analysis(user_input, ".HK" in user_input)
            if res: st.write(res)
