from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGridLayout, QFrame, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.services.data_service import DataService
from src.ui.theme import color_for_change, TEXT_SECONDARY, BG_PANEL, BORDER_COLOR


class MarketOverviewPanel(QWidget):
    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Market Overview")
        title.setProperty("heading", True)
        layout.addWidget(title)

        self.indices_widget = QWidget()
        self.indices_layout = QGridLayout(self.indices_widget)
        self.indices_layout.setSpacing(6)
        layout.addWidget(self.indices_widget)

        layout.addWidget(QLabel(""))

        movers_title = QLabel("Top Movers")
        movers_title.setProperty("heading", True)
        layout.addWidget(movers_title)

        self.movers_scroll = QScrollArea()
        self.movers_scroll.setWidgetResizable(True)
        self.movers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.movers_scroll.setMaximumHeight(250)

        self.movers_widget = QWidget()
        self.movers_layout = QVBoxLayout(self.movers_widget)
        self.movers_scroll.setWidget(self.movers_widget)
        layout.addWidget(self.movers_scroll)
        layout.addStretch()

    def _refresh(self):
        indices = self.data.get_market_indices()
        row = 0
        for name, data in indices.items():
            frame = QFrame()
            frame.setStyleSheet(f"background-color: {BG_PANEL.name()}; border: 1px solid {BORDER_COLOR.name()}; border-radius: 4px; padding: 6px;")
            fl = QVBoxLayout(frame)
            fl.setSpacing(2)
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-size: 11px;")
            fl.addWidget(name_lbl)

            price_lbl = QLabel(f"${data['price']:.2f}")
            price_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #e6edf3;")
            fl.addWidget(price_lbl)

            chg = data["change"]
            chg_lbl = QLabel(f"{chg:+.2f} ({data['change_pct']:+.2f}%)")
            clr = color_for_change(chg)
            chg_lbl.setStyleSheet(f"font-size: 12px; color: {clr.name()};")
            fl.addWidget(chg_lbl)

            self.indices_layout.addWidget(frame, row // 3, row % 3)
            row += 1

        self._load_movers()

    def _load_movers(self):
        for i in reversed(range(self.movers_layout.count())):
            w = self.movers_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        quotes = self.data.get_top_movers()
        for q in quotes:
            frame = QFrame()
            frame.setStyleSheet(f"background-color: {BG_PANEL.name()}; border: 1px solid {BORDER_COLOR.name()}; border-radius: 4px; padding: 4px 8px;")
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(8, 4, 8, 4)

            sym_lbl = QLabel(q.symbol)
            sym_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
            fl.addWidget(sym_lbl)

            price_lbl = QLabel(f"${q.price:.2f}")
            price_lbl.setStyleSheet("font-size: 13px;")
            fl.addWidget(price_lbl)

            fl.addStretch()

            chg_lbl = QLabel(f"{q.change_pct:+.2f}%")
            chg_lbl.setStyleSheet(f"color: {color_for_change(q.change_pct).name()}; font-weight: bold;")
            fl.addWidget(chg_lbl)

            vol_lbl = QLabel(f"Vol: {q.volume/1e6:.1f}M")
            vol_lbl.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-size: 11px;")
            fl.addWidget(vol_lbl)

            self.movers_layout.addWidget(frame)
