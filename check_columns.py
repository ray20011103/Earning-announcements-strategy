from FinMind.data import DataLoader
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNyAxOTo0MjoyMiIsInVzZXJfaWQiOiJyYXk5MDExMDMiLCJlbWFpbCI6InJheTIwMDExMTAzQGdtYWlsLmNvbSIsImlwIjoiMTIyLjExNi4xOTYuMjEyIn0.ll3u65A0LnZA2nEHYmcEGkmhxTg0vUn57W0ipj6Qyxo"
api = DataLoader()
api.login_by_token(FINMIND_TOKEN)
df = api.taiwan_stock_month_revenue(stock_id='2330', start_date='2025-01-01')
print("FinMind 營收欄位列表:")
print(df.columns.tolist())
print("\n最新一筆資料內容:")
print(df.tail(1))
