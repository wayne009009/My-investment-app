import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="全球收息雙榜大師", layout="wide")

# --- 核心運算：四維防禦系統 ---
def get_security_analysis(symbol, is_hk=False):
    try:
        # 修正港股代碼格式
        formatted_symbol = symbol
        tk = yf.Ticker(formatted_symbol)
        
        # 獲取基礎資訊 (使用 fast_info 提高穩定性)
        info = tk.info
        if not info or 'currentPrice' not in info:
            return None
            
        # 1. 財務健康檢查
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        payout = info.get('payoutRatio', 0)
        
        # 2. 3年業績檢查
        fin = tk.financials
        is_safe_3y = "✅ 穩健"
        if fin is not None and not fin.empty and 'Net Income' in fin.index:
            last_3y = fin.loc['Net Income'].head(3)
            if (last_3y <= 0).any(): is_safe_3y = "🚨 波動"
        
        # 3. RSI 避險指標
        hist = tk.history(period="3mo")
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
        else:
            rsi = 50 # 數據不足時設為中性
        
        # 4. 派息與手數計算
        price = info.get('currentPrice', 0)
        div = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        # 港股手數設定
        lot_map = {
            "0005.HK": 400, "0011.HK": 100, "0941.HK": 500, "0883.HK": 1000, 
            "0939.HK": 1000, "1398.HK": 1000, "3988.HK": 1000, "0003.HK": 1000, 
            "2638.HK": 500, "0066.HK": 500
        }
        lot_size = lot_map.get(formatted_symbol, 100) if is_hk else 1
        
        # 官方鏈接
        link = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={formatted_symbol.replace('.HK','').lstrip('0')}" if is_hk else f"https://www.sec.gov/edgar/browse/?CIK={formatted_symbol}"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "股息率%": round((div/price)*100, 2) if price > 0 else 0,
            "一手成本": f"{price * lot_size:,.0f}",
            "一手年息預估": f"{div * lot_size:,.1f}",
            "D/E(債務比)": round(de_ratio, 2),
            "Payout(派息比)": f"{payout*100:.1f}%",
            "3年業績": is_safe_3y,
            "RSI時機": round(rsi, 1),
            "建議": "🟢 持有" if rsi < 65 else "🔴 過熱避開",
            "官方新聞連結": link
        }
    except Exception as e:
        return None

# --- 榜單定義 ---
HK_TOP10 = ["0005.HK", "0011.HK", "0941.HK", "0883.HK", "0939.HK", "1398.HK", "3988.HK", "0003.HK", "2638.HK", "0066.HK"]
US_TOP10 = ["MO", "T", "PFE", "VZ", "EPD", "O", "ABBV", "SCHD", "VYM", "KO"]

st.title("🛡️ 全球收息防禦系統 (港/美 Top 10)")

if st.button("🚀 啟動港美雙榜掃描"):
    t1, t2 = st.tabs(["🇭🇰 香港高息榜", "🇺🇸 美國高息榜"])
    
    with t1:
        res_hk = []
        progress_hk = st.progress(0, text="獲取港股數據中...")
        for i, s in enumerate(HK_TOP10):
            data = get_security_analysis(s, True)
            if data: res_hk.append(data)
            progress_hk.progress((i + 1) / len(HK_TOP10))
            
        if res_hk:
            df_hk = pd.DataFrame(res_hk).sort_values("股息率%", ascending=False).reset_index(drop=True)
            df_hk.index += 1
            st.table(df_hk.drop(columns=['官方新聞連結']))
            for idx, row in df_hk.iterrows():
                st.link_button(f"查看 第{idx}名 {row['公司']} 最新公告", row['官方新聞連結'])
        else:
            st.error("暫時無法獲取港股數據，請稍後再試。")

    with t2:
        res_us = []
        progress_us = st.progress(0, text="獲取美股數據中...")
        for i, s in enumerate(US_TOP10):
            data = get_security_analysis(s, False)
            if data: res_us.append(data)
            progress_us.progress((i + 1) / len(US_TOP10))
            
        if res_us:
            df_us = pd.DataFrame(res_us).sort_values("股息率%", ascending=False).reset_index(drop=True)
            df_us.index += 1
            st.table(df_us.drop(columns=['官方新聞連結']))
            for idx, row in df_us.iterrows():
                st.link_button(f"查看 第{idx}名 {row['公司']} SEC公告", row['官方新聞連結'])
        else:
            st.error("暫時無法獲取美股數據。")
