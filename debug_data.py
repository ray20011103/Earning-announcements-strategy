import pandas as pd
from FinMind.data import DataLoader
import datetime

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNyAxOTo0MjoyMiIsInVzZXJfaWQiOiJyYXk5MDExMDMiLCJlbWFpbCI6InJheTIwMDExMTAzQGdtYWlsLmNvbSIsImlwIjoiMTIyLjExNi4xOTYuMjEyIn0.ll3u65A0LnZA2nEHYmcEGkmhxTg0vUn57W0ipj6Qyxo"
api = DataLoader()
api.login_by_token(FINMIND_TOKEN)

def debug_revenue():
    print("--- 診斷 1: 檢查營收資料範圍 ---")
    start_date = (datetime.date.today() - datetime.timedelta(days=100)).strftime('%Y-%m-%d')
    df_rev = api.taiwan_stock_month_revenue(start_date=start_date)
    
    if df_rev.empty:
        print("!!! 錯誤: 抓不到任何營收資料")
        return

    print(f"資料筆數: {len(df_rev)}")
    print(f"最晚的營收日期: {df_rev['date'].max()}")
    print("\n前 5 筆資料範例:")
    print(df_rev[['stock_id', 'stock_name', 'date', 'revenue', 'revenue_year_growth_percent']].head())

    print("\n--- 診斷 2: 檢查特定個股 (以 2330 台積電為例) ---")
    df_tsmc = api.taiwan_stock_month_revenue(
        stock_id='2330',
        start_date=(datetime.date.today() - datetime.timedelta(days=500)).strftime('%Y-%m-%d')
    )
    if not df_tsmc.empty:
        df_tsmc = df_tsmc.sort_values('date')
        print(df_tsmc[['date', 'revenue', 'revenue_year_growth_percent']].tail(14))
    else:
        print("!!! 錯誤: 抓不到 2330 的資料")

if __name__ == "__main__":
    debug_revenue()
