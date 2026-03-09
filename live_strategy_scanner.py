import pandas as pd
import datetime
import os
import sys
import subprocess

# ==========================================
# 設定區
# ==========================================
REVENUE_FILE = 'announcement_daily.csv'
PRICE_FILE = 'price.csv'
PORTFOLIO_FILE = 'portfolio.csv'
OUTPUT_DIR = 'scan_results'

# 欄位對應
COL_REV_SYMBOL = '代號'
COL_REV_NAME = '名稱'
COL_REV_DATE = '營收發布日'
COL_REV_GROWTH = '單月營收成長率％'
COL_REV_HIGH = '創新高/低(近一年)'

COL_PRC_SYMBOL = '證券代碼'
COL_PRC_DATE = '年月日'
COL_PRC_CLOSE = '收盤價(元)'
COL_PRC_TURNOVER = '週轉率％'

MAX_POSITIONS = 20
HOLDING_DAYS = 60 

def load_revenue_signals(target_date_str=None):
    """讀取營收訊號"""
    abs_path = os.path.abspath(REVENUE_FILE)
    print(f"--- 步驟 1: 讀取營收訊號 ({REVENUE_FILE}) ---")
    if not os.path.exists(REVENUE_FILE):
        print(f"錯誤: 找不到檔案 {abs_path}")
        return pd.DataFrame(), None

    df = pd.read_csv(REVENUE_FILE, dtype=str)
    # 只保留 4 碼數字個股
    df = df[df[COL_REV_SYMBOL].str.match(r'^\d{4}$', na=False)].copy()
    
    # 處理數值與日期
    df[COL_REV_GROWTH] = pd.to_numeric(df[COL_REV_GROWTH], errors='coerce').fillna(-999)
    df['dt_announce'] = pd.to_datetime(df[COL_REV_DATE], format='%Y/%m/%d', errors='coerce')

    # 自動偵測日期
    if target_date_str is None:
        if df['dt_announce'].dropna().empty: 
            print("找不到有效的營收發布日期。")
            return pd.DataFrame(), None
        
        # 抓取檔案中最新的日期
        latest_date = df['dt_announce'].max()
        target_date_str = latest_date.strftime('%Y/%m/%d')
        print(f"自動偵測最新日期: {target_date_str}")
    
    target_dt = pd.to_datetime(target_date_str)
    candidates = df[df['dt_announce'] == target_dt].copy()
    
    # 策略濾網: 成長 > 0 且 創新高 (H)
    candidates = candidates[
        (candidates[COL_REV_GROWTH] > 0) & 
        (candidates[COL_REV_HIGH].str.strip().str.upper() == 'H')
    ]
    
    print(f"在 {target_date_str} 發現 {len(candidates)} 檔符合營收條件股票。")
    return candidates, target_date_str

def apply_technical_filters(candidates, target_date_str):
    """使用高效能方式檢查 20MA"""
    if candidates.empty: return []

    print(f"--- 步驟 2: 檢查技術面 (只讀取 {PRICE_FILE} 最近資料) ---")
    if not os.path.exists(PRICE_FILE):
        print(f"錯誤: 找不到股價檔 {PRICE_FILE}")
        return []

    # 效能優化：不讀取 200MB 全量資料，只讀取檔案末尾約 15 萬行 (涵蓋所有個股約最近 3 個月的資料)
    try:
        # 使用 tail 指令快速獲取末尾
        result = subprocess.run(['tail', '-n', '150000', PRICE_FILE], capture_output=True, text=True)
        # 重新組合 Header
        header = pd.read_csv(PRICE_FILE, nrows=0).columns.tolist()
        from io import StringIO
        df_price = pd.read_csv(StringIO(result.stdout), names=header, dtype={COL_PRC_SYMBOL: str})
        
        # 清理代號 (處理 "1101 台泥" 這種格式)
        df_price['clean_symbol'] = df_price[COL_PRC_SYMBOL].str.split().str[0]
        df_price[COL_PRC_DATE] = pd.to_datetime(df_price[COL_PRC_DATE], format='%Y%m%d', errors='coerce')
        df_price = df_price.sort_values([COL_PRC_DATE, 'clean_symbol'])
        
    except Exception as e:
        print(f"快速讀取股價檔失敗 ({e})，嘗試常規讀取...")
        df_price = pd.read_csv(PRICE_FILE, dtype={COL_PRC_SYMBOL: str})
        df_price['clean_symbol'] = df_price[COL_PRC_SYMBOL].str.split().str[0]

    target_symbols = candidates[COL_REV_SYMBOL].tolist()
    final_list = []
    
    for _, row in candidates.iterrows():
        symbol = row[COL_REV_SYMBOL]
        name = row[COL_REV_NAME]
        
        # 取得該股在資料庫中最近的 20 筆記錄
        df_stock = df_price[df_price['clean_symbol'] == symbol].tail(20)
        
        if len(df_stock) < 20:
            continue
            
        latest_price = df_stock[COL_PRC_CLOSE].iloc[-1]
        ma20 = df_stock[COL_PRC_CLOSE].mean()
        turnover = df_stock[COL_PRC_TURNOVER].iloc[-1]
        
        if latest_price > ma20:
            final_list.append({
                'Symbol': symbol,
                'Name': name,
                'Price': latest_price,
                'MA20': ma20,
                'Revenue_YoY': row[COL_REV_GROWTH],
                'Turnover_Score': turnover
            })

    print(f"技術面過濾完成，最終選出 {len(final_list)} 檔強勢股。")
    return final_list

def manage_portfolio(current_date_str):
    """庫存管理"""
    if not os.path.exists(PORTFOLIO_FILE): return [], 0
    try:
        df_pf = pd.read_csv(PORTFOLIO_FILE)
        if df_pf.empty: return [], 0
        holding = df_pf[df_pf['Status'] == 'Holding'].copy() if 'Status' in df_pf.columns else df_pf.copy()
        current_date = pd.to_datetime(current_date_str)
        sell_list = [row for _, row in holding.iterrows() if current_date >= pd.to_datetime(row['Target_Sell_Date'])]
        return sell_list, len(holding)
    except:
        return [], 0

def main():
    target_date_str = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 1. 營收訊號
    candidates, target_date_str = load_revenue_signals(target_date_str)
    
    # 2. 技術面過濾
    scan_results = apply_technical_filters(candidates, target_date_str)
    
    # 排序
    df_scan = pd.DataFrame(scan_results)
    if not df_scan.empty:
        df_scan = df_scan.sort_values('Turnover_Score', ascending=False)

    # 3. 庫存管理
    sell_candidates, current_count = manage_portfolio(target_date_str)

    # 4. 產出報告
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    date_file_str = target_date_str.replace('/', '')
    report_path = f"{OUTPUT_DIR}/daily_report_{date_file_str}.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"=== 每日策略報告 (高效優化版): {target_date_str} ===\n\n")
        f.write(f"[1] 賣出建議\n")
        if sell_candidates:
            for item in sell_candidates: f.write(f"  - {item['Symbol']} {item['Name']} (買進: {item['Buy_Date']})\n")
        else: f.write("  - 無\n")
        f.write("\n")

        available = MAX_POSITIONS - (current_count - len(sell_candidates))
        f.write(f"[2] 買進建議 (可用額度: {available})\n")
        if not df_scan.empty and available > 0:
            for item in df_scan.head(available).to_dict('records'):
                est_sell = (pd.to_datetime(target_date_str) + datetime.timedelta(days=90)).strftime('%Y/%m/%d')
                f.write(f"  - {item['Symbol']} {item['Name']} | 收盤: {item['Price']:.2f} | YoY: {item['Revenue_YoY']}% | 預計賣出: {est_sell}\n")
        else: f.write("  - 無符合條件股票\n")

    print(f"\n報告已生成: {report_path}\n")

if __name__ == "__main__":
    main()
