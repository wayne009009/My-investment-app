import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 頁面配置 ---
st.set_page_config(page_title="全球收息終極戰情室 Pro", layout="wide", initial_sidebar_state="expanded")

# --- 自定義 CSS 強化 UI ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00d4ff; }
    .stDataFrame { border-radius: 10px; }
    .status-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 核心邏輯 (保留並優化) ---
@st.cache_data(ttl=600)
def get_stock_pro_data(symbol, budget, is_hk=True):
    try:
        tk = yf.Ticker(symbol)
        fast = tk.fast_info
        price = fast.get('last_price')
        if not price or price <= 0: return None
        
        info = tk.info
        # 抓取 1 年內數據確保穩定
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=366)
        divs = tk.dividends[tk.dividends.index.date >= start_date]
        
        # 基礎指標
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0) or 0
        exch_rate = 1.0 if is_hk else 7.8
        
        # 一手成本計算
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
                   "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        one_lot_cost_hkd = price * exch_rate * lot_size
        
        # 實戰策略
        if budget >= one_lot_cost_hkd:
            lots = int(budget // one_lot_cost_hkd)
            strategy = f"✅ 買入 {lots} 手"
            rem_cash = budget - (lots * one_lot_cost_hkd)
            est_income = div_rate * exch_rate * lots * lot_size
        else:
            strategy = f"❌ 資金不足 (缺 ${one_lot_cost_hkd - budget:,.0f})"
            rem_cash = budget
            est_income = 0

        # 安全指標
        payout = info.get('payoutRatio', 0)
        de_ratio = info.get('debtToEquity', 0) / 100.0 if info.get('debtToEquity') else 0
        
        # 估值 (5年平均)
        avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"

        # RSI 計算
        hist = tk.history(period="3mo")
        rsi = 50
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
            rsi = 100 - (100 / (1 + (gain/loss))) if loss != 0 else 100

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "策略": strategy,
            "估值": val,
            "股息率%": round((div_rate/price)*100, 2),
            "一手成本": one_lot_cost_hkd,
            "預計年息": est_income,
            "剩餘現金": rem_cash,
            "RSI": round(rsi, 1),
            "Payout%": round(payout * 100, 1),
            "D/E": round(de_ratio, 2),
            "months": sorted(list(set(divs.index.month))),
            "raw_divs": divs
        }
    except: return None

# --- 2. UI 側邊欄 ---
with st.sidebar:
    st.title("💰 資金配置")
    user_budget = st.number_input("您的投資本金 (HKD)", value=50000, step=5000)
    st.divider()
    
    with st.expander("📚 指標說明書"):
        st.markdown("""
        - **💎 特價**: 現價低於歷史平均，安全邊際高。
        - **RSI > 70**: 市場過熱，短期不宜追高。
        - **Payout > 100%**: 派息超過利潤，不可持續。
        - **D/E > 2**: 負債比率較高，風險增加。
        """)
    
    if st.button("🔄 刷新即時數據", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 3. 主界面內容 ---
st.markdown("# 🛡️ 全球收息終極戰情室")
st.markdown("### 實時資產配置與風險掃描")

HK_LIST = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

# 執行分析
results = []
for s in HK_LIST:
    data = get_stock_pro_data(s, user_budget)
    if data: results.append(data)

if results:
    df = pd.DataFrame(results)
    
    # --- 頂部關鍵指標卡片 ---
    c1, c2, c3, c4 = st.columns(4)
    total_income = df['預計年息'].sum()
    avg_yield = df['股息率%'].mean()
    
    c1.metric("預計年總利息", f"HKD ${total_income:,.0f}")
    c2.metric("平均股息率", f"{avg_yield:.2f}%")
    c3.metric("監控代碼總數", f"{len(df)} 隻")
    c4.metric("最大現金回補", f"HKD ${df['剩餘現金'].min():,.0f}")

    st.divider()

    # --- 核心數據分析表 ---
    st.subheader("📊 投資組合實戰分析")
    st.dataframe(
        df,
        column_config={
            "代碼": st.column_config.TextColumn("代碼"),
            "策略": st.column_config.TextColumn("實戰建議", width="medium"),
            "股息率%": st.column_config.NumberColumn("股息率", format="%.2f%%"),
            "一手成本": st.column_config.NumberColumn("一手入場費", format="$%d"),
            "預計年息": st.column_config.NumberColumn("年回報", format="$%d"),
            "RSI": st.column_config.ProgressColumn("買入時機 (RSI)", min_value=0, max_value=100, format="%.0f"),
            "Payout%": st.column_config.NumberColumn("派息比率", format="%.1f%%"),
            "D/E": st.column_config.NumberColumn("槓桿率 (D/E)"),
        },
        hide_index=True,
        use_container_width=True
    )

    # --- 派息時間月曆表 (💰) ---
    st.divider()
    st.subheader("🗓️ 派息現金流預算 (💰 標註為發錢月份)")
    m_data = []
    for _, r in df.iterrows():
        row = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
        m_data.append(row)
    
    st.table(pd.DataFrame(m_data, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

# --- 4. 個股深度溯源 (整合 UI) ---
st.divider()
st.subheader("🔍 個股深度溯源 (填息能力檢查)")
sc1, sc2 = st.columns([1, 2])

with sc1:
    search_code = st.text_input("輸入股票代碼 (例如: 0700.HK)").strip().upper()

if search_code:
    res = get_stock_pro_data(search_code, user_budget)
    if res:
        with sc2:
            st.success(f"已成功載入 {res['公司']} ({search_code}) 的年度分析資料")
            
        hist_cols = st.columns(3)
        hist_cols[0].metric("1年累計派息", f"${res['raw_divs'].sum():.2f}")
        hist_cols[1].metric("估值狀態", res['估值'])
        hist_cols[2].metric("當前 RSI", res['RSI'])
        
        st.markdown("#### 📅 最近 1 年派息明細")
        st.write(res['raw_divs'].sort_index(ascending=False))
    else:
        st.error("代碼有誤或 Yahoo Finance 暫時無回應")

# --- 頁腳 ---
st.caption("數據來源：Yahoo Finance | 本系統僅供參考，投資前請務必自行審慎評估風險。")
