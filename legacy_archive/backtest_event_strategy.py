import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Settings
HOLDING_DAYS = 20
TURNOVER_RANK_THRESHOLD = 0.5 # Filter stocks with turnover rank <= 0.5 (Bottom 50%)
FEES = 0.001425 * 0.25 # Discounted trading fee
TAX = 0.003 # Transaction tax

def load_data():
    print("Loading data...")
    
    # 1. Load Daily Price Data
    # Columns: 證券代碼,年月日,收盤價(元),成交值(千元),週轉率％,市值(百萬元)
    df_price = pd.read_csv('daily_price_data.csv', dtype={'證券代碼': str})
    
    # Rename for easier access
    price_cols = {
        '證券代碼': 'symbol',
        '年月日': 'Date',
        '收盤價(元)': 'Close',
        '週轉率％': 'Turnover_Pct'
    }
    df_price = df_price.rename(columns=price_cols)
    
    # Clean up Date
    # The format is YYYYMMDD (e.g., 20150105)
    df_price['Date'] = pd.to_datetime(df_price['Date'], format='%Y%m%d', errors='coerce')
    
    # Clean up Symbol (remove names if any, though looks like just code "1101")
    df_price['symbol'] = df_price['symbol'].astype(str).str.split().str[0]
    
    # Sort
    df_price = df_price.sort_values(['symbol', 'Date']).reset_index(drop=True)
    print(f"Daily Price Data: {df_price.shape}")

    # 2. Load Announcement Data
    # Columns from user file: 代碼,名稱,營收發布日,預估營收發佈日,單月營收成長率％,創新高/低(近一年)
    try:
        df_ann = pd.read_csv('announcement.csv', dtype={'代碼': str})
    except:
        df_ann = pd.read_csv('announcement.csv', dtype={0: str})
    
    print(f"Announcement Data Columns: {df_ann.columns.tolist()}")
    
    # Standardize column names
    ann_cols = {
        '代碼': 'symbol', '公司': 'symbol', 
        '營收發布日': 'ann_date', 
        '單月營收成長率％': 'growth_yoy',
        '創新高/低(近一年)': 'high_year',
        '創新高/低(歷史)': 'high_hist'
    }
    df_ann = df_ann.rename(columns=ann_cols)
    
    # Clean symbol
    df_ann['symbol'] = df_ann['symbol'].astype(str).str.split().str[0]
    
    # Parse dates
    df_ann['ann_date'] = pd.to_datetime(df_ann['ann_date'], errors='coerce')
    
    # Filter valid announcements
    df_ann = df_ann.dropna(subset=['ann_date'])
    
    return df_price, df_ann

def run_backtest():
    df_price, df_ann = load_data()
    
    # 1. Filter Announcements (Signal Generation)
    print("Filtering Announcements (Signal)...")
    # Condition: Growth > 0 AND (New High Year == 'H')
    mask_growth = pd.to_numeric(df_ann['growth_yoy'], errors='coerce') > 0
    
    # Check for 'H' in high_year (handle NaN)
    if 'high_year' in df_ann.columns:
        mask_high = df_ann['high_year'].astype(str).str.contains('H', na=False)
    else:
        mask_high = pd.Series(False, index=df_ann.index)
        
    # Optional: Check Historical High if Year High not available or preferred
    if 'high_hist' in df_ann.columns:
        mask_high_hist = df_ann['high_hist'].astype(str).str.contains('H', na=False)
        mask_high = mask_high | mask_high_hist
    
    valid_signals = df_ann[mask_growth & mask_high].copy()
    print(f"Signals after basic filter (Pos Growth & High): {len(valid_signals)}")
    
    # 2. Prepare Data for Backtest
    # We need to map Ann Date -> T (Price Date) -> T+1 (Buy Date)
    # And check Turnover at T-1 (or T).
    
    # Ensure Date index for fast lookup
    # Creating a MultiIndex DataFrame for fast lookup: (Date, Symbol) -> Price/Turnover
    print("Indexing Price Data...")
    df_price.set_index(['Date', 'symbol'], inplace=True)
    df_price = df_price.sort_index()
    
    trades = []
    
    # Get all unique trading dates for finding T+1, T+20
    all_trading_dates = df_price.index.get_level_values('Date').unique().sort_values()
    
    print("Processing Signals and Simulating Trades...")
    # This loop can be optimized, but with ~20k signals it's manageable.
    
    for idx, row in valid_signals.iterrows():
        sym = row['symbol']
        ann_date = row['ann_date']
        
        # Find T (Announcement Date Trading Day)
        t_loc = all_trading_dates.searchsorted(ann_date)
        
        if t_loc >= len(all_trading_dates):
            continue # Data ends
            
        t_date = all_trading_dates[t_loc]
        
        # Check Turnover Filter on T-1 (Day before signal is actionable)
        if t_loc == 0:
            continue
            
        t_minus_1_date = all_trading_dates[t_loc - 1]
        
        try:
            # Look up Turnover on T-1
            turnover = df_price.at[(t_minus_1_date, sym), 'Turnover_Pct']
            
            # Basic Liquidity Filter
            if pd.isna(turnover) or turnover == 0:
                continue
                
        except KeyError:
            continue # No price/turnover data for this stock on T-1
            
        # Buy Date = T+1 (Next Trading Day after T)
        buy_loc = t_loc + 1
        if buy_loc >= len(all_trading_dates):
            continue
            
        buy_date = all_trading_dates[buy_loc]
        
        # Sell Date = Buy Date + 20
        sell_loc = buy_loc + HOLDING_DAYS
        if sell_loc >= len(all_trading_dates):
            # Close at last available date
            sell_date = all_trading_dates[-1]
            status = 'Early_Close'
        else:
            sell_date = all_trading_dates[sell_loc]
            status = 'Normal'
            
        # Get Prices
        try:
            # Buy at Close of T+1 (Since Open is missing)
            buy_price = df_price.at[(buy_date, sym), 'Close']
            sell_price = df_price.at[(sell_date, sym), 'Close']
            
            if pd.isna(buy_price) or pd.isna(sell_price):
                continue
                
            # Calculate Return (Gross for list)
            raw_ret = (sell_price - buy_price) / buy_price
            net_ret = raw_ret - (FEES * 2 + TAX)
            
            trades.append({
                'symbol': sym,
                'ann_date': ann_date,
                'buy_date': buy_date,
                'sell_date': sell_date,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'turnover_T-1': turnover,
                'return': net_ret,
                'status': status
            })
            
        except KeyError:
            continue

    df_trades = pd.DataFrame(trades)
    print(f"Total Trades Simulated: {len(df_trades)}")
    
    if df_trades.empty:
        print("No trades generated.")
        return

    # 5. Analysis (Portfolio Level Equity Curve)
    print("Calculating Portfolio Equity Curve...")
    
    # Reset index to make 'symbol' and 'Date' columns again for analysis pivot
    df_price_reset = df_price.reset_index()
    
    # We need daily returns for all stocks involved
    # Re-pivot df_price to wide format: Index=Date, Columns=Symbol, Values=Close
    # Filter only relevant symbols to save memory
    traded_symbols = df_trades['symbol'].unique()
    df_price_sub = df_price_reset[df_price_reset['symbol'].isin(traded_symbols)]
    
    # Pivot Close Prices
    df_close = df_price_sub.pivot(index='Date', columns='symbol', values='Close')
    # Calculate Daily Returns
    df_daily_rets = df_close.pct_change()
    
    # Initialize Positions Matrix (0 = Not Held, 1 = Held)
    # Align index with close prices
    positions = pd.DataFrame(0, index=df_close.index, columns=df_close.columns)
    
    for idx, row in df_trades.iterrows():
        sym = row['symbol']
        b_date = row['buy_date']
        s_date = row['sell_date']
        
        # Check if dates exist in index
        if b_date in positions.index and s_date in positions.index:
            try:
                # Find loc
                b_idx = positions.index.get_loc(b_date)
                s_idx = positions.index.get_loc(s_date)
                
                if s_idx > b_idx:
                    # Mark holding period
                    # We hold from b_date (Close) through s_date-1 (Close)
                    # Exposure starts from returns of b_date+1
                    if sym in positions.columns:
                        col_idx = positions.columns.get_loc(sym)
                        # Slice includes b_idx (Buy Close) up to s_idx-1 (Day before Sell Close)
                        # Positions at end of day.
                        # Position at b_idx means we hold it overnight -> exposed to b_idx+1 return
                        positions.iloc[b_idx:s_idx, col_idx] += 1
                    
            except Exception as e:
                continue

    # Calculate Portfolio Daily Return
    # Portfolio Return_t = mean( Stock_Ret_t ) for all stocks held at t-1
    # shift(1) aligns positions at t-1 with returns at t
    
    held_yesterday = positions.shift(1)
    
    # Sum of returns of held stocks
    daily_sum_ret = (df_daily_rets * held_yesterday).sum(axis=1)
    daily_count = held_yesterday.sum(axis=1)
    
    # Avoid division by zero
    portfolio_daily_ret = daily_sum_ret / daily_count.replace(0, np.nan)
    portfolio_daily_ret = portfolio_daily_ret.fillna(0)
    
    # Equity Curve
    equity_curve = (1 + portfolio_daily_ret).cumprod()
    
    # Stats
    total_return = equity_curve.iloc[-1] - 1
    # CAGR approximation
    if len(equity_curve) > 0:
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365.25
        cagr = (total_return + 1) ** (1/years) - 1 if years > 0 else 0
    else:
        cagr = 0
    
    sharpe = (portfolio_daily_ret.mean() * 252) / (portfolio_daily_ret.std() * np.sqrt(252)) if portfolio_daily_ret.std() != 0 else 0
    
    print("\n--- Portfolio Backtest Results (Gross) ---")
    if len(equity_curve) > 0:
        print(f"Total Period: {equity_curve.index[0].date()} to {equity_curve.index[-1].date()}")
    print(f"Total Return: {total_return:.2%}")
    print(f"CAGR: {cagr:.2%}")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Avg Positions per Day: {daily_count.mean():.1f}")
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve.index, equity_curve.values, label='Event Strategy (Gross)')
    plt.title(f'Event Strategy Equity Curve (Buy T+1, Hold {HOLDING_DAYS} Days)')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return (1.0 = Start)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('event_strategy_performance.png')
    
    # Save Daily Returns
    portfolio_daily_ret.to_csv('event_strategy_daily_returns.csv')
    df_trades.to_csv('event_strategy_trades_v2.csv', index=False)
    print("Results saved: event_strategy_performance.png, event_strategy_daily_returns.csv")

if __name__ == "__main__":
    run_backtest()