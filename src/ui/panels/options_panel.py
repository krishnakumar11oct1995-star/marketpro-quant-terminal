from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QComboBox, QGroupBox, QGridLayout, QFrame, QTabWidget,
                             QDoubleSpinBox, QSpinBox, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import numpy as np
import pyqtgraph as pg
from py_vollib.black_scholes import black_scholes
from py_vollib.black_scholes.implied_volatility import implied_volatility
from src.services.data_service import DataService
from src.ui.theme import color_for_change, TEXT_SECONDARY, BG_PANEL, BG_DARK

pg.setConfigOptions(antialias=True, useOpenGL=True)
pg.setConfigOption("background", BG_DARK.getRgb())
pg.setConfigOption("foreground", (200, 200, 200))

_STRATEGIES = {
    "Long Call": [{"type": "call", "sign": 1}],
    "Long Put": [{"type": "put", "sign": 1}],
    "Short Call": [{"type": "call", "sign": -1}],
    "Short Put": [{"type": "put", "sign": -1}],
    "Covered Call": [{"type": "stock", "sign": 1}, {"type": "call", "sign": -1}],
    "Protective Put": [{"type": "stock", "sign": 1}, {"type": "put", "sign": 1}],
    "Bull Spread": [{"type": "call", "sign": 1}, {"type": "call", "sign": -1}],
    "Bear Spread": [{"type": "put", "sign": 1}, {"type": "put", "sign": -1}],
    "Straddle": [{"type": "call", "sign": 1}, {"type": "put", "sign": 1}],
    "Strangle": [{"type": "call", "sign": 1}, {"type": "put", "sign": 1}],
    "Iron Condor": [{"type": "call", "sign": -1}, {"type": "call", "sign": 1},
                    {"type": "put", "sign": -1}, {"type": "put", "sign": 1}],
}


class StrategyBuilderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._legs = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        for s in _STRATEGIES:
            self.strategy_combo.addItem(s)
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_change)
        controls.addWidget(self.strategy_combo)

        self.spot_input = QDoubleSpinBox()
        self.spot_input.setRange(1, 100000)
        self.spot_input.setValue(500)
        self.spot_input.setPrefix("Spot: $")
        controls.addWidget(self.spot_input)

        self.plot_btn = QPushButton("Plot Payoff")
        self.plot_btn.clicked.connect(self._plot_payoff)
        controls.addWidget(self.plot_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.legs_widget = QWidget()
        self.legs_layout = QVBoxLayout(self.legs_widget)
        self.legs_layout.setContentsMargins(0, 0, 0, 0)
        self._build_legs_ui("Long Call")
        layout.addWidget(self.legs_widget)

        self.payoff_plot = pg.PlotWidget()
        self.payoff_plot.showGrid(x=True, y=True, alpha=0.3)
        self.payoff_plot.setLabel("left", "P&L ($)")
        self.payoff_plot.setLabel("bottom", "Underlying Price ($)")
        self.payoff_plot.setMouseEnabled(x=False, y=False)
        self.payoff_plot.setMenuEnabled(False)
        layout.addWidget(self.payoff_plot)

        stats_widget = QWidget()
        stats = QHBoxLayout(stats_widget)
        self.max_profit_label = QLabel("Max Profit: --")
        self.max_loss_label = QLabel("Max Loss: --")
        self.be_label = QLabel("Breakeven: --")
        for lbl in [self.max_profit_label, self.max_loss_label, self.be_label]:
            lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
            stats.addWidget(lbl)
        stats.addStretch()
        layout.addWidget(stats_widget)

    def _build_legs_ui(self, strategy_name: str):
        for i in reversed(range(self.legs_layout.count())):
            w = self.legs_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        legs = _STRATEGIES.get(strategy_name, [])
        self._leg_params = []
        for idx, leg in enumerate(legs):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setStyleSheet("QFrame { border: 1px solid #30363d; border-radius: 4px; padding: 4px; margin: 2px; }")
            row = QHBoxLayout(frame)
            row.setContentsMargins(4, 2, 4, 2)

            lbl = QLabel(f"Leg {idx+1}: {leg['type'].title()} ({'+' if leg['sign'] > 0 else '-'})")
            row.addWidget(lbl)

            row.addWidget(QLabel("Strike:"))
            strike_spin = QDoubleSpinBox()
            strike_spin.setRange(1, 100000)
            strike_spin.setValue(500 + (idx - len(legs)//2) * 10)
            strike_spin.setPrefix("$")
            row.addWidget(strike_spin)

            row.addWidget(QLabel("Premium:"))
            prem_spin = QDoubleSpinBox()
            prem_spin.setRange(0, 100000)
            prem_spin.setValue(10)
            prem_spin.setPrefix("$")
            row.addWidget(prem_spin)

            row.addWidget(QLabel("Qty:"))
            qty_spin = QSpinBox()
            qty_spin.setRange(1, 1000)
            qty_spin.setValue(1)
            row.addWidget(qty_spin)

            row.addStretch()
            self.legs_layout.addWidget(frame)
            self._leg_params.append({
                "type": leg["type"],
                "sign": leg["sign"],
                "strike": strike_spin,
                "premium": prem_spin,
                "qty": qty_spin,
            })

    def _on_strategy_change(self, name: str):
        self._build_legs_ui(name)

    def _get_legs(self):
        result = []
        for p in self._leg_params:
            result.append({
                "type": p["type"],
                "sign": p["sign"],
                "strike": p["strike"].value(),
                "premium": p["premium"].value(),
                "qty": p["qty"].value(),
            })
        return result

    def _compute_payoff(self, legs, spot_range) -> np.ndarray:
        payoff = np.zeros_like(spot_range)
        for leg in legs:
            S = spot_range
            if leg["type"] == "stock":
                leg_pnl = (S - leg["strike"]) * leg["sign"]
            elif leg["type"] == "call":
                intrinsic = np.maximum(S - leg["strike"], 0)
                leg_pnl = (intrinsic - leg["premium"]) * leg["sign"]
            elif leg["type"] == "put":
                intrinsic = np.maximum(leg["strike"] - S, 0)
                leg_pnl = (intrinsic - leg["premium"]) * leg["sign"]
            payoff += leg_pnl * leg["qty"]
        return payoff

    def _plot_payoff(self):
        legs = self._get_legs()
        spot = self.spot_input.value()
        rng = max(spot * 0.5, 50)
        spot_range = np.linspace(spot - rng, spot + rng, 200)
        payoff = self._compute_payoff(legs, spot_range)

        self.payoff_plot.clear()
        self.payoff_plot.plot(spot_range, payoff, pen=pg.mkPen(color=(31, 111, 235), width=2))
        zero_line = np.zeros_like(spot_range)
        self.payoff_plot.plot(spot_range, zero_line, pen=pg.mkPen(color=(100, 100, 100), width=1, style=Qt.PenStyle.DashLine))
        self.payoff_plot.addLine(x=spot, pen=pg.mkPen(color=(255, 165, 0), width=1, style=Qt.PenStyle.DotLine))

        max_p = payoff.max()
        min_p = payoff.min()
        be_points = []
        for i in range(1, len(payoff)):
            if payoff[i-1] * payoff[i] < 0:
                be = spot_range[i-1] - payoff[i-1] * (spot_range[i] - spot_range[i-1]) / (payoff[i] - payoff[i-1])
                be_points.append(be)
            elif abs(payoff[i]) < 0.01:
                be_points.append(spot_range[i])

        self.max_profit_label.setText(f"Max Profit: ${max_p:+,.2f}" if max_p > 0 else "Max Profit: Unlimited")
        self.max_loss_label.setText(f"Max Loss: ${min_p:+,.2f}" if min_p < 0 else "Max Loss: Unlimited")
        be_str = ", ".join(f"${b:,.2f}" for b in sorted(set(round(b, 2) for b in be_points))) if be_points else "--"
        self.be_label.setText(f"Breakeven: {be_str}")


class OptionsPanel(QWidget):
    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self.symbol = "AAPL"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #30363d; }
            QTabBar::tab { background: #21262d; color: #8b949e; padding: 6px 16px; border: 1px solid #30363d; border-bottom: none; }
            QTabBar::tab:selected { background: #0d1117; color: #e6edf3; }
        """)

        self._build_chain_tab()
        self._build_strategy_tab()
        layout.addWidget(self.tabs)

    def _build_chain_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Symbol:"))
        self.sym_label = QLabel("AAPL")
        self.sym_label.setStyleSheet("font-weight: bold;")
        controls.addWidget(self.sym_label)

        self.expiry_combo = QComboBox()
        controls.addWidget(self.expiry_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_chain)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.chain_table = QTableWidget()
        self.chain_table.setColumnCount(9)
        self.chain_table.setHorizontalHeaderLabels(
            ["Strike", "Type", "Bid", "Ask", "Last", "Vol", "OI", "IV", "Delta"])
        self.chain_table.horizontalHeader().setStretchLastSection(True)
        self.chain_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.chain_table.verticalHeader().setVisible(False)
        layout.addWidget(self.chain_table)

        self.greeks_group = QGroupBox("Greeks")
        g_layout = QGridLayout(self.greeks_group)
        self.greeks_labels = {}
        for i, g in enumerate(["Delta", "Gamma", "Theta", "Vega", "Rho"]):
            lbl = QLabel(f"{g}: --")
            lbl.setStyleSheet("font-size: 13px;")
            self.greeks_labels[g] = lbl
            g_layout.addWidget(lbl, i // 3, i % 3)
        layout.addWidget(self.greeks_group)

        self.tabs.addTab(tab, "Chain")

    def _build_strategy_tab(self):
        self.strategy_builder = StrategyBuilderWidget()
        self.tabs.addTab(self.strategy_builder, "Strategy")

    def _load_chain(self):
        self.chain_table.setRowCount(0)
        try:
            import yfinance as yf
            tk = yf.Ticker(self.symbol)
            expirations = tk.options
            if not expirations:
                return
            self.expiry_combo.clear()
            self.expiry_combo.addItems(expirations[:5])
            expiry = expirations[0]

            opt_chain = tk.option_chain(expiry)
            calls = opt_chain.calls
            puts = opt_chain.puts

            self.chain_table.setRowCount(len(calls) + len(puts))
            row = 0
            for _, opt in calls.iterrows():
                self._add_option_row(row, opt, "CALL", expiry)
                row += 1
            for _, opt in puts.iterrows():
                self._add_option_row(row, opt, "PUT", expiry)
                row += 1
        except Exception as e:
            pass

    def _add_option_row(self, row: int, opt, opt_type: str, expiry: str):
        strike = opt["strike"]
        bid = opt.get("bid", 0)
        ask = opt.get("ask", 0)
        last = opt.get("lastPrice", 0)
        vol = opt.get("volume", 0)
        oi = opt.get("openInterest", 0)
        iv = opt.get("impliedVolatility", 0)

        quote = self.data.get_quote(self.symbol)
        S = quote.price if quote else 150
        T = max((pd.to_datetime(expiry) - pd.Timestamp.now()).days / 365, 0.01)
        try:
            delta = self._calc_greeks(S, strike, T, 0.05, iv, opt_type, "delta") if iv > 0 else 0
        except:
            delta = 0

        self.chain_table.setItem(row, 0, QTableWidgetItem(f"${strike:.2f}"))
        type_item = QTableWidgetItem(opt_type)
        type_item.setForeground(color_for_change(1 if opt_type == "CALL" else -1))
        self.chain_table.setItem(row, 1, type_item)
        self.chain_table.setItem(row, 2, QTableWidgetItem(f"${bid:.2f}" if bid else "--"))
        self.chain_table.setItem(row, 3, QTableWidgetItem(f"${ask:.2f}" if ask else "--"))
        self.chain_table.setItem(row, 4, QTableWidgetItem(f"${last:.2f}" if last else "--"))
        self.chain_table.setItem(row, 5, QTableWidgetItem(str(vol) if vol else "0"))
        self.chain_table.setItem(row, 6, QTableWidgetItem(str(oi) if oi else "0"))
        self.chain_table.setItem(row, 7, QTableWidgetItem(f"{iv*100:.1f}%" if iv else "--"))
        self.chain_table.setItem(row, 8, QTableWidgetItem(f"{delta:.3f}" if delta else "--"))

    def _calc_greeks(self, S, K, T, r, sigma, opt_type, greek):
        flag = "c" if opt_type == "CALL" else "p"
        price = black_scholes(flag, S, K, T, r, sigma)
        if greek == "delta":
            dS = S * 0.001
            price_up = black_scholes(flag, S + dS, K, T, r, sigma)
            return (price_up - price) / dS
        return 0


import pandas as pd
