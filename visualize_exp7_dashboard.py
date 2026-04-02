import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import os

def create_dashboard():
    # Load data
    equity_file = 'analysis_results/data/cashflow_equity.csv'
    if not os.path.exists(equity_file):
        print("Equity data not found. Please run the backtest first.")
        return

    df = pd.read_csv(equity_file)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')

    # Constants
    MAX_POSITIONS = 20

    # Performance Stats
    start_val = df['TotalEquity'].iloc[0]
    end_val = df['TotalEquity'].iloc[-1]
    years = (df.index[-1] - df.index[0]).days / 365.25
    total_ret = (end_val / start_val) - 1
    cagr = (end_val / start_val) ** (1/years) - 1
    
    daily_ret = df['TotalEquity'].pct_change().dropna()
    sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252))
    
    rolling_max = df['TotalEquity'].cummax()
    drawdown = (df['TotalEquity'] - rolling_max) / rolling_max
    mdd = drawdown.min()

    # Create Figure
    fig = plt.figure(figsize=(15, 12), constrained_layout=True)
    gs = gridspec.GridSpec(4, 3, figure=fig)
    
    # 1. Summary Stats (Text)
    ax_text = fig.add_subplot(gs[0, :])
    ax_text.axis('off')
    summary_info = (
        f"Experiment 7: Trend-Filtered Revenue Momentum Strategy\n"
        f"Period: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}\n"
        f"CAGR: {cagr:.2%}  |  Sharpe: {sharpe:.2f}  |  Max Drawdown: {mdd:.2%}\n"
        f"Logic: Revenue High + 20MA Filter + High Turnover Priority"
    )
    ax_text.text(0.5, 0.5, summary_info, size=20, ha='center', va='center', 
                 bbox=dict(boxstyle="round", facecolor='skyblue', alpha=0.3))

    # 2. Equity Curve
    ax_equity = fig.add_subplot(gs[1:3, :])
    ax_equity.plot(df.index, df['TotalEquity'], color='#2980b9', linewidth=2, label='Strategy Equity')
    ax_equity.set_title('Cumulative Equity Curve (11-Year View)', fontsize=16)
    ax_equity.set_ylabel('Portfolio Value (TWD)', fontsize=12)
    ax_equity.grid(True, alpha=0.3)
    ax_equity.legend()

    # 3. Drawdown Plot
    ax_dd = fig.add_subplot(gs[3, :2])
    ax_dd.fill_between(df.index, drawdown * 100, color='#e74c3c', alpha=0.3)
    ax_dd.set_title('Drawdown (%)', fontsize=14)
    ax_dd.set_ylabel('Percentage (%)', fontsize=12)
    ax_dd.grid(True, alpha=0.3)

    # 4. Position Concentration
    ax_pos = fig.add_subplot(gs[3, 2])
    ax_pos.hist(df['Positions'], bins=range(MAX_POSITIONS + 2), color='#f1c40f', edgecolor='black', alpha=0.7)
    ax_pos.set_title('Daily Positions Distribution', fontsize=14)
    ax_pos.set_xlabel('Number of Positions', fontsize=12)
    ax_pos.set_ylabel('Frequency (Days)', fontsize=12)

    plt.savefig('analysis_results/plots/exp7_dashboard_final.png', dpi=300)
    print("Dashboard saved to: analysis_results/plots/exp7_dashboard_final.png")

if __name__ == "__main__":
    create_dashboard()
