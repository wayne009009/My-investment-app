import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 1. 頁面專業美化與樣式 ---
st.set_page_config(page_title="全球收息終極戰情室 Pro Max", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #00d4ff !important; }
    .stDataFrame { border-radius: 10px; }
    .instruction-card {
        background-color: #1e212b;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00d4ff;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心數據引擎 (修復 0700.HK 補償機制) ---
@st.cache_data(ttl=600)
def get_full_analysis(symbol, budget, is_hk=True):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        price = info.get('currentPrice') or info.get('previousClose')
        if not price: return None

        # A. 數據補償：修復抓不到派息數據的問題
        div_rate = info.get('trailingAnnualDividendRate') or info.get('dividendRate') or 0
        today = datetime.date.today()
        # 追蹤 500 天確保能抓到年配息
        div_history = tk.dividends[tk.dividends.index.date >= (today - datetime.timedelta(days=500))]
        
        # B. 派息月份 (💰) 與 倒數 (🔥)
        months = sorted(list(set(div_history.index.month))) if not div_history.empty else []
        countdown = "確認中"
        if not div_history.empty:
            last_ex = div_history.index[-1].date()
            est_next = last_ex + datetime.timedelta(days=365)
            diff = (est_next - today).days
            countdown = f"🔥 {diff}天" if 0 < diff <= 30 else f"{diff}天" if diff > 0 else "已過除淨"

        # C. 預算策略與一手成本
        exch = 1.0 if is_hk else 7.8
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
                   "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        one_lot_hkd = price * exch * lot_size
        
        # D. 實戰配單邏輯
        if budget >= one_lot_hkd:
            lots = int(budget // one_lot_hkd)
            strategy = f"✅ 買 {lots} 手"
            rem_cash = budget - (lots * one_lot_hkd)
            annual_inc = div_rate * exch * (lots * lot_size)
        else:
            strategy = f"❌ 缺 ${int(one_lot_hkd - budget)}"
            rem_cash = budget
            annual_inc = 0

        # E. 安全與估值指標
        avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"
        payout = info.get('payoutRatio', 0)
        de_ratio = (info.get('debtToEquity', 0) / 100.0) if info.get('debtToEquity') else 0
        
        # F. RSI 計算
        hist = tk.history(period="1mo")
        rsi = 50
        if len(hist) > 10:
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).mean()
            loss = -delta.where(delta < 0, 0).mean()
            if loss != 0: rsi = 100 - (100 / (1 + (gain/loss)))

        return {
            "代碼": symbol, "公司": info.get('shortName', symbol), "策略": strategy,
            "估值": val, "倒數": countdown, "股息率%": round((div_rate/price)*100, 2),
            "一手成本": one_lot_hkd, "預計年息": annual_inc, "剩餘現金": rem_cash,
            "RSI": rsi, "Payout%": payout*100, "D/E": de_ratio, "months": months, "history": div_history,
            "raw_div": div_rate, "lot_size": lot_size
        }
    except: return None

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("💰 實戰配置設定")
    # 使用 unique key 避免 DuplicateElementId
    budget = st.number_input("您的總本金 (HKD):", value=50000, step=5000, key="budget_input")
    st.divider()
    if st.button("🔄 全盤數據重整", key="refresh_all"):
        st.cache_data.clear()
        st.rerun()

# --- 4. 主界面與 Tabs ---
st.title("🛡️ 全球收息終極戰情室 Pro Max")

HK_LIST = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]
US_LIST = ["SCHD", "VYM", "O", "MO", "KO", "T"]

t1, t2 = st.tabs(["🇭🇰 港股戰區", "🇺🇸 美股戰區"])

for tab, stocks, is_hk in zip([t1, t2], [HK_LIST, US_LIST], [True, False]):
    with tab:
        res_list = [get_full_analysis(s, budget, is_hk) for s in stocks if get_full_analysis(s, budget, is_hk)]
        
        if res_list:
            df = pd.DataFrame(res_list)

            # --- 💡 智能組合教學模式 ---
            st.subheader("🤖 組合操作建議 (具體買入順序)")
            # 優先選特價股並按倒數天數排列
            teaching_df = df[df['估值'] == "💎 特價"].sort_values('倒數')
            if teaching_df.empty: teaching_df = df.sort_values('倒數')

            temp_budget = budget
            portfolio = []
            cols = st.columns(3)
            for i, (_, row) in enumerate(teaching_df.iterrows()):
                if temp_budget >= row['一手成本'] and len(portfolio) < 3:
                    portfolio.append(row)
                    temp_budget -= row['一手成本']
                    with cols[len(portfolio)-1]:
                        st.markdown(f"""
                        <div class="instruction-card">
                        <b>第 {len(portfolio)} 步買入：{row['代碼']}</b><br>
                        支出：${row['一手成本']:,.0f}<br>
                        目標：{row['months']} 月收息<br>
                        狀態：{row['估值']} / {row['倒數']}
                        </div>
                        """, unsafe_allow_html=True)

            # 關鍵指標卡
            total_inc = sum([p['預計年息'] for p in portfolio])
            m1, m2, m3 = st.columns(3)
            m1.metric("預計組合年息", f"${total_inc:,.0f} HKD")
            m2.metric("剩餘備用金", f"${temp_budget:,.0f} HKD")
            m3.metric("組合收益率", f"{(total_inc/budget)*100:.2f}%")

            # 1. 12個月派息表
            st.subheader("🗓️ 全年派息月份預測 (💰)")
            m_rows = [[r['公司']] + [("💰" if m in r['months'] else "") for m in range(1, 13)] for r in res_list]
            st.table(pd.DataFrame(m_rows, columns=["公司"] + [f"{m}月" for m in range(1, 13)]))

            # 2. 實戰數據大表
            st.subheader("📊 全維度市場數據掃描")
            st.dataframe(
                df[["代碼", "公司", "策略", "估值", "倒數", "股息率%", "一手成本", "預計年息", "RSI", "Payout%", "D/E"]],
                column_config={
                    "股息率%": st.column_config.NumberColumn("股息率", format="%.2f%%"),
                    "RSI": st.column_config.ProgressColumn("買入時機(RSI)", min_value=0, max_value=100, format="%.0f"),
                    "一手成本": st.column_config.NumberColumn("成本", format="$%d"),
                },
                use_container_width=True, hide_index=True
            )

# --- 5. 個股深度溯源 (含 0700.HK) ---
st.divider()
st.subheader("🔍 個股深度溯源 (填息與歷史檢查)")
search = st.text_input("輸入代碼 (例: 0700.HK):", key="search_box").strip().upper()
if search:
    res = get_full_analysis(search, budget, (".HK" in search))
    if res:
        ca, cb = st.columns([1, 2])
        with ca:
            st.write(f"### {res['公司']} ({search})")
            st.write(f"**實戰策略：** {res['策略']}")
            st.write(f"**安全指標：** Payout {res['Payout%']:.0f}% / D/E {res['D/E']:.2f}")
        with cb:
            st.write("#### 📅 1.5 年內派息紀錄")
            st.write(res['history'].sort_index(ascending=False))
    else:
        st.error("查無資料，請檢查代碼或稍後再試。")
