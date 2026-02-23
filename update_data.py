import pandas as pd
import os
import shutil

# 檔案設定
MASTER_FILE = 'price.csv'
DAILY_FILE = 'price_daily.csv'
BACKUP_DIR = 'backup_data'

# 欄位定義 (TEJ)
COL_DATE = '年月日'
COL_SYMBOL = '證券代碼'

def update_price_data():
    print("=== Starting Price Data Update ===")
    
    # 檢查必要檔案
    if not os.path.exists(DAILY_FILE):
        print(f"No daily file found: {DAILY_FILE}")
        return

    # 1. 讀取主檔 (優先 UTF-8, 失敗嘗試 CP950)
    df_master = None
    if os.path.exists(MASTER_FILE):
        print(f"Reading master file: {MASTER_FILE}...")
        try:
            df_master = pd.read_csv(MASTER_FILE, dtype={COL_SYMBOL: str}, encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            print("UTF-8 read failed for Master, trying cp950...")
            try:
                df_master = pd.read_csv(MASTER_FILE, dtype={COL_SYMBOL: str}, encoding='cp950', low_memory=False)
            except Exception as e:
                print(f"Critical Error reading Master file: {e}")
                return
    else:
        print(f"Master file {MASTER_FILE} not found. Will create new one.")
        df_master = pd.DataFrame()

    # 2. 讀取 Daily 檔
    print(f"Reading daily file: {DAILY_FILE}...")
    df_daily = None
    try:
        df_daily = pd.read_csv(DAILY_FILE, dtype={COL_SYMBOL: str}, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        print("UTF-8 read failed for Daily, trying cp950...")
        try:
            df_daily = pd.read_csv(DAILY_FILE, dtype={COL_SYMBOL: str}, encoding='cp950', low_memory=False)
        except Exception as e:
            print(f"Critical Error reading Daily file: {e}")
            return
            
    # 若 Daily 是空的 (可能已被清空)，直接結束
    if df_daily.empty:
        print("Daily file is empty. Nothing to update.")
        return

    # 3. 欄位對齊優化
    # (A) 統一將 '代號' 改為 '證券代碼'
    if '代號' in df_daily.columns:
        df_daily = df_daily.rename(columns={'代號': COL_SYMBOL})
    
    # (B) 若主檔存在，確保 Daily 欄位與主檔對齊
    if not df_master.empty:
        master_cols = df_master.columns.tolist()
        daily_cols = df_daily.columns.tolist()
        
        rename_map = {}
        for m_col in master_cols:
            m_clean = m_col.replace(' ', '')
            for d_col in daily_cols:
                # 模糊比對: 移除空格後相同，且原始名稱不同
                if d_col.replace(' ', '') == m_clean and d_col != m_col:
                    rename_map[d_col] = m_col
        
        if rename_map:
            print(f"Renaming daily columns to match master: {rename_map}")
            df_daily = df_daily.rename(columns=rename_map)

        # 只保留 Master 存在的欄位進行合併 (避免污染資料庫)
        cols_to_use = df_master.columns.intersection(df_daily.columns)
        df_daily = df_daily[cols_to_use]
    
    # 4. 合併與去重
    print("Merging data...")
    initial_len = len(df_master)
    
    df_combined = pd.concat([df_master, df_daily])
    
    # 移除重複 (根據 代碼 + 日期)，保留最新的
    if COL_SYMBOL in df_combined.columns and COL_DATE in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=[COL_SYMBOL, COL_DATE], keep='last')
        
        # 排序
        print("Sorting data...")
        df_combined = df_combined.sort_values(by=[COL_DATE, COL_SYMBOL])
    else:
        print("Warning: Key columns for deduplication not found. Skipping drop_duplicates.")

    final_len = len(df_combined)
    added_count = final_len - initial_len
    
    print(f"Added {added_count} new records. Total records: {final_len}")
    
    # 5. 備份舊檔
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    if os.path.exists(MASTER_FILE):
        backup_path = os.path.join(BACKUP_DIR, f"price_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv")
        shutil.copy(MASTER_FILE, backup_path)
        print(f"Backup saved to: {backup_path}")
    
    # 6. 寫回主檔 (統一使用 utf-8-sig)
    print(f"Saving to {MASTER_FILE} (Encoding: utf-8-sig)...")
    df_combined.to_csv(MASTER_FILE, index=False, encoding='utf-8-sig') 
    
    # 7. 清理 Daily File (清空內容但保留 Header，使用 utf-8-sig)
    try:
        # 如果 master 不為空，用 master 的 columns 做 header，確保一致性
        header_source = df_master if not df_master.empty else df_daily
        header_source.iloc[0:0].to_csv(DAILY_FILE, index=False, encoding='utf-8-sig')
        print(f"Cleared {DAILY_FILE} (header preserved).")
    except Exception as e:
        print(f"Error clearing daily file: {e}")
    
    print("=== Update Complete ===")

if __name__ == "__main__":
    update_price_data()