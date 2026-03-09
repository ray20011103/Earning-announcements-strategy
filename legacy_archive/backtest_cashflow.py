import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Settings
INITIAL_CAPITAL = 10_000_000
MAX_POSITIONS = 20
POSITION_SIZE = INITIAL_CAPITAL / MAX_POSITIONS # 500,000
HOLDING_DAYS = 60
FEE_RATE = 0.001425 * 0.25
TAX_RATE = 0.003

# Strategy Parameters
TURNOVER_STRATEGY = 'high'  # 'low' or 'high' (Priority when signals > slots)
COMPOUNDING = False        # True for 複利模式, False for 固定金額模式

def load_data():
    print("Loading Price Data...")
    # Load price.csv (Unified Database)
    try:
        df_price = pd.read_csv('price.csv', encoding='utf-8', dtype={'證券代碼': str})
    except UnicodeDecodeError:
        df_price = pd.read_csv('price.csv', encoding='cp950', dtype={'證券代碼': str})
    
    # Rename
    df_price = df_price.rename(columns={
        '證券代碼': 'symbol', '年月日': 'Date', 
        '開盤價(元)': 'Open', '收盤價(元)': 'Close', 
        '週轉率％': 'Turnover'
    })
    
    # Parse Date
    df_price['Date'] = pd.to_datetime(df_price['Date'], format='%Y%m%d', errors='coerce')
    
    # Drop NaT Dates
    df_price = df_price.dropna(subset=['Date'])
    
    # Parse Symbol
    df_price['symbol'] = df_price['symbol'].astype(str).str.split().str[0]
    
    # Sort
    df_price = df_price.sort_values(['Date', 'symbol']).reset_index(drop=True)
    
    # Drop duplicates for (Date, symbol)
    print("Cleaning Price Data (Dropping Duplicates)...")
    df_price = df_price.drop_duplicates(subset=['Date', 'symbol'], keep='last')
    
    print("Loading Announcement Data...")
    try:
        df_ann = pd.read_csv('announcement.csv', dtype={'代碼': str})
    except:
        df_ann = pd.read_csv('announcement.csv', dtype={0: str})
        
    df_ann = df_ann.rename(columns={
        '代碼': 'symbol', '公司': 'symbol',
        '營收發布日': 'ann_date',
        '單月營收成長率％': 'growth',
        '創新高/低(近一年)': 'high_year',
        '創新高/低(歷史)': 'high_hist'
    })
    
    df_ann['symbol'] = df_ann['symbol'].astype(str).str.split().str[0]
    df_ann['ann_date'] = pd.to_datetime(df_ann['ann_date'], errors='coerce')
    df_ann['growth'] = pd.to_numeric(df_ann['growth'], errors='coerce')
    
    return df_price, df_ann

def run_backtest_engine():
    df_price, df_ann = load_data()
    
    # 1. Prepare Price Data for Fast Lookup
    print("Indexing Price Data...")
    # Pivot for fast lookup by Date
    price_open = df_price.pivot(index='Date', columns='symbol', values='Open')
    price_close = df_price.pivot(index='Date', columns='symbol', values='Close')
    price_turnover = df_price.pivot(index='Date', columns='symbol', values='Turnover')
    
    # Clean Data: Replace 0 with NaN (Price can't be 0)
    price_open = price_open.replace(0, np.nan)
    price_close = price_close.replace(0, np.nan)
    
    # Forward Fill missing prices
    print("Handling missing data (Forward Fill)...")
    price_open = price_open.ffill()
    price_close = price_close.ffill()
    price_turnover = price_turnover.ffill()
    
    # Calculate 20MA for Trend Filter
    print("Calculating Technical Indicators (20MA)...")
    price_ma20 = price_close.rolling(window=20).mean()
    
    trading_dates = price_close.index.sort_values()
    trading_dates_np = trading_dates.values
    
    # 2. Filter Signals
    print("Filtering Signals...")
    mask_high = df_ann['high_year'].astype(str).str.contains('H', na=False) | \
                df_ann['high_hist'].astype(str).str.contains('H', na=False)
    mask_growth = df_ann['growth'] > 0
    
    valid_signals = df_ann[mask_growth & mask_high].copy()
    valid_signals = valid_signals.dropna(subset=['ann_date'])
    
    ann_dates = valid_signals['ann_date'].values
    buy_indices = np.searchsorted(trading_dates_np, ann_dates, side='right')
    curr_indices = np.searchsorted(trading_dates_np, ann_dates, side='left')
    turnover_indices = curr_indices - 1
    
    valid_mask = (buy_indices < len(trading_dates_np)) & (turnover_indices >= 0) & (curr_indices < len(trading_dates_np))
    valid_signals = valid_signals[valid_mask].copy()
    
    valid_signals['buy_date'] = trading_dates_np[buy_indices[valid_mask]]
    valid_signals['ann_trading_date'] = trading_dates_np[curr_indices[valid_mask]] # T (Ann Date)
    valid_signals['turnover_date'] = trading_dates_np[turnover_indices[valid_mask]] # T-1
    
    print("Pre-fetching Turnover & MA20 Data...")
    def get_signal_metrics(row):
        try:
            to_val = price_turnover.at[row['turnover_date'], row['symbol']]
            
            # Trend Filter: Close(T) > 20MA(T)
            close_t = price_close.at[row['ann_trading_date'], row['symbol']]
            ma20_t = price_ma20.at[row['ann_trading_date'], row['symbol']]
            trend_up = close_t > ma20_t if not pd.isna(ma20_t) else False
            
            return pd.Series([to_val, trend_up])
        except KeyError:
            return pd.Series([np.nan, False])

    valid_signals[['turnover_val', 'trend_up']] = valid_signals.apply(get_signal_metrics, axis=1)
    valid_signals = valid_signals[valid_signals['trend_up'] == True].copy()
    valid_signals = valid_signals.dropna(subset=['turnover_val'])
    
    signals_by_buy_date = {}
    for _, row in valid_signals.iterrows():
        d = row['buy_date']
        if d not in signals_by_buy_date:
            signals_by_buy_date[d] = []
        signals_by_buy_date[d].append({'symbol': row['symbol'], 'turnover': row['turnover_val']})
    
    # 3. Simulation Loop
    print("Running Cash Flow Simulation...")
    cash = INITIAL_CAPITAL
    holdings = [] 
    history = [] 
    trades_log = []
    
    # Keep track of last known total equity for compounding
    last_total_equity = INITIAL_CAPITAL
    
    for i, date in enumerate(trading_dates):
        # Determine Position Size for today
        if COMPOUNDING:
            current_pos_size = last_total_equity / MAX_POSITIONS
        else:
            current_pos_size = INITIAL_CAPITAL / MAX_POSITIONS # e.g. 500,000
            
        # --- Step 1: Buy at Open ---
        if date in signals_by_buy_date:
            candidates = signals_by_buy_date[date]
            held_symbols = {h['symbol'] for h in holdings}
            candidates = [c for c in candidates if c['symbol'] not in held_symbols]
            
            if candidates:
                reverse = True if TURNOVER_STRATEGY == 'high' else False
                candidates.sort(key=lambda x: x['turnover'], reverse=reverse)
                slots = MAX_POSITIONS - len(holdings)
                if slots > 0:
                    buy_list = candidates[:slots]
                    for item in buy_list:
                        sym = item['symbol']
                        open_price = price_open.at[date, sym]
                        if pd.isna(open_price): continue
                        
                        cost = current_pos_size * (1 + FEE_RATE)
                        if cash >= cost:
                            shares = current_pos_size / open_price
                            holdings.append({'symbol': sym, 'shares': shares, 'buy_day_idx': i, 'buy_price': open_price})
                            cash -= cost
        
        # --- Step 2: Sell at Close ---
        next_holdings = []
        for pos in holdings:
            if pos['buy_day_idx'] == i:
                next_holdings.append(pos)
                continue
            curr_price = price_close.at[date, pos['symbol']]
            if pd.isna(curr_price):
                curr_price = price_open.at[date, pos['symbol']]
                if pd.isna(curr_price): curr_price = 0
            
            if (i - pos['buy_day_idx']) >= HOLDING_DAYS:
                proceeds = pos['shares'] * curr_price
                txn_cost = proceeds * (FEE_RATE + TAX_RATE)
                cash += (proceeds - txn_cost)
                trades_log.append({
                    'symbol': pos['symbol'], 'buy_date': trading_dates[pos['buy_day_idx']], 'sell_date': date,
                    'buy_price': pos['buy_price'], 'sell_price': curr_price,
                    'return': (curr_price - pos['buy_price']) / pos['buy_price'] - (FEE_RATE*2 + TAX_RATE)
                })
            else:
                next_holdings.append(pos)
        holdings = next_holdings
        
        # --- Step 3: Valuation ---
        todays_market_value = 0
        for pos in holdings:
            curr_price = price_close.at[date, pos['symbol']]
            if pd.isna(curr_price):
                curr_price = price_open.at[date, pos['symbol']]
                if pd.isna(curr_price): curr_price = 0
            todays_market_value += pos['shares'] * curr_price

        last_total_equity = cash + todays_market_value
        history.append({'Date': date, 'Cash': cash, 'TotalEquity': last_total_equity, 'Positions': len(holdings)})

    df_res = pd.DataFrame(history).set_index('Date')
    df_trades_res = pd.DataFrame(trades_log)
    
    # Benchmark
    try:
        df_market = pd.read_csv('market.csv')
        df_market['Date'] = pd.to_datetime(df_market['年月日'], format='%Y%m%d', errors='coerce')
        df_market = df_market.set_index('Date')['收盤價(元)'].sort_index()
        common_start = max(df_res.index[0], df_market.index[0])
        common_end = min(df_res.index[-1], df_market.index[-1])
        df_market = df_market.loc[common_start:common_end]
        market_norm = (df_market / df_market.iloc[0]) * INITIAL_CAPITAL
    except:
        market_norm = None

    calculate_metrics(df_res['TotalEquity'], df_trades_res, market_norm)
    
    # Plotting
    plt.figure(figsize=(12, 10))
    plt.subplot(3, 1, 1)
    plt.plot(df_res['TotalEquity'], label='Strategy')
    if market_norm is not None:
        plt.plot(market_norm, label='Benchmark', color='gray', linestyle='--')
    plt.title('Equity Curve')
    plt.legend(); plt.grid(True)
    
    rolling_max = df_res['TotalEquity'].cummax()
    drawdown = (df_res['TotalEquity'] - rolling_max) / rolling_max
    plt.subplot(3, 1, 2)
    plt.plot(drawdown, color='red'); plt.title('Drawdown'); plt.grid(True)
    
    plt.subplot(3, 1, 3)
    plt.bar(df_res.index, df_res['Positions'], color='orange'); plt.title('Positions'); plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('analysis_results/plots/cashflow_simulation.png')
    df_res.to_csv('analysis_results/data/cashflow_equity.csv')
    df_trades_res.to_csv('analysis_results/data/cashflow_trades.csv')
    
    return df_res, df_trades_res

def calculate_metrics(equity_curve, trade_log, benchmark_curve=None):
    print("\n" + "="*40 + "\n       PERFORMANCE REPORT\n" + "="*40)
    start_value, end_value = equity_curve.iloc[0], equity_curve.iloc[-1]
    years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
    total_return = (end_value / start_value) - 1
    cagr = (end_value / start_value) ** (1/years) - 1
    
    rolling_max = equity_curve.cummax()
    max_drawdown = ((equity_curve - rolling_max) / rolling_max).min()
    
    daily_ret = equity_curve.pct_change().dropna()
    sharpe = (daily_ret.mean() * 252) / (daily_ret.std() * np.sqrt(252))
    
    print(f"Total Return: {total_return:.2%}\nCAGR: {cagr:.2%}\nSharpe: {sharpe:.2f}\nMDD: {max_drawdown:.2%}")
    if benchmark_curve is not None:
        b_ret = (benchmark_curve.iloc[-1] / benchmark_curve.iloc[0]) - 1
        print(f"Benchmark Return: {b_ret:.2%}")

if __name__ == "__main__":
    run_backtest_engine()