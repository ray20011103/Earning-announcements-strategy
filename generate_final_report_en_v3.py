import pandas as pd
from fpdf import FPDF
import os

class StrategyReportEN(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy', 0, 1, 'C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'From Base Model (Exp 7) to Optimized Engine (Exp 10)', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    pdf = StrategyReportEN()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Section 1: Base Strategy (Exp 7)
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Strategy Methodology (Experiment 7 Base)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    logic_text = (
        "The core strategy is designed to capture the 'Post-Earnings Announcement Drift' (PEAD) effect. "
        "Base Configuration (Exp 7): 10M TWD capital, 500k per position, max 20 positions, 60-day holding period."
    )
    pdf.multi_cell(0, 7, logic_text)
    
    if os.path.exists('analysis_results/plots/exp7_dashboard_final.png'):
        pdf.image('analysis_results/plots/exp7_dashboard_final.png', x=15, w=180)
    pdf.ln(5)

    # Section 2: Robustness Analysis
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Robustness Testing: Period Sensitivity', 0, 1)
    pdf.set_font('helvetica', '', 11)
    robust_text = (
        "Testing holding periods from 5 to 100 days confirmed that a 20-day holding period (monthly rotation) "
        "yields the highest performance (425.95% return), establishing our new optimized baseline."
    )
    pdf.multi_cell(0, 7, robust_text)
    
    if os.path.exists('analysis_results/plots/robustness_short_long.png'):
        pdf.image('analysis_results/plots/robustness_short_long.png', x=15, w=170)
    pdf.ln(5)

    # Section 3: Final Optimization (Exp 10)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Final Optimized Model (Experiment 10)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    opt_text = (
        "Experiment 10 integrates high-conviction fundamental filters and tactical risk management:\n"
        "1. Monthly Rotation: 20-day holding period for high capital efficiency.\n"
        "2. Conviction Filter: Minimum 20% YoY growth threshold for revenue peaks.\n"
        "3. Capital Protection: -10% fixed stop-loss per position.\n"
        "The chart below illustrates the 11-year equity growth of this final configuration."
    )
    pdf.multi_cell(0, 7, opt_text)
    
    if os.path.exists('analysis_results/plots/exp10_final_equity.png'):
        pdf.image('analysis_results/plots/exp10_final_equity.png', x=15, w=180)
    
    if os.path.exists('analysis_results/plots/optimization_final_comparison.png'):
        pdf.image('analysis_results/plots/optimization_final_comparison.png', x=15, w=170)
    pdf.ln(5)

    # Section 4: Conclusion
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Research Conclusion', 0, 1)
    pdf.set_font('helvetica', '', 11)
    conclusion = (
        "By iteratively refining the holding period and adding conviction filters, the strategy "
        "demonstrates significant alpha generation capabilities. The final Optimized Engine (Exp 10) "
        "provides a scalable foundation for systematic momentum trading in the Taiwan stock market."
    )
    pdf.multi_cell(0, 7, conclusion)

    output_path = 'Final_Strategy_Report_Optimized_EN.pdf'
    pdf.output(output_path)
    print(f"Final Optimized Report Generated: {output_path}")

if __name__ == "__main__":
    generate_report()
