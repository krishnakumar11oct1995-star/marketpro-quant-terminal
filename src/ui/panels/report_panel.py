from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QFileDialog, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime
import json
import csv
import os
from src.services.data_service import DataService
from src.core.logger import Logger


class ReportPanel(QWidget):
    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self.log = Logger()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Reports & Export")
        title.setProperty("heading", True)
        layout.addWidget(title)

        controls = QHBoxLayout()

        self.report_type = QComboBox()
        self.report_type.addItems([
            "Market Summary Report",
            "Portfolio Snapshot",
            "Stock Analysis Report",
            "Performance Report"
        ])
        controls.addWidget(self.report_type)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["HTML", "CSV", "JSON"])
        controls.addWidget(self.format_combo)

        generate_btn = QPushButton("Generate Report")
        generate_btn.clicked.connect(self._generate_report)
        controls.addWidget(generate_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export)
        controls.addWidget(export_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setStyleSheet(
            "background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px; padding: 8px;")
        self.report_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.report_view)

        self._current_report = ""

    def _generate_report(self):
        rtype = self.report_type.currentText()
        fmt = self.format_combo.currentText()

        if rtype == "Market Summary Report":
            self._generate_market_summary(fmt)
        elif rtype == "Portfolio Snapshot":
            self._generate_portfolio_snapshot(fmt)
        elif rtype == "Stock Analysis Report":
            self._generate_stock_analysis(fmt)
        elif rtype == "Performance Report":
            self._generate_performance(fmt)

    def _generate_market_summary(self, fmt: str):
        indices = self.data.get_market_indices()
        lines = [f"Market Summary Report", "=" * 40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        for name, data in indices.items():
            lines.append(f"{name:20s} ${data['price']:>8.2f}  ({data['change_pct']:+.2f}%)")
        self._display_report("\n".join(lines), fmt)

    def _generate_portfolio_snapshot(self, fmt: str):
        quote = self.data.get_quote("AAPL")
        lines = [f"Portfolio Snapshot", "=" * 40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        if quote:
            lines.append(f"Cash: $10,000.00")
            lines.append(f"Holdings: 1 position")
            lines.append(f"Total Value: ${quote.price * 10 + 10000:,.2f}")
            lines.append(f"Today's P&L: ${quote.change * 10:+,.2f}")
        self._display_report("\n".join(lines), fmt)

    def _generate_stock_analysis(self, fmt: str):
        sym = "AAPL"
        quote = self.data.get_quote(sym)
        ratios = self.data.get_ratios(sym)
        lines = [f"Stock Analysis: {sym}", "=" * 40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        if quote:
            lines.append(f"Price: ${quote.price:.2f} ({quote.change_pct:+.2f}%)")
            lines.append(f"Market Cap: ${quote.market_cap/1e9:.1f}B")
            lines.append(f"P/E: {quote.pe_ratio or 'N/A'}")
        if ratios:
            lines.append(f"EPS: {ratios.eps or 'N/A'}")
            lines.append(f"ROE: {ratios.roe*100:.1f}%" if ratios.roe else "")
            lines.append(f"Div Yield: {ratios.dividend_yield*100:.2f}%" if ratios.dividend_yield else "")
        self._display_report("\n".join(lines), fmt)

    def _generate_performance(self, fmt: str):
        lines = [
            "Performance Report", "=" * 40,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
            "YTD Return: +12.5%",
            "Benchmark (S&P 500): +8.2%",
            "Alpha: +4.3%",
            "Sharpe Ratio: 1.85",
            "Max Drawdown: -8.3%",
            "Win Rate: 62%",
        ]
        self._display_report("\n".join(lines), fmt)

    def _display_report(self, content: str, fmt: str):
        self._current_report = content
        if fmt == "HTML":
            html = content.replace("\n", "<br>").replace("=" * 40,
                "<hr style='border-color:#30363d;'>")
            self.report_view.setHtml(
                f"<pre style='color:#c9d1d9; font-family:Consolas;'>{html}</pre>")
        else:
            self.report_view.setPlainText(content)

    def _export(self):
        if not self._current_report:
            return
        fmt = self.format_combo.currentText().lower()
        ext = fmt
        name, _ = QFileDialog.getSaveFileName(
            self, "Export Report", f"report_{datetime.now().strftime('%Y%m%d')}.{ext}",
            f"*.{ext}")
        if not name:
            return
        try:
            with open(name, "w") as f:
                f.write(self._current_report)
            self.log.info(f"Report exported to {name}")
        except Exception as e:
            self.log.error(f"Export error: {e}")
