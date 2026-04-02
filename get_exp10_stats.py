import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def calculate_exp10_metrics():
    # Load the equity curve we just generated for Exp 10
    # Note: I need to ensure I have the daily returns to calc Sharpe
    # I will re-run the core logic briefly to get the Series
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

    # Exp 10 Params
    HOLDING_DAYS = 20
    GROWTH_THRESH = 20
    STOP_LOSS = -0.10
    INITIAL_CAPITAL = 10_000_000
    MAX_POS = 20
    FEE = 0.001425 * 0.25
    TAX = 0.003

    p_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    p_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    p_to = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
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
    holdings = [] 
    history = []
    pos_size = INITIAL_CAPITAL / MAX_POS
    
    for i, date in enumerate(dates):
        next_h = []
        for p in holdings:
            curr_p = p_close.at[date, p['sym']]
            ret = (curr_p / p['buy_p']) - 1
            if (i - p['buy_idx']) >= HOLDING_DAYS or ret <= STOP_LOSS:
                cash += p['shares'] * curr_p * (1 - FEE - TAX)
            else:
                next_h.append(p)
        holdings = next_h
        
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
    
    # Calculate Stats
    total_ret = (equity.iloc[-1] / INITIAL_CAPITAL) - 1
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / INITIAL_CAPITAL) ** (1/years) - 1
    
    daily_rets = equity.pct_change().dropna()
    sharpe = (daily_rets.mean() * 252) / (daily_rets.std() * np.sqrt(252))
    
    rolling_max = equity.cummax()
    mdd = ((equity - rolling_max) / rolling_max).min()
    
    print(f"EXP10_STATS: CAGR={cagr:.2%}, Sharpe={sharpe:.2f}, MDD={mdd:.2%}, Total={total_ret:.2%}")
    
    # Re-generate the comparison plot with FIXED legends
    scenarios = ['Base (20d, >0%)', 'Growth+ (20d, >20%)', 'Safe (Exp 10)']
    returns = [4.2595, 5.3819, total_ret] # Total returns
    mdds = [-0.2178, -0.1933, mdd]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    x = np.arange(len(scenarios))
    width = 0.35
    
    bar1 = ax1.bar(x - width/2, [r * 100 for r in returns], width, label='Total Return (%)', color='#2c3e50')
    ax1.set_ylabel('Total Return (%)', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, fontsize=11)
    
    ax2 = ax1.twinx()
    bar2 = ax2.bar(x + width/2, [m * 100 for m in mdds], width, label='Max Drawdown (%)', color='#e74c3c', alpha=0.7)
    ax2.set_ylabel('Max Drawdown (%)', fontsize=12, fontweight='bold')
    
    # Combine legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left', frameon=True, shadow=True)
    
    plt.title('Strategy Evolution: Return vs. Risk Profile', fontsize=14, pad=20)
    plt.grid(axis='y', alpha=0.3)
    plt.savefig('analysis_results/plots/optimization_comparison_fixed.png', bbox_inches='tight')
    print("Re-generated comparison plot with fixed legends.")

if __name__ == "__main__":
    calculate_exp10_metrics()
