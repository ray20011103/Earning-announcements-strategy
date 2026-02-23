import pandas as pd
import numpy as np
import datetime

def run_strategy():
    file_path = 'monthly_data.csv'
    
    print("Loading data...")
    try:
        df = pd.read_csv(file_path, header=[0, 1], encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, header=[0, 1], encoding='cp950')
    
    # Extract date column (first column, level 0 is 'Unnamed: 0_level_0' or empty, level 1 is '年月日')
    date_col = df.iloc[:, 0]
    
    # Initialize lists to hold processed data
    long_data = []
    
    # The first column is Date, skip it.
    # Level 0 contains Stock Names/IDs repeated.
    # Level 1 contains attributes.
    
    # Get unique stock identifiers from Level 0, excluding the first empty/date column
    stock_cols = df.columns.get_level_values(0).unique()
    stock_cols = [c for c in stock_cols if 'Unnamed' not in str(c)]
    
    print(f"Processing {len(stock_cols)} stocks...")
    
    for stock in stock_cols:
        try:
            # Extract data for this stock
            stock_df = df[stock].copy()
            
            # We need '年月日' (Date), '單月營收(千元)' (Sales), '收盤價(元)' (Price)
            # The Date is in the main df, let's add it
            stock_df['Date'] = date_col
            
            # Check if columns exist
            if '單月營收(千元)' not in stock_df.columns or '收盤價(元)' not in stock_df.columns:
                continue
                
            # Rename columns for simpler access
            stock_df = stock_df.rename(columns={
                '單月營收(千元)': 'Sales',
                '收盤價(元)': 'Price'
            })
            
            # Keep only relevant columns
            stock_df = stock_df[['Date', 'Sales', 'Price']]
            
            # Add Stock ID column
            stock_df['Stock'] = stock
            
            long_data.append(stock_df)
        except Exception as e:
            print(f"Error processing {stock}: {e}")
            continue
            
    # Concatenate all stock data
    if not long_data:
        print("No valid stock data found.")
        return

    full_df = pd.concat(long_data, ignore_index=True)
    
    # Data Cleaning
    print("Cleaning data...")
    # Convert numeric columns (remove commas)
    for col in ['Sales', 'Price']:
        full_df[col] = full_df[col].astype(str).str.replace(',', '', regex=False)
        full_df[col] = pd.to_numeric(full_df[col], errors='coerce')
    
    # Convert Date
    full_df['Date'] = pd.to_datetime(full_df['Date'], errors='coerce')
    full_df = full_df.dropna(subset=['Date', 'Sales'])
    
    # Sort for rolling calculation
    full_df = full_df.sort_values(by=['Stock', 'Date'])
    
    # Calculate Historical Maximum Sales (excluding current month)
    # Shift 1 to exclude current, then expanding max
    print("Calculating HI indicator...")
    
    full_df['HistMaxSales'] = full_df.groupby('Stock')['Sales'].apply(
        lambda x: x.expanding().max().shift(1)
    ).reset_index(level=0, drop=True)
    
    # Calculate HI (Sales / HistMaxSales)
    # Handle division by zero or NaN
    full_df['HI'] = full_df['Sales'] / full_df['HistMaxSales']
    
    # Filter valid HI values (not infinite, not NaN)
    valid_df = full_df[np.isfinite(full_df['HI'])].copy()
    
    # Get the latest date
    latest_date = valid_df['Date'].max()
    print(f"\nLatest Data Date: {latest_date.strftime('%Y-%m-%d')}")
    
    # Filter for latest date
    latest_df = valid_df[valid_df['Date'] == latest_date].copy()
    
    if latest_df.empty:
        print("No data found for the latest date.")
        return
    
    # Rank by HI
    latest_df['Rank_Pct'] = latest_df['HI'].rank(pct=True)
    
    # Select Winners (Top 10%)
    winners = latest_df[latest_df['Rank_Pct'] >= 0.9].sort_values(by='HI', ascending=False)
    
    # Select Losers (Bottom 10%) - Optional, for info
    losers = latest_df[latest_df['Rank_Pct'] <= 0.1].sort_values(by='HI', ascending=True)
    
    print("\n--- Strategy: Highest Monthly Sales Momentum (HI) ---")
    print(f"Number of stocks analyzed: {len(latest_df)}")
    print(f"Top 10% Threshold HI > {winners['HI'].min():.4f}")
    
    print("\n[Top 20 Winners - Potential Buys]")
    print(f"{ 'Stock':<15} | { 'Price':<8} | { 'Sales(k)':<12} | { 'HistMax(k)':<12} | { 'HI Ratio':<8}")
    print("-" * 75)
    for _, row in winners.head(20).iterrows():
        print(f"{row['Stock']:<15} | {row['Price']:<8.2f} | {row['Sales']:<12.0f} | {row['HistMaxSales']:<12.0f} | {row['HI']:<8.4f}")
        
    # Save results
    output_file = 'strategy_results_latest.csv'
    winners.to_csv(output_file, index=False)
    print(f"\nFull list of winners saved to {output_file}")

if __name__ == "__main__":
    run_strategy()