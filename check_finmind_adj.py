from FinMind.data import DataLoader
import pandas as pd

def check_adj_price():
    dl = DataLoader()
    # 測試 5314 世紀 在 2025-03 到 2025-04 期間的股價
    # 這是你提到的 -95% 交易
    stock_id = '5314'
    start_date = '2025-03-01'
    end_date = '2025-04-15'
    
    print(f"--- 正在獲取 {stock_id} 的原始與調整後股價 ---")
    
    # 1. 原始股價
    raw_price = dl.taiwan_stock_daily(
        stock_id=stock_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # 2. 嘗試獲取調整後股價 (FinMind 通常在同一個 API 或透過參數提供)
    # 註：FinMind 的新版 API 中，調整後股價通常在 Dataset.TaiwanStockPrice 裡面就有 Adjusted_Close 欄位
    # 或者需要調用不同的 method。我們來檢查 raw_price 的欄位。
    
    if not raw_price.empty:
        print("\n[原始股價 欄位]:", list(raw_price.columns))
        # 如果沒有 Adjusted_Close，我們試著抓取 TaiwanStockPriceAdj (如果有的話)
        try:
            adj_price = dl.taiwan_stock_daily_adj(
                stock_id=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            print("\n[調整後股價 範例]:")
            print(adj_price[['date', 'stock_id', 'close']].head())
        except Exception as e:
            print(f"\n無法直接抓取調整後股價: {e}")
            print("我們將手動計算調整因子。")

if __name__ == "__main__":
    check_adj_price()
