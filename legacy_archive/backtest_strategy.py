
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

# 設定繪圖風格
plt.style.use('ggplot')
# 解決 matplotlib 中文顯示問題 (Mac)
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False

warnings.filterwarnings('ignore')

def load_and_process_data(file_path):
    print("1. 正在讀取與清洗數據...")
    try:
        df = pd.read_csv(file_path, header=[0, 1], encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, header=[0, 1], encoding='cp950')
    
    # 提取所有股票代號
    stock_ids = [c for c in df.columns.get_level_values(0).unique() if 'Unnamed' not in str(c)]
    
    # 提取日期 (第一欄)
    master_date_col = df.iloc[:, 0]
    master_date_col.name = 'Date'
    
    all_data = []
    
    for stock in stock_ids:
        sub_df = df[stock].copy()
        sub_df['Date'] = master_date_col
        
        # 欄位對應
        required_cols = ['單月營收(千元)', '市值(百萬元)', '週轉率％', '收盤價(元)']
        col_map = {}
        for rc in required_cols:
            matches = [c for c in sub_df.columns if rc in c]
            if matches: col_map[matches[0]] = rc
        
        if len(col_map) < len(required_cols): continue
            
        sub_df = sub_df.rename(columns={
            col_map.get('單月營收(千元)'): 'Revenue',
            col_map.get('市值(百萬元)'): 'MarketCap',
            col_map.get('週轉率％'): 'TurnoverRate',
            col_map.get('收盤價(元)'): 'Close'
        })
        
        sub_df = sub_df[['Date', 'Revenue', 'MarketCap', 'TurnoverRate', 'Close']]
        sub_df = sub_df.dropna(subset=['Date', 'Revenue', 'Close'])
        
        # 轉數值
        for col in ['Revenue', 'MarketCap', 'TurnoverRate', 'Close']:
            sub_df[col] = sub_df[col].astype(str).str.replace(',', '').replace('--', np.nan)
            sub_df[col] = pd.to_numeric(sub_df[col], errors='coerce')
            
        sub_df['Date'] = pd.to_datetime(sub_df['Date'], errors='coerce')
        sub_df = sub_df.sort_values('Date')
        
        # === 特徵工程 ===
        
        # 1. 計算歷史最高營收 (不含當月)
        sub_df['HistMaxRevenue'] = sub_df['Revenue'].expanding().max().shift(1)
        
        # 2. 計算 HI 指標
        sub_df['HI'] = sub_df['Revenue'] / sub_df['HistMaxRevenue']
        
        # 3. 6個月平均週轉率
        sub_df['TR6'] = sub_df['TurnoverRate'].rolling(window=6).mean()
        
        # 4. 計算"下個月"的報酬率
        sub_df['Next_Return'] = sub_df['Close'].shift(-1) / sub_df['Close'] - 1
        
        # 5. Shift 特徵至 T 月 (模擬 T 月底選股，只能看 T-1 月營收)
        sub_df['Signal_HI'] = sub_df['HI'].shift(1)
        sub_df['Signal_MarketCap'] = sub_df['MarketCap'].shift(1)
        sub_df['Signal_TR6'] = sub_df['TR6'].shift(1)
        
        sub_df['StockID'] = stock
        all_data.append(sub_df)
    
    full_df = pd.concat(all_data)
    return full_df.dropna(subset=['Signal_HI', 'Signal_MarketCap', 'Signal_TR6', 'Next_Return'])

def calculate_metrics(returns, risk_free_rate=0.01):
    """
    計算量化指標
    returns: pd.Series (月報酬率)
    risk_free_rate: 年化無風險利率 (預設 1%)
    """
    # 1. 年化報酬率 (CAGR)
    total_months = len(returns)
    total_return = (1 + returns).prod() - 1
    annualized_return = (1 + total_return) ** (12 / total_months) - 1
    
    # 2. 年化波動率
    annualized_vol = returns.std() * np.sqrt(12)
    
    # 3. 夏普比率 (Sharpe Ratio)
    # 將年化無風險利率轉換為月無風險利率
    rf_monthly = (1 + risk_free_rate) ** (1/12) - 1
    excess_returns = returns - rf_monthly
    sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(12)
    
    # 4. 最大回撤 (MDD)
    cum_wealth = (1 + returns).cumprod()
    running_max = cum_wealth.cummax()
    drawdown = (cum_wealth - running_max) / running_max
    mdd = drawdown.min()
    
    # 5. 勝率 (Win Rate)
    win_rate = (returns > 0).mean()
    
    return {
        'Annualized_Return': annualized_return,
        'Annualized_Volatility': annualized_vol,
        'Sharpe_Ratio': sharpe_ratio,
        'Max_Drawdown': mdd,
        'Win_Rate': win_rate
    }

def run_backtest(df):
    print("2. 開始執行回測...")
    
    dates = df['Date'].sort_values().unique()
    
    strategy_returns = []
    benchmark_returns = []
    trade_dates = []
    
    for d in dates:
        current_data = df[df['Date'] == d].copy()
        
        if len(current_data) < 50: continue
            
        # 流動性濾網
        mv_threshold = current_data['Signal_MarketCap'].quantile(2/3)
        tr_threshold = current_data['Signal_TR6'].quantile(2/3)
        
        universe = current_data[
            (current_data['Signal_MarketCap'] >= mv_threshold) & 
            (current_data['Signal_TR6'] >= tr_threshold)
        ]
        
        if universe.empty: continue
            
        # Benchmark
        bench_ret = universe['Next_Return'].mean()
        
        # 營收動能排序 (Top 10%)
        top_n = int(len(universe) * 0.1)
        if top_n < 1: top_n = 1
        
        winners = universe.sort_values('Signal_HI', ascending=False).head(top_n)
        
        # 策略報酬 (等權重)
        strat_ret = winners['Next_Return'].mean()
        
        strategy_returns.append(strat_ret)
        benchmark_returns.append(bench_ret)
        trade_dates.append(d)

    # === 整合結果 ===
    results = pd.DataFrame({
        'Date': trade_dates,
        'Strategy': strategy_returns,
        'Benchmark': benchmark_returns
    })
    results = results.set_index('Date')
    
    # 累積報酬
    results['Cum_Strategy'] = (1 + results['Strategy']).cumprod()
    results['Cum_Benchmark'] = (1 + results['Benchmark']).cumprod()
    
    # 計算指標
    strat_metrics = calculate_metrics(results['Strategy'])
    bench_metrics = calculate_metrics(results['Benchmark'])
    
    print("\n" + "="*50)
    print("3. 回測績效詳細報告 (2013-2025)")
    print("="*50)
    print(f"{'指標':<15} | {'策略 (Strategy)':<15} | {'大盤 (Benchmark)':<15}")
    print("-" * 50)
    print(f"{'總報酬率':<15} | {results['Cum_Strategy'].iloc[-1]-1:>14.2%} | {results['Cum_Benchmark'].iloc[-1]-1:>14.2%}")
    print(f"{'年化報酬率':<15} | {strat_metrics['Annualized_Return']:>14.2%} | {bench_metrics['Annualized_Return']:>14.2%}")
    print(f"{'年化波動率':<15} | {strat_metrics['Annualized_Volatility']:>14.2%} | {bench_metrics['Annualized_Volatility']:>14.2%}")
    print(f"{'夏普比率':<15} | {strat_metrics['Sharpe_Ratio']:>14.2f} | {bench_metrics['Sharpe_Ratio']:>14.2f}")
    print(f"{'最大回撤 (MDD)':<15} | {strat_metrics['Max_Drawdown']:>14.2%} | {bench_metrics['Max_Drawdown']:>14.2%}")
    print(f"{'月勝率':<15} | {strat_metrics['Win_Rate']:>14.2%} | {bench_metrics['Win_Rate']:>14.2%}")
    print("="*50)
    
    # === 繪圖 ===
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
    
    # 上圖：累積報酬
    ax1.plot(results.index, results['Cum_Strategy'], label='營收創新高策略 (Top 10%)', color='#d62728', linewidth=2)
    ax1.plot(results.index, results['Cum_Benchmark'], label='市場平均 (Benchmark)', color='grey', linestyle='--', alpha=0.7)
    ax1.set_title('營收創新高動能策略 - 累積績效走勢', fontsize=14)
    ax1.set_ylabel('累積淨值 (起始=1)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 下圖：回撤
    cum_wealth = results['Cum_Strategy']
    running_max = cum_wealth.cummax()
    drawdown = (cum_wealth - running_max) / running_max
    
    ax2.fill_between(drawdown.index, drawdown, 0, color='#d62728', alpha=0.3, label='策略回撤 (Drawdown)')
    ax2.plot(drawdown.index, drawdown, color='#d62728', linewidth=1)
    ax2.set_title('最大回撤 (Drawdown)', fontsize=12)
    ax2.set_ylabel('回撤幅度 %')
    ax2.set_xlabel('年份')
    ax2.legend(loc='lower left')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_img = 'strategy_metrics.png'
    plt.savefig(output_img)
    print(f"\n進階績效圖表已儲存至: {output_img}")
    
    return results

if __name__ == "__main__":
    file_path = 'monthly_data.csv'
    df = load_and_process_data(file_path)
    run_backtest(df)
