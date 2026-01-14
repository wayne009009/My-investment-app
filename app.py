import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="全球收息佈局精準版", layout="wide")

# --- 港股每手股數資料庫 (手動校準以確保準確) ---
HK_LOT_SIZES = {
    "0005.HK": 400, "0011.HK": 100, "0939.HK": 1000, "1398.HK": 1000,
    "3988.HK": 1000, "0941.HK": 500, "0883.HK": 1000, "0003.HK": 1000,
    "0066.HK": 500, "2800.HK": 500
}

def get_accurate_info(symbol, is_hk=False):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        
        # 1. 3年業績檢查 (Net Income)
        earnings = tk.financials
        is_safe_3y = "未知"
        if earnings is not None and not earnings.empty and 'Net Income' in earnings.index:
            last_3y = earnings.loc['Net Income'].head(3)
            is_safe_3y = "✅ 正面" if (last_3y > 0).all() else "🚨 虧損"
        
        # 2. 派息日期修復邏輯
        ex_date, pay_date = "N/A", "N/A"
        # 優先從日曆抓取
        cal = tk.calendar
        if cal is not None and isinstance(cal, dict):
            if 'Dividend Date' in cal: ex_date = cal['Dividend Date'].strftime('%Y-%m-%d')
            if 'Payment Date' in cal: pay_date = cal['Payment Date'].strftime('%Y-%m-%d')
        
        # 若日曆為空，從歷史紀錄抓取最近一次
        if ex_date == "N/A":
            actions = tk.actions
            if not actions.empty:
                divs_only = actions[actions['Dividends'] > 0]
                if not divs_only.empty:
                    ex_date = divs_only.index[-1].strftime('%Y-%m-%d') + " (上次)"

        # 3. 每手股數與成本計算
        price = info.get('currentPrice', 0)
        lot_size = HK_LOT_SIZES.get(symbol, 1) if is_hk else 1
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        return {
            "代碼": symbol,
            "公司": info.get('shortName', symbol),
            "現價": price,
            "一手股數": lot_size,
            "一手成本": f"{price * lot_size:,.2f}",
            "一手年息": f"{div_rate * lot_size:,.2f}",
            "股息率": f"{ (div_rate/price)*100:.2f}%" if price > 0 else "0.00%",
            "除淨日": ex_date,
            "派息日": pay_date,
            "3年業績": is_safe_3y,
            "幣種": info.get('currency', 'USD')
        }
    except: return None

# --- 側邊欄 ---
st.sidebar.header("🔍 自由輸入查詢")
custom_code = st.sidebar.text_input("輸入代碼 (例: 0016.HK):").strip().upper()

# --- 主頁面 ---
st.title("💰 全球收息佈局：數據校準版")
if st.button("🚀 啟動港美股數據掃描"):
    hk_df = pd.DataFrame([get_accurate_info(s, True) for s in HK_LOT_SIZES.keys() if get_accurate_info(s, True)])
    us_list = ["SCHD", "O", "VICI", "JEPI", "VIG", "VYM", "KO", "PEP", "MO", "T"]
    us_df = pd.DataFrame([get_accurate_info(s, False) for s in us_list if get_accurate_info(s, False)])
    
    t1, t2, t3 = st.tabs(["🇭🇰 港股 Top 10", "🇺🇸 美股 Top 10", "🧐 自由查詢"])
    with t1:
        st.dataframe(hk_df, use_container_width=True)
        for s in HK_LOT_SIZES.keys():
            st.link_button(f"🔗 {s} 披露易公告", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={s.replace('.HK','').zfill(5)}")
    with t2:
        st.dataframe(us_df, use_container_width=True)
    with t3:
        if custom_code:
            res = get_accurate_info(custom_code, ".HK" in custom_code)
            if res: st.json(res)
            else: st.error("查無資料")
else:
    st.info("請點擊按鈕獲取數據。")
