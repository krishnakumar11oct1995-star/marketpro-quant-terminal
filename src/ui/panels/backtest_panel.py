from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QComboBox, QSpinBox, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from src.ui.theme import TEXT_SECONDARY, color_for_change


class BacktestWorker(QThread):
    progress = pyqtSignal(str)
    result = pyqtSignal(dict)

    def __init__(self, symbol: str, strategy: str, initial_capital: float, params: dict):
        super().__init__()
        self.symbol = symbol
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.params = params

    def run(self):
        self.progress.emit(f"Loading {self.symbol} data...")
        tk = yf.Ticker(self.symbol)
        df = tk.history(period="2y")
        if df.empty:
            self.result.emit({"error": "No data"})
            return

        df["SMA_20"] = df["Close"].rolling(20).mean()
        df["SMA_50"] = df["Close"].rolling(50).mean()
        df["RSI"] = self._rsi(df["Close"])
        df["Signal"] = 0

        if self.strategy == "SMA Crossover":
            df.loc[df["SMA_20"] > df["SMA_50"], "Signal"] = 1
            df.loc[df["SMA_20"] <= df["SMA_50"], "Signal"] = -1
        elif self.strategy == "RSI Mean Reversion":
            df.loc[df["RSI"] < 30, "Signal"] = 1
            df.loc[df["RSI"] > 70, "Signal"] = -1
        elif self.strategy == "Buy & Hold":
            df["Signal"] = 1

        position = 0
        cash = self.initial_capital
        trades = []
        for i in range(1, len(df)):
            price = df["Close"].iloc[i]
            signal = df["Signal"].iloc[i]
            if signal == 1 and position == 0:
                position = cash / price
                cash = 0
                trades.append({"date": df.index[i], "type": "BUY", "price": price})
            elif signal == -1 and position > 0:
                cash = position * price
                position = 0
                trades.append({"date": df.index[i], "type": "SELL", "price": price})

        if position > 0:
            cash = position * df["Close"].iloc[-1]
            position = 0

        total_return = ((cash - self.initial_capital) / self.initial_capital) * 100
        df["Returns"] = df["Close"].pct_change()
        sharpe = np.sqrt(252) * df["Returns"].mean() / df["Returns"].std() if df["Returns"].std() > 0 else 0
        max_dd = ((df["Close"] / df["Close"].cummax()) - 1).min() * 100

        self.progress.emit("Backtest complete!")
        self.result.emit({
            "symbol": self.symbol,
            "strategy": self.strategy,
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "num_trades": len([t for t in trades if t["type"] == "BUY"]),
            "final_capital": cash,
            "trades": trades
        })

    def _rsi(self, series, period=14):
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 0.001)
        return 100 - (100 / (1 + rs))


class BacktestPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Backtesting Engine")
        title.setProperty("heading", True)
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Symbol:"))
        self.symbol_input = QLabel("AAPL")
        controls.addWidget(self.symbol_input)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["SMA Crossover", "RSI Mean Reversion", "Buy & Hold"])
        controls.addWidget(self.strategy_combo)

        controls.addWidget(QLabel("Capital:"))
        self.capital_input = QSpinBox()
        self.capital_input.setRange(1000, 10000000)
        self.capital_input.setValue(10000)
        self.capital_input.setPrefix("$")
        controls.addWidget(self.capital_input)

        self.run_btn = QPushButton("Run Backtest")
        self.run_btn.clicked.connect(self._run_backtest)
        controls.addWidget(self.run_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        splitter.addWidget(self.results_table)

        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(3)
        self.trades_table.setHorizontalHeaderLabels(["Date", "Type", "Price"])
        self.trades_table.horizontalHeader().setStretchLastSection(True)
        self.trades_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.trades_table.verticalHeader().setVisible(False)
        splitter.addWidget(self.trades_table)
        layout.addWidget(splitter)

    def _run_backtest(self):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        self.status_label.setText("Running backtest...")

        self.worker = BacktestWorker(
            self.symbol_input.text(),
            self.strategy_combo.currentText(),
            self.capital_input.value(),
            {}
        )
        self.worker.progress.connect(self.status_label.setText)
        self.worker.result.connect(self._on_result)
        self.worker.start()

    def _on_result(self, result: dict):
        if "error" in result:
            self.status_label.setText(f"Error: {result['error']}")
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Run Backtest")
            return

        metrics = [
            ("Symbol", result["symbol"]),
            ("Strategy", result["strategy"]),
            ("Total Return", f"{result['total_return']:+.2f}%"),
            ("Sharpe Ratio", f"{result['sharpe']:.2f}"),
            ("Max Drawdown", f"{result['max_drawdown']:.2f}%"),
            ("Final Capital", f"${result['final_capital']:,.2f}"),
            ("Num Trades", str(result["num_trades"])),
        ]
        self.results_table.setRowCount(len(metrics))
        for i, (k, v) in enumerate(metrics):
            self.results_table.setItem(i, 0, QTableWidgetItem(k))
            item = QTableWidgetItem(str(v))
            if "Return" in k or "Drawdown" in k:
                item.setForeground(color_for_change(result["total_return"]))
            self.results_table.setItem(i, 1, item)

        trades = result.get("trades", [])
        self.trades_table.setRowCount(len(trades))
        for i, t in enumerate(trades):
            self.trades_table.setItem(i, 0, QTableWidgetItem(str(t["date"]).split()[0]))
            type_item = QTableWidgetItem(t["type"])
            type_item.setForeground(color_for_change(1 if t["type"] == "BUY" else -1))
            self.trades_table.setItem(i, 1, type_item)
            self.trades_table.setItem(i, 2, QTableWidgetItem(f"${t['price']:.2f}"))

        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Backtest")
        self.status_label.setText(f"Backtest complete - {result['total_return']:+.2f}% return")
