# 台股月營收創新高動能策略
> **Revenue Announcement Momentum — Event Study & Systematic Backtest**

本專案以嚴謹的事件研究（Event Study）與系統性回測框架，驗證「月營收創新高」事件驅動策略在台股市場的超額報酬（Alpha）。

---

## 專案結構

```
營收策略/
├── revenue_strategy_research.ipynb  ← 主研究 Notebook（完整研究流程）
├── price.csv                        ← TEJ 日頻股價資料（2015~2026）
├── announcement.csv                 ← TEJ 月營收公告資料（2015~2026）
├── market.csv                       ← 加權指數（TAIEX）日收盤
├── update_data.py                   ← 資料更新腳本
├── live_strategy_scanner.py         ← 實盤掃描腳本（每月 10 日後執行）
├── auto_update_and_scan.py          ← 自動排程腳本
├── run_daily_scan.command           ← macOS 快捷執行
└── analysis_results/
    ├── data/    ← 回測輸出（equity curve, trades, stats）
    └── plots/   ← 圖表輸出
```

---

## 研究設計

### 核心假說
> 當上市櫃公司公告月營收創「近一年新高」且年增率 > 20% 時，短期（20 交易日）存在顯著正向異常報酬（Post-Announcement Drift）。

### 進場信號（三條件同時成立）
| 條件 | 說明 |
|:---|:---|
| **營收創新高** | 近一年新高 OR 歷史新高（TEJ 欄位） |
| **年增率 > 20%** | 單月營收 YoY 成長率超過門檻 |
| **趨勢過濾** | T 日（公告日）收盤 > 20MA |

### 執行邏輯
- **買入**：T+1 日開盤價（公告日次一交易日）
- **排序**：依週轉率由高到低，優先選入流動性最高標的
- **持倉**：最多 20 檔，固定等資金部位（50 萬/檔）
- **出場**：固定 20 交易日 **OR** 股價跌破 20MA（MA Stop）

### 交易成本
| 項目 | 費率 |
|:---|:---|
| 手續費（買/賣） | 0.1425% × 2.5 折 = 0.0356%（單邊） |
| 證交稅（賣） | 0.3% |
| 雙邊合計 | ~0.371% |

---

## Notebook 研究流程（`revenue_strategy_research.ipynb`）

| Section | 內容 |
|:---:|:---|
| 1 | 研究設定與參數（所有參數集中一處） |
| 2 | 資料讀取與完整性驗證 |
| 3 | 探索性分析（信號分佈、年增率統計） |
| 4 | **事件研究（Event Study）**：CAAR + 95% CI + Cross-sectional t-test |
| 5 | **組合回測引擎**（方法論修正版） |
| 6 | 績效指標（CAGR / Sharpe / Sortino / MDD / Calmar） |
| 7 | 月度報酬熱力圖 & CAPM Alpha（Newey-West HAC SE） |
| 8 | **Walk-Forward OOS 驗證**（IS: 2015-2020 / OOS: 2021-2026） |
| 9 | 參數敏感度熱力圖 & 年度子期間分析 |
| 10 | 交易紀錄分析（出場原因、報酬分佈） |
| 11 | 研究結論與後續方向 |

---

## 方法論修正說明（v5 vs 舊版）

| 問題 | 舊版 | 修正版 |
|:---|:---|:---|
| MA 過濾時間點 | 用 T+1（買入日）收盤 → **前視偏誤** | 改用 T 日（info_date）收盤 ✅ |
| 重複持倉 | 同一股票可被重複加入 holdings | 加入 `held_syms` 防護 ✅ |
| Sharpe 計算 | 未扣無風險利率 | 正確扣除 Rf（1.5% 年化）✅ |
| 統計顯著性 | 無 | Newey-West t-stat ✅ |
| 樣本外驗證 | 全樣本優化 | Walk-Forward IS/OOS 分割 ✅ |

---

## 資料說明

- **價格資料**：TEJ 日頻資料，欄位含開/高/低/收、週轉率、市值
- **公告資料**：TEJ 月營收公告，含發布日、年增率、創新高/低標記
- **基準指數**：加權指數（TAIEX）日收盤
- **存活者偏差**：待確認 `price.csv` 是否包含已下市股票

---

## 環境需求

```bash
pip install pandas numpy matplotlib seaborn scipy statsmodels tqdm
```

Python 3.10+

---

*Last updated: 2026-04-27 ── Refactored with methodology corrections (v5)*
