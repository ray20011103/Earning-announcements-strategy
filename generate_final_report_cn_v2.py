import pandas as pd
from fpdf import FPDF
import os

# 字體路徑 (針對 macOS)
FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"

class FinalReportCN(FPDF):
    def __init__(self):
        super().__init__()
        if os.path.exists(FONT_PATH):
            self.add_font("Chinese", "", FONT_PATH)
            self.add_font("ChineseB", "", FONT_PATH)

    def header(self):
        if "Chinese" in self.fonts:
            self.set_font("Chinese", "", 16)
            self.cell(0, 10, '台股營收創新高動能策略：從基礎模型到極致優化', 0, 1, 'C')
        else:
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, 'Taiwan Stock Revenue Strategy Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        if "Chinese" in self.fonts:
            self.set_font("Chinese", "", 8)
            self.cell(0, 10, f'第 {self.page_no()} 頁', 0, 0, 'C')
        else:
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    pdf = FinalReportCN()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    has_cn = "Chinese" in pdf.fonts
    font_name = "Chinese" if has_cn else "helvetica"
    
    # 第一章
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '一、 基礎策略定義 (Experiment 7)' if has_cn else '1. Base Strategy', 0, 1)
    pdf.set_font(font_name, "", 11)
    logic_text = (
        "本策略旨在捕獲「盈餘公告後漂移 (PEAD)」效應。核心邏輯建立於以下三層過濾：\n"
        "1. 基本面：月營收創下歷史新高或近一年新高，且營收年增率 (YoY) 為正。\n"
        "2. 技術面：股價站上 20 日移動平均線 (20MA)，確保進場時處於上升趨勢。\n"
        "3. 市場熱度：當訊號過多時，優先選擇「週轉率」最高之個股，利用群眾動能。\n"
        "基礎配置：初始資金 1000 萬，固定部位 50 萬，最大持有 20 檔，持有期 60 交易日。"
    ) if has_cn else "Logic in English..."
    pdf.multi_cell(0, 8, logic_text)
    
    if os.path.exists('analysis_results/plots/exp7_dashboard_final.png'):
        pdf.image('analysis_results/plots/exp7_dashboard_final.png', x=15, w=180)
    pdf.ln(5)

    # 第二章
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '二、 穩健性測試：持有天數的敏感度分析' if has_cn else '2. Robustness Test', 0, 1)
    pdf.set_font(font_name, "", 11)
    robust_text = (
        "為了驗證策略是否對參數過度擬合，我們測試了從 5 天到 100 天的持有天數。測試發現：\n"
        "1. 20 交易日 (約一個月) 為最佳持有期，總報酬率達 425.95%，顯著優於原始的 60 天。\n"
        "2. 策略在 20-80 天之間表現極為穩定，證明營收動能具備長期有效性，而非隨機噴發。\n"
        "3. 5 天持有期表現較差，說明基本面利多需要時間讓市場充分反映。"
    ) if has_cn else "Robustness in English..."
    pdf.multi_cell(0, 8, robust_text)
    
    if os.path.exists('analysis_results/plots/robustness_short_long.png'):
        pdf.image('analysis_results/plots/robustness_short_long.png', x=15, w=170)
    pdf.ln(5)

    # 第三章
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '三、 極致優化與風險控制 (Experiment 10)' if has_cn else '3. Optimization', 0, 1)
    pdf.set_font(font_name, "", 11)
    opt_text = (
        "基於 20 天持有期的基準，我們進一步引入「成長強度」與「停損機制」進行優化：\n"
        "1. 成長門檻 (Growth+): 將營收年增率門檻由 0% 提高至 20%，總報酬率由 425% 提升至 538%。\n"
        "2. 風險控制 (Safe): 加入 -10% 固定停損機制。雖然總報酬降至 470%，但最大回撤 (MDD) "
        "從 -21.7% 改善至 -16.0%。\n"
        "最終版本 (Exp 10) 建議採納：20 天持倉 + 20% 成長門檻 + 10% 停損。"
    ) if has_cn else "Optimization in English..."
    pdf.multi_cell(0, 8, opt_text)
    
    if os.path.exists('analysis_results/plots/optimization_final_comparison.png'):
        pdf.image('analysis_results/plots/optimization_final_comparison.png', x=15, w=170)
    pdf.ln(5)

    # 第四章
    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, '四、 實戰洞察：Cluster 3 主力的角色' if has_cn else '4. Insights', 0, 1)
    pdf.set_font(font_name, "", 11)
    insight_text = (
        "除了量化參數外，籌碼面分析揭示了 Cluster 3 (關鍵主力分點) 的決定性作用：\n"
        "1. 領先指標：Cluster 3 通常在營收公告前 5-10 天開始佈局。\n"
        "2. 趨勢續航：公告後若 Cluster 3 持續買入，勝率大幅提升。\n\n"
        "結論：本策略結合了基本面爆發力與技術趨勢。透過 20 天高效輪轉與嚴格停損，能在長期市場週期中產生穩定的 Alpha。"
    ) if has_cn else "Conclusion in English..."
    pdf.multi_cell(0, 8, insight_text)

    output_name = 'Taiwan_Stock_Revenue_Strategy_Final_Report_CN_v2.pdf'
    pdf.output(output_name)
    print(f"最終中文報告已生成：{output_name}")

if __name__ == "__main__":
    generate_report()
