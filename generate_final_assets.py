import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_data():
    print("Loading Data...")
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

def run_backtest_logic(df_price, df_ann, holding_days=20, use_ma20_exit=True):
    # Standard Setup
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    POSITION_SIZE = INITIAL_CAPITAL / MAX_POS
    FEE = 0.001425 * 0.25
    TAX = 0.003
    GROWTH_THRESH = 20 if use_ma20_exit else 0 # Exp 10 use 20%, Exp 7 use 0%

    # Pivot Tables
    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_to = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    p_ma = p_close.rolling(20).mean()
    dates = p_close.index.sort_values()
    dates_np = dates.values
    
    # Signal Selection
    mask = (df_ann['growth'] > GROWTH_THRESH) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    signals = df_ann[mask].copy()
    
    # T+1 Mapping
    def get_buy_date(ann_date):
        idx = np.searchsorted(dates_np, np.datetime64(ann_date), side='right')
        return dates[idx] if idx < len(dates) else None
    
    signals['buy_date'] = signals['ann_date'].apply(get_buy_date)
    signals = signals.dropna(subset=['buy_date'])
    
    def get_info_date(buy_date):
        idx = np.searchsorted(dates_np, np.datetime64(buy_date))
        return dates[idx-1] if idx > 0 else None
    
    signals['info_date'] = signals['buy_date'].apply(get_info_date)
    sig_map = signals.groupby('buy_date')

    # Simulation
    cash = INITIAL_CAPITAL
    holdings = [] 
    history = []
    
    for i, date in enumerate(dates):
        # 1. Sell
        next_h = []
        for p in holdings:
            sym = p['sym']
            curr_p = p_close.at[date, sym]
            ma20 = p_ma.at[date, sym]
            
            exit_signal = False
            if (i - p['buy_idx']) >= holding_days:
                exit_signal = True
            elif use_ma20_exit and not pd.isna(ma20) and curr_p < ma20:
                exit_signal = True
                
            if exit_signal:
                cash += p['shares'] * curr_p * (1 - FEE - TAX)
            else:
                next_h.append(p)
        holdings = next_h
        
        # 2. Buy
        if date in sig_map.groups:
            day_sigs = sig_map.get_group(date)
            info_date = day_sigs['info_date'].iloc[0]
            candidates = []
            for _, row in day_sigs.iterrows():
                sym = row['symbol']
                if sym in p_close.columns and not pd.isna(info_date):
                    try:
                        # Correct T-day Filter
                        if p_close.at[info_date, sym] > p_ma.at[info_date, sym]:
                            candidates.append({'sym': sym, 'to': p_to.at[info_date, sym]})
                    except: continue
            
            candidates = sorted(candidates, key=lambda x: x['to'] if not pd.isna(x['to']) else 0, reverse=True)
            slots = MAX_POS - len(holdings)
            for c in candidates[:slots]:
                sym = c['sym']
                buy_p = p_open.at[date, sym]
                if not pd.isna(buy_p) and buy_p > 0 and cash >= POSITION_SIZE * (1 + FEE):
                    holdings.append({'sym': sym, 'shares': POSITION_SIZE/buy_p, 'buy_idx': i, 'buy_p': buy_p})
                    cash -= POSITION_SIZE * (1 + FEE)
        
        mv = sum(p['shares'] * p_close.at[date, p['sym']] for p in holdings)
        history.append(cash + mv)
        
    return pd.Series(history, index=dates)

def generate_assets():
    df_p, df_a = load_data()
    
    # 1. Run Exp 7 (Baseline: 60d, No Auto Exit)
    print("Running Corrected Exp 7...")
    equity_exp7 = run_backtest_logic(df_p, df_a, holding_days=60, use_ma20_exit=False)
    
    # 2. Run Exp 10 (Optimized: 20d + MA20 Exit)
    print("Running Corrected Exp 10...")
    equity_exp10 = run_backtest_logic(df_p, df_a, holding_days=20, use_ma20_exit=True)
    
    # Save Figures
    os.makedirs('analysis_results/plots', exist_ok=True)
    
    # Exp 7 Dashboard Image
    plt.figure(figsize=(12, 6))
    plt.plot(equity_exp7, color='steelblue', label='Exp 7 (Baseline)')
    plt.title('Corrected Experiment 7: 60-Day Holding (No Future Function)')
    plt.grid(True, alpha=0.3); plt.legend()
    plt.savefig('analysis_results/plots/exp7_dashboard_final.png')
    print("Generated: exp7_dashboard_final.png")
    
    # Exp 10 Equity Image
    plt.figure(figsize=(12, 6))
    plt.plot(equity_exp10, color='darkgreen', label='Exp 10 (Optimized)')
    plt.title('Corrected Experiment 10: 20-Day + MA20 Exit (No Future Function)')
    plt.grid(True, alpha=0.3); plt.legend()
    plt.savefig('analysis_results/plots/exp10_final_equity.png')
    print("Generated: exp10_final_equity.png")
    
    # Print Stats for verification
    for name, eq in [("Exp 7", equity_exp7), ("Exp 10", equity_exp10)]:
        cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / ((eq.index[-1] - eq.index[0]).days / 365.25)) - 1
        mdd = ((eq - eq.cummax()) / eq.cummax()).min()
        print(f"{name}: CAGR={cagr:.2%}, MDD={mdd:.2%}")

if __name__ == "__main__":
    generate_assets()
