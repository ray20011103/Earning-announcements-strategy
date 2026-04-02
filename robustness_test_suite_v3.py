import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

def load_data_fixed():
    price_path = 'price.csv'
    ann_path = 'legacy_archive/announcement.csv'
    
    print(f"Loading Price Data from {price_path}...")
    df_price = pd.read_csv(price_path, low_memory=False, dtype={'證券代碼': str})
    df_price = df_price.rename(columns={
        '證券代碼': 'symbol', '年月日': 'Date', 
        '開盤價(元)': 'Open', '收盤價(元)': 'Close', 
        '週轉率％': 'Turnover'
    })
    df_price['Date'] = pd.to_datetime(df_price['Date'], format='mixed')
    df_price['symbol'] = df_price['symbol'].astype(str).str.split().str[0]
    
    # 重要：處理重複資料 (Duplicate handling)
    df_price = df_price.drop_duplicates(subset=['Date', 'symbol'])
    df_price = df_price.sort_values(['Date', 'symbol'])
    
    print(f"Loading Announcement Data from {ann_path}...")
    df_ann = pd.read_csv(ann_path, dtype={'代碼': str})
    df_ann = df_ann.rename(columns={
        '代碼': 'symbol', '營收發布日': 'ann_date',
        '單月營收成長率％': 'growth',
        '創新高/低(近一年)': 'high_year',
        '創新高/低(歷史)': 'high_hist'
    })
    df_ann['ann_date'] = pd.to_datetime(df_ann['ann_date'])
    return df_price, df_ann

def run_parameter_test(df_price, df_ann, holding_days=60, entry_type='Open', max_pos=20):
    INITIAL_CAPITAL = 10_000_000
    FEE_RATE = 0.001425 * 0.25
    TAX_RATE = 0.003
    
    # Pivot handles unique indices now
    price_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    price_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    price_turnover = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    price_ma20 = price_close.rolling(window=20).mean()
    
    trading_dates = price_close.index.sort_values()
    trading_dates_np = trading_dates.values
    
    mask = (df_ann['growth'] > 0) & (df_ann['high_year'].str.contains('H', na=False) | df_ann['high_hist'].str.contains('H', na=False))
    valid_signals = df_ann[mask].copy()
    
    ann_dates = valid_signals['ann_date'].values
    buy_indices = np.searchsorted(trading_dates_np, ann_dates, side='right')
    curr_indices = np.searchsorted(trading_dates_np, ann_dates, side='left')
    
    valid_mask = (buy_indices < len(trading_dates_np)) & (curr_indices < len(trading_dates_np))
    valid_signals = valid_signals[valid_mask].copy()
    valid_signals['buy_date'] = trading_dates_np[buy_indices[valid_mask]]
    valid_signals['ann_trading_date'] = trading_dates_np[curr_indices[valid_mask]]
    
    signals_by_date = {}
    for _, row in valid_signals.iterrows():
        try:
            close_t = price_close.at[row['ann_trading_date'], row['symbol']]
            ma20_t = price_ma20.at[row['ann_trading_date'], row['symbol']]
            if close_t > ma20_t:
                d = row['buy_date']
                if d not in signals_by_date: signals_by_date[d] = []
                to_val = price_turnover.at[row['ann_trading_date'], row['symbol']]
                signals_by_date[d].append({'symbol': row['symbol'], 'turnover': to_val})
        except: continue

    cash = INITIAL_CAPITAL
    holdings = []
    history = []
    curr_pos_size = INITIAL_CAPITAL / max_pos
    
    for i, date in enumerate(trading_dates):
        if date in signals_by_date:
            candidates = sorted(signals_by_date[date], key=lambda x: x['turnover'], reverse=True)
            slots = max_pos - len(holdings)
            for item in candidates[:slots]:
                sym = item['symbol']
                if sym not in price_open.columns: continue
                buy_price = price_open.at[date, sym] if entry_type == 'Open' else price_close.at[date, sym]
                if pd.isna(buy_price): continue
                if cash >= curr_pos_size * (1 + FEE_RATE):
                    shares = curr_pos_size / buy_price
                    holdings.append({'symbol': sym, 'shares': shares, 'buy_idx': i, 'buy_price': buy_price})
                    cash -= curr_pos_size * (1 + FEE_RATE)
        
        next_holdings = []
        for pos in holdings:
            if (i - pos['buy_idx']) >= holding_days:
                sell_price = price_close.at[date, pos['symbol']]
                if pd.isna(sell_price): sell_price = pos['buy_price']
                proceeds = pos['shares'] * sell_price
                cash += proceeds * (1 - FEE_RATE - TAX_RATE)
            else:
                next_holdings.append(pos)
        holdings = next_holdings
        
        mv = sum(p['shares'] * price_close.at[date, p['symbol']] for p in holdings if p['symbol'] in price_close.columns)
        history.append(cash + mv)
    
    equity = pd.Series(history, index=trading_dates)
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1/years) - 1
    return cagr

def run_robustness_suite():
    df_price, df_ann = load_data_fixed()
    
    # Test 1: Holding Period
    hp_results = {}
    print("Testing Holding Periods...")
    for days in [20, 40, 60, 80]:
        cagr = run_parameter_test(df_price, df_ann, holding_days=days)
        hp_results[days] = cagr
        print(f"  {days}d: {cagr:.2%}")

    # Test 2: Entry Timing
    et_results = {}
    print("Testing Entry Timing...")
    for et in ['Open', 'Close']:
        cagr = run_parameter_test(df_price, df_ann, entry_type=et)
        et_results[et] = cagr
        print(f"  {et}: {cagr:.2%}")

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    pd.Series(hp_results).plot(kind='bar', ax=ax1, color='skyblue', title='CAGR vs. Holding Days')
    pd.Series(et_results).plot(kind='bar', ax=ax2, color='salmon', title='CAGR vs. Entry Timing')
    plt.savefig('analysis_results/plots/robustness_final.png')
    print("Robustness Report saved: analysis_results/plots/robustness_final.png")

if __name__ == "__main__":
    run_robustness_suite()
