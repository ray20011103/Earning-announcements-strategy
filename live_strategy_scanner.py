import pandas as pd
import datetime
import os
import sys

# ==========================================
# 設定區
# ==========================================
REVENUE_FILE = 'announcement_daily.csv'
PRICE_FILE = 'price.csv'  # 主股價資料庫
PORTFOLIO_FILE = 'portfolio.csv'
OUTPUT_DIR = 'scan_results'

# 欄位對應 (announcement_daily.csv)
COL_REV_SYMBOL = '代號'
COL_REV_NAME = '名稱'
COL_REV_DATE = '營收發布日'
COL_REV_GROWTH = '單月營收成長率％'
COL_REV_HIGH = '創新高/低(近一年)'

# 欄位對應 (20251227084340.csv - TEJ 格式)
COL_PRC_SYMBOL = '證券代碼'
COL_PRC_DATE = '年月日'
COL_PRC_CLOSE = '收盤價(元)'
COL_PRC_TURNOVER = '週轉率％'

# 策略參數
MAX_POSITIONS = 20
HOLDING_DAYS = 60 

def load_revenue_signals(target_date_str=None):
    """讀取營收訊號"""
    print(f"Loading revenue signals from {REVENUE_FILE}...")
    if not os.path.exists(REVENUE_FILE):
        print(f"Error: {REVENUE_FILE} not found.")
        return pd.DataFrame(), None

    df = pd.read_csv(REVENUE_FILE, dtype=str)
    # 只保留 4 碼數字個股
    df = df[df[COL_REV_SYMBOL].str.match(r'^\d{4}$', na=False)].copy()
    
    # 處理數值
    df[COL_REV_GROWTH] = pd.to_numeric(df[COL_REV_GROWTH], errors='coerce').fillna(-999)
    df['dt_announce'] = pd.to_datetime(df[COL_REV_DATE], format='%Y/%m/%d', errors='coerce')

    # 自動偵測日期
    if target_date_str is None:
        if df['dt_announce'].dropna().empty: return pd.DataFrame(), None
        # 改為抓取最新的日期，而非出現最多次的日期
        latest_date = df['dt_announce'].max()
        target_date_str = latest_date.strftime('%Y/%m/%d')
        print(f"Auto-detected target date: {target_date_str}")
    
    target_dt = pd.to_datetime(target_date_str)
    candidates = df[df['dt_announce'] == target_dt].copy()
    
    # 策略濾網: 成長 > 0 且 創新高
    candidates = candidates[
        (candidates[COL_REV_GROWTH] > 0) & 
        (candidates[COL_REV_HIGH].str.strip().str.upper() == 'H')
    ]
    
    print(f"Found {len(candidates)} candidates passing Revenue filters.")
    return candidates, target_date_str

def apply_technical_filters(candidates):
    """使用本地股價檔檢查 20MA 與 週轉率"""
    if candidates.empty:
        return []

    print(f"Reading price database from {PRICE_FILE} to check 20MA...")
    if not os.path.exists(PRICE_FILE):
        print(f"Error: {PRICE_FILE} not found.")
        return []

    # 為了效能，我們不一次讀完 200MB。
    # 我們先找出需要的代號清單
    target_symbols = candidates[COL_REV_SYMBOL].unique().tolist()
    
    # 讀取股價大檔 (使用 chunksize 或是先讀特定欄位來優化)
    # 這裡先讀入需要的代號資料
    try:
        # 優先嘗試 utf-8
        try:
            iter_csv = pd.read_csv(PRICE_FILE, encoding='utf-8', dtype={COL_PRC_SYMBOL: str}, chunksize=100000, low_memory=False)

        except UnicodeDecodeError:
            print("UTF-8 read failed for price DB, falling back to CP950...")
            iter_csv = pd.read_csv(PRICE_FILE, encoding='cp950', dtype={COL_PRC_SYMBOL: str}, chunksize=100000, low_memory=False)

        df_price_list = []
        for chunk in iter_csv:
            # 清理代號 (處理 "1101 台泥" 這種格式)
            chunk['clean_symbol'] = chunk[COL_PRC_SYMBOL].str.split().str[0]
            # 篩選出我們關心的代號
            filtered_chunk = chunk[chunk['clean_symbol'].isin(target_symbols)]
            df_price_list.append(filtered_chunk)
        
        df_price_all = pd.concat(df_price_list)
        df_price_all[COL_PRC_DATE] = pd.to_datetime(df_price_all[COL_PRC_DATE], format='%Y%m%d', errors='coerce')
        df_price_all = df_price_all.sort_values([COL_PRC_DATE, 'clean_symbol'])

    except Exception as e:
        print(f"Error reading price file: {e}")
        return []

    final_list = []
    
    for idx, row in candidates.iterrows():
        symbol = row[COL_REV_SYMBOL]
        name = row[COL_REV_NAME]
        
        # 取得該股的歷史資料
        df_stock = df_price_all[df_price_all['clean_symbol'] == symbol].tail(20)
        
        if len(df_stock) < 20:
            print(f"  [SKIP] {symbol}: Insufficient price history (< 20 days).")
            continue
            
        latest_price = df_stock[COL_PRC_CLOSE].iloc[-1]
        ma20 = df_stock[COL_PRC_CLOSE].mean()
        turnover = df_stock[COL_PRC_TURNOVER].iloc[-1]
        
        if latest_price > ma20:
            print(f"  [PASS] {symbol} {name}: Price {latest_price:.2f} > 20MA {ma20:.2f}")
            final_list.append({
                'Symbol': symbol,
                'Name': name,
                'Price': latest_price,
                'MA20': ma20,
                'Revenue_YoY': row[COL_REV_GROWTH],
                'Turnover_Score': turnover # 直接使用 TEJ 的週轉率
            })
        else:
            print(f"  [FAIL] {symbol} {name}: Price {latest_price:.2f} < 20MA {ma20:.2f}")

    return final_list

def manage_portfolio(current_date_str):
    """檢查庫存"""
    if not os.path.exists(PORTFOLIO_FILE): return [], 0
    df_pf = pd.read_csv(PORTFOLIO_FILE)
    if df_pf.empty: return [], 0
    holding = df_pf[df_pf['Status'] == 'Holding'].copy() if 'Status' in df_pf.columns else df_pf.copy()
    current_date = pd.to_datetime(current_date_str)
    sell_list = [row for _, row in holding.iterrows() if current_date >= pd.to_datetime(row['Target_Sell_Date'])]
    return sell_list, len(holding)

def main():
    target_date_str = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 1. 營收訊號
    candidates, target_date_str = load_revenue_signals(target_date_str)
    
    # 2. 技術面過濾 (從本機大檔讀取)
    scan_results = apply_technical_filters(candidates)
    
    # 排序 (依照週轉率)
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
        f.write(f"=== 每日策略報告 (TEJ Data Version): {target_date_str} ===\n\n")
        
        f.write(f"[1] 賣出建議 (持有滿 {HOLDING_DAYS} 交易日)\n")
        if sell_candidates:
            for item in sell_candidates: f.write(f"  - {item['Symbol']} {item['Name']} (買進: {item['Buy_Date']})\n")
        else: f.write("  - 無\n")
        f.write("\n")

        available = MAX_POSITIONS - (current_count - len(sell_candidates))
        f.write(f"[2] 買進建議 (可用額度: {available})\n")
        if not df_scan.empty and available > 0:
            for item in df_scan.head(available).to_dict('records'):
                est_sell = (pd.to_datetime(target_date_str) + datetime.timedelta(days=90)).strftime('%Y/%m/%d')
                f.write(f"  - {item['Symbol']} {item['Name']} | 收盤: {item['Price']:.2f} | YoY: {item['Revenue_YoY']}% | 週轉率: {item['Turnover_Score']}% | 預計賣出: {est_sell}\n")
        else: f.write("  - 無 (部位滿或無訊號)\n")
        f.write("\n")

        f.write("[3] 今日原始掃描結果 (By Turnover)\n")
        if not df_scan.empty:
            f.write(df_scan.to_string(index=False, columns=['Symbol', 'Name', 'Price', 'Revenue_YoY', 'Turnover_Score']))
        else: f.write("  - 無符合條件股票")

    print(f"\nREPORT GENERATED: {report_path}\n" + "="*40)
    with open(report_path, 'r', encoding='utf-8') as f: print(f.read())

if __name__ == "__main__":
    main()
