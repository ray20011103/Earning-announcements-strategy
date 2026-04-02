import pandas as pd
from FinMind.data import DataLoader
import matplotlib.pyplot as plt
import numpy as np

def analyze_event_effect():
    dl = DataLoader()
    df = pd.read_csv('analysis_results/data/event_strategy_trades_cleaned.csv')
    
    # 挑選具備代表性的樣本 (例如近期交易)
    sample_df = df.sort_values('buy_date', ascending=False).head(40)
    
    all_rel_returns = []
    
    for idx, row in sample_df.iterrows():
        sym = str(row['symbol']).zfill(4)
        ann_date = pd.to_datetime(row['ann_date'])
        
        try:
            # 抓取較寬的時間範圍
            p_df = dl.taiwan_stock_daily(stock_id=sym, 
                                        start_date=(ann_date - pd.Timedelta(days=20)).strftime('%Y-%m-%d'),
                                        end_date=(ann_date + pd.Timedelta(days=20)).strftime('%Y-%m-%d'))
            if p_df.empty: continue
            
            p_df['date'] = pd.to_datetime(p_df['date'])
            p_df = p_df.sort_values('date').reset_index(drop=True)
            
            # 找到最接近公告日的索引
            ann_candidates = p_df[p_df['date'] >= ann_date].index
            if len(ann_candidates) == 0: continue
            t0_idx = ann_candidates[0]
            
            # 建立相對時間序列 (-10 到 +10)
            window = 10
            start = t0_idx - window
            end = t0_idx + window + 1
            
            if start < 0 or end > len(p_df): continue
            
            # 以 T-1 (公告前一天) 的價格作為 1.0 基點，觀察漲跌
            base_price = p_df.loc[t0_idx - 1, 'close']
            segment = p_df.iloc[start:end].copy()
            segment['rel_ret'] = segment['close'] / base_price - 1
            segment['rel_day'] = np.arange(-window, window + 1)
            
            all_rel_returns.append(segment[['rel_day', 'rel_ret']])
            
        except:
            continue

    if not all_rel_returns:
        print("未獲取足夠有效的事件樣本。")
        return

    # 合併並計算平均值
    combined = pd.concat(all_rel_returns)
    event_avg = combined.groupby('rel_day')['rel_ret'].mean()
    
    # 繪圖
    plt.figure(figsize=(12, 7))
    plt.plot(event_avg.index, event_avg.values * 100, marker='o', linewidth=2, color='#2c3e50')
    plt.axvline(x=0, color='#e74c3c', linestyle='--', label='Announcement (T=0)')
    plt.axvspan(-10, 0, color='green', alpha=0.1, label='Pre-Ann (Information Leakage?)')
    plt.axvspan(0, 10, color='blue', alpha=0.1, label='Post-Ann (Momentum Reaction)')
    
    plt.title('Average Cumulative Return Around Revenue Announcement (Event Study)', fontsize=14)
    plt.xlabel('Days Relative to Announcement', fontsize=12)
    plt.ylabel('Cumulative Return (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('analysis_results/plots/event_study_final.png')
    
    # 計算具體數據
    pre_ret = event_avg.loc[0] - event_avg.loc[-10]
    post_ret = event_avg.loc[10] - event_avg.loc[0]
    print(f"\n--- 事件研究結果摘要 ---")
    print(f"公告前 10 天平均漲幅: {pre_ret:.2%}")
    print(f"公告後 10 天平均漲幅: {post_ret:.2%}")
    print(f"圖表已存至: analysis_results/plots/event_study_final.png")

if __name__ == "__main__":
    analyze_event_effect()
