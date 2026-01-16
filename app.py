import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 1. 專業介面與樣式配置 ---
st.set_page_config(page_title="全球收息終極戰情室 Pro Max", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #00d4ff !important; }
    .stDataFrame { border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心數據引擎 (具備 0700.HK 補償機制) ---
@st.cache_data(ttl=600)
def get_mega_analysis(symbol, budget, is_hk=True):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        price = info.get('currentPrice') or info.get('previousClose')
        if not price: return None

        # A. 股息數據補償邏輯 (修復 0700.HK 查無資料)
        div_rate = info.get('trailingAnnualDividendRate') or info.get('dividendRate') or 0
        today = datetime.date.today()
        # 抓取 1.5 年確保 0700.HK 年配息能被抓到
        div_history = tk.dividends[tk.dividends.index.date >= (today - datetime.timedelta(days=500))]
        
        # B. 派息月份 (💰) 與 發錢倒數 (🔥)
        months = sorted(list(set(div_history.index.month))) if not div_history.empty else []
        countdown = "確認中"
        if not div_history.empty:
            last_ex = div_history.index[-1].date()
            est_next = last_ex + datetime.timedelta(days=365)
            diff = (est_next - today).days
            countdown = f"🔥 {diff}天" if 0 < diff <= 30 else f"{diff}天" if diff > 0 else "已過除淨"

        # C. 匯率與一手成本 (HKD 轉換)
        exch = 1.0 if is_hk else 7.8
        lot_map = {"0005.HK": 400, "0941.HK": 500, "0883.HK": 1000, "0939.HK": 1000, 
                   "0700.HK": 100, "1398.HK": 1000, "3988.HK": 1000, "0011.HK": 100, "0823.HK": 100}
        lot_size = lot_map.get(symbol, 100) if is_hk else 1
        one_lot_hkd = price * exch * lot_size
        
        # D. 5萬預算策略
        if budget >= one_lot_hkd:
            lots = int(budget // one_lot_hkd)
            strategy = f"✅ 買 {lots} 手"
            rem_cash = budget - (lots * one_lot_hkd)
            annual_inc = div_rate * exch * lots * lot_size
        else:
            strategy = f"❌ 缺 ${int(one_lot_hkd - budget)}"
            rem_cash = budget
            annual_inc = 0

        # E. 安全指標與估值
        avg_y = info.get('fiveYearAvgDividendYield', 0) / 100.0
        val = "💎 特價" if avg_y > 0 and price <= (div_rate / (avg_y * 1.05)) else "⚠️ 溢價"
        payout = info.get('payoutRatio', 0)
        de_ratio = info.get('debtToEquity', 0) / 100.0
        
        # RSI 時機
        hist = tk.history(period="1mo")
        rsi = 50
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).mean()
            loss = -delta.where(delta < 0, 0).mean()
            if loss != 0: rsi = 100 - (100 / (1 + (gain/loss)))

        return {
            "代碼": symbol, "公司": info.get('shortName', symbol), "策略": strategy,
            "估值": val, "倒數": countdown, "股息率%": round((div_rate/price)*100, 2),
            "一手成本": one_lot_hkd, "預計年息": annual_inc, "剩餘現金": rem_cash,
            "RSI": rsi, "Payout%": payout*100, "D/E": de_ratio, "months": months, "history": div_history
        }
    except: return None

# --- 3. UI 介面佈局 ---
st.title("🛡️ 全球收息終極戰情室 Pro Max")

with st.sidebar:
    st.header("💰 實戰預算設定")
    budget = st.number_input("HKD 本金:", value=50000, step=5000)
    st.divider()
    with st.expander("📚 指標定義"):
        st.write("💎 特價: 現價低於歷史平均")
        st.write("🔥 倒數: 距離下次派息預估天數")
        st.write("💰 表: 該股在這些月份會發錢")
    if st.button("🔄 全盤數據刷新"):
        st.cache_data.clear()
        st.rerun()

HK_LIST = ["0005.HK", "0941.HK", "0883.HK", "0939.HK", "0700.HK", "1398.HK", "3988.HK", "0011.HK", "0823.HK"]
US_LIST = ["SCHD", "VYM", "O", "MO", "KO", "T"]

t1, t2 = st.tabs(["🇭🇰 港股核心 (一手門檻)", "🇺🇸 美股配置 (靈活買入)"])

for tab, stocks, is_hk in zip([t1, t2], [HK_LIST, US_LIST], [True, False]):
    with tab:
        res_list = []
        for s in stocks:
            data = get_mega_analysis(s, budget, is_hk)
            if data: res_list.append(data)
        
        if res_list:
            df = pd.DataFrame(res_list)
            
            # 頂部戰情卡片
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("預計組合年息", f"${df['預計年息'].sum():,.0f} HKD")
            c2.metric("平均股息率", f"{df['股息率%'].mean():.2f}%")
            c3.metric("最低剩餘現金", f"${df['剩餘現金'].min():,.0f}")
            c4.metric("監控總數", f"{len(df)} 隻")

            # 1. 12個月派息表 (💰)
            st.subheader("🗓️ 全年派息月份分佈 (💰)")
            m_rows = []
            for _, r in df.iterrows():
                row = [r['公司']] + [("💰" if i in r['months'] else "") for i in range(1, 13)]
                m_rows.append(row)
            st.table(pd.DataFrame(m_rows, columns=["公司"] + [f"{i}月" for i in range(1, 13)]))

            # 2. 綜合實戰大表
            st.subheader("📊 5萬預算全維度分析")
            st.dataframe(
                df[["代碼", "公司", "策略", "估值", "倒數", "股息率%", "一手成本", "預計年息", "RSI", "Payout%", "D/E"]],
                column_config={
                    "股息率%": st.column_config.NumberColumn("股息率", format="%.2f%%"),
                    "一手成本": st.column_config.NumberColumn("一手成本(HKD)", format="$%d"),
                    "預計年息": st.column_config.NumberColumn("年收息", format="$%d"),
                    "RSI": st.column_config.ProgressColumn("時機(RSI)", min_value=0, max_value=100, format="%.0f"),
                    "Payout%": st.column_config.NumberColumn("派息比", format="%.0f%%"),
                },
                use_container_width=True, hide_index=True
            )

# --- 4. 歷史溯源與個股檢查 ---
st.divider()
st.subheader("🔍 個股深度溯源 (填息能力檢查)")
search = st.text_input("輸入代碼 (例: 0700.HK):").strip().upper()
if search:
    res = get_mega_analysis(search, budget, (".HK" in search))
    if res:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.write(f"### {res['公司']} ({search})")
            st.write(f"**實戰建議：** {res['策略']}")
            st.write(f"**估值狀態：** {res['估值']}")
            st.write(f"**安全指標：** Payout {res['Payout%']:.0f}% / D/E {res['D/E']:.2f}")
        with col_b:
            st.write("#### 📅 1年內派息歷史紀錄")
            st.write(res['history'].sort_index(ascending=False))
    else:
        st.error("查無資料，請確認代碼正確")
