import pyqtgraph as pg
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from src.core.constants import Timeframe, ChartType, INDICATORS
from src.ui.theme import BG_DARK, POSITIVE_GREEN, NEGATIVE_RED, TEXT_PRIMARY, TEXT_SECONDARY


pg.setConfigOptions(antialias=True, useOpenGL=True)
pg.setConfigOption("background", BG_DARK.getRgb())
pg.setConfigOption("foreground", (200, 200, 200))


class ChartWidget(QWidget):
    symbol_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.symbol = "AAPL"
        self.timeframe = Timeframe.DAY_1
        self.chart_type = ChartType.CANDLESTICK
        self.df: pd.DataFrame = None
        self._indicators = {}
        self._plots = {}
        self._setup_ui()
        self._setup_plot()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)

        self.symbol_label = QLabel("AAPL")
        self.symbol_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e6edf3;")
        toolbar.addWidget(self.symbol_label)

        self.interval_combo = QComboBox()
        for tf in Timeframe:
            self.interval_combo.addItem(tf.value, tf)
        self.interval_combo.setCurrentIndex(4)
        self.interval_combo.currentIndexChanged.connect(self._on_timeframe_change)
        toolbar.addWidget(self.interval_combo)

        self.chart_type_combo = QComboBox()
        for ct in ChartType:
            self.chart_type_combo.addItem(ct.value.replace("_", " ").title(), ct)
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_change)
        toolbar.addWidget(self.chart_type_combo)

        toolbar.addStretch()

        self.indicator_combo = QComboBox()
        self.indicator_combo.addItem("Add Indicator...", None)
        for key, val in INDICATORS.items():
            self.indicator_combo.addItem(val["name"], key)
        self.indicator_combo.currentIndexChanged.connect(self._on_add_indicator)
        toolbar.addWidget(self.indicator_combo)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_indicators)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)
        self.plot_container = QVBoxLayout()
        layout.addLayout(self.plot_container)

    def _setup_plot(self):
        self.main_plot = pg.PlotWidget()
        self.main_plot.showGrid(x=False, y=True, alpha=0.3)
        self.main_plot.setLabel("left", "Price")
        self.main_plot.setMouseEnabled(x=True, y=True)
        self.main_plot.enableAutoRange(enable=True)
        self.main_plot.setMenuEnabled(False)

        self.volume_plot = pg.PlotWidget()
        self.volume_plot.showGrid(x=False, y=True, alpha=0.3)
        self.volume_plot.setLabel("left", "Volume")
        self.volume_plot.setMaximumHeight(80)
        self.volume_plot.setMouseEnabled(x=True, y=False)
        self.volume_plot.setMenuEnabled(False)
        self.volume_plot.setXLink(self.main_plot)

        self.plot_container.addWidget(self.main_plot)
        self.plot_container.addWidget(self.volume_plot)

    def set_data(self, df: pd.DataFrame):
        self.df = df
        self._render()

    def _render(self):
        if self.df is None or self.df.empty:
            return
        self.main_plot.clear()
        self.volume_plot.clear()
        self._plots.clear()

        df = self.df.copy()
        if "datetime" in df.columns:
            dates = pd.to_datetime(df["datetime"])
        else:
            dates = pd.to_datetime(df.index) if not df.index.name == "Date" else pd.to_datetime(df.index)
        x = np.arange(len(df))

        if self.chart_type == ChartType.CANDLESTICK:
            self._draw_candlesticks(x, df)
        elif self.chart_type == ChartType.LINE:
            line = self.main_plot.plot(x, df["close"], pen=pg.mkPen(color=(31, 111, 235), width=2))
            self._plots["price"] = line
        elif self.chart_type == ChartType.HEIKIN_ASHI:
            ha = TechnicalService.heikin_ashi(df)
            self._draw_candlesticks(x, ha)

        self._draw_volume(x, df)
        self._draw_indicators(x)
        self._setup_axes(x, dates)

    def _draw_candlesticks(self, x, df):
        ohlc = np.column_stack([
            x, df["open"], df["high"], df["low"], df["close"]
        ])
        for i in range(len(ohlc)):
            xi, o, h, l, c = ohlc[i]
            color = POSITIVE_GREEN.getRgb()[:3] if c >= o else NEGATIVE_RED.getRgb()[:3]
            self.main_plot.plot([xi, xi], [l, h], pen=pg.mkPen(color=color, width=1))
            if c >= o:
                rect = pg.QtWidgets.QGraphicsRectItem(xi - 0.3, o, 0.6, c - o)
            else:
                rect = pg.QtWidgets.QGraphicsRectItem(xi - 0.3, c, 0.6, o - c)
            rect.setBrush(pg.mkBrush(color))
            rect.setPen(pg.mkPen(color=color, width=0))
            self.main_plot.addItem(rect)

    def _draw_volume(self, x, df):
        for i in range(len(df)):
            xi = x[i]
            vol = df["volume"].iloc[i]
            c_val = df["close"].iloc[i]
            o_val = df["open"].iloc[i]
            color = POSITIVE_GREEN.getRgb()[:3] if c_val >= o_val else NEGATIVE_RED.getRgb()[:3]
            bar = pg.BarGraphItem(x=[xi], height=[vol], width=0.8, brush=color, pen=color)
            self.volume_plot.addItem(bar)

    def _draw_indicators(self, x):
        for name, data in self._indicators.items():
            if isinstance(data, tuple):
                for i, d in enumerate(data):
                    color = [(31, 111, 235), (255, 165, 0), (100, 100, 100)][i % 3]
                    self.main_plot.plot(x, d.values, pen=pg.mkPen(color=color, width=1))
            elif name == "bbands":
                upper, middle, lower = data
                self.main_plot.plot(x, upper, pen=pg.mkPen(color=(100, 100, 100), width=1))
                self.main_plot.plot(x, middle, pen=pg.mkPen(color=(255, 165, 0), width=1.5))
                self.main_plot.plot(x, lower, pen=pg.mkPen(color=(100, 100, 100), width=1))
            else:
                self.main_plot.plot(x, data.values, pen=pg.mkPen(color=(31, 111, 235), width=1.5))

    def _setup_axes(self, x, dates):
        n = len(x)
        step = max(n // 8, 1)
        ticks = [(i, dates[i].strftime("%m/%d")) for i in range(0, n, step)]
        ax = self.main_plot.getAxis("bottom")
        ax.setTicks([ticks])
        ax.setStyle(tickFont=QFont("Segoe UI", 9))

    def _on_timeframe_change(self, idx):
        self.timeframe = self.interval_combo.itemData(idx)
        self.symbol_changed.emit(self.symbol)

    def _on_chart_type_change(self, idx):
        self.chart_type = self.chart_type_combo.itemData(idx)
        self._render()

    def _on_add_indicator(self, idx):
        if idx == 0:
            return
        key = self.indicator_combo.itemData(idx)
        if key and self.df is not None:
            ts = TechnicalService()
            result = ts.compute_indicator(key, self.df)
            self._indicators[key] = result
            self._render()
        self.indicator_combo.setCurrentIndex(0)

    def _clear_indicators(self):
        self._indicators.clear()
        self._render()

    def set_symbol(self, symbol: str):
        self.symbol = symbol.upper()
        self.symbol_label.setText(self.symbol)


from src.services.technical_service import TechnicalService
