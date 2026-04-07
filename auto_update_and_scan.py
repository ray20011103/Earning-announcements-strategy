import pandas as pd
import numpy as np
import datetime
import os
from FinMind.data import DataLoader

# ==========================================
# 設定區
# ==========================================
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNyAxOTo0MjoyMiIsInVzZXJfaWQiOiJyYXk5MDExMDMiLCJlbWFpbCI6InJheTIwMDExMTAzQGdtYWlsLmNvbSIsImlwIjoiMTIyLjExNi4xOTYuMjEyIn0.ll3u65A0LnZA2nEHYmcEGkmhxTg0vUn57W0ipj6Qyxo"
api = DataLoader()
api.login_by_token(FINMIND_TOKEN)

OUTPUT_DIR = 'scan_results'
MAX_POSITIONS = 20

def fetch_and_calculate_revenue():
    """精準計算 YoY 與 12 個月新高"""
    print("--- 步驟 1: 抓取全市場歷史營收 (24個月) ---")
    
    # 抓取較長歷史資料以計算 YoY (需 13 個月) 與 12個月新高 (需 12 個月)
    start_date = (datetime.date.today() - datetime.timedelta(days=800)).strftime('%Y-%m-%d')
    df_rev = api.taiwan_stock_month_revenue(start_date=start_date)
    
    if df_rev.empty:
        print("錯誤: 抓不到營收資料。")
        return pd.DataFrame()

    # 格式化
    df_rev['revenue'] = pd.to_numeric(df_rev['revenue'], errors='coerce')
    df_rev = df_rev.sort_values(['stock_id', 'revenue_year', 'revenue_month'])
    
    results = []
    
    print("正在計算每檔個股的策略指標...")
    # 針對每一檔股票進行邏輯比對
    for stock_id, group in df_rev.groupby('stock_id'):
        if len(group) < 13: continue # 至少要有一年以上的資料算 YoY
        
        group = group.reset_index(drop=True)
        latest = group.iloc[-1]
        
        # 1. 尋找去年同期的營收 (YoY 計算)
        # 比對 year-1 且 month 相同的資料
        target_year = latest['revenue_year'] - 1
        target_month = latest['revenue_month']
        prev_year_data = group[(group['revenue_year'] == target_year) & (group['revenue_month'] == target_month)]
        
        if prev_year_data.empty:
            yoy = 0
        else:
            prev_revenue = prev_year_data['revenue'].values[0]
            yoy = (latest['revenue'] / prev_revenue - 1) * 100 if prev_revenue > 0 else 0
            
        # 2. 計算 12 個月新高 (不含當月)
        hist_12m = group.iloc[:-1].tail(11) # 過去 11 個月
        is_high = latest['revenue'] > hist_12m['revenue'].max() if not hist_12m.empty else False
        
        if is_high and yoy > 0:
            results.append({
                'Symbol': stock_id,
                'Year': latest['revenue_year'],
                'Month': latest['revenue_month'],
                'Revenue': latest['revenue'],
                'YoY': yoy,
                'Is_High': 'H'
            })
            
    df_signals = pd.DataFrame(results)
    print(f"初步篩選出 {len(df_signals)} 檔營收符合條件個股。")
    return df_signals

def fetch_prices_and_filter(df_signals):
    """抓取技術面資料並過濾 (20MA)"""
    if df_signals.empty: return []

    print("--- 步驟 2: 檢查技術面 (20MA) ---")
    
    # 取得最新交易日 (FinMind 的 daily_info 通常在盤後更新)
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    start_date_ma = (datetime.date.today() - datetime.timedelta(days=60)).strftime('%Y-%m-%d')
    
    final_list = []
    
    # 為了穩定，我們一檔一檔抓取最近 30 天股價
    total = len(df_signals)
    for i, (_, row) in enumerate(df_signals.iterrows()):
        symbol = row['Symbol']
        if i % 20 == 0: print(f"進度: {i}/{total}...")
        
        df_hist = api.taiwan_stock_daily(stock_id=symbol, start_date=start_date_ma)
        
        if len(df_hist) < 20: continue
        
        latest_close = df_hist['close'].iloc[-1]
        ma20 = df_hist['close'].tail(20).mean()
        
        if latest_close > ma20:
            final_list.append({
                'Symbol': symbol,
                'Price': latest_close,
                'MA20': ma20,
                'YoY': row['YoY'],
                'Month': f"{row['Year']}/{row['Month']}"
            })
            
    return final_list

def main():
    # 1. 算營收
    df_signals = fetch_and_calculate_revenue()
    
    # 2. 過濾技術面
    final_results = fetch_prices_and_filter(df_signals)
    
    # 3. 排序與產出
    df_final = pd.DataFrame(final_results)
    if not df_final.empty:
        df_final = df_final.sort_values('YoY', ascending=False)
    
    # 產出報告
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    today_file = datetime.date.today().strftime('%Y%m%d')
    report_path = f"{OUTPUT_DIR}/auto_scan_report_{today_file}.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"=== 實盤全自動化策略報告: {datetime.date.today()} ===\n\n")
        f.write(f"營收邏輯: 當月營收 > 過去 11 個月最高值 且 YoY > 0\n")
        f.write(f"技術邏輯: 收盤價 > 20MA\n\n")
        
        if not df_final.empty:
            for item in df_final.head(MAX_POSITIONS).to_dict('records'):
                f.write(f"  - {item['Symbol']} | 營收月份: {item['Month']} | 收盤: {item['Price']:.2f} | YoY: {item['YoY']:.1f}% | 20MA: {item['MA20']:.2f}\n")
        else:
            f.write("  - 無符合條件股票\n")
            
    print(f"\n自動化報告已完成: {report_path}")
    if not df_final.empty:
        print(df_final.head(10))

if __name__ == "__main__":
    main()
