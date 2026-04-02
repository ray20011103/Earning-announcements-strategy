import pandas as pd
import numpy as np
from fpdf import FPDF
import os

class StrategyReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    # 1. Load Data
    try:
        returns_df = pd.read_csv('analysis_results/data/revenue_strategy_returns.csv')
        trades_df = pd.read_csv('analysis_results/data/event_strategy_trades_v2.csv')
        
        # Basic Stats Calculation
        total_return = (1 + returns_df['Momentum (R5-R1)']).prod() - 1
        num_trades = len(trades_df)
        avg_win_rate = (trades_df['return'] > 0).mean()
        max_drawdown = "TBD (from plots)" # Placeholder or calc if daily returns available
    except Exception as e:
        print(f"Error loading data: {e}")
        total_return, num_trades, avg_win_rate = 0, 0, 0

    # 2. Create PDF
    pdf = StrategyReport()
    pdf.add_page()
    
    # Section 1: Executive Summary
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Executive Summary', 0, 1)
    pdf.set_font('helvetica', '', 12)
    summary_text = (
        f"This report details the 'Taiwan Stock Revenue Momentum Strategy'. "
        f"The strategy focuses on capturing alpha from companies reporting all-time high monthly revenue. "
        f"\n\nKey Metrics:\n"
        f"- Total Period Return: {total_return:.2%}\n"
        f"- Number of Events Identified: {num_trades}\n"
        f"- Trade Win Rate: {avg_win_rate:.2%}\n"
    )
    pdf.multi_cell(0, 10, summary_text)
    pdf.ln(5)

    # Section 2: Strategy Logic
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Strategy Methodology', 0, 1)
    pdf.set_font('helvetica', '', 12)
    logic_text = (
        "The strategy employs a dual-factor filtering mechanism:\n"
        "1. Fundamental Factor: Monthly revenue reaching a new historical peak with YoY growth > 20%.\n"
        "2. Momentum/Chip Factor: Identifying 'Cluster 1' brokerage branches (Smart Money/Insider clusters) "
        "showing significant accumulation prior to the revenue announcement.\n"
        "3. Execution: Entry on the first trading day post-announcement, with a tactical holding period of 20-40 days."
    )
    pdf.multi_cell(0, 10, logic_text)
    pdf.ln(5)

    # Section 3: Performance Visualization
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Performance Visualization', 0, 1)
    if os.path.exists('analysis_results/plots/strategy_performance.png'):
        pdf.image('analysis_results/plots/strategy_performance.png', x=10, w=180)
    pdf.ln(10)

    # Section 4: Expert Feedback & Optimization (The "Smart BPS" Feedback)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Expert Review & Future Enhancements', 0, 1)
    pdf.set_font('helvetica', '', 12)
    feedback_text = (
        "Based on recent review from the 'Smart BPS' strategy feedback, several critical optimizations are scheduled:\n\n"
        "1. Story vs. Quant: Move from narrative-based observations to robust quantitative verification.\n"
        "2. Precision Timing: Integrate FinMind API to fetch exact 'update_date' for revenue announcements to eliminate look-ahead bias.\n"
        "3. Alpha Decomposition: Calculate excess returns by stripping out Market Beta (TAIEX effect) to confirm true strategy alpha.\n"
        "4. Cluster Refinement: Re-evaluate high-turnover branches (Day Trading clusters) as potential momentum indicators during bull markets.\n"
        "5. Causality Audit: Validate the 16 primary trades against specific news events to ensure revenue was the primary driver."
    )
    pdf.multi_cell(0, 10, feedback_text)

    # Save PDF
    output_path = 'Strategy_Report_Revenue_Momentum.pdf'
    pdf.output(output_path)
    print(f"Report successfully generated: {output_path}")

if __name__ == "__main__":
    generate_report()
