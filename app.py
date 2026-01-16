import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

st.set_page_config(page_title="全球收息終極戰情室", layout="wide")

# --- 1. 輔助功能：判定派息頻率 ---
def detect_frequency(divs):
    if divs.empty or len(divs) < 2: return "每年/不定期"
    # 取最近兩次派息日期的間隔
    diff = (divs.index[-1] - divs.index[-2]).days
    diff = abs(diff)
    
    if 60 <= diff <= 110: return "每季 (3個月收一次)"
    elif 150 <= diff <= 210: return "每半年 (6個月收一次)"
    elif 330 <= diff <= 400: return "每年 (1年收一次)" # 放寬範圍以適應騰訊等年配股
    else: return "不定期"

# --- 2. 核心數據抓取 (包含錢不夠的處理) ---
def get_mega_data(symbol, budget, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        # 使用 fast_info 獲取價格更穩定
        price = tk.fast_info.get('last_price', None)
        if price is None: return None # 代碼錯誤

        info = tk.info
        divs = tk.dividends

        # --- A. 基礎資料 ---
        # 嘗試獲取股息率，如果沒有則設為 0
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        
        # 匯率與一手成本
        exch_rate = 1.0 if is_hk else 7.8
        price_hkd = price * exch_rate
        
        # 港股一手股數定義 (加入 0700)
        lot_map = {
            "0005.HK": 400, "0011.HK": 100, "0941.HK": 500, "0883.HK": 1000, 
            "0939.HK": 1000, "1398.HK": 1000, "3988.HK": 1000, "0003.HK": 1000, 
            "0823.HK": 100, "1171.HK": 2000, "0700.HK": 100, "0016.HK": 1000, "0001.HK": 500
        }
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        one_lot_cost_hkd = price_hkd * lot_size
        
        # --- B. 5萬元實戰計算 (關鍵修改：錢不夠也顯示) ---
        if budget >= one_lot_cost_hkd:
            max_lots = int(budget // one_lot_cost_hkd)
            total_cost_hkd = max_lots * one_lot_cost_hkd
            remaining_cash = budget - total_cost_hkd
            strategy_text = f"✅ 買 {max_lots} 手"
            est_income = (div_rate * exch_rate) * (max_lots * lot_size)
        else:
            # 錢不夠的情況
            shortfall = one_lot_cost_hkd - budget
            max_lots = 0
            total_cost_hkd = 0
            remaining_cash = budget
            strategy_text = f"❌ 缺 ${shortfall:,.0f}"
            est_income = 0
        
        # --- C. 安全與估值指標 ---
        payout = info.get('payoutRatio', 0) if info.get('payoutRatio') else 0
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        
        # 頻率判定 (騰訊等年配股需要較長歷史數據)
        freq = detect_frequency(divs.tail(5))
        
        # 目標價邏輯 (加入詳細說明)
        five_yr_avg = info.get('fiveYearAvgDividendYield', 0) / 100.0
        if five_yr_avg > 0 and div_rate > 0:
            target_price = div_rate / (five_yr_avg * 1.05)
            # 判斷狀態
            val_status = "💎 特價" if price <= target_price else "⚠️ 溢價"
        else:
            target_price = 0
            val_status = "⚪ 無數據"

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
            if loss.iloc[-1] != 0:
                rsi = 100 - (100 / (1 + (gain.iloc[-1]/loss.iloc[-1])))
            else:
                rsi = 100

        # 官方連結
        link = f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={symbol.replace('.HK','').lstrip('0')}" if is_hk else f"https://www.sec.gov/edgar/browse/?CIK={symbol}"

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "頻率": freq, # 移到前面，方便投資者看時間
            "一手入場費": f"${one_lot_cost_hkd:,.0f}", # 顯示一手要多少錢
            "實戰策略": strategy_text,
            "預計年息(HKD)": f"${est_income:,.0f}",
            "估值狀態": val_status,
            "股息率%": round((div_rate/price)*100, 2),
            "目標價": round(target_price, 2) if target_price > 0 else "N/A",
            "RSI": round(rsi, 0),
            "link": link
        }
    except Exception as e: 
        return None

# --- 3. 歷史溯源功能 (修復 0700 抓取問題) ---
def get_history_check(symbol):
    try:
        tk = yf.Ticker(symbol)
        # 1. 先確認代碼是否存在
        price = tk.fast_info.get('last_price', None)
        if price is None:
            return "INVALID_CODE", None
            
        # 2. 獲取派息 (放寬到 3 年，因為騰訊是年配，有時候 2 年只抓到一次)
        divs = tk.dividends
        if divs.empty:
            return "NO_DIVS", None
            
        three_years_ago = datetime.datetime.now() - datetime.timedelta(days=1095)
        divs = divs[divs.index >= three_years_ago].sort_index(ascending=False)
        
        if divs.empty:
            return "NO_RECENT_DIVS", None

        data = []
        for date, amt in divs.items():
            # 抓取除淨日前後的股價
            h = tk.history(start=date - datetime.timedelta(days=1), end=date+datetime.timedelta(days=5))
            if not h.empty:
                close_price = h['Close'].iloc[0]
                data.append({
                    "除淨日期": date.strftime('%Y-%m-%d'),
                    "派息金額": amt,
                    "當日股價": round(close_price, 2),
                    "單次回報": f"{(amt/close_price)*100:.2f}%"
                })
        return "SUCCESS", pd.DataFrame(data)
    except: return "ERROR", None

# --- UI 佈局 ---
st.title("🛡️ 全球收息終極戰情室 (資金效率版)")

# 側邊欄：輸入與說明
with st.sidebar:
    st.header("💰 實戰預算設定")
    user_budget = st.number_input("您的投資本金 (HKD):", value=50000, step=1000)
    
    st.divider()
    with st.expander("📊 估值狀態是如何判斷的？(點擊展開)"):
        st.markdown("""
        我們使用 **歷史平均殖利率法** 來判斷貴與便宜：
        
        $$目標價 = \\frac{目前股息}{5年平均股息率 \\times 1.05}$$
        
        1. **💎 特價**: 現價 < 目標價。代表現在的股息率比過去 5 年平均還要高（包含 5% 安全邊際），值得買入。
        2. **⚠️ 溢價**: 現價 > 目標價。代表現在股價漲多了，導致股息率變低，買入的性價比不高。
        3. **⚪ 無數據**: 該股票可能派息不穩定或上市不足 5 年。
        """)

    st.info("💡 資金有限者請注意「一手入場費」與「實戰策略」欄位。若顯示 ❌，代表您的本金不足以買入一手。")

# 列表定義 (加入 0700 騰訊測試)
HK_LIST = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "0011.HK", "0003.HK", "0823.HK", "1171.HK"]
US_LIST = ["MO", "T", "PFE", "VZ", "EPD", "O", "SCHD", "KO"]

# 主功能區
if st.button("🚀 啟動掃描 (含資金與頻率分析)"):
    t1, t2 = st.tabs(["🇭🇰 港股 (注意一手門檻)", "🇺🇸 美股 (靈活配置)"])
    
    for tab, stocks, is_hk in zip([t1, t2], [HK_LIST, US_LIST], [True, False]):
        with tab:
            res = []
            progress = st.progress(0, text="正在分析價格與派息頻率...")
            for i, s in enumerate(stocks):
                d = get_mega_data(s, user_budget, is_hk)
                if d: res.append(d)
                progress.progress((i+1)/len(stocks))
            
            if res:
                df = pd.DataFrame(res)
                # 將 "實戰策略" 移到前面
                cols = ["代碼", "公司", "實戰策略", "一手入場費", "頻率", "估值狀態", "股息率%", "RSI", "link"]
                st.dataframe(
                    df[cols],
                    column_config={
                        "實戰策略": st.column_config.TextColumn("實戰策略", help="根據您的本金計算"),
                        "頻率": st.column_config.TextColumn("派息週期", help="越頻繁，資金回籠越快"),
                        "估值狀態": st.column_config.TextColumn("估值", help="特價代表性價比高"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # 官方連結區
                st.caption("🔗 點擊前往官方公告：")
                col_links = st.columns(6)
                for i, row in df.iterrows():
                    col_links[i % 6].link_button(row['代碼'], row['link'])

st.divider()

# --- 歷史溯源與頻率教學 ---
st.subheader("🕰️ 個股派息溯源 & 資金時間控制")
st.markdown("由於資金有限，**派息頻率**決定了您的現金流轉速度。請在下方查詢以確認：")

col1, col2 = st.columns([1, 2])
with col1:
    search_code = st.text_input("輸入代碼查詢 (例 0700.HK):").strip().upper()
    
if search_code:
    status, hist_df = get_history_check(search_code)
    
    if status == "SUCCESS":
        # 自動判斷頻率並給出建議
        freq = detect_frequency(hist_df['派息金額'])
        st.success(f"📊 {search_code} 查詢成功！ 判定週期：**{freq}**")
        
        if "年" in freq:
            st.warning(f"⚠️ **注意資金佔用**：{search_code} 是一年派一次息。如果您現在買入，可能需要等很久才能拿到現金。適合不需要短期現金流的長線資金。")
        elif "季" in freq:
            st.info(f"✅ **資金效率高**：{search_code} 是每季派息。現金回流快，適合需要靈活周轉的資金。")
            
        st.table(hist_df)
    elif status == "INVALID_CODE":
        st.error(f"❌ 找不到代碼 {search_code}，港股請記得加 .HK (例如 0700.HK)")
    elif status == "NO_DIVS":
        st.warning(f"⚠️ {search_code} 是一隻成長股，過去 3 年似乎沒有派息紀錄 (或數據缺失)。")
    elif status == "NO_RECENT_DIVS":
        st.warning(f"⚠️ {search_code} 過去 3 年內沒有派息紀錄。")

st.divider()
with st.expander("📚 資金有限？如何利用「派息頻率」控制投資時間 (必讀)"):
    st.markdown("""
    當資金只有 5 萬元時，**「等待時間」** 是最大的成本。
    
    1. **每季派息 (Quarterly)** 🇺🇸 美股 / 匯豐 (0005.HK)
       - **優點**：每 3 個月就有錢進帳。如果急需用錢，或者想把股息再投資，這種頻率效率最高。
       - **策略**：適合當作「每月零用錢」的來源。
       
    2. **每半年派息 (Semi-Annual)** 🇭🇰 大部分港股 (0941, 0939)
       - **優點**：單次派息金額通常較大 (中期+末期)。
       - **缺點**：買入後可能要等 5-6 個月才看得到回頭錢。
       - **策略**：**一定要看「除淨日」**！如果在除淨日前 1 個月買入，效率最高；如果在除淨日剛過後買入，資金要「坐牢」半年。
       
    3. **每年派息 (Annual)** 🇨🇳 騰訊 (0700), 國企紅籌
       - **風險**：一年只發一次。錯過了除淨日，就要再等 365 天。
       - **策略**：除非有極大的股價價差 (特價)，否則對於只有 5 萬元且需要現金流的人來說，**不建議重倉**，因為資金會被鎖死太久。
    """)
