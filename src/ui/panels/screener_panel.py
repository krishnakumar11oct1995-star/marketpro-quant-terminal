from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import yfinance as yf
import pandas as pd
from src.ui.theme import color_for_change, TEXT_SECONDARY


class ScannerWorker(QThread):
    results_ready = pyqtSignal(list)

    def __init__(self, filters: dict):
        super().__init__()
        self.filters = filters

    def run(self):
        candidates = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                       "BRK-B", "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH",
                       "HD", "DIS", "PYPL", "ADBE", "NFLX", "CMCSA", "PEP",
                       "INTC", "AMD", "CRM", "TMO", "ABT", "TXN", "COST", "AVGO"]
        results = []
        for sym in candidates:
            try:
                tk = yf.Ticker(sym)
                info = tk.info or {}
                price = info.get("currentPrice", 0)
                pe = info.get("trailingPE", 0)
                mcap = info.get("marketCap", 0)
                sector = info.get("sector", "")
                vol = info.get("volume", 0)
                avg_vol = info.get("averageVolume", 0)
                div = info.get("dividendYield", 0)
                rsi_val = self._calc_rsi(tk)

                if mcap < self.filters.get("min_mcap", 0):
                    continue
                if self.filters.get("max_mcap", 1e15) < mcap:
                    continue
                if pe > 0 and self.filters.get("max_pe", 100) < pe:
                    continue
                if self.filters.get("sector") and self.filters.get("sector") != sector:
                    continue
                if self.filters.get("min_div") and (div or 0) * 100 < self.filters["min_div"]:
                    continue
                if rsi_val and self.filters.get("rsi_max", 100) < rsi_val:
                    continue
                if rsi_val and self.filters.get("rsi_min", 0) > rsi_val:
                    continue

                results.append({
                    "symbol": sym, "price": price, "pe": pe,
                    "mcap": mcap, "sector": sector, "volume": vol,
                    "div": div, "rsi": rsi_val
                })
            except:
                continue
        self.results_ready.emit(results)

    def _calc_rsi(self, tk, period=14):
        try:
            hist = tk.history(period="2mo")
            if len(hist) < period:
                return None
            delta = hist["Close"].diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss.replace(0, 0.001)
            return 100 - (100 / (1 + rs)).iloc[-1]
        except:
            return None


class StockScreenerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Stock Screener")
        title.setProperty("heading", True)
        layout.addWidget(title)

        filters_layout = QHBoxLayout()

        filter_group = QWidget()
        fg = QHBoxLayout(filter_group)
        fg.setSpacing(8)

        fg.addWidget(QLabel("Min Mcap:"))
        self.min_mcap = QSpinBox()
        self.min_mcap.setRange(0, 1000000)
        self.min_mcap.setValue(0)
        self.min_mcap.setSuffix("B")
        fg.addWidget(self.min_mcap)

        fg.addWidget(QLabel("Max P/E:"))
        self.max_pe = QDoubleSpinBox()
        self.max_pe.setRange(0, 1000)
        self.max_pe.setValue(50)
        fg.addWidget(self.max_pe)

        fg.addWidget(QLabel("Sector:"))
        self.sector = QComboBox()
        self.sector.addItems(["All", "Technology", "Healthcare", "Financials", "Energy", "Consumer Cyclical"])
        fg.addWidget(self.sector)

        fg.addWidget(QLabel("Min RSI:"))
        self.rsi_min = QSpinBox()
        self.rsi_min.setRange(0, 100)
        self.rsi_min.setValue(0)
        fg.addWidget(self.rsi_min)

        fg.addWidget(QLabel("Max RSI:"))
        self.rsi_max = QSpinBox()
        self.rsi_max.setRange(0, 100)
        self.rsi_max.setValue(100)
        fg.addWidget(self.rsi_max)

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self._run_scan)
        fg.addWidget(self.scan_btn)
        filters_layout.addWidget(filter_group)
        layout.addLayout(filters_layout)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels(
            ["Symbol", "Price", "P/E", "Market Cap", "Sector", "Volume", "Div Yield", "RSI", "Score"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        layout.addWidget(self.results_table)

        self.status_label = QLabel("Ready - click Scan to filter stocks")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(self.status_label)

    def _run_scan(self):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.status_label.setText("Running screen...")

        filters = {
            "min_mcap": self.min_mcap.value() * 1e9,
            "max_mcap": 1e15,
            "max_pe": self.max_pe.value(),
            "sector": None if self.sector.currentText() == "All" else self.sector.currentText(),
            "min_div": 0,
            "rsi_min": self.rsi_min.value(),
            "rsi_max": self.rsi_max.value(),
        }

        self.worker = ScannerWorker(filters)
        self.worker.results_ready.connect(self._on_results)
        self.worker.start()

    def _on_results(self, results: list):
        self.results_table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(r["symbol"]))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"${r['price']:.2f}"))
            self.results_table.setItem(i, 2, QTableWidgetItem(f"{r['pe']:.2f}" if r["pe"] else "N/A"))
            mcap = r["mcap"]
            self.results_table.setItem(i, 3, QTableWidgetItem(f"${mcap/1e9:.1f}B" if mcap > 1e9 else f"${mcap/1e6:.1f}M"))
            self.results_table.setItem(i, 4, QTableWidgetItem(r["sector"] or ""))
            self.results_table.setItem(i, 5, QTableWidgetItem(f"{r['volume']:,}"))
            self.results_table.setItem(i, 6, QTableWidgetItem(f"{r['div']*100:.2f}%" if r["div"] else "0%"))
            self.results_table.setItem(i, 7, QTableWidgetItem(f"{r['rsi']:.1f}" if r["rsi"] else "N/A"))
            score = self._calc_score(r)
            score_item = QTableWidgetItem(f"{score:.1f}")
            score_item.setForeground(color_for_change(score - 50))
            self.results_table.setItem(i, 8, score_item)

        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan")
        self.status_label.setText(f"Found {len(results)} matches")

    def _calc_score(self, r: dict) -> float:
        score = 50
        if r.get("pe") and 10 < r["pe"] < 25:
            score += 10
        if r.get("rsi") and 30 < r["rsi"] < 70:
            score += 10
        if r.get("div") and r["div"] > 0.01:
            score += 5
        return score
