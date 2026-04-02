import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# 將 legacy_archive 加入路徑以便調用核心邏輯
sys.path.append('legacy_archive')
from backtest_cashflow import load_data, INITIAL_CAPITAL, MAX_POSITIONS, POSITION_SIZE, FEE_RATE, TAX_RATE

def run_parameter_test(df_price, df_ann, holding_days=60, entry_type='Open', max_pos=20):
    # 簡化版回測引擎，專門用於快速參數測試
    # 此處邏輯與 backtest_cashflow.py 核心一致
    
    price_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    price_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    price_turnover = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    price_ma20 = price_close.rolling(window=20).mean()
    
    trading_dates = price_close.index.sort_values()
    trading_dates_np = trading_dates.values
    
    # 訊號過濾 (Exp 7 邏輯)
    mask = (df_ann['growth'] > 0) & (df_ann['high_year'].str.contains('H', na=False) | df_ann['high_hist'].str.contains('H', na=False))
    valid_signals = df_ann[mask].copy()
    valid_signals = valid_signals.dropna(subset=['ann_date'])
    
    ann_dates = valid_signals['ann_date'].values
    buy_indices = np.searchsorted(trading_dates_np, ann_dates, side='right')
    curr_indices = np.searchsorted(trading_dates_np, ann_dates, side='left')
    
    valid_mask = (buy_indices < len(trading_dates_np)) & (curr_indices < len(trading_dates_np))
    valid_signals = valid_signals[valid_mask].copy()
    valid_signals['buy_date'] = trading_dates_np[buy_indices[valid_mask]]
    valid_signals['ann_trading_date'] = trading_dates_np[curr_indices[valid_mask]]
    
    # Trend Filter & Turnover
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

    # Simulation
    cash = INITIAL_CAPITAL
    holdings = []
    history = []
    curr_pos_size = INITIAL_CAPITAL / max_pos
    
    for i, date in enumerate(trading_dates):
        # Buy
        if date in signals_by_date:
            candidates = sorted(signals_by_date[date], key=lambda x: x['turnover'], reverse=True)
            slots = max_pos - len(holdings)
            for item in candidates[:slots]:
                sym = item['symbol']
                buy_price = price_open.at[date, sym] if entry_type == 'Open' else price_close.at[date, sym]
                if pd.isna(buy_price): continue
                if cash >= curr_pos_size * (1 + FEE_RATE):
                    shares = curr_pos_size / buy_price
                    holdings.append({'symbol': sym, 'shares': shares, 'buy_idx': i, 'buy_price': buy_price})
                    cash -= curr_pos_size * (1 + FEE_RATE)
        
        # Sell
        next_holdings = []
        for pos in holdings:
            if (i - pos['buy_idx']) >= holding_days:
                sell_price = price_close.at[date, pos['symbol']]
                proceeds = pos['shares'] * sell_price
                cash += proceeds * (1 - FEE_RATE - TAX_RATE)
            else:
                next_holdings.append(pos)
        holdings = next_holdings
        
        # Valuation
        mv = sum(p['shares'] * price_close.at[date, p['symbol']] for p in holdings)
        history.append(cash + mv)
    
    equity = pd.Series(history, index=trading_dates)
    total_ret = (equity.iloc[-1] / equity.iloc[0]) - 1
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1/years) - 1
    return cagr, total_ret

def run_robustness_suite():
    print("Loading Data for Robustness Test...")
    df_price, df_ann = load_data()
    
    # Test 1: Holding Period Sensitivity
    print("Test 1: Holding Period Sensitivity Analysis...")
    hp_results = {}
    for days in [20, 40, 60, 80, 100, 120]:
        cagr, _ = run_parameter_test(df_price, df_ann, holding_days=days)
        hp_results[days] = cagr
        print(f"  Holding {days} days: CAGR = {cagr:.2%}")

    # Test 2: Entry Timing Sensitivity
    print("Test 2: Entry Timing Sensitivity Analysis...")
    et_results = {}
    for et in ['Open', 'Close']:
        cagr, _ = run_parameter_test(df_price, df_ann, entry_type=et)
        et_results[et] = cagr
        print(f"  Entry at {et}: CAGR = {cagr:.2%}")

    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot HP
    pd.Series(hp_results).plot(kind='bar', ax=ax1, color='teal')
    ax1.set_title('CAGR vs. Holding Period (Days)')
    ax1.set_ylabel('Annualized Return (CAGR)')
    ax1.set_xlabel('Holding Period (Trading Days)')
    ax1.axhline(y=0.146, color='red', linestyle='--', label='Exp 7 (60d)')
    ax1.legend()

    # Plot ET
    pd.Series(et_results).plot(kind='bar', ax=ax2, color='orange')
    ax2.set_title('CAGR vs. Entry Timing')
    ax2.set_ylabel('Annualized Return (CAGR)')
    ax2.set_xlabel('Entry Price Point')
    
    plt.tight_layout()
    plt.savefig('analysis_results/plots/robustness_test_results.png')
    print("\nRobustness tests completed. Chart saved: analysis_results/plots/robustness_test_results.png")

if __name__ == "__main__":
    run_robustness_suite()
