import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 輔助功能：判定派息頻率 ---
def detect_frequency(divs):
    if divs.empty or len(divs) < 2: return "不定期"
    diff = (divs.index[-1] - divs.index[-2]).days
    diff = abs(diff)
    if 60 <= diff <= 110: return "每季 (4次/年)"
    elif 150 <= diff <= 210: return "每半年 (2次/年)"
    elif 330 <= diff <= 390: return "每年 (1次/年)"
    else: return "不定期"

# --- 2. 核心數據抓取與計算 ---
def get_mega_data(symbol, budget, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        divs = tk.dividends
        if not info or 'currentPrice' not in info: return None

        # --- A. 基礎資料 ---
        price = info.get('currentPrice', 0)
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        # 匯率處理 (美股轉港幣計算預算)
        exch_rate = 1.0 if is_hk else 7.8
        price_hkd = price * exch_rate
        
        # 港股一手股數定義
        lot_map = {
            "0005.HK": 400, "0011.HK": 100, "0941.HK": 500, "0883.HK": 1000, 
            "0939.HK": 1000, "1398.HK": 1000, "3988.HK": 1000, "0003.HK": 1000, 
            "0823.HK": 100, "1171.HK": 2000, "0001.HK": 500, "0002.HK": 500, "0016.HK": 1000
        }
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        one_lot_cost = price * lot_size # 原幣別
        
        # --- B. 5萬元實戰計算 ---
        # 買入門檻 (HKD)
        entry_fee_hkd = price_hkd * lot_size
        max_lots = int(budget // entry_fee_hkd)
        total_cost_hkd = max_lots * entry_fee_hkd
        remaining_cash = budget - total_cost_hkd
        est_annual_income_hkd = (div_rate * exch_rate) * (max_lots * lot_size)
        
        # --- C. 安全與估值指標 ---
        payout = info.get('payoutRatio', 0)
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        freq = detect_frequency(divs.tail(5))
        
        # 目標價 (5年平均 + 5% 安全邊際)
        five_yr_avg = info.get('fiveYearAvgDividendYield', 0) / 100.0
        target_price = div_rate / (five_yr_avg * 1.05) if five_yr_avg > 0 else price * 0.9
        valuation_status = "💎 特價" if price <= target_price else "⚠️ 溢價"

        # 3年業績
        fin = tk.financials
        is_safe_3y = "✅ 穩"
        if fin is not None and not fin.empty and 'Net Income' in fin.index:
            if (fin.loc['Net Income'].head(3) <= 0).any(): is_safe_3y = "🚨 虧損"

        # --- D. 技術時機 (RSI) ---
        hist = tk.history(period="3mo")
        rsi = 50
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain.iloc[-1]/loss.iloc[-1])))

        # 官方連結
        link = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={symbol.replace('.HK','').lstrip('0')}" if is_hk else f"https://www.sec.gov/edgar/browse/?CIK={symbol}"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "股息率%": round((div_rate/price)*100, 2),
            "頻率": freq,
            "一手成本(原幣)": f"{one_lot_cost:,.0f}",
            "實戰策略": f"買 {max_lots} 手" if max_lots > 0 else "❌ 錢不夠",
            "總花費(HKD)": f"${total_cost_hkd:,.0f}",
            "剩餘現金": f"${remaining_cash:,.0f}",
            "預計年息(HKD)": f"${est_annual_income_hkd:,.0f}",
            "估值": valuation_status,
            "目標價": round(target_price, 2),
            "Payout": f"{payout*100:.0f}%",
            "D/E": round(de_ratio, 2),
            "業績": is_safe_3y,
            "RSI": round(rsi, 0),
            "link": link
        }
    except: return None

# --- 3. 歷史溯源功能 ---
def get_history_check(symbol):
    try:
        tk = yf.Ticker(symbol)
        divs = tk.dividends
        if divs.empty: return None
        # 取過去2年
        two_years_ago = datetime.datetime.now() - datetime.timedelta(days=730)
        divs = divs[divs.index >= two_years_ago].sort_index(ascending=False)
        
        data = []
        for date, amt in divs.items():
            h = tk.history(start=date, end=date+datetime.timedelta(days=5)) # 寬限幾天找數據
            price = h['Close'].iloc[0] if not h.empty else 0
            data.append({
                "除淨日期": date.strftime('%Y-%m-%d'),
                "派息金額": amt,
                "當日股價": round(price, 2),
                "單次殖利率": f"{(amt/price)*100:.2f}%" if price > 0 else "N/A"
            })
        return pd.DataFrame(data)
    except: return None

# --- UI 佈局 ---
st.title("🛡️ 全球收息終極戰情室 (全功能整合版)")

# 側邊欄：預算與說明
with st.sidebar:
    st.header("💰 實戰預算設定")
    user_budget = st.number_input("您的投資本金 (HKD):", value=50000, step=1000)
    st.divider()
    st.info("此系統已整合：\n1. 一手成本/頻率\n2. 5萬元最大購買量\n3. D/E 與 Payout 安全指標\n4. 目標價估值")
    st.divider()
    st.markdown("**指標教學:**")
    st.markdown("- **D/E > 2**: 負債高 (危險)")
    st.markdown("- **Payout > 100%**: 吃老本 (危險)")
    st.markdown("- **RSI > 70**: 過熱 (勿追)")

# 列表定義
HK_LIST = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "1398.HK", "3988.HK", "0011.HK", "0003.HK", "0823.HK", "1171.HK"]
US_LIST = ["MO", "T", "PFE", "VZ", "EPD", "O", "ABBV", "KO", "SCHD", "VYM"]

# 主功能區
if st.button("🚀 啟動全盤掃描 (含預算分析)"):
    t1, t2 = st.tabs(["🇭🇰 港股全覽", "🇺🇸 美股全覽"])
    
    for tab, stocks, is_hk in zip([t1, t2], [HK_LIST, US_LIST], [True, False]):
        with tab:
            with st.spinner("正在計算估值與預算策略..."):
                res = []
                for s in stocks:
                    d = get_mega_data(s, user_budget, is_hk)
                    if d: res.append(d)
                
                if res:
                    df = pd.DataFrame(res).sort_values("股息率%", ascending=False).reset_index(drop=True)
                    df.index += 1
                    
                    # 顯示大表格
                    st.dataframe(
                        df.drop(columns=["link"]),
                        column_config={
                            "估值": st.column_config.TextColumn("估值狀態", help="特價代表現價低於目標價"),
                            "RSI": st.column_config.NumberColumn("RSI", format="%.0f"),
                        },
                        use_container_width=True
                    )
                    
                    st.caption("💡 提示：點擊下方按鈕可跳轉至官方公告")
                    cols = st.columns(5)
                    for i, row in df.iterrows():
                        cols[i % 5].link_button(f"{row['代碼']} 公告", row['link'])

st.divider()

# 歷史溯源區
st.subheader("🕰️ 過去 2 年派息與股價溯源 (賺息蝕價檢查)")
col1, col2 = st.columns([1, 3])
with col1:
    search_code = st.text_input("輸入代碼 (例 0005.HK):").strip().upper()
with col2:
    st.write("") # Spacer

if search_code:
    hist_df = get_history_check(search_code)
    if hist_df is not None:
        st.success(f"📊 {search_code} 歷史派息紀錄抓取成功")
        st.table(hist_df)
        st.info("💡 觀察重點：若每次除淨後股價都長期低於『當日股價』，代表無法填息，需小心賺息蝕價。")
    else:
        st.error("查無資料，請確認代碼正確 (港股需加 .HK)")
