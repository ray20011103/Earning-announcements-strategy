import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_data_v7():
    print("Loading Data (v7 - corrected column names)...")
    # Price Data
    df_price = pd.read_csv('price.csv', low_memory=False)
    df_price = df_price.rename(columns={'證券代碼': 'symbol', '年月日': 'Date', '開盤價(元)': 'Open', '收盤價(元)': 'Close', '週轉率％': 'Turnover'})
    df_price['Date'] = pd.to_datetime(df_price['Date'], format='%Y%m%d', errors='coerce')
    df_price['symbol'] = df_price['symbol'].astype(str).str.split().str[0]
    df_price = df_price.drop_duplicates(subset=['Date', 'symbol']).dropna(subset=['Date', 'Close'])
    
    # Announcement Data
    # 根據 head 觀察：公司,年月,營收發布日,單月營收成長率％,創新高/低(歷史),創新高/低(近一年)
    df_ann = pd.read_csv('legacy_archive/announcement.csv')
    df_ann = df_ann.rename(columns={
        '公司': 'symbol', 
        '營收發布日': 'ann_date', 
        '單月營收成長率％': 'growth', 
        '創新高/低(近一年)': 'high_year', 
        '創新高/低(歷史)': 'high_hist'
    })
    df_ann['ann_date'] = pd.to_datetime(df_ann['ann_date'], errors='coerce')
    df_ann['growth'] = pd.to_numeric(df_ann['growth'], errors='coerce')
    # 這裡要注意 symbol 可能是 "2330 台積電"，我們只要數字
    df_ann['symbol'] = df_ann['symbol'].astype(str).str.split().str[0]
    df_ann = df_ann.dropna(subset=['ann_date', 'symbol'])
    
    return df_price, df_ann

def run_test(df_price, df_ann, holding_days=60, entry='Open'):
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    FEE = 0.001425 * 0.25
    TAX = 0.003
    
    print(f"  Testing: {holding_days}d")
    # Pivot
    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_to = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    p_ma = p_close.rolling(20).mean()
    dates = p_close.index.sort_values()
    
    # Valid Signals
    mask = (df_ann['growth'] > 0) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    signals = df_ann[mask].copy()
    
    def get_next_date(d):
        idx = np.searchsorted(dates.values, d, side='right')
        return dates[idx] if idx < len(dates) else None
    
    signals['buy_date'] = signals['ann_date'].apply(get_next_date)
    signals = signals.dropna(subset=['buy_date'])
    
    # Simulation
    cash = INITIAL_CAPITAL
    holdings = [] 
    history = []
    pos_size = INITIAL_CAPITAL / MAX_POS
    sig_map = signals.groupby('buy_date')
    
    for i, date in enumerate(dates):
        # 1. Sell
        next_h = []
        for p in holdings:
            if (i - p['buy_idx']) >= holding_days:
                sell_p = p_close.at[date, p['sym']]
                cash += p['shares'] * sell_p * (1 - FEE - TAX)
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
                    holdings.append({'sym': sym, 'shares': pos_size/buy_p, 'buy_idx': i})
                    cash -= pos_size * (1 + FEE)
        
        mv = sum(p['shares'] * p_close.at[date, p['sym']] for p in holdings)
        history.append(cash + mv)
        
    final_equity = history[-1] if history else INITIAL_CAPITAL
    return (final_equity / INITIAL_CAPITAL) - 1

def run_suite():
    df_price, df_ann = load_data_v7()
    results = {}
    print("Robustness Test: Holding Period Impact")
    for d in [40, 60, 80, 100]:
        r = run_test(df_price, df_ann, holding_days=d)
        results[f'{d}d'] = r
        print(f"  {d}d: {r:.2%}")
    
    # Plot
    plt.figure(figsize=(10, 6))
    pd.Series(results).plot(kind='line', marker='o', color='navy', linewidth=2)
    plt.title('Robustness: CAGR vs. Holding Period (Exp 7 Logic)')
    plt.ylabel('Total Return')
    plt.grid(True, alpha=0.3)
    plt.savefig('analysis_results/plots/robustness_holding_final.png')
    print("Saved to analysis_results/plots/robustness_holding_final.png")

if __name__ == "__main__":
    run_suite()
