import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_data():
    df_price = pd.read_csv('price.csv', low_memory=False)
    df_price = df_price.rename(columns={'證券代碼': 'symbol', '年月日': 'Date', '開盤價(元)': 'Open', '收盤價(元)': 'Close', '週轉率％': 'Turnover'})
    df_price['Date'] = pd.to_datetime(df_price['Date'], format='%Y%m%d', errors='coerce')
    df_price['symbol'] = df_price['symbol'].astype(str).str.split().str[0]
    df_price = df_price.drop_duplicates(subset=['Date', 'symbol']).dropna(subset=['Date', 'Close'])
    
    df_ann = pd.read_csv('legacy_archive/announcement.csv')
    df_ann = df_ann.rename(columns={'公司': 'symbol', '營收發布日': 'ann_date', '單月營收成長率％': 'growth', '創新高/低(近一年)': 'high_year', '創新高/低(歷史)': 'high_hist'})
    df_ann['ann_date'] = pd.to_datetime(df_ann['ann_date'], errors='coerce')
    df_ann['growth'] = pd.to_numeric(df_ann['growth'], errors='coerce')
    df_ann['symbol'] = df_ann['symbol'].astype(str).str.split().str[0]
    df_ann = df_ann.dropna(subset=['ann_date', 'symbol'])
    return df_price, df_ann

def run_exit_test(df_price, df_ann, exit_type='Fixed', trailing_pct=0.10):
    # Core Params
    HOLDING_DAYS_MAX = 40 # Allow longer holding for dynamic exits
    FIXED_HOLDING = 20
    GROWTH_THRESH = 20
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    FEE = 0.001425 * 0.25
    TAX = 0.003

    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_ma = p_close.rolling(20).mean()
    dates = p_close.index.sort_values()
    
    mask = (df_ann['growth'] > GROWTH_THRESH) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    signals = df_ann[mask].copy()
    
    def get_buy_date(ann_date):
        idx = np.searchsorted(dates.values, ann_date, side='right')
        return dates[idx] if idx < len(dates) else None
    signals['buy_date'] = signals['ann_date'].apply(get_buy_date)
    signals = signals.dropna(subset=['buy_date'])
    sig_map = signals.groupby('buy_date')
    
    cash = INITIAL_CAPITAL
    holdings = [] # {'sym', 'shares', 'buy_idx', 'buy_p', 'max_p'}
    history = []
    pos_size = INITIAL_CAPITAL / MAX_POS
    
    for i, date in enumerate(dates):
        # 1. Sell Logic
        next_h = []
        for p in holdings:
            curr_p = p_close.at[date, p['sym']]
            # Update high price for trailing stop
            p['max_p'] = max(p['max_p'], curr_p)
            
            should_exit = False
            if exit_type == 'Fixed':
                # Exp 10: 20d OR -10% Stop Loss
                ret = (curr_p / p['buy_p']) - 1
                if (i - p['buy_idx']) >= FIXED_HOLDING or ret <= -0.10:
                    should_exit = True
            
            elif exit_type == 'Trailing':
                # Trailing Stop from peak
                if curr_p < p['max_p'] * (1 - trailing_pct):
                    should_exit = True
                elif (i - p['buy_idx']) >= HOLDING_DAYS_MAX:
                    should_exit = True
            
            elif exit_type == 'MA_Exit':
                # Close below 20MA
                try:
                    if curr_p < p_ma.at[date, p['sym']]:
                        should_exit = True
                    elif (i - p['buy_idx']) >= HOLDING_DAYS_MAX:
                        should_exit = True
                except: pass

            if should_exit:
                cash += p['shares'] * curr_p * (1 - FEE - TAX)
            else:
                next_h.append(p)
        holdings = next_h
        
        # 2. Buy Logic
        if date in sig_map.groups:
            day_sigs = sig_map.get_group(date)
            candidates = []
            for _, row in day_sigs.iterrows():
                sym = row['symbol']
                if sym in p_close.columns:
                    try:
                        if p_close.at[date, sym] > p_ma.at[date, sym]:
                            candidates.append(sym)
                    except: continue
            
            slots = MAX_POS - len(holdings)
            for sym in candidates[:slots]:
                buy_p = p_open.at[date, sym]
                if buy_p > 0 and cash >= pos_size * (1 + FEE):
                    holdings.append({'sym': sym, 'shares': pos_size/buy_p, 'buy_idx': i, 'buy_p': buy_p, 'max_p': buy_p})
                    cash -= pos_size * (1 + FEE)
        
        mv = sum(p['shares'] * p_close.at[date, p['sym']] for p in holdings)
        history.append(cash + mv)
        
    final_equity = history[-1]
    total_ret = (final_equity / INITIAL_CAPITAL) - 1
    equity_series = pd.Series(history, index=dates)
    rolling_max = equity_series.cummax()
    mdd = ((equity_series - rolling_max) / rolling_max).min()
    
    return total_ret, mdd

def compare_exits():
    df_p, df_a = load_data()
    results = []
    
    # 1. Exp 10 Fixed
    print("Testing Fixed Exit (Exp 10 Baseline)...")
    r, m = run_exit_test(df_p, df_a, exit_type='Fixed')
    results.append({'Type': 'Fixed (Exp 10)', 'Return': r, 'MDD': m})
    
    # 2. Trailing Stop 10%
    print("Testing Trailing Stop (10%)...")
    r, m = run_exit_test(df_p, df_a, exit_type='Trailing', trailing_pct=0.10)
    results.append({'Type': 'Trailing Stop 10%', 'Return': r, 'MDD': m})
    
    # 3. MA Exit
    print("Testing MA Exit (Close < 20MA)...")
    r, m = run_exit_test(df_p, df_a, exit_type='MA_Exit')
    results.append({'Type': 'MA Exit (20MA)', 'Return': r, 'MDD': m})
    
    df_res = pd.DataFrame(results).set_index('Type')
    print("\n--- Exit Optimization Results ---")
    print(df_res)
    
    # Plot
    df_res[['Return']].plot(kind='bar', figsize=(10, 6), color='skyblue', title='Impact of Exit Strategies on Total Return')
    plt.ylabel('Total Return (%)')
    plt.savefig('analysis_results/plots/exit_strategy_optimization.png')
    print("\nComparison saved: analysis_results/plots/exit_strategy_optimization.png")

if __name__ == "__main__":
    compare_exits()
