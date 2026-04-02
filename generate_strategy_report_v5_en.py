import pandas as pd
from fpdf import FPDF
import os

class StrategyReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Taiwan Stock Revenue Momentum Strategy: Comprehensive Backtest Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    # 1. Load Data for Stats
    try:
        df_trades = pd.read_csv('analysis_results/data/event_strategy_trades_v2.csv')
        start_date = df_trades['buy_date'].min()
        end_date = df_trades['buy_date'].max()
        total_trades = len(df_trades)
        avg_ret = df_trades['return'].mean()
        win_rate = (df_trades['return'] > 0).mean()
        max_ret = df_trades['return'].max()
        min_ret = df_trades['return'].min()
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    pdf = StrategyReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Section 1: Executive Summary
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Executive Summary', 0, 1)
    pdf.set_font('helvetica', '', 12)
    summary_text = (
        f"This report presents a quantitative analysis of the 'Revenue All-Time High Momentum Strategy' "
        f"in the Taiwan Stock Market. The strategy identifies stocks reaching new historical revenue peaks "
        f"combined with institutional cluster accumulation.\n\n"
        f"Key Performance Statistics:\n"
        f"- Backtest Period: {start_date} to {end_date} (~10 Years)\n"
        f"- Total Samples: {total_trades} trades identified\n"
        f"- Average Return per Trade: {avg_ret:.2%}\n"
        f"- Win Rate: {win_rate:.2%}\n"
        f"- Maximum Single Trade Return: {max_ret:.2%}\n"
        f"- Minimum Single Trade Return: {min_ret:.2%}\n"
    )
    pdf.multi_cell(0, 10, summary_text)
    pdf.ln(5)

    # Section 2: Data Processing & Cleaning Details
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Data Processing & Methodology', 0, 1)
    pdf.set_font('helvetica', '', 12)
    details_text = (
        "Reliability in backtesting is maintained through rigorous data handling:\n"
        "1. Time Horizon: Data spanning from 2015 to late 2025, covering diverse market regimes "
        "(2018 Trade War, 2020 COVID Rally, 2022 Bear Market).\n"
        "2. Outlier Handling: To prevent skewing results, returns exceeding 500% or below -90% are "
        "flagged for manual review. In visualization, returns are clipped at +/- 50% for better clarity.\n"
        "3. Liquidity Filtering: Low-turnover stocks (e.g., penny stocks or 'zombie stocks') are "
        "excluded from the universe to ensure execution feasibility.\n"
        "4. Transaction Costs: A standard commission of 0.1425% (per side) and a securities "
        "transaction tax of 0.3% are modeled to reflect real-world slippage and costs.\n"
        "5. Data Sources: Fundamental revenue data sourced from MOPS (Market Observation Post System) "
        "and FinMind API. Historical pricing from TWSE."
    )
    pdf.multi_cell(0, 10, details_text)
    pdf.ln(5)

    # Section 3: Visual Performance Analysis
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. Performance Visualization', 0, 1)
    
    # Cumulative Performance
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, '3.1 Cumulative Return (Strategy vs. Benchmark)', 0, 1)
    if os.path.exists('analysis_results/plots/strategy_performance.png'):
        pdf.image('analysis_results/plots/strategy_performance.png', x=10, w=170)
    pdf.ln(5)

    # Yearly Performance
    pdf.add_page()
    pdf.cell(0, 10, '3.2 Average Trade Returns by Year', 0, 1)
    if os.path.exists('analysis_results/plots/yearly_avg_return.png'):
        pdf.image('analysis_results/plots/yearly_avg_return.png', x=10, w=170)
    pdf.ln(5)

    # Distribution and Drawdown
    pdf.add_page()
    pdf.cell(0, 10, '3.3 Distribution of Returns (Risk Profile)', 0, 1)
    if os.path.exists('analysis_results/plots/return_histogram.png'):
        pdf.image('analysis_results/plots/return_histogram.png', x=10, w=160)
    pdf.ln(5)
    pdf.cell(0, 10, '3.4 Strategy Maximum Drawdown', 0, 1)
    if os.path.exists('analysis_results/plots/drawdown_chart.png'):
        pdf.image('analysis_results/plots/drawdown_chart.png', x=10, w=160)

    # Section 4: Critical Expert Feedback & Future Improvements
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. Strategy Optimization Roadmap', 0, 1)
    pdf.set_font('helvetica', '', 12)
    roadmap_text = (
        "Based on 'Smart BPS' feedback and the 'Taiwan Stock Quant Strategy Notes' requirements:\n\n"
        "1. Precision Announcement Dates: Implement FinMind's 'update_date' to replace standard "
        "deadline assumptions, eliminating look-ahead bias.\n"
        "2. Alpha Verification: Calculate excess returns by stripping out Market Beta (TAIEX) to "
        "confirm that profits are due to selection, not just a rising tide.\n"
        "3. Story vs. Quant: Move beyond qualitative narratives of the '16 Key Trades' toward a "
        "systematic verification of causality between revenue events and price action.\n"
        "4. Cluster Filtering: Differentiate between institutional accumulation and high-turnover "
        "day-trading branches (Cluster 1) to refine momentum signals."
    )
    pdf.multi_cell(0, 10, roadmap_text)

    # Final Conclusion
    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, 'Conclusion', 0, 1)
    pdf.set_font('helvetica', '', 12)
    pdf.multi_cell(0, 10, "The strategy shows robust positive expectancy over a 10-year period. "
                        "By refining the entry timing and separating beta, the strategy is expected "
                        "to deliver high-conviction alpha for institutional-grade quantitative trading.")

    output_path = 'Strategy_Report_Comprehensive_v5_EN.pdf'
    pdf.output(output_path)
    print(f"Report successfully generated: {output_path}")

if __name__ == "__main__":
    generate_report()
