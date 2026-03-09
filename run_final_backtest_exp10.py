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

def run_final_exp10():
    # Exp 10 Parameters (Following Exp 7 Logic: Fixed Amount)
    HOLDING_DAYS = 20
    GROWTH_THRESH = 20
    FIXED_STOP_LOSS = -0.10
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    POSITION_SIZE = INITIAL_CAPITAL / MAX_POS # 固定金額 500,000
    FEE = 0.001425 * 0.25
    TAX = 0.003

    df_price, df_ann = load_data()
    
    print("Preparing Pivot Tables...")
    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_to = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    p_ma = p_close.rolling(20).mean()
    
    # Ensure index is datetime and sorted
    p_close.index = pd.to_datetime(p_close.index)
    dates = p_close.index.sort_values()
    dates_np = dates.values
    
    # Signal Generation
    mask = (df_ann['growth'] > GROWTH_THRESH) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    signals = df_ann[mask].copy()
    
    # Fast Buy Date Lookup
    print("Generating Signal Map...")
    def get_buy_date(ann_date):
        ts = np.datetime64(ann_date)
        idx = np.searchsorted(dates_np, ts, side='right')
        return dates[idx] if idx < len(dates) else None
    
    signals['buy_date'] = signals['ann_date'].apply(get_buy_date)
    signals = signals.dropna(subset=['buy_date'])
    sig_map = signals.groupby('buy_date')
    
    # Simulation
    cash = INITIAL_CAPITAL
    holdings = [] 
    history = []
    trades_log = []
    
    print("Simulating Experiment 10 (Single Interest - Fixed Amount 500k)...")
    for i, date in enumerate(dates):
        # 1. Sell / Stop-Loss / 20MA Exit
        next_h = []
        for p in holdings:
            sym = p['sym']
            curr_p = p_close.at[date, sym]
            ma20 = p_ma.at[date, sym]
            ret = (curr_p / p['buy_p']) - 1
            
            exit_signal = False
            exit_reason = ""
            
            if (i - p['buy_idx']) >= HOLDING_DAYS:
                exit_signal = True
                exit_reason = "Expired (20d)"
            elif ret <= FIXED_STOP_LOSS:
                exit_signal = True
                exit_reason = "Fixed Stop Loss (-10%)"
            elif not pd.isna(ma20) and curr_p < ma20:
                exit_signal = True
                exit_reason = "MA20 Trend Exit"
                
            if exit_signal:
                proceeds = p['shares'] * curr_p * (1 - FEE - TAX)
                cash += proceeds
                trades_log.append({
                    'symbol': sym, 'buy_date': p['buy_date'], 'sell_date': date,
                    'buy_price': p['buy_p'], 'sell_price': curr_p, 'reason': exit_reason,
                    'return': (curr_p - p['buy_p']) / p['buy_p'] - (FEE*2 + TAX)
                })
            else:
                next_h.append(p)
        holdings = next_h
        
        # 2. Buy (Fixed Amount: 500,000 per position)
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
                # Fixed Amount Buy
                cost = POSITION_SIZE * (1 + FEE)
                if not pd.isna(buy_p) and buy_p > 0 and cash >= cost:
                    holdings.append({'sym': sym, 'shares': POSITION_SIZE/buy_p, 'buy_idx': i, 'buy_p': buy_p, 'buy_date': date})
                    cash -= cost
        
        mv = sum(p['shares'] * p_close.at[date, p['sym']] for p in holdings)
        history.append({'Date': date, 'TotalEquity': cash + mv, 'Positions': len(holdings)})
        
    df_history = pd.DataFrame(history).set_index('Date')
    df_trades = pd.DataFrame(trades_log)
    
    # Calculate Final Metrics
    start_v, end_v = df_history['TotalEquity'].iloc[0], df_history['TotalEquity'].iloc[-1]
    years = (df_history.index[-1] - df_history.index[0]).days / 365.25
    cagr = (end_v / start_v) ** (1/years) - 1
    mdd = ((df_history['TotalEquity'] - df_history['TotalEquity'].cummax()) / df_history['TotalEquity'].cummax()).min()
    daily_ret = df_history['TotalEquity'].pct_change().dropna()
    sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252))
    
    print(f"\nExperiment 10 (20MA Stop-Loss) Result:")
    print(f"CAGR: {cagr:.2%}")
    print(f"Sharpe: {sharpe:.2f}")
    print(f"MDD: {mdd:.2%}")
    print(f"Total Return: {(end_v/start_v - 1):.2%}")
    
    # Save results
    df_history.to_csv('analysis_results/data/exp10_history.csv')
    df_trades.to_csv('analysis_results/data/exp10_trades.csv')
    
    # Visualization
    plt.figure(figsize=(12, 6))
    plt.plot(df_history['TotalEquity'], color='blue', linewidth=2, label='Exp 10 (Optimized + 20MA Exit)')
    plt.title('Experiment 10: 20-Day Holding & 20MA Stop-Loss', fontsize=14)
    plt.ylabel('Portfolio Value (TWD)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('analysis_results/plots/exp10_final_equity.png')
    print(f"Report figures updated in analysis_results/plots/")

if __name__ == "__main__":
    run_final_exp10()
