import pandas as pd
import numpy as np
import datetime
from FinMind.data import DataLoader

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNyAxOTo0MjoyMiIsInVzZXJfaWQiOiJyYXk5MDExMDMiLCJlbWFpbCI6InJheTIwMDExMTAzQGdtYWlsLmNvbSIsImlwIjoiMTIyLjExNi4xOTYuMjEyIn0.ll3u65A0LnZA2nEHYmcEGkmhxTg0vUn57W0ipj6Qyxo"
api = DataLoader()
api.login_by_token(FINMIND_TOKEN)

def test_full_history_logic():
    print("--- 深度測試: 掃描歷史中所有符合「創新高+YoY>0」的時刻 ---")
    df_rev = api.taiwan_stock_month_revenue(stock_id='2330', start_date='2024-01-01')
    
    # 增加更多股票來測試
    symbols = ['2330', '2317', '2454', '1101', '2303']
    
    for sym in symbols:
        df = api.taiwan_stock_month_revenue(stock_id=sym, start_date='2023-01-01')
        df['revenue'] = pd.to_numeric(df['revenue'])
        df = df.sort_values(['revenue_year', 'revenue_month']).reset_index(drop=True)
        
        print(f"\n檢查股票: {sym}")
        for i in range(13, len(df)):
            current = df.iloc[i]
            # 12個月新高: 比對當前與過去 11 筆
            hist_11 = df.iloc[i-11:i]
            is_high = current['revenue'] > hist_11['revenue'].max()
            
            # YoY: 比對 12 筆前
            prev_year = df.iloc[i-12]
            yoy = (current['revenue'] / prev_year['revenue'] - 1) * 100
            
            if is_high and yoy > 0:
                print(f"  [符合] 日期:{current['date']} (營收月:{current['revenue_month']}) | YoY:{yoy:.1f}% | 創12月新高!")

if __name__ == "__main__":
    test_full_history_logic()
