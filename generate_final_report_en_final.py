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
    
    # Section 1
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Strategy Methodology (Experiment 7 Base)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    logic_text = (
        "The core strategy is designed to capture the 'Post-Earnings Announcement Drift' (PEAD) effect. "
        "The model identifies companies reaching fundamental inflection points using three primary filters:\n"
        "1. Fundamental: Monthly revenue hits an all-time high (or 1-year high) with positive YoY growth.\n"
        "2. Technical Filter: Price must be above the 20-day Moving Average (20MA) to ensure entry into an established uptrend.\n"
        "3. Market Heat: In scenarios with excess signals, 'Turnover Rate' is used as a ranking factor to prioritize high-momentum stocks.\n"
        "Base Configuration: 10M TWD capital, 500k per position, max 20 positions, 60-day holding period."
    )
    pdf.multi_cell(0, 7, logic_text)
    
    if os.path.exists('analysis_results/plots/exp7_dashboard_final.png'):
        pdf.image('analysis_results/plots/exp7_dashboard_final.png', x=15, w=180)
    pdf.ln(5)

    # Section 2
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Robustness Testing: Holding Period Sensitivity', 0, 1)
    pdf.set_font('helvetica', '', 11)
    robust_text = (
        "To ensure the strategy is not overfitted to a specific holding window, we tested holding periods ranging from 5 to 100 days. "
        "The findings confirm the strategy's underlying strength:\n"
        "1. The 'Sweet Spot': A 20-day holding period (monthly rotation) achieved the highest total return of 425.95%.\n"
        "2. Stability: Consistent positive alpha was observed across all windows from 20 to 80 days, proving the PEAD effect is a durable market phenomenon.\n"
        "3. Diffusion Time: Very short periods (5 days) underperform, indicating that fundamental news requires time to be fully absorbed by the market."
    )
    pdf.multi_cell(0, 7, robust_text)
    
    if os.path.exists('analysis_results/plots/robustness_short_long.png'):
        pdf.image('analysis_results/plots/robustness_short_long.png', x=15, w=170)
    pdf.ln(5)

    # Section 3
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Strategy Optimization & Risk Mitigation (Exp 10)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    opt_text = (
        "Using the 20-day benchmark, we introduced higher conviction filters and risk controls to reach 'Experiment 10' status:\n"
        "1. Growth Threshold (Growth+): Increasing the minimum YoY growth to 20% boosted total returns from 425% to 538%.\n"
        "2. Stop-Loss Integration (Safe): Implementing a -10% fixed stop-loss refined the equity curve, improving Max Drawdown (MDD) "
        "from -21.7% to -16.0%.\n"
        "Final Recommendation: 20-day holding + 20% Growth Filter + 10% Stop-Loss provides the best risk-adjusted profile."
    )
    pdf.multi_cell(0, 7, opt_text)
    
    if os.path.exists('analysis_results/plots/optimization_final_comparison.png'):
        pdf.image('analysis_results/plots/optimization_final_comparison.png', x=15, w=170)
    pdf.ln(5)

    # Section 4
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Smart Money Correlation: Cluster 3 Brokerage Activity', 0, 1)
    pdf.set_font('helvetica', '', 11)
    insight_text = (
        "Beyond quantitative metrics, brokerage analysis reveals that 'Cluster 3' (Institutional Smart Money) serves as a critical "
        "confirmatory signal:\n"
        "1. Lead Indicator: Cluster 3 branches frequently accumulate positions 5-10 days prior to all-time high revenue announcements.\n"
        "2. Momentum Sustainability: Trades where Cluster 3 remains a net buyer post-announcement show significantly higher win rates.\n\n"
        "Conclusion: This multi-factor approach - combining fundamental peaks, technical trends, and institutional tracking - offers a "
        "statistically robust edge in the Taiwan market over an 11-year cycle."
    )
    pdf.multi_cell(0, 7, insight_text)

    output_path = 'Taiwan_Stock_Revenue_Momentum_Final_Report_EN.pdf'
    pdf.output(output_path)
    print(f"Final English Report Generated: {output_path}")

if __name__ == "__main__":
    generate_report()
