import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

st.set_page_config(page_title="全球收息終極安全監控", layout="wide")

def get_final_safety_info(symbol, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        
        # 1. 債務股本比 (D/E Ratio)
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        
        # 2. 派息比率 (Payout Ratio) - yfinance 傳回小數 (0.8 代表 80%)
        payout_ratio = info.get('payoutRatio', 0)
        
        # 3. 3年盈利檢查
        financials = tk.financials
        is_safe_3y = False
        if financials is not None and 'Net Income' in financials.index:
            last_3y = financials.loc['Net Income'].head(3)
            is_safe_3y = (last_3y > 0).all()

        # 4. RSI 技術指標 (時機)
        hist = tk.history(period="3mo")
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain/loss))).iloc[-1]

        # 5. 綜合評分與警示
        score = 100
        alerts = []
        if not is_safe_3y: 
            score -= 40; alerts.append("🚨 盈利中斷")
        if de_ratio > 2.0: 
            score -= 20; alerts.append("⚠️ 債務沈重")
        if payout_ratio > 1.0: 
            score -= 30; alerts.append("🛑 竭澤而漁 (發放超過利潤)")
        if rsi > 70: 
            score -= 10; alerts.append("⏳ 股價過熱")

        price = info.get('currentPrice', 0)
        div = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        # 官方連結處理
        code_for_hk = symbol.replace('.HK','').zfill(5)
        official_link = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={code_for_hk}" if is_hk else f"https://www.sec.gov/edgar/browse/?CIK={symbol}"

        return {
            "代碼": symbol,
            "安全分": score,
            "評級": "🛡️ 極安全" if score >= 80 else ("⚠️ 觀察" if score >= 50 else "💣 高風險"),
            "D/E (債務比)": round(de_ratio, 2),
            "Payout (派息比)": f"{payout_ratio*100:.1f}%",
            "3年業績": "✅ 穩定" if is_safe_3y else "❌ 虧損",
            "RSI時機": round(rsi, 1),
            "股息率": f"{(div/price)*100:.2f}%" if price > 0 else "0%",
            "警示標籤": " | ".join(alerts) if alerts else "良好",
            "官方新聞": official_link
        }
    except: return None

# 主界面
st.title("💰 全球收息終極監控：避開「賺息蝕價」災難")
st.markdown("### 四維防禦體系：債務、盈利、派息可持續性、技術時機")

STOCKS = ["0005.HK", "0939.HK", "0011.HK", "0941.HK", "KO", "O", "T", "VZ", "SCHD"]

if st.button("🚀 執行全方位風險掃描"):
    data = [get_final_safety_info(s, ".HK" in s) for s in STOCKS]
    df = pd.DataFrame([d for d in data if d]).sort_values("安全分", ascending=False)
    
    # 顯示主表格
    st.dataframe(df.drop(columns=['官方新聞']), use_container_width=True)
    
    # 官方連結與行動建議
    st.subheader("📢 官方即時消息與行動建議")
    for _, r in df.iterrows():
        with st.expander(f"查看 {r['代碼']} 的詳細分析與連結"):
            st.write(f"**目前狀態：** {r['評級']}")
            st.write(f"**風險分析：** {r['警示標籤']}")
            if r['RSI時機'] > 70:
                st.error(f"建議：{r['代碼']} 目前股價過熱 (RSI={r['RSI時機']})，現在買入極易面臨 Readjustment 回調，請等待 RSI 回落至 50 以下。")
            st.link_button(f"🔗 前往政府/交易所官方平台 (查最新派息消息)", r['官方新聞'])
