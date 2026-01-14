import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import io

st.set_page_config(page_title="全球收息佈局大師", layout="wide")

# --- 核心運算：3年盈利、每手計算、派息日期 ---
def get_advanced_info(tk_obj, is_hk=False):
    try:
        info = tk_obj.info
        # 1. 盈利檢查 (過去3年 Net Income)
        hist_earnings = tk_obj.financials
        is_safe_3y = "未知"
        if hist_earnings is not None and not hist_earnings.empty:
            if 'Net Income' in hist_earnings.index:
                last_3y_net = hist_earnings.loc['Net Income'].head(3)
                is_safe_3y = "✅ 正面" if (last_3y_net > 0).all() else "🚨 虧損"
        
        # 2. 派息日期與除淨日 (從 calendar 獲取)
        ex_date_str = "N/A"
        pay_date_str = "N/A"
        days_to_ex = 999
        try:
            cal = tk_obj.calendar
            if cal is not None:
                if 'Dividend Date' in cal:
                    ex_date = cal['Dividend Date']
                    ex_date_str = ex_date.strftime('%Y-%m-%d')
                    days_to_ex = (ex_date - datetime.datetime.now().date()).days
                if 'Payment Date' in cal:
                    pay_date_str = cal['Payment Date'].strftime('%Y-%m-%d')
        except: pass

        # 3. 每手費用與派息計算
        price = info.get('currentPrice', 0)
        lot_size = info.get('sharesPerLot', 1) if is_hk else 1 
        div_rate = info.get('trailingAnnualDividendRate', 0) or info.get('dividendRate', 0)
        
        return {
            "公司": info.get('shortName', 'N/A'),
            "現價": price,
            "一手股數": lot_size,
            "一手成本": price * lot_size,
            "一手年息": div_rate * lot_size,
            "股息率": (div_rate / price) if price > 0 else 0,
            "除淨日": ex_date_str,
            "派息日": pay_date_str,
            "除淨倒數": days_to_ex,
            "3年業績": is_safe_3y,
            "幣種": info.get('currency', 'USD')
        }
    except: return None

# --- 側邊欄：自由查詢 ---
st.sidebar.header("🔍 自由輸入查詢")
custom_code = st.sidebar.text_input("輸入代碼 (例: 0941.HK 或 O):").strip().upper()

# --- 主頁面 ---
st.title("💰 全球收息佈局：除淨日與業績掃描")

HK_LIST = ["0005.HK", "0011.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0003.HK", "0066.HK", "2800.HK"]
US_LIST = ["SCHD", "O", "VICI", "JEPI", "VIG", "VYM", "KO", "PEP", "MO", "T"]

def process_list(symbols, is_hk=False):
    data = []
    for s in symbols:
        res = get_advanced_info(yf.Ticker(s), is_hk)
        if res:
            res['代碼'] = s
            data.append(res)
    return pd.DataFrame(data)

if st.button("🚀 啟動港美股數據掃描"):
    tab1, tab2, tab3 = st.tabs(["🇭🇰 港股 Top 10", "🇺🇸 美股 Top 10", "🧐 自由查詢結果"])
    
    with tab1:
        df_hk = process_list(HK_LIST, True)
        if not df_hk.empty:
            # 整理顯示格式
            df_hk['股息率'] = df_hk['股息率'].apply(lambda x: f"{x*100:.2f}%")
            display_cols = ["代碼", "公司", "現價", "一手成本", "一手年息", "股息率", "除淨日", "派息日", "3年業績"]
            st.dataframe(df_hk[display_cols], use_container_width=True)
            
            for _, r in df_hk.iterrows():
                code = r['代碼'].replace('.HK','').zfill(5)
                st.link_button(f"🔗 {r['代碼']} 披露易公告 (查派息消息)", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={code}")
    
    with tab2:
        df_us = process_list(US_LIST, False)
        if not df_us.empty:
            df_us['股息率'] = df_us['股息率'].apply(lambda x: f"{x*100:.2f}%")
            display_cols_us = ["代碼", "公司", "現價", "一手年息", "股息率", "除淨日", "派息日", "3年業績"]
            st.dataframe(df_us[display_cols_us], use_container_width=True)
            
            for _, r in df_us.iterrows():
                st.link_button(f"🔗 {r['代碼']} SEC 官方公告", f"https://www.sec.gov/edgar/browse/?CIK={r['代碼']}")

    with tab3:
        if custom_code:
            res = get_advanced_info(yf.Ticker(custom_code), ".HK" in custom_code)
            if res:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"### {res['公司']} ({custom_code})")
                    st.metric("3年業績安全性", res['3年業績'])
                    st.write(f"📅 **除淨日 (X-Day):** {res['除淨日']}")
                    st.write(f"🎁 **派息日:** {res['派息日']}")
                with c2:
                    st.write(f"💰 **一手成本:** {res['一手成本']:,.2f} {res['幣種']}")
                    st.write(f"💵 **一手年息:** {res['一手年息']:,.2f} {res['幣種']}")
                    st.write(f"📈 **股息率:** {res['股息率']*100:.2f}%")
                
                if ".HK" in custom_code:
                    st.link_button("前往披露易查看公告", f"https://www.hkexnews.hk/sdsearch/searchcas_c.aspx?stockcode={custom_code.replace('.HK','').zfill(5)}")
                else:
                    st.link_button("前往 SEC 查看官方文件", f"https://www.sec.gov/edgar/browse/?CIK={custom_code}")
            else:
                st.error("找不到該股票代碼，請檢查輸入是否正確。")
else:
    st.info("請點擊上方按鈕開始獲取最新數據。掃描過程約需 15-30 秒，請稍候。")
