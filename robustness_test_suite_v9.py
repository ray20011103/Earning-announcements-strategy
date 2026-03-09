import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

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

def run_backtest(df_price, df_ann, holding_days=20, exit_mode='ma20_stop', growth_thresh=20):
    # Fixed Parameters (Single Interest Logic)
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    POSITION_SIZE = INITIAL_CAPITAL / MAX_POS # 500,000
    FEE = 0.001425 * 0.25
    TAX = 0.003
    FIXED_STOP_LOSS = -0.10

    # Pivot Tables
    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_to = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    p_ma = p_close.rolling(20).mean()
    
    dates = p_close.index.sort_values()
    dates_np = dates.values
    
    # Signal Selection
    mask = (df_ann['growth'] > growth_thresh) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    signals = df_ann[mask].copy()
    
    # Pre-map Signal Date to Buy Date (Next Trading Day)
    def get_buy_date(ann_date):
        idx = np.searchsorted(dates_np, np.datetime64(ann_date), side='right')
        return dates[idx] if idx < len(dates) else None
    
    signals['buy_date'] = signals['ann_date'].apply(get_buy_date)
    signals = signals.dropna(subset=['buy_date'])
    
    # Correct Logic: We know T-day info, we buy at T+1 Open
    # But we must check T-day MA filter before buying at T+1
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
        # 1. Sell Logic
        next_h = []
        for p in holdings:
            sym = p['sym']
            curr_p = p_close.at[date, sym]
            ma20 = p_ma.at[date, sym]
            ret = (curr_p / p['buy_p']) - 1
            
            exit_signal = False
            if (i - p['buy_idx']) >= holding_days:
                exit_signal = True
            elif 'ma20' in exit_mode and not pd.isna(ma20) and curr_p < ma20:
                exit_signal = True
            elif 'stop' in exit_mode and ret <= FIXED_STOP_LOSS:
                exit_signal = True
                
            if exit_signal:
                cash += p['shares'] * curr_p * (1 - FEE - TAX)
            else:
                next_h.append(p)
        holdings = next_h
        
        # 2. Buy Logic
        if date in sig_map.groups:
            day_sigs = sig_map.get_group(date)
            info_date = day_sigs['info_date'].iloc[0]
            candidates = []
            for _, row in day_sigs.iterrows():
                sym = row['symbol']
                if sym in p_close.columns and not pd.isna(info_date):
                    try:
                        # CRITICAL FIX: Use Info Date (T) to decide Buy Date (T+1)
                        if p_close.at[info_date, sym] > p_ma.at[info_date, sym]:
                            candidates.append({'sym': sym, 'to': p_to.at[info_date, sym]})
                    except: continue
            
            candidates = sorted(candidates, key=lambda x: x['to'] if not pd.isna(x['to']) else 0, reverse=True)
            slots = MAX_POS - len(holdings)
            for c in candidates[:slots]:
                sym = c['sym']
                buy_p = p_open.at[date, sym]
                cost = POSITION_SIZE * (1 + FEE)
                if not pd.isna(buy_p) and buy_p > 0 and cash >= cost:
                    holdings.append({'sym': sym, 'shares': POSITION_SIZE/buy_p, 'buy_idx': i, 'buy_p': buy_p})
                    cash -= cost
        
        mv = sum(p['shares'] * p_close.at[date, p['sym']] for p in holdings)
        history.append(cash + mv)
        
    df_h = pd.DataFrame({'TotalEquity': history}, index=dates)
    
    # Calculate Metrics
    start_v, end_v = df_h['TotalEquity'].iloc[0], df_h['TotalEquity'].iloc[-1]
    years = (df_h.index[-1] - df_h.index[0]).days / 365.25
    cagr = (end_v / start_v) ** (1/years) - 1
    mdd = ((df_h['TotalEquity'] - df_h['TotalEquity'].cummax()) / df_h['TotalEquity'].cummax()).min()
    return cagr, mdd

def run_suite():
    df_price, df_ann = load_data()
    
    holding_periods = [10, 20, 40, 60]
    exit_strategies = {
        'Time Only': 'time',
        'Time + MA20': 'ma20',
        'Time + MA20 + Stop': 'ma20_stop'
    }
    
    results = []
    
    print("\nStarting Robustness Test Suite...")
    for hp in holding_periods:
        for name, mode in exit_strategies.items():
            print(f"Testing: Holding={hp}d, Mode={name}...")
            cagr, mdd = run_backtest(df_price, df_ann, holding_days=hp, exit_mode=mode)
            results.append({
                'Holding Days': hp,
                'Exit Strategy': name,
                'CAGR': f"{cagr:.2%}",
                'MDD': f"{mdd:.2%}",
                'Sharpe-ish': round(cagr / abs(mdd), 2) if mdd != 0 else 0
            })
            
    df_results = pd.DataFrame(results)
    print("\n" + "="*50)
    print("          ROBUSTNESS TEST RESULTS")
    print("="*50)
    print(df_results.to_string(index=False))
    print("="*50)
    
    df_results.to_csv('analysis_results/data/robustness_comparison_v9.csv')

if __name__ == "__main__":
    run_suite()
