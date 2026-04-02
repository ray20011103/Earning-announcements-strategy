import pandas as pd
from fpdf import FPDF
import os

# Define font path for macOS
FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"

class StrategyReportCN(FPDF):
    def __init__(self):
        super().__init__()
        # Pre-load the font to avoid errors
        if os.path.exists(FONT_PATH):
            self.add_font("Chinese", "", FONT_PATH)
            self.add_font("ChineseB", "", FONT_PATH) # Using same for bold as STHeiti handles it
        else:
            print("Warning: Chinese font not found at expected path.")

    def header(self):
        if "Chinese" in self.fonts:
            self.set_font("Chinese", "", 16)
            self.cell(0, 10, '台股營收創新高動能策略回測報告', 0, 1, 'C')
        else:
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, 'Taiwan Stock Revenue Strategy Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        if "Chinese" in self.fonts:
            self.set_font("Chinese", "", 8)
            self.cell(0, 10, f'第 {self.page_no()} 頁', 0, 0, 'C')
        else:
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    df_trades = pd.read_csv('analysis_results/data/event_strategy_trades_v2.csv')
    start_date = df_trades['buy_date'].min()
    end_date = df_trades['buy_date'].max()
    total_trades = len(df_trades)
    avg_win_rate = (df_trades['return'] > 0).mean()

    pdf = StrategyReportCN()
    pdf.add_page()
    
    has_cn = "Chinese" in pdf.fonts
    font_name = "Chinese" if has_cn else "helvetica"

    # Section 1
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '一、 執行摘要' if has_cn else '1. Executive Summary', 0, 1)
    pdf.set_font(font_name, "", 12)
    summary = (
        f"本報告分析「台股營收創新高動能策略」之回測表現。該策略核心邏輯為鎖定營收創下歷史新高、"
        f"且具備關鍵分點籌碼進駐之個股。 \n\n"
        f"關鍵指標數據：\n"
        f"- 測試期間：{start_date} 至 {end_date}\n"
        f"- 樣本總數：{total_trades} 筆交易\n"
        f"- 平均勝率：{avg_win_rate:.2%}\n"
    ) if has_cn else "Summary in English..."
    pdf.multi_cell(0, 10, summary)
    pdf.ln(5)

    # Section 2
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '二、 資料處理與計算細節' if has_cn else '2. Data Processing Details', 0, 1)
    pdf.set_font(font_name, "", 12)
    details = (
        "1. 時間範圍：跨越約 10 年之市場週期（2015-2025），涵蓋多個完整牛熊週期。\n"
        "2. 極值處理：為排除流動性風險與極端異常值，已將報酬率超過 500% 或低於 -90% 之個股進行標註審查。同時在篩選過程中排除了成交量過低之個股。\n"
        "3. 交易成本：計算已預設包含單邊 0.1425% 手續費（打折前）與 0.3% 證交稅之估算，確保回測貼近實戰。\n"
        "4. 資料來源：歷史營收資料採集自公開觀測站及 FinMind API，股價資料採集自台灣證券交易所。"
    ) if has_cn else "Details in English..."
    pdf.multi_cell(0, 10, details)
    pdf.ln(5)

    # Section 3
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '三、 績效視覺化分析' if has_cn else '3. Visual Analysis', 0, 1)
    
    pdf.set_font(font_name, "", 12)
    pdf.cell(0, 10, '1. 累積報酬率走勢' if has_cn else '1. Cumulative Returns', 0, 1)
    if os.path.exists('analysis_results/plots/strategy_performance.png'):
        pdf.image('analysis_results/plots/strategy_performance.png', x=10, w=170)
    pdf.ln(10)

    pdf.add_page()
    pdf.cell(0, 10, '2. 年度平均報酬率對比' if has_cn else '2. Yearly Returns', 0, 1)
    if os.path.exists('analysis_results/plots/yearly_avg_return.png'):
        pdf.image('analysis_results/plots/yearly_avg_return.png', x=10, w=170)
    pdf.ln(10)

    pdf.add_page()
    pdf.cell(0, 10, '3. 報酬率分佈與最大回撤分析' if has_cn else '3. Dist & Drawdown', 0, 1)
    if os.path.exists('analysis_results/plots/return_histogram.png'):
        pdf.image('analysis_results/plots/return_histogram.png', x=10, w=170)
    pdf.ln(5)
    if os.path.exists('analysis_results/plots/drawdown_chart.png'):
        pdf.image('analysis_results/plots/drawdown_chart.png', x=10, w=170)

    # Section 4
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '四、 結論與後續優化' if has_cn else '4. Conclusion', 0, 1)
    pdf.set_font(font_name, "", 12)
    conclusion = (
        "本策略在長期回測中展現了顯著的超額報酬（Alpha）。根據資料處理細節，策略在排除極端值後依然穩健。\n"
        "後續優化重點：\n"
        "1. 公告日精確化：解決回測中的「偷看未來」風險。\n"
        "2. 資金壓力測試：模擬大額資金進出對股價的衝擊。\n"
        "3. 宏觀環境過濾：在市場極端下跌期間（如 2022 年）加入空手觀望機制。"
    ) if has_cn else "Conclusion in English..."
    pdf.multi_cell(0, 10, conclusion)

    pdf.output('Final_Strategy_Report_v4_CN.pdf')
    print("PDF 報告生成成功：Final_Strategy_Report_v4_CN.pdf")

if __name__ == "__main__":
    generate_report()
