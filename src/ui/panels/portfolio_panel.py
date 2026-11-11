from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QDoubleSpinBox, QFormLayout, QGroupBox, QTabWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import numpy as np
from src.services.data_service import DataService
from src.ui.theme import color_for_change, TEXT_SECONDARY, BG_PANEL


class PortfolioPanel(QWidget):
    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self._positions = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Portfolio Dashboard")
        title.setProperty("heading", True)
        layout.addWidget(title)

        self.overview_bar = QWidget()
        self.overview_layout = QHBoxLayout(self.overview_bar)
        layout.addWidget(self.overview_bar)

        self._add_overview_card("Total Value", "$0.00")
        self._add_overview_card("Day P&L", "$0.00")
        self._add_overview_card("Total P&L", "$0.00")
        self._add_overview_card("Sharpe", "0.00")
        self._add_overview_card("Max DD", "0.00%")

        self.tabs = QTabWidget()

        self.positions_tab = QWidget()
        pos_layout = QVBoxLayout(self.positions_tab)

        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Symbol:"))
        self.pos_symbol = QLabel("AAPL")
        add_layout.addWidget(self.pos_symbol)
        add_layout.addWidget(QLabel("Qty:"))
        self.pos_qty = QDoubleSpinBox()
        self.pos_qty.setRange(0, 100000)
        self.pos_qty.setValue(10)
        add_layout.addWidget(self.pos_qty)
        add_layout.addWidget(QLabel("Cost:"))
        self.pos_cost = QDoubleSpinBox()
        self.pos_cost.setRange(0, 100000)
        self.pos_cost.setDecimals(2)
        self.pos_cost.setValue(150.0)
        add_layout.addWidget(self.pos_cost)
        add_btn = QPushButton("Add Position")
        add_btn.clicked.connect(self._add_position)
        add_layout.addWidget(add_btn)
        add_layout.addStretch()
        pos_layout.addLayout(add_layout)

        self.pos_table = QTableWidget()
        self.pos_table.setColumnCount(7)
        self.pos_table.setHorizontalHeaderLabels(["Symbol", "Qty", "Avg Cost", "Price", "Value", "P&L", "P&L%"])
        self.pos_table.horizontalHeader().setStretchLastSection(True)
        self.pos_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pos_table.verticalHeader().setVisible(False)
        pos_layout.addWidget(self.pos_table)
        self.tabs.addTab(self.positions_tab, "Positions")

        self.risk_tab = QWidget()
        risk_layout = QVBoxLayout(self.risk_tab)
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(2)
        self.risk_table.setHorizontalHeaderLabels(["Risk Metric", "Value"])
        self.risk_table.horizontalHeader().setStretchLastSection(True)
        self.risk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.risk_table.verticalHeader().setVisible(False)
        risk_layout.addWidget(self.risk_table)
        self.tabs.addTab(self.risk_tab, "Risk")

        layout.addWidget(self.tabs)

    def _add_overview_card(self, title: str, value: str):
        card = QWidget()
        card.setStyleSheet(f"background-color: {BG_PANEL.name()}; border: 1px solid #30363d; border-radius: 6px; padding: 8px;")
        cl = QVBoxLayout(card)
        cl.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-size: 11px;")
        cl.addWidget(lbl_title)
        lbl_val = QLabel(value)
        lbl_val.setObjectName(f"card_{title.lower().replace(' ', '_')}")
        lbl_val.setStyleSheet("font-size: 18px; font-weight: bold; color: #e6edf3;")
        cl.addWidget(lbl_val)
        self.overview_layout.addWidget(card)

    def _add_position(self):
        symbol = self.pos_symbol.text().strip().upper()
        qty = self.pos_qty.value()
        cost = self.pos_cost.value()
        quote = self.data.get_quote(symbol)
        price = quote.price if quote else cost
        self._positions.append({
            "symbol": symbol, "qty": qty, "cost": cost,
            "price": price, "value": qty * price,
            "pnl": (price - cost) * qty, "pnl_pct": ((price - cost) / cost) * 100
        })
        self._refresh_positions()

    def _refresh_positions(self):
        self.pos_table.setRowCount(len(self._positions))
        total_value = 0
        total_pnl = 0
        for i, p in enumerate(self._positions):
            quote = self.data.get_quote(p["symbol"])
            if quote:
                p["price"] = quote.price
                p["value"] = p["qty"] * quote.price
                p["pnl"] = (quote.price - p["cost"]) * p["qty"]
                p["pnl_pct"] = ((quote.price - p["cost"]) / p["cost"]) * 100
            total_value += p["value"]
            total_pnl += p["pnl"]

            self.pos_table.setItem(i, 0, QTableWidgetItem(p["symbol"]))
            self.pos_table.setItem(i, 1, QTableWidgetItem(str(int(p["qty"]))))
            self.pos_table.setItem(i, 2, QTableWidgetItem(f"${p['cost']:.2f}"))
            self.pos_table.setItem(i, 3, QTableWidgetItem(f"${p['price']:.2f}"))
            self.pos_table.setItem(i, 4, QTableWidgetItem(f"${p['value']:.2f}"))
            pnl_item = QTableWidgetItem(f"${p['pnl']:+.2f}")
            pnl_item.setForeground(color_for_change(p["pnl"]))
            self.pos_table.setItem(i, 5, pnl_item)
            pnlp_item = QTableWidgetItem(f"{p['pnl_pct']:+.2f}%")
            pnlp_item.setForeground(color_for_change(p["pnl_pct"]))
            self.pos_table.setItem(i, 6, pnlp_item)

        self._update_overview(total_value, total_pnl)
        self._update_risk()

    def _update_overview(self, total_value: float, total_pnl: float):
        value_lbl = self.findChild(QLabel, "card_total_value")
        if value_lbl:
            value_lbl.setText(f"${total_value:,.2f}")
        pnl_lbl = self.findChild(QLabel, "card_day_p&l")
        if pnl_lbl:
            pnl_lbl.setText(f"${total_pnl:+,.2f}")
            pnl_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color_for_change(total_pnl).name()};")

    def _update_risk(self):
        if len(self._positions) < 2:
            self.risk_table.setRowCount(4)
            data = [("Positions", str(len(self._positions))),
                    ("Total Value", f"${sum(p['value'] for p in self._positions):,.2f}"),
                    ("Diversification", "Add more positions"),
                    ("Concentration", "100% in single asset")]
            for i, (k, v) in enumerate(data):
                self.risk_table.setItem(i, 0, QTableWidgetItem(k))
                self.risk_table.setItem(i, 1, QTableWidgetItem(v))
            return

        values = [p["value"] for p in self._positions]
        weights = np.array(values) / sum(values)
        rets = [p["pnl_pct"] / 100 for p in self._positions]
        mean_ret = np.mean(rets) if rets else 0
        std_ret = np.std(rets) if len(rets) > 1 else 0
        sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0

        risk_data = [
            ("Positions", str(len(self._positions))),
            ("Total Value", f"${sum(values):,.2f}"),
            ("Avg Return", f"{mean_ret*100:+.2f}%"),
            ("Volatility", f"{std_ret*100:.2f}%"),
            ("Sharpe Ratio", f"{sharpe:.2f}"),
            ("Largest Position", f"{max(weights)*100:.1f}%"),
            ("Diversification", f"{1 - sum(w**2 for w in weights):.3f}" if len(weights) > 1 else "N/A"),
        ]
        self.risk_table.setRowCount(len(risk_data))
        for i, (k, v) in enumerate(risk_data):
            self.risk_table.setItem(i, 0, QTableWidgetItem(k))
            self.risk_table.setItem(i, 1, QTableWidgetItem(v))
