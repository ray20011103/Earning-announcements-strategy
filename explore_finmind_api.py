import pandas as pd
from FinMind.data import DataLoader
import json

def explore_finmind():
    # 初始化 DataLoader
    # 如果你有 Token，可以使用 dl.login(token="你的Token")
    dl = DataLoader()

    print("--- 正在獲取 台積電 (2330) 的營收資料 ---")
    # 獲取營收資料 (TaiwanStockMonthRevenue)
    # 包含營收月份、公告日期、YoY、MoM 等
    revenue_data = dl.taiwan_stock_month_revenue(
        stock_id='2330',
        start_date='2024-01-01'
    )
    
    if not revenue_data.empty:
        print("\n[營收資料 欄位與範例]")
        print(revenue_data.head())
        print("\n[所有欄位名稱]:", list(revenue_data.columns))
        # 說明重要欄位
        # revenue: 當月營收
        # update_date: 資料更新日 (通常就是公告日)
        # last_year_growth_rate: YoY
    else:
        print("未能獲取營收資料，請檢查網路或 API 限制。")

    print("\n" + "="*50 + "\n")

    print("--- 正在獲取 台積電 (2330) 的日成交資料 ---")
    # 獲取日成交資料 (TaiwanStockPrice)
    price_data = dl.taiwan_stock_daily(
        stock_id='2330',
        start_date='2024-02-01',
        end_date='2024-02-15'
    )

    if not price_data.empty:
        print("\n[股價資料 欄位與範例]")
        print(price_data.head())
        print("\n[所有欄位名稱]:", list(price_data.columns))
    else:
        print("未能獲取股價資料。")

if __name__ == "__main__":
    try:
        explore_finmind()
    except Exception as e:
        print(f"執行出錯: {e}")
        print("\n提示: 如果尚未安裝 FinMind，請執行: pip install FinMind")
