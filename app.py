import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 1. 頁面專業美化配置 ---
st.set_page_config(page_title="全球收息終極戰情室 Pro", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1e212b; padding: 15px; border-radius: 10px; border-left: 5px solid #00d4ff; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    h1, h2, h3 { color: #00d4ff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 強大數據引擎 (修復 0700.HK 與 超時問題) ---
@st.cache_data(ttl=3600) # 緩存1小時，極大降低被封鎖機率
def get_stock_data_pro(symbol, budget):
    try:
        tk = yf.Ticker(symbol)
        # 優先使用快取資訊
        info = tk.info
        price = info.get('currentPrice') or info.get('previousClose')
        if not price: return None

        # 核心數據 fallback 邏輯：確保 0700.HK 有資料
        div_rate = info.get('trailingAnnualDividendRate') or info.get('dividendRate') or 0
        
        # 抓取派息歷史 (限 1 年確保速度)
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=366)
        div_history = tk.dividends[tk.dividends.index.date >= start_date]
        
        # A. 派息月份 (💰)
        months = sorted(list(set(div_history.index.month))) if not div_history.empty else []

        # B. 5萬預算實戰策略
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
                   "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100)
        cost_per_lot = price * lot_size
        
        if budget >= cost_per_lot:
            lots = int(budget // cost_per_lot)
            strategy = f"✅ 買入 {lots} 手"
            rem_cash = budget - (lots * cost_per_lot)
            est_income = div_rate * lots * lot_size
        else:
            strategy = f"❌ 資金不足 (缺 ${int(cost_per_lot - budget)})"
            rem_cash = budget
            est_income = 0

        # C. 估值狀態 (💎) & RSI (時機)
        avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"
        
        hist = tk.history(period="1mo")
        rsi = 50 # 預設中性
        if len(hist) > 10:
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).mean()
            loss = -delta.where(delta < 0, 0).mean()
            if loss != 0: rsi = 100 - (100 / (1 + (gain/loss)))

        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "現價": price,
            "策略": strategy,
            "估值": val,
            "股息率%": round((div_rate/price)*100, 2) if price > 0 else 0,
            "一手成本": cost_per_lot,
            "年回報預期": est_income,
            "RSI": rsi,
            "months": months,
            "history": div_history
        }
    except: return None

# --- 3. UI 佈局 ---
st.title("🛡️ 全球收息終極戰情室 Pro")
st.markdown("#### 基於 1 年數據優化版 | 穩定性與視覺雙重升級")

with st.sidebar:
    st.header("💰 實戰預算設定")
    budget = st.number_input("HKD 本金:", value=50000, step=5000)
    st.divider()
    if st.button("🔄 強制刷新數據"):
        st.cache_data.clear()
        st.rerun()

# 掃描名單
STOCKS = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]

# 顯示載入進度
with st.spinner("🚀 正在接入全球金融 API 並解析 0700.HK 等數據..."):
    results = []
    for s in STOCKS:
        data = get_stock_data_pro(s, budget)
        if data: results.append(data)

if results:
    df = pd.DataFrame(results)

    # --- 功能 A: 頂部戰情指標 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("預計組合年股息總收", f"${df['年回報預期'].sum():,.0f} HKD")
    c2.metric("平均股息率", f"{df['股息率%'].mean():.2f}%")
    c3.metric("監控個股數量", f"{len(df)} 隻")

    st.divider()

    # --- 功能 B: 12個月 💰 派息表 ---
    st.subheader("🗓️ 全年派息月份分佈預測")
    m_rows = []
    for _, r in df.iterrows():
        m_row = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
        m_rows.append(m_row)
    st.table(pd.DataFrame(m_rows, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

    # --- 功能 C: 專業實戰數據大表 ---
    st.subheader("📊 5萬預算實戰策略一覽")
    st.dataframe(
        df[["代碼", "公司", "策略", "估值", "股息率%", "一手成本", "年回報預期", "RSI"]],
        column_config={
            "股息率%": st.column_config.NumberColumn("股息率", format="%.2f%%"),
            "一手成本": st.column_config.NumberColumn("一手成本", format="$%d"),
            "年回報預期": st.column_config.NumberColumn("預計年息", format="$%d"),
            "RSI": st.column_config.ProgressColumn("買入時機 (RSI)", min_value=0, max_value=100, format="%.0f"),
        },
        use_container_width=True, hide_index=True
    )

st.divider()

# --- 功能 D: 深度溯源 (解決 0700.HK 查無資料問題) ---
st.subheader("🔍 個股深度溯源")
search = st.text_input("輸入代碼查看詳細派息紀錄 (如: 0700.HK):").strip().upper()
if search:
    res = get_stock_data_pro(search, budget)
    if res:
        col_l, col_r = st.columns([1, 2])
        col_l.write(f"### {res['公司']} ({search})")
        col_l.write(f"**目前估值：** {res['估值']}")
        col_l.write(f"**派息月份：** {res['months']}")
        
        col_r.write("#### 📅 最近 1 年派息明細 (含除淨日)")
        if not res['history'].empty:
            col_r.write(res['history'].sort_index(ascending=False))
        else:
            col_r.warning("注意：該股 1 年內可能以實物派息，或尚未公佈現金息。")
    else:
        st.error("查無資料，請確認代碼含 .HK")
