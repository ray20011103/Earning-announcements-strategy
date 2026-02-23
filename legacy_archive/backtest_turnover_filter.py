import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def run_turnover_backtest():
    print("Loading data...")
    
    # 1. Load Signals (Revenue Announcements)
    try:
        signals_df = pd.read_csv('營收公告日.csv', encoding='utf-8', dtype={'代碼': str, '營收發布日': str})
    except:
        signals_df = pd.read_csv('營收公告日.csv', encoding='cp950', dtype={'代碼': str, '營收發布日': str})
    
    # Filter for 'H'
    # The column name might have special characters
    target_col = [c for c in signals_df.columns if '創新高' in c][0]
    buy_signals = signals_df[signals_df[target_col] == 'H'].copy()
    buy_signals['AnnounceDate'] = pd.to_datetime(buy_signals['營收發布日'], format='%Y%m%d', errors='coerce')
    buy_signals = buy_signals.dropna(subset=['AnnounceDate'])
    
    # 2. Load Price Data (Daily)
    price_df = pd.read_csv('daily_price_data.csv', dtype={'symbol': str})
    price_df['Date'] = pd.to_datetime(price_df['Date'])
    price_df.set_index(['symbol', 'Date'], inplace=True)
    price_df.sort_index(inplace=True)
    
    # 3. Load Turnover Data (Volume CSV)
    print("Loading turnover data...")
    try:
        vol_df = pd.read_csv('成交量.csv', encoding='utf-8', dtype={'證券代碼': str, '年月日': str})
    except:
        vol_df = pd.read_csv('成交量.csv', encoding='cp950', dtype={'證券代碼': str, '年月日': str})
    
    vol_df['Date'] = pd.to_datetime(vol_df['年月日'], format='%Y%m%d', errors='coerce')
    vol_df.rename(columns={'證券代碼': 'symbol', '週轉率％': 'Turnover'}, inplace=True)
    vol_df.set_index(['symbol', 'Date'], inplace=True)
    vol_df.sort_index(inplace=True)
    
    # 4. Processing
    print("Processing signals and linking turnover...")
    
    all_trading_dates = price_df.index.get_level_values(1).unique().sort_values()
    
    results = []
    
    for idx, row in buy_signals.iterrows():
        stock_id = row['代碼']
        ann_date = row['AnnounceDate']
        
        # Locate AnnounceDate index
        search_idx = all_trading_dates.searchsorted(ann_date)
        if search_idx == 0:
            continue
            
        # T-1 (Previous Trading Day)
        t_minus_1_date = all_trading_dates[search_idx - 1]
        
        # T+1 (Entry Date)
        future_dates = all_trading_dates[all_trading_dates > ann_date]
        if len(future_dates) == 0:
            continue
        t_plus_1_date = future_dates[0]
        
        # Get Turnover at T-1
        try:
            turnover = vol_df.loc[(stock_id, t_minus_1_date), 'Turnover']
            if isinstance(turnover, pd.Series):
                turnover = turnover.iloc[0]
        except KeyError:
            continue
            
        # Get Returns
        try:
            entry_data = price_df.loc[(stock_id, t_plus_1_date)]
            entry_price = entry_data['Open']
            
            periods = [1, 3, 5, 10, 20]
            start_pos = all_trading_dates.searchsorted(t_plus_1_date)
            
            res_row = {'Turnover_T_minus_1': turnover}
            
            for hp in periods:
                exit_pos = start_pos + hp - 1
                if exit_pos < len(all_trading_dates):
                    exit_date = all_trading_dates[exit_pos]
                    try:
                        exit_price = price_df.loc[(stock_id, exit_date), 'Close']
                        ret = (exit_price - entry_price) / entry_price
                        res_row[f'Ret_{hp}d'] = ret
                    except:
                        res_row[f'Ret_{hp}d'] = np.nan
                else:
                    res_row[f'Ret_{hp}d'] = np.nan
            
            results.append(res_row)
            
        except KeyError:
            continue

    df_res = pd.DataFrame(results)
    print(f"Total valid samples: {len(df_res)}")
    
    # 5. Analyze by Thresholds (Focused on 20 Days)
    print("\n" + "="*85)
    print(f"--- 20-Day (Monthly) Holding Period Analysis ---")
    print(f"{ 'Filter Type':<20} | { 'Condition':<12} | { 'Count':<6} | { 'Avg Ret 20D':<12} | { 'Win Rate 20D':<12} | { 'Median 20D':<12}")
    print("-" * 85)
    
    # Test High Turnover Filters
    high_thresholds = [0, 0.5, 1.0, 3.0, 5.0]
    for th in high_thresholds:
        subset = df_res[df_res['Turnover_T_minus_1'] > th]
        count = len(subset)
        if count == 0: continue
        
        r20 = subset['Ret_20d']
        avg_20 = r20.mean() * 100
        win_20 = (r20 > 0).mean() * 100
        med_20 = r20.median() * 100
        
        print(f"{ 'High Turnover':<20} | { f'> {th}%':<12} | { count:<6} | { avg_20:>10.2f}% | { win_20:>10.2f}% | { med_20:>10.2f}%")

    print("-" * 85)

    # Test Low Turnover Filters
    low_thresholds = [0.5, 1.0, 3.0, 5.0]
    for th in low_thresholds:
        subset = df_res[df_res['Turnover_T_minus_1'] <= th]
        count = len(subset)
        if count == 0: continue
        
        r20 = subset['Ret_20d']
        avg_20 = r20.mean() * 100
        win_20 = (r20 > 0).mean() * 100
        med_20 = r20.median() * 100
        
        print(f"{ 'Low Turnover':<20} | { f'<= {th}%':<12} | { count:<6} | { avg_20:>10.2f}% | { win_20:>10.2f}% | { med_20:>10.2f}%")
        
    print("="*85)
    
    # Save results
    df_res.to_csv('turnover_filter_analysis.csv', index=False)
    print("\nDetailed analysis saved to 'turnover_filter_analysis.csv'")

if __name__ == "__main__":
    run_turnover_backtest()