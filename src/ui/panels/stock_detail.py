from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLineEdit, QPushButton, QLabel,
                             QHeaderView, QTabWidget, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import numpy as np
from src.services.data_service import DataService
from src.services.technical_service import TechnicalService
from src.ui.theme import TEXT_SECONDARY, color_for_change


class StockDetailPanel(QWidget):
    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self.tech = TechnicalService()
        self.symbol = "AAPL"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search symbol...")
        self.search_input.returnPressed.connect(self._search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Analyze")
        self.search_btn.clicked.connect(self._search)
        search_layout.addWidget(self.search_btn)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        self.tabs = QTabWidget()

        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")

        self.financials_tab = QWidget()
        self._setup_financials_tab()
        self.tabs.addTab(self.financials_tab, "Financials")

        self.ratios_tab = QWidget()
        self._setup_ratios_tab()
        self.tabs.addTab(self.ratios_tab, "Ratios")

        self.valuation_tab = QWidget()
        self._setup_valuation_tab()
        self.tabs.addTab(self.valuation_tab, "Valuation")

        layout.addWidget(self.tabs)
        self._refresh()

    def _setup_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)

        self.quote_grid = QWidget()
        self.quote_layout = QHBoxLayout(self.quote_grid)
        layout.addWidget(self.quote_grid)

        self.price_label = QLabel("--")
        self.price_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #e6edf3;")
        self.quote_layout.addWidget(self.price_label)

        self.change_label = QLabel("--")
        self.change_label.setStyleSheet("font-size: 16px;")
        self.quote_layout.addWidget(self.change_label)

        self.quote_layout.addStretch()

        self.info_table = QTableWidget()
        self.info_table.setColumnCount(2)
        self.info_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.info_table.horizontalHeader().setStretchLastSection(True)
        self.info_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.info_table.verticalHeader().setVisible(False)
        layout.addWidget(self.info_table)

    def _setup_financials_tab(self):
        layout = QVBoxLayout(self.financials_tab)

        self.fin_table = QTableWidget()
        self.fin_table.setColumnCount(5)
        self.fin_table.setHorizontalHeaderLabels(["Metric", "TTM", "2024", "2023", "2022"])
        self.fin_table.horizontalHeader().setStretchLastSection(True)
        self.fin_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fin_table.verticalHeader().setVisible(False)
        layout.addWidget(self.fin_table)

    def _setup_ratios_tab(self):
        layout = QVBoxLayout(self.ratios_tab)

        self.ratio_table = QTableWidget()
        self.ratio_table.setColumnCount(3)
        self.ratio_table.setHorizontalHeaderLabels(["Ratio", "Value", "Interpretation"])
        self.ratio_table.horizontalHeader().setStretchLastSection(True)
        self.ratio_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ratio_table.verticalHeader().setVisible(False)
        layout.addWidget(self.ratio_table)

    def _setup_valuation_tab(self):
        layout = QVBoxLayout(self.valuation_tab)

        self.dcf_label = QLabel("Run analysis to see DCF valuation")
        self.dcf_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.dcf_label)

        self.valuation_table = QTableWidget()
        self.valuation_table.setColumnCount(2)
        self.valuation_table.setHorizontalHeaderLabels(["Method", "Fair Value"])
        self.valuation_table.horizontalHeader().setStretchLastSection(True)
        self.valuation_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.valuation_table.verticalHeader().setVisible(False)
        layout.addWidget(self.valuation_table)

    def _search(self):
        symbol = self.search_input.text().strip().upper()
        if symbol:
            self.symbol = symbol
            self._refresh()

    def _refresh(self):
        quote = self.data.get_quote(self.symbol)
        if quote:
            self.price_label.setText(f"${quote.price:.2f}")
            clr = color_for_change(quote.change)
            self.change_label.setText(f"{quote.change:+.2f} ({quote.change_pct:+.2f}%)")
            self.change_label.setStyleSheet(f"font-size: 16px; color: {clr.name()};")

            metrics = [
                ("Market Cap", f"${quote.market_cap/1e9:.2f}B" if quote.market_cap > 1e9 else f"${quote.market_cap/1e6:.2f}M"),
                ("P/E Ratio", f"{quote.pe_ratio:.2f}" if quote.pe_ratio else "N/A"),
                ("Dividend Yield", f"{quote.dividend_yield*100:.2f}%" if quote.dividend_yield else "N/A"),
                ("52W High", f"${quote.high_52w:.2f}" if quote.high_52w else "N/A"),
                ("52W Low", f"${quote.low_52w:.2f}" if quote.low_52w else "N/A"),
                ("Volume", f"{quote.volume:,}"),
                ("Avg Volume", f"{quote.avg_volume:,}"),
                ("Bid/Ask", f"${quote.bid:.2f} / ${quote.ask:.2f}" if quote.bid else "N/A"),
            ]
            self.info_table.setRowCount(len(metrics))
            for i, (k, v) in enumerate(metrics):
                self.info_table.setItem(i, 0, QTableWidgetItem(k))
                self.info_table.setItem(i, 1, QTableWidgetItem(str(v)))

        self._load_financials()
        self._load_ratios()
        self._load_valuation()

    def _load_financials(self):
        fin = self.data.get_financials(self.symbol)
        if fin and not fin.income_statement.empty:
            df = fin.income_statement
            metrics = [
                "Total Revenue", "Gross Profit", "Operating Income",
                "Net Income", "EBITDA", "Diluted EPS"
            ]
            cols = df.columns[:4]
            self.fin_table.setRowCount(len(metrics))
            for i, met in enumerate(metrics):
                self.fin_table.setItem(i, 0, QTableWidgetItem(met))
                for j, col in enumerate(cols):
                    val = df.loc[met, col] if met in df.index else None
                    self.fin_table.setItem(i, j + 1, QTableWidgetItem(
                        f"${val/1e9:.2f}B" if val and abs(val) > 1e9 else f"${val/1e6:.2f}M" if val else "N/A"
                    ))

    def _load_ratios(self):
        ratios = self.data.get_ratios(self.symbol)
        if ratios:
            data = [
                ("P/E Ratio", ratios.pe_ratio, "Lower = undervalued"),
                ("P/B Ratio", ratios.pb_ratio, "Compares market to book value"),
                ("P/S Ratio", ratios.ps_ratio, "Revenue multiple"),
                ("EV/EBITDA", ratios.ev_ebitda, "Enterprise valuation"),
                ("D/E Ratio", ratios.de_ratio, "Leverage measure"),
                ("Current Ratio", ratios.current_ratio, "Liquidity (>1 = good)"),
                ("ROE", ratios.roe, "Return on equity"),
                ("ROA", ratios.roa, "Return on assets"),
                ("Gross Margin", ratios.gross_margin, "Profitability"),
                ("Net Margin", ratios.net_margin, "Bottom line"),
                ("EPS", ratios.eps, "Earnings per share"),
                ("Div Yield", ratios.dividend_yield * 100 if ratios.dividend_yield else None, "Income return"),
            ]
            self.ratio_table.setRowCount(len(data))
            for i, (name, val, interp) in enumerate(data):
                self.ratio_table.setItem(i, 0, QTableWidgetItem(name))
                v_str = f"{val:.2f}" if val is not None else "N/A"
                self.ratio_table.setItem(i, 1, QTableWidgetItem(v_str))
                self.ratio_table.setItem(i, 2, QTableWidgetItem(interp))

    def _load_valuation(self):
        quote = self.data.get_quote(self.symbol)
        ratios = self.data.get_ratios(self.symbol)
        if not quote or not ratios:
            return

        price = quote.price
        pe = ratios.pe_ratio
        eps = ratios.eps

        methods = []
        if pe and eps:
            methods.append(("Current P/E", f"${price:.2f}"))
            methods.append(("Industry Avg P/E", f"${eps * 20:.2f}" if pe < 25 else f"${eps * 15:.2f}"))
        if ratios.pb_ratio and quote.market_cap:
            book_value = quote.market_cap / ratios.pb_ratio if ratios.pb_ratio else 0
            methods.append(("Book Value", f"${book_value/1e9:.2f}B"))

        self.valuation_table.setRowCount(len(methods))
        for i, (k, v) in enumerate(methods):
            self.valuation_table.setItem(i, 0, QTableWidgetItem(k))
            self.valuation_table.setItem(i, 1, QTableWidgetItem(v))

        self.dcf_label.setText(
            f"DCF Estimate: ${eps * 25:.2f}" if eps else "DCF: Insufficient data"
        )
