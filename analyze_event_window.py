import pandas as pd
from FinMind.data import DataLoader
import matplotlib.pyplot as plt
import numpy as np

def analyze_event_effect():
    dl = DataLoader()
    # 讀取現有的交易紀錄
    df = pd.read_csv('analysis_results/data/event_strategy_trades_cleaned.csv')
    
    # 隨機挑選 50 筆近期交易來做 Event Study (避免 API 額度耗盡)
    sample_df = df.sample(50, random_state=42)
    
    event_results = []
    
    for idx, row in sample_df.iterrows():
        sym = str(row['symbol']).zfill(4)
        ann_date = pd.to_datetime(row['ann_date'])
        
        # 定義觀察視窗：公告前後各 10 天
        start_obs = (ann_date - pd.Timedelta(days=15)).strftime('%Y-%m-%d')
        end_obs = (ann_date + pd.Timedelta(days=15)).strftime('%Y-%m-%d')
        
        try:
            price_df = dl.taiwan_stock_daily(stock_id=sym, start_date=start_obs, end_date=end_obs)
            if price_df.empty: continue
            
            price_df['date'] = pd.to_datetime(price_df['date'])
            price_df = price_df.sort_values('date')
            
            # 找到公告日當天的索引
            # 如果公告日當天沒開盤，找最接近的下一天
            ann_idx_list = price_df[price_df['date'] >= ann_date].index
            if len(ann_idx_list) == 0: continue
            ann_idx = ann_idx_list[0]
            
            # 計算以公告日當天價格為基點 (1.0) 的累積報酬
            base_price = price_df.loc[ann_idx, 'close']
            
            # 獲取公告前後各 N 天的價格
            # 我們用相對位置來記錄
            prices = price_df['close'].values
            ann_pos = price_df.index.get_loc(ann_idx)
            
            # 提取 T-10 到 T+10
            window_size = 10
            start_pos = max(0, ann_pos - window_size)
            end_pos = min(len(prices), ann_pos + window_size + 1)
            
            rel_prices = prices[start_pos:end_pos] / base_price
            rel_time = np.arange(start_pos - ann_pos, end_pos - ann_pos)
            
            event_results.append(pd.Series(rel_prices, index=rel_time))
            
        except Exception as e:
            continue

    # 彙整結果並繪圖
    event_df = pd.concat(event_results, axis=1).mean(axis=1)
    
    plt.figure(figsize=(10, 6))
    event_df.plot(marker='o', linestyle='-', color='b')
    plt.axvline(x=0, color='r', linestyle='--', label='Announcement Day (T=0)')
    plt.title('Event Study: Stock Price Reaction Around Revenue Announcement')
    plt.xlabel('Days Relative to Announcement')
    plt.ylabel('Cumulative Relative Return (Base T=0)')
    plt.grid(True)
    plt.legend()
    plt.savefig('analysis_results/plots/event_study_reaction.png')
    print("Event Study 完成，圖表已存至: analysis_results/plots/event_study_reaction.png")

if __name__ == "__main__":
    analyze_event_effect()
