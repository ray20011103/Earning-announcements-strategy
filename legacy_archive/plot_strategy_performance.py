import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def calculate_max_drawdown(equity_curve):
    roll_max = equity_curve.cummax()
    drawdown = (equity_curve - roll_max) / roll_max
    return drawdown.min() * 100

def plot_performance():
    print("Loading data...")
    
    # 1. Load Signals FIRST
    try:
        signals_df = pd.read_csv('營收公告日.csv', encoding='utf-8', dtype={'代碼': str, '營收發布日': str})
    except:
        signals_df = pd.read_csv('營收公告日.csv', encoding='cp950', dtype={'代碼': str, '營收發布日': str})
    
    target_col = [c for c in signals_df.columns if '創新高' in c][0]
    buy_signals = signals_df[signals_df[target_col] == 'H'].copy()
    buy_signals['AnnounceDate'] = pd.to_datetime(buy_signals['營收發布日'], format='%Y%m%d', errors='coerce')
    buy_signals = buy_signals.dropna(subset=['AnnounceDate'])
    
    # 2. Load Price Data
    price_df = pd.read_csv('daily_price_data.csv', dtype={'symbol': str})
    price_df['Date'] = pd.to_datetime(price_df['Date'])
    price_df.set_index(['symbol', 'Date'], inplace=True)
    price_df.sort_index(inplace=True)
    
    all_trading_dates = price_df.index.get_level_values(1).unique().sort_values()
    
    # 3. Calculate Benchmark (Optimized)
    print("Calculating market benchmark...")
    try:
        # Filter price data to relevant range to save memory
        min_date = buy_signals['AnnounceDate'].min() - pd.Timedelta(days=30)
        price_subset = price_df[price_df.index.get_level_values(1) >= min_date].copy()
        
        pivot_df = price_subset.reset_index().pivot(index='Date', columns='symbol', values='Close')
        daily_rets = pivot_df.pct_change()
        
        # Benchmark: Equal Weight of all stocks
        market_daily_ret = daily_rets.mean(axis=1).fillna(0)
        market_cum = (1 + market_daily_ret).cumprod()
        
        daily_ret_matrix = daily_rets # Use this for strategy too
    except Exception as e:
        print(f"Benchmark error: {e}")
        market_cum = pd.Series(1.0, index=all_trading_dates)
        daily_ret_matrix = None

    # 4. Load Turnover
    try:
        vol_df = pd.read_csv('成交量.csv', encoding='utf-8', dtype={'證券代碼': str, '年月日': str})
    except:
        vol_df = pd.read_csv('成交量.csv', encoding='cp950', dtype={'證券代碼': str, '年月日': str})
    
    vol_df['Date'] = pd.to_datetime(vol_df['年月日'], format='%Y%m%d', errors='coerce')
    vol_df.rename(columns={'證券代碼': 'symbol', '週轉率％': 'Turnover'}, inplace=True)
    vol_df.set_index(['symbol', 'Date'], inplace=True)
    vol_df.sort_index(inplace=True)
    
    print("Generating trades...")
    trades_enhanced = []
    
    for idx, row in buy_signals.iterrows():
        stock_id = row['代碼']
        ann_date = row['AnnounceDate']
        
        search_idx = all_trading_dates.searchsorted(ann_date)
        if search_idx == 0: continue
        t_minus_1_date = all_trading_dates[search_idx - 1]
        
        future_dates = all_trading_dates[all_trading_dates > ann_date]
        if len(future_dates) == 0: continue
        entry_date = future_dates[0]
        
        try:
            turnover = vol_df.loc[(stock_id, t_minus_1_date), 'Turnover']
            if isinstance(turnover, pd.Series): turnover = turnover.iloc[0]
        except KeyError:
            continue
            
        # 20 Day Hold
        start_pos = all_trading_dates.searchsorted(entry_date)
        exit_pos = start_pos + 19
        if exit_pos < len(all_trading_dates):
            exit_date = all_trading_dates[exit_pos]
            trades_enhanced.append({
                'Stock': stock_id,
                'EntryDate': entry_date,
                'ExitDate': exit_date,
                'Turnover': turnover
            })

    print(f"Simulating portfolio for {len(trades_enhanced)} trades...")
    
    # Portfolio Simulation
    sum_ret_A = pd.Series(0.0, index=all_trading_dates)
    count_A = pd.Series(0, index=all_trading_dates)
    sum_ret_B = pd.Series(0.0, index=all_trading_dates)
    count_B = pd.Series(0, index=all_trading_dates)
    
    if daily_ret_matrix is not None:
        for t in trades_enhanced:
            stock = t['Stock']
            s_date = t['EntryDate']
            e_date = t['ExitDate']
            
            try:
                # Get daily returns slice
                if s_date not in daily_ret_matrix.index or e_date not in daily_ret_matrix.index:
                    continue
                    
                stock_rets = daily_ret_matrix.loc[s_date:e_date, stock].copy()
                
                # Fix first day return (Open to Close)
                open_price = price_df.loc[(stock, s_date), 'Open']
                close_price = price_df.loc[(stock, s_date), 'Close']
                stock_rets.iloc[0] = (close_price - open_price) / open_price
                
                sum_ret_A.loc[s_date:e_date] += stock_rets.fillna(0)
                count_A.loc[s_date:e_date] += 1
                
                if t['Turnover'] <= 1.0:
                    sum_ret_B.loc[s_date:e_date] += stock_rets.fillna(0)
                    count_B.loc[s_date:e_date] += 1
            except:
                pass
    
    daily_avg_A = sum_ret_A / count_A.replace(0, 1)
    daily_avg_A[count_A == 0] = 0.0
    daily_avg_B = sum_ret_B / count_B.replace(0, 1)
    daily_avg_B[count_B == 0] = 0.0
    
    cum_A = (1 + daily_avg_A).cumprod()
    cum_B = (1 + daily_avg_B).cumprod()
    
    # Plotting
    # Determine common start date
    valid_dates = count_A[count_A > 0].index
    if len(valid_dates) > 0:
        start_date = valid_dates[0]
        
        # Align all series
        plot_data = pd.DataFrame({
            'Market': market_cum,
            'Strategy A': cum_A,
            'Strategy B': cum_B
        }).loc[start_date:].dropna()
        
        # Rebase to 1.0
        plot_data = plot_data / plot_data.iloc[0]
        
        plt.figure(figsize=(12, 6))
        plt.plot(plot_data.index, plot_data['Market'], label='Market Benchmark (Buy & Hold)', color='blue', alpha=0.5)
        plt.plot(plot_data.index, plot_data['Strategy A'], label='Strategy A (No Filter)', color='gray', linestyle='--')
        plt.plot(plot_data.index, plot_data['Strategy B'], label='Strategy B (Turnover < 1%)', color='red', linewidth=2)
        
        plt.title('Strategy Performance vs Market (2024-2025)')
        plt.ylabel('Normalized Value')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('strategy_equity_curve.png')
        
        # Final Stats
        def get_stats(s):
            ret = (s.iloc[-1] - 1) * 100
            dd = calculate_max_drawdown(s)
            return ret, dd
            
        rM, dM = get_stats(plot_data['Market'])
        rA, dA = get_stats(plot_data['Strategy A'])
        rB, dB = get_stats(plot_data['Strategy B'])
        
        print("\n--- Final Strategy Report (Holding 20 Days) ---")
        print(f"{ 'Strategy':<30} | { 'Total Return':<12} | { 'Max Drawdown':<12}")
        print("-" * 60)
        print(f"{ 'Market Benchmark (Eq Wt)':<30} | {rM:>11.2f}% | {dM:>11.2f}%")
        print(f"{ 'Strategy A (All Signals)':<30} | {rA:>11.2f}% | {dA:>11.2f}%")
        print(f"{ 'Strategy B (Low Turnover <1%)':<30} | {rB:>11.2f}% | {dB:>11.2f}%")
    else:
        print("No valid trades for simulation.")

if __name__ == "__main__":
    plot_performance()
