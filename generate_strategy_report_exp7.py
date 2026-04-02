import pandas as pd
from fpdf import FPDF
import os

class StrategyReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy: Experiment 7 Analysis', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    # Performance Stats from Experiment 7 (as per README.md)
    cagr = "14.60%"
    sharpe = "1.47"
    mdd = "-19.40%"
    
    pdf = StrategyReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Section 1: Experiment 7 Strategy Definition
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Strategy Methodology (Experiment 7 Focus)', 0, 1)
    pdf.set_font('helvetica', '', 12)
    logic_text = (
        "Experiment 7 represents the 'Trend-Filtered Revenue Momentum' approach. "
        "The strategy captures the 'Post-Earnings Announcement Drift' (PEAD) effect in Taiwan stocks.\n\n"
        "Core Logic:\n"
        "1. Fundamental Signal: Monthly revenue reaching a new historical or 1-year high with positive YoY growth.\n"
        "2. Trend Filter: Entry is only permitted if the stock price is above its 20-day Moving Average (20MA), "
        "ensuring the stock is in an established upward trend.\n"
        "3. Ranking Priority: When multiple signals occur, stocks with the highest 'Turnover Rate' are prioritized, "
        "as market heat is a proven positive factor for momentum (validated in Experiment 9).\n"
        "4. Execution: Buy at T+1 Open, hold for exactly 60 trading days, and exit at Close."
    )
    pdf.multi_cell(0, 10, logic_text)
    pdf.ln(5)

    # Section 2: Performance Summary
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Performance Metrics (Experiment 7)', 0, 1)
    pdf.set_font('helvetica', '', 12)
    stats_text = (
        f"- Compound Annual Growth Rate (CAGR): {cagr}\n"
        f"- Sharpe Ratio: {sharpe}\n"
        f"- Maximum Drawdown (MDD): {mdd}\n"
        "- Capital Allocation: 10M TWD initial capital, max 20 positions, 500k TWD per position."
    )
    pdf.multi_cell(0, 10, stats_text)
    pdf.ln(5)

    # Section 3: Visual Analysis (Experiment 7)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Visual Performance Analysis', 0, 1)
    
    # Note: Use existing plots which represent Exp 7
    if os.path.exists('analysis_results/plots/strategy_performance.png'):
        pdf.image('analysis_results/plots/strategy_performance.png', x=10, w=170)
    pdf.ln(5)
    
    if os.path.exists('analysis_results/plots/yearly_avg_return.png'):
        pdf.image('analysis_results/plots/yearly_avg_return.png', x=10, w=170)

    # Section 4: Supplemental Insight - Cluster 3 Analysis
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Supplemental Insight: The Role of Cluster 3', 0, 1)
    pdf.set_font('helvetica', '', 12)
    cluster_text = (
        "While the core quantitative filters (20MA & Revenue Highs) drive the base performance, "
        "on-chain/brokerage analysis reveals that 'Cluster 3' represents the primary institutional "
        "force driving these momentum events.\n\n"
        "Observations:\n"
        "1. Institutional Accumulation: Cluster 3 branches often show steady accumulation during the "
        "5-10 days leading up to the revenue peak announcement.\n"
        "2. Conviction Indicator: Success rates in Experiment 7 significantly increase when Cluster 3 "
        "remains a net buyer post-announcement.\n"
        "3. Risk Mitigation: Avoiding trades where Cluster 3 is a heavy seller despite positive "
        "revenue news helps filter out 'bull traps' or 'fake highs'."
    )
    pdf.multi_cell(0, 10, cluster_text)

    # Section 5: Optimization Roadmap
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '5. Strategy Roadmap', 0, 1)
    pdf.set_font('helvetica', '', 12)
    roadmap = (
        "1. Precision Entry: Transition to FinMind 'update_date' for exact signal timing.\n"
        "2. Market Regime Filter: Add an overall market trend filter (TAIEX 200MA) to avoid "
        "trading during systemic bear markets.\n"
        "3. Smart Stop-Loss: Implement a dynamic stop-loss based on Cluster 3 exit signals."
    )
    pdf.multi_cell(0, 10, roadmap)

    output_path = 'Strategy_Report_Exp7_Final.pdf'
    pdf.output(output_path)
    print(f"Exp 7 Final Report successfully generated: {output_path}")

if __name__ == "__main__":
    generate_report()
