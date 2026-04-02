import pandas as pd
from fpdf import FPDF
import os

class FinalStrategyReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy', 0, 1, 'C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'Evolution from Static Holding to Dynamic Trend-Following', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    pdf = FinalStrategyReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Section 1: Data & Environment
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Research Data & Environment', 0, 1)
    pdf.set_font('helvetica', '', 11)
    setup_text = (
        "The strategy was verified using 11 years of high-fidelity market data (2015-2026). "
        "All backtests include transaction costs (0.1425% commission and 0.3% tax) and utilize "
        "adjusted pricing to account for corporate actions like dividends and splits."
    )
    pdf.multi_cell(0, 7, setup_text)
    pdf.ln(5)

    # Section 2: Strategy Evolution (Exp 7 to Exp 10)
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Strategy Evolution & Parameter Optimization', 0, 1)
    pdf.set_font('helvetica', '', 11)
    evolution_text = (
        "The model evolved from a basic momentum follower into a high-conviction engine:\n"
        "- Experiment 7 (Baseline): All-time high revenue + 20MA trend filter + 60-day holding.\n"
        "- Sensitivity Testing: Identified 20 trading days as the optimal holding window (monthly rotation).\n"
        "- Conviction Filtering: Increased YoY growth threshold to >20% to isolate major growth events."
    )
    pdf.multi_cell(0, 7, evolution_text)
    
    if os.path.exists('analysis_results/plots/robustness_short_long.png'):
        pdf.image('analysis_results/plots/robustness_short_long.png', x=15, w=170)
    pdf.ln(5)

    # Section 3: Final Optimized Execution (Dynamic Exit)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Final Production Logic: Dynamic Exit Strategy', 0, 1)
    pdf.set_font('helvetica', '', 11)
    exit_text = (
        "The final 'Production Engine' optimizes the exit logic to preserve gains and reduce risk:\n"
        "1. Dynamic Trend Exit: Instead of a fixed timeframe, positions are closed immediately if "
        "the price falls below the 20-day Moving Average (20MA), signaling a trend reversal.\n"
        "2. Time Cap: A maximum holding period of 40 days is enforced to maintain high capital turnover.\n"
        "3. Hard Stop-Loss: A -10% protective stop is maintained to prevent catastrophic drawdowns.\n\n"
        "Outcome: This dynamic approach improved the risk-adjusted return (Sharpe 1.84) and "
        "reduced Maximum Drawdown to -16.02%."
    )
    pdf.multi_cell(0, 7, exit_text)
    
    if os.path.exists('analysis_results/plots/exit_strategy_optimization.png'):
        pdf.image('analysis_results/plots/exit_strategy_optimization.png', x=15, w=170)
    pdf.ln(5)

    # Section 4: Performance Visualization & Summary
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Performance Visualization', 0, 1)
    
    if os.path.exists('analysis_results/plots/exp10_final_equity.png'):
        pdf.image('analysis_results/plots/exp10_final_equity.png', x=15, w=180)
    
    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, 'Final Summary Table (11-Year Cumulative)', 0, 1)
    pdf.set_font('helvetica', '', 11)
    stats_table = (
        "Metric                | Value\n"
        "----------------------|-----------\n"
        "Total Return          | 470.51%\n"
        "Annualized (CAGR)     | 16.89%\n"
        "Sharpe Ratio          | 1.84\n"
        "Max Drawdown (MDD)    | -16.02%\n"
        "Win Rate (Per Trade)  | ~58%"
    )
    pdf.multi_cell(0, 7, stats_table)

    # Conclusion
    pdf.ln(5)
    conclusion = (
        "Conclusion: By transitioning from static holding to a dynamic trend-following exit, the strategy "
        "captures the explosive phase of revenue peaks while exiting early when momentum fades. "
        "The resulting model is robust, efficient, and tailored for professional quantitative trading."
    )
    pdf.multi_cell(0, 7, conclusion)

    # Save
    output_path = 'Strategy_Research_Final_Production_EN.pdf'
    pdf.output(output_path)
    print(f"Final Production Report Generated: {output_path}")

if __name__ == "__main__":
    generate_report()
