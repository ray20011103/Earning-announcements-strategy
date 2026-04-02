import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_data_final():
    price_path = 'price.csv'
    ann_path = 'legacy_archive/announcement.csv'
    
    print("Loading Price Data...")
    df_price = pd.read_csv(price_path, low_memory=False, dtype={'證券代碼': str})
    df_price = df_price.rename(columns={'證券代碼': 'symbol', '年月日': 'Date', '開盤價(元)': 'Open', '收盤價(元)': 'Close', '週轉率％': 'Turnover'})
    
    df_price['Date'] = pd.to_datetime(df_price['Date'], format='%Y%m%d', errors='coerce')
    df_price['symbol'] = df_price['symbol'].astype(str).str.split().str[0]
    df_price = df_price.drop_duplicates(subset=['Date', 'symbol']).dropna(subset=['Date', 'Close'])
    df_price = df_price.sort_values(['Date', 'symbol'])
    
    print("Loading Announcement Data...")
    df_ann = pd.read_csv(ann_path, dtype={'代碼': str})
    df_ann = df_ann.rename(columns={'代碼': 'symbol', '營收發布日': 'ann_date', '單月營收成長率％': 'growth', '創新高/低(近一年)': 'high_year', '創新高/低(歷史)': 'high_hist'})
    
    df_ann['ann_date'] = pd.to_datetime(df_ann['ann_date'], errors='coerce')
    df_ann['growth'] = pd.to_numeric(df_ann['growth'], errors='coerce')
    df_ann['symbol'] = df_ann['symbol'].astype(str).str.split().str[0]
    df_ann = df_ann.dropna(subset=['ann_date', 'symbol'])
    
    return df_price, df_ann

def run_parameter_test(df_price, df_ann, holding_days=60, entry_type='Open', max_pos=20):
    INITIAL_CAPITAL = 10_000_000
    FEE_RATE = 0.001425 * 0.25
    TAX_RATE = 0.003
    
    price_open = df_price.pivot(index='Date', columns='symbol', values='Open').ffill()
    price_close = df_price.pivot(index='Date', columns='symbol', values='Close').ffill()
    price_turnover = df_price.pivot(index='Date', columns='symbol', values='Turnover').ffill()
    price_ma20 = price_close.rolling(window=20).mean()
    
    trading_dates = price_close.index.sort_values()
    
    mask = (df_ann['growth'] > 0) & (df_ann['high_year'].astype(str).str.contains('H', na=False) | df_ann['high_hist'].astype(str).str.contains('H', na=False))
    valid_signals = df_ann[mask].copy()
    
    def get_buy_date(ann_date):
        future_dates = trading_dates[trading_dates > ann_date]
        return future_dates[0] if len(future_dates) > 0 else None

    valid_signals['buy_date'] = valid_signals['ann_date'].apply(get_buy_date)
    valid_signals = valid_signals.dropna(subset=['buy_date'])
    
    signals_by_date = {}
    for _, row in valid_signals.iterrows():
        d = row['buy_date']
        sym = row['symbol']
        if sym not in price_close.columns: continue
        
        if d not in signals_by_date: signals_by_date[d] = []
        try:
            ma20 = price_ma20.at[d, sym]
            close = price_close.at[d, sym]
            if not pd.isna(ma20) and close > ma20:
                to_val = price_turnover.at[d, sym]
                signals_by_date[d].append({'symbol': sym, 'turnover': to_val})
        except: continue

    cash = INITIAL_CAPITAL
    holdings = []
    history = []
    curr_pos_size = INITIAL_CAPITAL / max_pos
    
    for i, date in enumerate(trading_dates):
        # Sell
        next_holdings = []
        for pos in holdings:
            if (i - pos['buy_idx']) >= holding_days:
                sell_price = price_close.at[date, pos['symbol']]
                if pd.isna(sell_price) or sell_price <= 0: sell_price = pos['buy_price']
                cash += pos['shares'] * sell_price * (1 - FEE_RATE - TAX_RATE)
            else:
                next_holdings.append(pos)
        holdings = next_holdings
        
        # Buy
        if date in signals_by_date:
            candidates = sorted(signals_by_date[date], key=lambda x: x['turnover'] if not pd.isna(x['turnover']) else 0, reverse=True)
            slots = max_pos - len(holdings)
            for item in candidates[:slots]:
                sym = item['symbol']
                buy_price = price_open.at[date, sym] if entry_type == 'Open' else price_close.at[date, sym]
                if pd.isna(buy_price) or buy_price <= 0: continue
                if cash >= curr_pos_size * (1 + FEE_RATE):
                    shares = curr_pos_size / buy_price
                    holdings.append({'symbol': sym, 'shares': shares, 'buy_idx': i, 'buy_price': buy_price})
                    cash -= curr_pos_size * (1 + FEE_RATE)
        
        mv = sum(p['shares'] * price_close.at[date, p['symbol']] for p in holdings if not pd.isna(price_close.at[date, p['symbol']]))
        history.append(cash + mv)
    
    equity = pd.Series(history, index=trading_dates)
    total_ret = (equity.iloc[-1] / INITIAL_CAPITAL) - 1 if len(equity) > 0 else 0
    return total_ret

def run_robustness_suite():
    df_price, df_ann = load_data_final()
    
    results = {}
    print("Testing Sensitivity...")
    # 測試參數：持有天數
    for days in [20, 60, 100]:
        ret = run_parameter_test(df_price, df_ann, holding_days=days)
        results[f'Hold {days}d'] = ret
        print(f"  Hold {days}d: {ret:.2%}")
        
    # 測試參數：進場時機
    for et in ['Open', 'Close']:
        ret = run_parameter_test(df_price, df_ann, entry_type=et)
        results[f'Entry {et}'] = ret
        print(f"  Entry {et}: {ret:.2%}")

    # Plot
    if results:
        plt.figure(figsize=(10, 6))
        pd.Series(results).plot(kind='bar', color='teal', title='Robustness: Total Return Comparison')
        plt.ylabel('Total Return (%)')
        plt.grid(True, alpha=0.3)
        plt.savefig('analysis_results/plots/robustness_final_v6.png')
        print("Final Robustness Report saved: analysis_results/plots/robustness_final_v6.png")

if __name__ == "__main__":
    run_robustness_suite()
