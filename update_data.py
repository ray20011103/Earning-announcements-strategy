import pandas as pd
import os

# 檔案設定
MASTER_FILE = 'price.csv'
DAILY_FILE = 'price_daily.csv'

# 欄位定義 (TEJ 格式)
COL_SYMBOL = '證券代碼'

def update_price_data():
    print("=== 執行資料更新 (直接附加模式) ===")
    
    # 檢查必要檔案
    if not os.path.exists(DAILY_FILE):
        print(f"找不到每日更新檔: {DAILY_FILE}，跳過更新。")
        return

    # 1. 讀取每日更新資料
    print(f"讀取中: {DAILY_FILE}...")
    try:
        # 優先嘗試 UTF-8
        df_daily = pd.read_csv(DAILY_FILE, dtype={COL_SYMBOL: str}, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        # 失敗則嘗試 CP950 (TEJ 常用格式)
        df_daily = pd.read_csv(DAILY_FILE, dtype={COL_SYMBOL: str}, encoding='cp950', low_memory=False)
            
    if df_daily.empty:
        print("每日更新檔內容為空。")
        return

    # 2. 欄位對齊 (將 '代號' 統一轉換為 '證券代碼')
    if '代號' in df_daily.columns:
        df_daily = df_daily.rename(columns={'代號': COL_SYMBOL})
    
    # 3. 處理附加邏輯
    if os.path.exists(MASTER_FILE):
        # 讀取主檔 Header 以確保欄位順序與過濾
        df_header = pd.read_csv(MASTER_FILE, nrows=0, encoding='utf-8-sig')
        
        # 只保留主檔中存在的欄位，並依照主檔順序排序
        cols_to_use = [c for c in df_header.columns if c in df_daily.columns]
        df_daily = df_daily[cols_to_use]
        
        # 直接附加 (mode='a', 不寫 header)
        print(f"將新資料附加至 {MASTER_FILE}...")
        # 使用 utf-8 附加即可，主檔開頭的 BOM 會保留，後續附加不需要再加 BOM
        df_daily.to_csv(MASTER_FILE, mode='a', index=False, header=False, encoding='utf-8')
    else:
        # 主檔不存在則新建 (寫入 header 並加 BOM)
        print(f"建立新主檔: {MASTER_FILE}...")
        df_daily.to_csv(MASTER_FILE, index=False, encoding='utf-8-sig')

    print(f"成功新增 {len(df_daily)} 筆紀錄。已根據要求跳過備份。")
    
    # 4. 清理每日更新檔 (保留 Header 供下次使用)
    try:
        df_daily.iloc[0:0].to_csv(DAILY_FILE, index=False, encoding='utf-8-sig')
        print(f"已清空 {DAILY_FILE}。")
    except Exception as e:
        print(f"清空每日更新檔時出錯: {e}")

    print("=== 更新完成 ===")

if __name__ == "__main__":
    update_price_data()
