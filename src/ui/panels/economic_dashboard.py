from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QGridLayout, QFrame, QGroupBox)
from PyQt6.QtCore import Qt, QTimer
import yfinance as yf
import pandas as pd
from datetime import datetime
from src.ui.theme import color_for_change, TEXT_SECONDARY, BG_PANEL, BORDER_COLOR, POSITIVE_GREEN, NEGATIVE_RED


class EconomicDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Economic & Macro Dashboard")
        title.setProperty("heading", True)
        layout.addWidget(title)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        layout.addLayout(self.grid)

        self.status_label = QLabel("Loading economic data...")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3600000)

    def _refresh(self):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        data = self._fetch_econ_data()
        row = 0
        for category, items in data.items():
            cat_label = QLabel(category)
            cat_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f6feb; margin-top: 8px;")
            self.grid.addWidget(cat_label, row, 0, 1, 4)
            row += 1

            for name, value, change in items:
                card = QFrame()
                card.setStyleSheet(f"background-color: {BG_PANEL.name()}; border: 1px solid {BORDER_COLOR.name()}; border-radius: 6px; padding: 8px;")
                cl = QVBoxLayout(card)
                cl.setSpacing(2)
                lbl_name = QLabel(name)
                lbl_name.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; font-size: 11px;")
                cl.addWidget(lbl_name)
                lbl_val = QLabel(str(value))
                lbl_val.setStyleSheet("font-size: 16px; font-weight: bold; color: #e6edf3;")
                cl.addWidget(lbl_val)
                if change:
                    lbl_chg = QLabel(change)
                    clr = POSITIVE_GREEN if "+" in change else NEGATIVE_RED if "-" in change else TEXT_SECONDARY
                    lbl_chg.setStyleSheet(f"font-size: 11px; color: {clr.name()};")
                    cl.addWidget(lbl_chg)
                self.grid.addWidget(card, row, len(items) % 4)
                if (len(items) % 4) == 3:
                    row += 1
            row += 1

        self.status_label.setText(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    def _fetch_econ_data(self) -> dict:
        data = {}
        try:
            sp500 = yf.Ticker("^GSPC")
            sp_hist = sp500.history(period="5d")
            sp_chg = ((sp_hist["Close"].iloc[-1] - sp_hist["Close"].iloc[0]) / sp_hist["Close"].iloc[0]) * 100 if len(sp_hist) > 1 else 0
            data["US Indices"] = [
                ("S&P 500", f"${sp_hist['Close'].iloc[-1]:.2f}" if not sp_hist.empty else "N/A",
                 f"{sp_chg:+.2f}%" if sp_chg else None),
            ]

            dxy = yf.Ticker("DX-Y.NYB")
            dxy_hist = dxy.history(period="5d")
            dxy_chg = ((dxy_hist["Close"].iloc[-1] - dxy_hist["Close"].iloc[0]) / dxy_hist["Close"].iloc[0]) * 100 if len(dxy_hist) > 1 else 0
            data["FX & Commodities"] = [
                ("DXY Index", f"${dxy_hist['Close'].iloc[-1]:.2f}" if not dxy_hist.empty else "N/A",
                 f"{dxy_chg:+.2f}%" if dxy_chg else None),
            ]

            try:
                oil = yf.Ticker("CL=F")
                oil_hist = oil.history(period="2d")
                if not oil_hist.empty:
                    data["FX & Commodities"].append(
                        ("Crude Oil", f"${oil_hist['Close'].iloc[-1]:.2f}", None))
            except:
                pass

            try:
                gold = yf.Ticker("GC=F")
                gold_hist = gold.history(period="2d")
                if not gold_hist.empty:
                    data["FX & Commodities"].append(
                        ("Gold", f"${gold_hist['Close'].iloc[-1]:.2f}", None))
            except:
                pass

            try:
                tnx = yf.Ticker("^TNX")
                tnx_hist = tnx.history(period="5d")
                tnx_chg = tnx_hist["Close"].iloc[-1] - tnx_hist["Close"].iloc[0] if len(tnx_hist) > 1 else 0
                data["Rates"] = [
                    ("10Y Treasury", f"{tnx_hist['Close'].iloc[-1]:.2f}%" if not tnx_hist.empty else "N/A",
                     f"{tnx_chg:+.2f}bp" if tnx_chg else None),
                ]
            except:
                pass

            try:
                vix = yf.Ticker("^VIX")
                vix_hist = vix.history(period="5d")
                vix_chg = vix_hist["Close"].iloc[-1] - vix_hist["Close"].iloc[0] if len(vix_hist) > 1 else 0
                if "Rates" not in data:
                    data["Rates"] = []
                data["Rates"].append(
                    ("VIX", f"{vix_hist['Close'].iloc[-1]:.2f}",
                     f"{vix_chg:+.2f}" if vix_chg else None))
            except:
                pass

        except Exception as e:
            self.status_label.setText(f"Error: {e}")

        return data
