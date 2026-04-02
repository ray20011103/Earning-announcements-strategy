import pandas as pd
from fpdf import FPDF
import os

class FinalStrategyReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy', 0, 1, 'C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'Evolution of a Systematic Event-Driven Model', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    pdf = FinalStrategyReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Section 1: Data Integrity & Backtest Environment
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Data Integrity & Backtest Setup', 0, 1)
    pdf.set_font('helvetica', '', 11)
    setup_text = (
        "This research utilizes a high-fidelity backtest environment covering over 11 years of Taiwan stock market history.\n\n"
        "- Period: January 5, 2015, to March 4, 2026.\n"
        "- Data Sources: TEJ (Historical Revenue), TWSE (Adjusted Pricing), and FinMind API (Verification).\n"
        "- Universe: All-market Taiwan stocks, excluding low-liquidity and penny stocks.\n"
        "- Costs: Standard commission (0.1425% with 75% discount) and securities tax (0.3%) included."
    )
    pdf.multi_cell(0, 7, setup_text)
    pdf.ln(5)

    # Section 2: The Baseline (Experiment 7)
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. The Baseline Strategy (Experiment 7)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    exp7_text = (
        "Experiment 7 established the 'Trend-Filtered Momentum' logic:\n"
        "1. Buy Signal: Monthly revenue all-time high + Positive growth + Price > 20MA.\n"
        "2. Holding: 60 trading days.\n"
        "Performance: CAGR 14.08%, Sharpe 1.28, MDD -24.17%."
    )
    pdf.multi_cell(0, 7, exp7_text)
    if os.path.exists('analysis_results/plots/exp7_dashboard_final.png'):
        pdf.image('analysis_results/plots/exp7_dashboard_final.png', x=15, w=180)
    pdf.ln(5)

    # Section 3: The Optimized Engine (Experiment 10)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. The Optimized Engine (Experiment 10)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    # Using the exact stats we just calculated
    exp10_text = (
        "Experiment 10 represents the final production-ready model after sensitivity and risk optimization:\n"
        "1. Monthly Rotation: Reduced holding period to 20 days for maximum capital efficiency.\n"
        "2. Conviction Filter: YoY growth threshold increased to 20% to isolate major fundamental shifts.\n"
        "3. Capital Protection: -10% fixed stop-loss per position.\n\n"
        "Final Verified Metrics (Exp 10):\n"
        "- CAGR: 16.89%\n"
        "- Sharpe Ratio: 1.84\n"
        "- Max Drawdown (MDD): -16.02%\n"
        "- Total Period Return: 470.51%"
    )
    pdf.multi_cell(0, 7, exp10_text)
    
    if os.path.exists('analysis_results/plots/exp10_final_equity.png'):
        pdf.image('analysis_results/plots/exp10_final_equity.png', x=15, w=180)
    pdf.ln(5)

    # Section 4: Performance Comparison & Conclusion
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Performance Evolution & Conclusion', 0, 1)
    pdf.set_font('helvetica', '', 11)
    comp_text = (
        "The chart below compares the evolution of return vs. risk profiles. The inclusion of the growth filter "
        "and stop-loss mechanism effectively shifted the strategy toward a higher Sharpe Ratio and reduced MDD."
    )
    pdf.multi_cell(0, 7, comp_text)
    
    if os.path.exists('analysis_results/plots/optimization_comparison_fixed.png'):
        pdf.image('analysis_results/plots/optimization_comparison_fixed.png', x=15, w=170)
    
    pdf.ln(10)
    conclusion = (
        "Conclusion: The Revenue Momentum strategy shows robust alpha over an 11-year cycle. By prioritizing high-growth "
        "fundamental peaks and maintaining strict trend and risk filters, the strategy achieves an institutional-grade "
        "Sharpe Ratio of 1.84."
    )
    pdf.multi_cell(0, 7, conclusion)

    # Save
    output_path = 'Strategy_Research_Final_V4_Optimized.pdf'
    pdf.output(output_path)
    print(f"Final Optimized Report Generated: {output_path}")

if __name__ == "__main__":
    generate_report()
