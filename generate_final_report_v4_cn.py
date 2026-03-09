import pandas as pd
from fpdf import FPDF
import os

# Font Path on macOS
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

class FinalStrategyReportCN(FPDF):
    def __init__(self):
        super().__init__()
        if os.path.exists(FONT_PATH):
            print(f"Loading Font: {FONT_PATH}")
            self.add_font("chinese", "", FONT_PATH)
            self.set_font("chinese", "", 12)
        else:
            print(f"ERROR: Font NOT found at {FONT_PATH}")

    def header(self):
        available_fonts = [f.lower() for f in self.fonts.keys()]
        if "chinese" in available_fonts:
            self.set_font("chinese", "", 16)
            self.cell(0, 10, '台股營收動能策略研究報告', align='C', ln=1)
            self.set_font("chinese", "", 10)
            self.cell(0, 10, 'Alpha 驗證、大盤對比與全維度分析', align='C', ln=1)
        else:
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy', align='C', ln=1)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        available_fonts = [f.lower() for f in self.fonts.keys()]
        if "chinese" in available_fonts:
            self.set_font("chinese", "", 8)
            self.cell(0, 10, f'第 {self.page_no()} 頁', align='C')
        else:
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_report():
    pdf = FinalStrategyReportCN()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    available_fonts = [f.lower() for f in pdf.fonts.keys()]
    if "chinese" in available_fonts:
        font_name = "chinese"
    else:
        font_name = "helvetica"

    # Section 1
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '一、 資料完整性與回測邏輯修正', ln=1)
    pdf.set_font(font_name, "", 11)
    setup_text = (
        "本研究採用回測期間涵蓋超過 11 年的台股市場歷史數據。\n\n"
        "為避免出現前視偏誤(Look-ahead Bias)。將策略買入之邏輯設置為：於 T 日收盤後確認訊號，"
        "並於 T+1 日開盤價買入，此邏輯方符合實戰交易之可能性。\n\n"
        "- 測試期間：2015 年 1 月 5 日至 2026 年 3 月 4 日。\n"
        "- 數據來源：TEJ (歷史營收)、以及 FinMind API (還原股價、驗證)。\n"
        "- 標的範圍：全台股市場（上市＋上櫃），排除低流動性與股價小於 10 元的股票 。\n"
        "- 交易成本：包含標準手續費 (0.1425% 且有 2.5 折優惠) 與 證交稅 (0.3%)。"
    )
    pdf.multi_cell(180, 7, setup_text)
    pdf.ln(5)

    # Section 2
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '二、 基準策略', ln=1)
    pdf.set_font(font_name, "", 11)
    exp7_text = (
        "基準策略確立了趨勢過濾動能的核心邏輯：\n"
        "1. 進場訊號：月營收創歷史新高 + 公告前周轉率增加 + 股價站上 20MA。\n"
        "2. 持有時間：60 個交易日。\n"
        "3. 排序機制：優先選擇週轉率最高的標的，並最多持有20檔。\n"
        "績效呈現：CAGR 13.62%, Sharpe Ratio 1.20, 最大回撤 (MDD) -24.57%。"
    )
    pdf.multi_cell(180, 7, exp7_text)
    if os.path.exists('analysis_results/plots/exp7_dashboard_final.png'):
        pdf.image('analysis_results/plots/exp7_dashboard_final.png', x=15, w=170)
        pdf.ln(2) # Add space after image
    pdf.ln(5)

    # Section 3
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '三、 Alpha 驗證與策略優化', ln=1)
    pdf.set_font(font_name, "", 11)
    exp10_analysis = (
        "研究發現「持倉20日 + 跌破20MA止損」是修正邏輯後最具穩健性的配置：\n\n"
        "1. 提高資金周轉：20 日的期間精確捕捉了公告後動能最強時段，顯著優於 60 日持倉。\n"
        "2. 風險控制優化：當股價跌破 20MA 時立即出場，有效過濾掉轉弱期，成功降低回撤並提升夏普值。\n"
        "3. 超額報酬 (Alpha)：相較於台股大盤 (TAIEX)，策略展現了穩定且持續的領先走勢。\n\n"
        "最終驗證指標 (對比大盤)：\n"
        "- 策略年化報酬 (CAGR): 16.21%\n"
        "- 大盤年化報酬 (Benchmark): 11.99%\n"
        "- 超額報酬 (Alpha): +4.22% (年化)\n"
        "- 夏普值 (Sharpe Ratio): 1.85\n"
        "- 最大回撤 (MDD): -10.63%\n"
        "- 總期間報酬率: 434.91%"
    )
    # Note: 之前跑出 Alpha 4% 是因為對比的是 TAIEX 的某個基準點，這裡統一使用最新對齊數據。
    pdf.multi_cell(180, 7, exp10_analysis)
    
    if os.path.exists('analysis_results/plots/exp10_vs_benchmark.png'):
        pdf.image('analysis_results/plots/exp10_vs_benchmark.png', x=15, w=170)
        pdf.ln(2) # Add space after image
    pdf.multi_cell(180, 7, "【累積績效對比】：灰線為台股大盤，藍線為本策略。綠色區域代表策略產出的 Alpha 超額報酬。")
    pdf.ln(5)

    # Section 4
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '四、 穩健性測試與回撤對比', ln=1)
    pdf.set_font(font_name, "", 11)
    robust_text = (
        "不同參數組合下之績效對比，顯示月持倉在年化報酬與風險控制間取得最佳平衡。"
    )
    pdf.multi_cell(180, 7, robust_text)
    
    pdf.ln(2)
    table_text = (
        "- 20日持倉 (無止損): CAGR 15.45%, MDD -25.71%, Sharpe 1.45\n"
        "- 20日持倉 (MA20止損): CAGR 16.21%, MDD -10.63%, Sharpe 1.85\n"
        "- 60日持倉 (無止損): CAGR 13.62%, MDD -24.57%, Sharpe 1.20\n"
    )
    pdf.multi_cell(180, 7, table_text)
    
    if os.path.exists('analysis_results/plots/drawdown_comparison.png'):
        pdf.image('analysis_results/plots/drawdown_comparison.png', x=15, w=170)
        pdf.ln(2) # Add space after image
    pdf.multi_cell(180, 7, "【風險對比圖】：優化後策略(綠線) 的回撤深度顯著淺於 無優化 (紅區)，具備更高的資金安全性。")

    # Section 5
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '五、 年度績效分析', ln=1)
    pdf.set_font(font_name, "", 11)
    if os.path.exists('analysis_results/plots/yearly_returns_exp10.png'):
        pdf.image('analysis_results/plots/yearly_returns_exp10.png', x=15, w=170)
        pdf.ln(2) # Add space after image
    
    pdf.ln(10)
    conclusion = (
        "總結：營收動能策略在修正邏輯後依然具備顯著 Alpha。透過月頻轉倉與MA20動態止損的優化，成功實現了高品質的夏普值 (1.85)，兼具報酬與穩定性的交易模型。"
    )
    pdf.multi_cell(180, 7, conclusion)

    # Save
    output_path = 'Strategy_Research_Final_V4_CN_Optimized.pdf'
    pdf.output(output_path)
    print(f"中文優化報告 (大盤對比版) 已成功生成：{output_path}")

if __name__ == "__main__":
    generate_report()
