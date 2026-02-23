import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def run_event_study():
    print("Loading data...")
    
    # 1. Load Signals (Revenue Announcements)
    try:
        signals_df = pd.read_csv('營收公告日.csv', encoding='utf-8', dtype={'代碼': str, '營收發布日': str})
    except:
        signals_df = pd.read_csv('營收公告日.csv', encoding='cp950', dtype={'代碼': str, '營收發布日': str})
    
    # Filter for 'H' (High Revenue Momentum)
    # The column name might have special characters, let's be careful
    # Based on previous head: '創新高/低(近一年)'
    target_col = [c for c in signals_df.columns if '創新高' in c][0]
    
    # Filter for 'H' signals
    buy_signals = signals_df[signals_df[target_col] == 'H'].copy()
    
    # Format Date: 20241009 -> 2024-10-09
    buy_signals['AnnounceDate'] = pd.to_datetime(buy_signals['營收發布日'], format='%Y%m%d', errors='coerce')
    buy_signals = buy_signals.dropna(subset=['AnnounceDate'])
    
    print(f"Loaded {len(buy_signals)} 'High Revenue' buy signals.")

    # 2. Load Price Data
    price_df = pd.read_csv('daily_price_data.csv', dtype={'symbol': str})
    price_df['Date'] = pd.to_datetime(price_df['Date'])
    
    # Create a MultiIndex for fast lookup: (Symbol, Date)
    price_df.set_index(['symbol', 'Date'], inplace=True)
    price_df = price_df.sort_index()
    
    print("Price data loaded and indexed.")

    # 3. Backtest Logic
    # We want to buy on T+1 (Next Trading Day after Announcement)
    # And hold for N days
    
    holding_periods = [1, 3, 5, 10, 20, 60] # Days to hold
    results = []
    
    # Get all unique trading dates to find T+N
    all_trading_dates = price_df.index.get_level_values(1).unique().sort_values()
    
    print("Running backtest...")
    
    for idx, row in buy_signals.iterrows():
        stock_id = row['代碼']
        ann_date = row['AnnounceDate']
        
        # Find T+1 (Entry Date)
        # Get dates greater than announcement date
        future_dates = all_trading_dates[all_trading_dates > ann_date]
        
        if len(future_dates) == 0:
            continue
            
        entry_date = future_dates[0] # T+1
        
        # Check if we have data for this stock on entry date
        try:
            entry_data = price_df.loc[(stock_id, entry_date)]
            entry_price = entry_data['Open'] # Buy at Open on T+1
        except KeyError:
            # Stock might be delisted or missing data for that day
            continue
            
        record = {
            'Stock': stock_id,
            'AnnounceDate': ann_date,
            'EntryDate': entry_date,
            'EntryPrice': entry_price
        }
        
        # Calculate Exit for each holding period
        # We need the index of entry_date in the all_trading_dates array to find T+N
        # This search sorted array is fast
        start_idx = all_trading_dates.searchsorted(entry_date)
        
        for hp in holding_periods:
            exit_idx = start_idx + hp - 1 # Hold for hp trading days. If hp=1, sell on same day Close? 
            # User said "Buy next day", usually means hold for 1 day return = (Close_T+1 - Open_T+1)/Open_T+1? 
            # Or Buy T+1 Open, Sell T+2 Open?
            # Let's assume Buy T+1 Open, Sell T+1+N Close.
            # If hp=1, Buy T+1 Open, Sell T+1 Close.
            
            # Actually, standard event study usually tracks cumulative return.
            # Let's define:
            # Hold 1 Day: Buy T+1 Open, Sell T+1 Close (Intraday) OR Buy T+1 Open, Sell T+2 Open.
            # Let's go with: Buy T+1 Open, Sell T+hp Close (closing price after hp days of trading).
            # If hp=1, Sell T+1 Close.
            
            target_date_idx = start_idx + hp - 1
            
            if target_date_idx < len(all_trading_dates):
                exit_date = all_trading_dates[target_date_idx]
                
                try:
                    exit_data = price_df.loc[(stock_id, exit_date)]
                    exit_price = exit_data['Close']
                    
                    ret = (exit_price - entry_price) / entry_price
                    record[f'Ret_{hp}d'] = ret
                except KeyError:
                    record[f'Ret_{hp}d'] = np.nan
            else:
                record[f'Ret_{hp}d'] = np.nan
                
        results.append(record)

    results_df = pd.DataFrame(results)
    
    # 4. Analyze Results
    print("\n--- Backtest Results: Buy Next Day Open (T+1) ---")
    print(f"Total Trades: {len(results_df)}")
    
    summary = []
    for hp in holding_periods:
        col = f'Ret_{hp}d'
        valid_trades = results_df[col].dropna()
        if valid_trades.empty:
            continue
            
        avg_ret = valid_trades.mean() * 100
        win_rate = (valid_trades > 0).mean() * 100
        median_ret = valid_trades.median() * 100
        
        print(f"Hold {hp} Days | Avg Return: {avg_ret:6.2f}% | Win Rate: {win_rate:6.2f}% | Median: {median_ret:6.2f}% | Trades: {len(valid_trades)}")
        
        summary.append({
            'Days': hp,
            'Avg_Return': avg_ret,
            'Win_Rate': win_rate
        })
        
    # Save detailed trade log
    results_df.to_csv('event_study_results.csv', index=False)
    print("\nDetailed trade log saved to 'event_study_results.csv'")
    
    # Simple Plot
    if summary:
        sum_df = pd.DataFrame(summary)
        plt.figure(figsize=(10, 6))
        plt.plot(sum_df['Days'], sum_df['Avg_Return'], marker='o', linestyle='-', linewidth=2)
        plt.title('Average Return vs Holding Period (Revenue High Momentum)')
        plt.xlabel('Holding Days')
        plt.ylabel('Average Return (%)')
        plt.grid(True)
        plt.axhline(0, color='red', linestyle='--')
        plt.savefig('event_study_chart.png')
        print("Chart saved to 'event_study_chart.png'")

if __name__ == "__main__":
    run_event_study()
