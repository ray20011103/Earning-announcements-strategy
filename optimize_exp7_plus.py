import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_data_final():
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

def run_optimized_test(df_price, df_ann, holding_days=20, growth_thresh=0, stop_loss=None):
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    FEE = 0.001425 * 0.25
    TAX = 0.003
    
    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_to = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    p_ma = p_close.rolling(20).mean()
    dates = p_close.index.sort_values()
    
    # Filter with Growth Threshold
    mask = (df_ann['growth'] > growth_thresh) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    signals = df_ann[mask].copy()
    
    def get_next_date(d):
        idx = np.searchsorted(dates.values, d, side='right')
        return dates[idx] if idx < len(dates) else None
    
    signals['buy_date'] = signals['ann_date'].apply(get_next_date)
    signals = signals.dropna(subset=['buy_date'])
    sig_map = signals.groupby('buy_date')
    
    cash = INITIAL_CAPITAL
    holdings = [] # List of {'sym', 'shares', 'buy_idx', 'buy_p'}
    history = []
    pos_size = INITIAL_CAPITAL / MAX_POS
    
    for i, date in enumerate(dates):
        # 1. Sell / Stop-Loss check
        next_h = []
        for p in holdings:
            curr_p = p_close.at[date, p['sym']]
            unrealized_ret = (curr_p / p['buy_p']) - 1
            
            # Condition: Time to sell OR Stop Loss triggered
            is_stop_loss = stop_loss is not None and unrealized_ret <= stop_loss
            is_time_up = (i - p['buy_idx']) >= holding_days
            
            if is_time_up or is_stop_loss:
                cash += p['shares'] * curr_p * (1 - FEE - TAX)
            else:
                next_h.append(p)
        holdings = next_h
        
        # 2. Buy
        if date in sig_map.groups:
            day_sigs = sig_map.get_group(date)
            candidates = []
            for _, row in day_sigs.iterrows():
                sym = row['symbol']
                if sym in p_close.columns:
                    try:
                        if p_close.at[date, sym] > p_ma.at[date, sym]:
                            candidates.append({'sym': sym, 'to': p_to.at[date, sym]})
                    except: continue
            
            candidates = sorted(candidates, key=lambda x: x['to'] if not pd.isna(x['to']) else 0, reverse=True)
            slots = MAX_POS - len(holdings)
            for c in candidates[:slots]:
                sym = c['sym']
                buy_p = p_open.at[date, sym]
                if not pd.isna(buy_p) and buy_p > 0 and cash >= pos_size * (1 + FEE):
                    holdings.append({'sym': sym, 'shares': pos_size/buy_p, 'buy_idx': i, 'buy_p': buy_p})
                    cash -= pos_size * (1 + FEE)
        
        mv = sum(p['shares'] * p_close.at[date, p['sym']] for p in holdings)
        history.append(cash + mv)
        
    equity = pd.Series(history, index=dates)
    total_ret = (equity.iloc[-1] / INITIAL_CAPITAL) - 1
    
    # Calculate MDD
    rolling_max = equity.cummax()
    mdd = ((equity - rolling_max) / rolling_max).min()
    
    return total_ret, mdd

def run_optimization():
    df_price, df_ann = load_data_final()
    
    scenarios = [
        {'name': 'Base (20d, >0%)', 'days': 20, 'growth': 0, 'stop': None},
        {'name': 'Growth+ (20d, >20%)', 'days': 20, 'growth': 20, 'stop': None},
        {'name': 'Safe (20d, >20%, -10%SL)', 'days': 20, 'growth': 20, 'stop': -0.10},
    ]
    
    results = []
    print("Running Optimization Scenarios...")
    for s in scenarios:
        ret, mdd = run_optimized_test(df_price, df_ann, holding_days=s['days'], growth_thresh=s['growth'], stop_loss=s['stop'])
        results.append({'Scenario': s['name'], 'Return': ret, 'MDD': mdd})
        print(f"  {s['name']}: Return={ret:.2%}, MDD={mdd:.2%}")

    # Plot
    df_res = pd.DataFrame(results).set_index('Scenario')
    fig, ax1 = plt.subplots(figsize=(12, 6))
    df_res['Return'].plot(kind='bar', ax=ax1, color='navy', position=0, width=0.4, label='Total Return')
    ax2 = ax1.twinx()
    df_res['MDD'].plot(kind='bar', ax=ax2, color='red', alpha=0.5, position=1, width=0.4, label='Max Drawdown')
    
    ax1.set_ylabel('Total Return')
    ax2.set_ylabel('Max Drawdown')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.title('Optimization Comparison: Growth Threshold & Stop-Loss')
    plt.savefig('analysis_results/plots/optimization_final_comparison.png')
    print("Optimization Analysis saved: analysis_results/plots/optimization_final_comparison.png")

if __name__ == "__main__":
    run_optimization()
