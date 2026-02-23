import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 1. Load Data
print("Loading monthly_data.csv...")
# The file has a 2-row header. 
# Row 0: Stock Name (e.g., "1101 台泥")
# Row 1: Feature Name (e.g., "單月營收(千元)")
df = pd.read_csv('monthly_data.csv', header=[0, 1], encoding='utf-8')

# The first column is "Unnamed: 0_level_0", "年月日". 
# We need to set it as index.
# The column name in MultiIndex might be strange.
date_col = df.columns[0]
df.set_index(date_col, inplace=True)
df.index = pd.to_datetime(df.index)
df.index.name = 'Date'

print(f"Data loaded. Shape: {df.shape}")
print(f"Time range: {df.index.min()} to {df.index.max()}")

# 2. Extract Features
# We need Close Price and Monthly Sales
# Features are in the second level of columns
# We can swap levels to make selecting features easier
df_swapped = df.swaplevel(axis=1)

# Extract Close Price
try:
    prices = df_swapped['收盤價(元)']
    prices = prices.apply(pd.to_numeric, errors='coerce')
    print("Extracted Price data.")
except KeyError:
    print("Error: '收盤價(元)' not found.")
    exit()

# Extract Revenue
# The column name might be "單月營收(千元)" or similar.
try:
    revenue = df_swapped['單月營收(千元)']
    # Remove commas and convert to numeric
    revenue = revenue.replace({',': ''}, regex=True)
    revenue = revenue.apply(pd.to_numeric, errors='coerce')
    print("Extracted Revenue data.")
except KeyError:
    print("Error: '單月營收(千元)' not found.")
    exit()

# 3. Calculate Returns
# Monthly Return = P_t / P_{t-1} - 1
returns = prices.pct_change()

# 4. Calculate HI (Highest Monthly Sales Momentum)
# HI_t = Sales_t / Max(Sales_0 ... Sales_{t-1})
# Note: "Historical High" excludes current month per paper?
# "單月營收對歷史最高單月營收比率(HI)定義為本月單月營收 / 歷史最高單月營收"
# "歷史最高單月營收是以 TEJ 資料庫有資料起之紀錄，但不含當月營收"
# So for Month t, we divide Sales_t by Max(Sales_{0..t-1})

# Expanding max of Sales (shifted by 1 to exclude current)
hist_max_sales = revenue.expanding().max().shift(1)

# Calculate HI
hi_ratio = revenue / hist_max_sales

# 5. Align Signals and Returns for Backtesting
# Strategy: Rebalance at End of Month T.
# Signal used: Sales of Month T-1 (Released ~10th of Month T).
# Return captured: Month T+1.
# So, Return at Index i (End of Month i) should be predicted by Sales of Month i-2?
# Let's trace:
# Index i: 2013-03-31.
# P_i: Price on Mar 31.
# Return_i: Change from Feb 28 to Mar 31. (Already happened).
# We want to trade for NEXT month (April). Return_{i+1}.
# Signal Available at Mar 31: Feb Sales (Index i-1).
# So we use Sales_{i-1} to select portfolio for Return_{i+1}.
# In DataFrame alignment:
# Target Y: returns.shift(-1) (Next month's return)
# Feature X: hi_ratio (HI calculated using Sales_{i-1}??)
# Wait. 
# Row i (Mar 31) contains Mar Sales (Available Apr 10).
# Row i-1 (Feb 28) contains Feb Sales (Available Mar 10).
# At Mar 31, we have Feb Sales (Row i-1).
# HI calculated from Feb Sales is hi_ratio.iloc[i-1].
# So at Mar 31 (Row i), our signal is hi_ratio.shift(1).
# We assume we hold for 1 month (April).
# The return for April is captured in Row i+1 (Apr 30).
# So we want to align:
# Signal(Row i) = hi_ratio(Row i-1)
# Result(Row i) = returns(Row i+1) ? No. 
# We typically align everything to "Trading Date".
# Trading Date = Mar 31.
# Signal = hi_ratio.shift(1) (Feb HI).
# Forward Return = returns.shift(-1).

# Let's define the "Signal" dataframe aligned to the Rebalance Date.
# At Date T, Signal = HI_{T-1}.
signal = hi_ratio.shift(1)

# Forward Return (Next Month)
fwd_ret = returns.shift(-1)

# 6. Portfolio Construction
# Rank stocks by Signal
# R5: Top 20%, R1: Bottom 20%
ranks = signal.rank(axis=1, pct=True)

# Define Masks
r5_mask = ranks > 0.8
r1_mask = ranks <= 0.2

# Calculate Portfolio Returns (Equal Weighted)
# We assume we invest in stocks where mask is True.
# Average forward return of selected stocks.

r5_ret = (fwd_ret * r5_mask).sum(axis=1) / r5_mask.sum(axis=1)
r1_ret = (fwd_ret * r1_mask).sum(axis=1) / r1_mask.sum(axis=1)
mom_ret = r5_ret - r1_ret

# 7. Performance Analysis
strategy_df = pd.DataFrame({
    'Winner (R5)': r5_ret,
    'Loser (R1)': r1_ret,
    'Momentum (R5-R1)': mom_ret
})

# Drop NaNs (early period)
strategy_df = strategy_df.dropna()

# Cumulative Return
cum_ret = (1 + strategy_df).cumprod()

print("\n--- Strategy Performance (Monthly Rebalancing, 1-Month Holding) ---")
print(strategy_df.describe())

# Annual Metrics
mean_ret = strategy_df.mean() * 12
std_ret = strategy_df.std() * np.sqrt(12)
sharpe = mean_ret / std_ret

print("\n--- Annualized Metrics ---")
print("Mean Return:")
print(mean_ret)
print("\nSharpe Ratio:")
print(sharpe)

# 8. Plotting
plt.figure(figsize=(12, 6))
plt.plot(cum_ret['Winner (R5)'], label='Winner (R5)')
plt.plot(cum_ret['Loser (R1)'], label='Loser (R1)')
plt.plot(cum_ret['Momentum (R5-R1)'], label='Momentum (R5-R1)')
plt.title('Revenue High Momentum Strategy - Cumulative Returns')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid(True)
plt.savefig('revenue_strategy_backtest.png')
print("\nPlot saved to revenue_strategy_backtest.png")

# Save results
strategy_df.to_csv('revenue_strategy_returns.csv')
print("Returns data saved to revenue_strategy_returns.csv")
