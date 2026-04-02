import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def generate_plots():
    # Load daily returns for drawdown calculation
    # Using event_strategy_trades_v2 as a proxy for strategy performance
    df = pd.read_csv('analysis_results/data/event_strategy_trades_v2.csv')
    df['buy_date'] = pd.to_datetime(df['buy_date'])
    df = df.sort_values('buy_date')

    # 1. Monthly/Yearly Returns (Simplified)
    df['year'] = df['buy_date'].dt.year
    yearly_ret = df.groupby('year')['return'].mean()
    
    plt.figure(figsize=(10, 6))
    yearly_ret.plot(kind='bar', color='skyblue')
    plt.title('Average Trade Return by Year')
    plt.xlabel('Year')
    plt.ylabel('Avg Return')
    plt.savefig('analysis_results/plots/yearly_avg_return.png')
    plt.close()

    # 2. Return Distribution (Histogram)
    plt.figure(figsize=(10, 6))
    # Clip extreme outliers for visualization
    clipped_rets = df['return'].clip(-0.5, 0.5)
    plt.hist(clipped_rets, bins=50, color='coral', edgecolor='black')
    plt.title('Distribution of Trade Returns (Clipped at +/- 50%)')
    plt.xlabel('Return')
    plt.ylabel('Frequency')
    plt.savefig('analysis_results/plots/return_histogram.png')
    plt.close()

    # 3. Drawdown Proxy
    # Note: Real drawdown needs time-series equity curve, but we'll use trades sequence for now
    cum_ret = (1 + df['return']).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / running_max
    
    plt.figure(figsize=(10, 6))
    plt.fill_between(df['buy_date'], drawdown, color='red', alpha=0.3)
    plt.title('Strategy Max Drawdown Over Time')
    plt.xlabel('Time')
    plt.ylabel('Drawdown')
    plt.savefig('analysis_results/plots/drawdown_chart.png')
    plt.close()

if __name__ == "__main__":
    generate_plots()
