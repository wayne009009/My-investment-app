import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="5萬元收息實戰策劃", layout="wide")

# --- 核心邏輯：預算與最大購買量計算 ---
def analyze_budget_buy(symbol, budget_hkd=50000, is_hk=True):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        if not info or 'currentPrice' not in info: return None
        
        # 1. 獲取價格與匯率
        price = info.get('currentPrice', 0)
        # 簡單匯率轉換: 美股 USD 1 = HKD 7.8
        exch_rate = 1.0 if is_hk else 7.8
        price_hkd = price * exch_rate
        
        # 2. 判斷一手股數
        lot_map = {
            "0005.HK": 400, "0011.HK": 100, "0941.HK": 500, "0883.HK": 1000, 
            "0939.HK": 1000, "1398.HK": 1000, "3988.HK": 1000, "0003.HK": 1000, 
            "0823.HK": 100, "1171.HK": 2000
        }
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        
        # 一手入場費 (HKD)
        entry_fee = price_hkd * lot_size
        
        # 如果一手都買不起，直接剔除
        if entry_fee > budget_hkd:
            return None
            
        # 3. 計算 5 萬元能買幾手
        max_lots = int(budget_hkd // entry_fee)
        total_cost = max_lots * entry_fee
        remaining_cash = budget_hkd - total_cost
        
        # 4. 預計每年收息
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        # 美股股息也要換算回 HKD 顯示方便比較
        annual_income = (div_rate * exch_rate) * (max_lots * lot_size)
        
        # 5. 買入時機分析 (RSI + 估值)
        hist = tk.history(period="3mo")
        rsi = 50
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain.iloc[-1]/loss.iloc[-1])))
            
        # 目標價邏輯
        five_yr_avg = info.get('fiveYearAvgDividendYield', 0) / 100.0
        target_price = div_rate / (five_yr_avg * 1.05) if five_yr_avg > 0 else price * 0.9
        
        action = "🛑 觀望"
        if price <= target_price and rsi < 40: action = "🔥 強烈買入 (雙重訊號)"
        elif price <= target_price: action = "✅ 買入 (估值便宜)"
        elif rsi < 35: action = "✅ 買入 (技術超賣)"
        elif rsi > 70: action = "⚠️ 嚴重超買 (勿追)"
        
        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "現價": f"{price:.2f} {info.get('currency')}",
            "策略": f"買入 {max_lots} 手/股",
            "總成本(HKD)": f"${total_cost:,.0f}",
            "剩餘現金(HKD)": f"${remaining_cash:,.0f}",
            "預計年收息(HKD)": f"${annual_income:,.0f}",
            "回報率": f"{(annual_income/total_cost)*100:.2f}%",
            "時機建議": action,
            "RSI": round(rsi, 1)
        }
    except: return None

# --- UI ---
st.title("🎯 5萬元資金：精準狙擊實戰表")
st.info("此表格僅顯示「5 萬元內買得起」的股票，並自動計算最大購買量。")

budget = st.number_input("您的投資本金 (HKD):", value=50000, step=1000)

HK_TARGETS = ["0941.HK", "0883.HK", "0939.HK", "1398.HK", "0005.HK", "0003.HK", "0823.HK", "0011.HK"]
US_TARGETS = ["SCHD", "O", "T", "KO", "VZ", "MO"]

if st.button("🚀 計算最佳買入組合"):
    t1, t2 = st.tabs(["🇭🇰 港股方案", "🇺🇸 美股方案"])
    
    with t1:
        res = [analyze_budget_buy(s, budget, True) for s in HK_TARGETS]
        df = pd.DataFrame([r for r in res if r]).sort_values("回報率", ascending=False).reset_index(drop=True)
        df.index += 1
        st.table(df)
        st.markdown("**💡 港股策略：** 由於有一手限制，建議優先選擇「剩餘現金」較少的選項，以避免資金閒置。")
        
    with t2:
        res = [analyze_budget_buy(s, budget, False) for s in US_TARGETS]
        df = pd.DataFrame([r for r in res if r]).sort_values("回報率", ascending=False).reset_index(drop=True)
        df.index += 1
        st.table(df)
        st.markdown("**💡 美股策略：** 美股可買碎股 (視券商而定) 或單股，此表以「買入整數股」計算，靈活性極高。")

st.divider()
st.subheader("⚠️ 重要：什麼時候按下買入鍵？")
st.markdown("""
1. **看 RSI**：表格中的 RSI 數值如果顯示 **< 35**，代表短期跌過頭了，這是 5 萬元進場的最佳時機，通常能買在相對低點。
2. **避開除淨日前夕**：如果下週就要除淨（派息），股價通常會比較高。**除淨日當天**股價會下跌，那時候買通常更便宜。
3. **不要頻繁交易**：您只有 5 萬，買入後請**鎖倉不動**。每次買賣的手續費對小本金來說是重傷。
""")
