import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import legacy_archive.backtest_cashflow as backtest_cashflow  # Import the core logic

def run_optimization():
    # Parameters to test
    holding_periods = [10, 20, 40, 60, 90, 120]
    
    results = []
    
    # Load data once to save time (if refactoring allows, otherwise we reload inside backtest)
    # Since backtest_cashflow.load_data() is fast enough, we can just reload or pass data.
    # To avoid modifying backtest_cashflow.py too much, we will slightly modify it to accept params
    # or we just monkey-patch the parameter for this script.
    
    print("Starting Holding Period Optimization...")
    print(f"Testing periods: {holding_periods}")
    
    for days in holding_periods:
        print(f"\n--- Testing Holding Period: {days} Days ---")
        
        # Monkey-patch the setting
        backtest_cashflow.HOLDING_DAYS = days
        
        # Capture output? We need the metrics.
        # We need to modify backtest_cashflow to RETURN metrics instead of just printing.
        # But for now, let's just run it and grab the equity curve from the CSV it saves,
        # OR we can modify backtest_cashflow to return the df_res.
        
        # Let's modify backtest_cashflow.py slightly to be callable and return data.
        # I will perform a quick refactor on backtest_cashflow.py first to make it return 'df_res'.
        
        df_res, df_trades = backtest_cashflow.run_backtest_engine() # We need to rename/expose this
        
        # Calculate Metrics
        final_equity = df_res['TotalEquity'].iloc[-1]
        initial_equity = df_res['TotalEquity'].iloc[0]
        total_ret = (final_equity / initial_equity) - 1
        
        # Sharpe
        daily_ret = df_res['TotalEquity'].pct_change().dropna()
        sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252)) if daily_ret.std() != 0 else 0
        
        # MDD
        rolling_max = df_res['TotalEquity'].cummax()
        drawdown = (df_res['TotalEquity'] - rolling_max) / rolling_max
        mdd = drawdown.min()
        
        print(f"Result: Return={total_ret:.2%}, Sharpe={sharpe:.2f}, MDD={mdd:.2%}")
        
        results.append({
            'Holding Days': days,
            'Total Return': total_ret,
            'CAGR': (final_equity/initial_equity)**(1/((df_res.index[-1]-df_res.index[0]).days/365.25)) - 1,
            'Sharpe Ratio': sharpe,
            'Max Drawdown': mdd
        })

    # Output Results
    df_results = pd.DataFrame(results).set_index('Holding Days')
    print("\n=== Optimization Results ===")
    print(df_results)
    
    # Plotting
    fig, ax1 = plt.figure(figsize=(10, 6)), plt.gca()
    
    # Dual axis plot
    color = 'tab:blue'
    ax1.set_xlabel('Holding Days')
    ax1.set_ylabel('CAGR', color=color)
    ax1.plot(df_results.index, df_results['CAGR'], marker='o', color=color, label='CAGR')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True)
    
    ax2 = ax1.twinx() 
    color = 'tab:red'
    ax2.set_ylabel('Sharpe Ratio', color=color)
    ax2.plot(df_results.index, df_results['Sharpe Ratio'], marker='s', linestyle='--', color=color, label='Sharpe')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('Optimization: Holding Period vs Performance')
    plt.tight_layout()
    plt.savefig('analysis_results/plots/optimization_holding_period.png')
    df_results.to_csv('analysis_results/data/optimization_results.csv')
    print("Saved analysis_results/plots/optimization_holding_period.png and analysis_results/data/optimization_results.csv")

if __name__ == "__main__":
    run_optimization()
