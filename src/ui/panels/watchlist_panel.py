from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLineEdit, QLabel,
                             QHeaderView, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QAction
from src.core.config import Config
from src.services.data_service import DataService
from src.ui.theme import color_for_change, TEXT_SECONDARY


class WatchlistPanel(QWidget):
    symbol_selected = pyqtSignal(str)

    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self.config = Config()
        self.symbols = self.config.get("watchlists", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"])
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        title = QLabel("Watchlist")
        title.setProperty("heading", True)
        header.addWidget(title)
        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Add symbol...")
        self.search_input.returnPressed.connect(self._add_symbol)
        self.search_input.setMaximumWidth(140)
        header.addWidget(self.search_input)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.clicked.connect(self._add_symbol)
        header.addWidget(add_btn)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Symbol", "Price", "Chg", "Chg%", "Vol"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.table)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(self.config.get("refresh_interval", 60) * 1000)

    def _add_symbol(self):
        symbol = self.search_input.text().strip().upper()
        if symbol and symbol not in self.symbols:
            self.symbols.append(symbol)
            self.config.set("watchlists", self.symbols)
            self._refresh()
        self.search_input.clear()

    def _on_double_click(self, row, col):
        item = self.table.item(row, 0)
        if item:
            self.symbol_selected.emit(item.text())

    def _on_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = self.table.row(item)
        sym_item = self.table.item(row, 0)
        if not sym_item:
            return
        symbol = sym_item.text()
        menu = QMenu(self)
        chart_action = menu.addAction(f"Chart {symbol}")
        remove_action = menu.addAction(f"Remove {symbol}")
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == chart_action:
            self.symbol_selected.emit(symbol)
        elif action == remove_action:
            if symbol in self.symbols:
                self.symbols.remove(symbol)
                self.config.set("watchlists", self.symbols)
                self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self.symbols))
        for i, sym in enumerate(self.symbols):
            quote = self.data.get_quote(sym)
            self.table.setItem(i, 0, QTableWidgetItem(sym))
            if quote:
                self.table.setItem(i, 1, QTableWidgetItem(f"${quote.price:.2f}"))
                chg_item = QTableWidgetItem(f"{quote.change:+.2f}")
                chg_item.setForeground(color_for_change(quote.change))
                self.table.setItem(i, 2, chg_item)
                pct_item = QTableWidgetItem(f"{quote.change_pct:+.2f}%")
                pct_item.setForeground(color_for_change(quote.change_pct))
                self.table.setItem(i, 3, pct_item)
                vol_str = f"{quote.volume/1e6:.1f}M" if quote.volume > 1e6 else str(quote.volume)
                self.table.setItem(i, 4, QTableWidgetItem(vol_str))
            else:
                for j in range(1, 5):
                    self.table.setItem(i, j, QTableWidgetItem("--"))
