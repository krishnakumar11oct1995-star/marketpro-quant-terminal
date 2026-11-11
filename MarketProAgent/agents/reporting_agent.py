"""
Reporting Agent — generates text summary and optionally a PDF report.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import os


class ReportingAgent:
    def __init__(self, config: dict):
        self.config = config
        self.reports_dir = config.get('reports', {}).get('output_dir', 'reports')

    def generate_text_report(self, ticker: str, analysis: Dict,
                             strategy_results: Dict, market_context: Dict = None) -> str:
        lines = [
            "=" * 60,
            f"MarketProAgent Report — {ticker}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
        ]

        # Market context
        if market_context:
            lines.append("\n[MARKET CONTEXT]")
            for key, val in market_context.items():
                if isinstance(val, dict):
                    lines.append(f"  {key}: {val.get('last_price', 'N/A')} ({val.get('change_pct', 0):+.2f}%)")

        # Signals
        lines.append(f"\n[STRATEGY SIGNALS]")
        for name, result in strategy_results.items():
            lines.append(f"  {name}: {result.signal} (conf: {result.confidence:.0%})")
            if result.reason:
                lines.append(f"    Reason: {result.reason}")

        # Analysis results
        if 'valuation' in analysis:
            lines.append(f"\n[VALUATION]")
            val = analysis['valuation']
            if isinstance(val, dict) and 'error' not in val:
                lines.append(f"  {val.get('output', 'N/A')}")

        if 'ml_forecast' in analysis:
            lines.append(f"\n[ML FORECAST]")
            ml = analysis['ml_forecast']
            if isinstance(ml, dict) and 'error' not in ml:
                lines.append(f"  {ml.get('output', 'N/A')}")

        lines.append(f"\n{'=' * 60}")
        return '\n'.join(lines)

    def save_report(self, ticker: str, content: str, fmt: str = 'txt'):
        os.makedirs(self.reports_dir, exist_ok=True)
        path = os.path.join(self.reports_dir, f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}")
        with open(path, 'w') as f:
            f.write(content)
        return path
