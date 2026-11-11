from PyQt6.QtWidgets import (QMainWindow, QStatusBar, QMenuBar, QMenu,
                             QDockWidget, QTabWidget, QMessageBox, QWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QLineEdit, QFrame, QToolBar)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QFont, QIcon
from src.ui.theme import DARK_THEME_STYLESHEET, TEXT_SECONDARY, TEXT_PRIMARY, BG_PANEL
from src.core.logger import Logger
from src.services.data_service import DataService
from src.core.config import Config
from src.ui.charting.chart_widget import ChartWidget
from src.ui.panels.watchlist_panel import WatchlistPanel
from src.ui.panels.market_overview import MarketOverviewPanel
from src.ui.panels.stock_detail import StockDetailPanel
from src.ui.panels.ai_chat_panel import AIChatPanel
from src.ui.panels.portfolio_panel import PortfolioPanel
from src.ui.panels.screener_panel import StockScreenerPanel
from src.ui.panels.news_panel import NewsPanel
from src.ui.panels.economic_dashboard import EconomicDashboard
from src.ui.panels.options_panel import OptionsPanel
from src.ui.panels.backtest_panel import BacktestPanel
from src.ui.panels.report_panel import ReportPanel
from src.ui.dialogs.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.log = Logger()
        self.data = DataService()
        self.config = Config()
        self._init_window()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()
        self._create_panels()
        self._setup_docking()
        self._load_initial_data()
        self._start_refresh_timer()

    def _init_window(self):
        self.setWindowTitle("NVIDIA Financial Terminal")
        self.setMinimumSize(1400, 900)
        self.resize(1800, 1100)

    def _create_menus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background: #161b22; color: #c9d1d9; border-bottom: 1px solid #30363d; padding: 2px; }
            QMenuBar::item { padding: 6px 12px; }
            QMenuBar::item:selected { background: #1f6feb; }
            QMenu { background: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
            QMenu::item:selected { background: #1f6feb; }
            QMenu::separator { background: #30363d; height: 1px; margin: 4px 8px; }
        """)

        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "New Watchlist", self._on_new_watchlist)
        self._add_action(file_menu, "Export Report", self._on_export)
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit", self.close, "Ctrl+Q")

        view_menu = menubar.addMenu("&View")
        self._add_action(view_menu, "Reset Layout", self._reset_layout)
        self._add_action(view_menu, "Full Screen", self._toggle_fullscreen, "F11")

        tools_menu = menubar.addMenu("&Tools")
        self._add_action(tools_menu, "Stock Screener", self._focus_screener)
        self._add_action(tools_menu, "Backtest", self._focus_backtest)
        self._add_action(tools_menu, "Settings", self._on_settings)

        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "About", self._on_about)

    def _add_action(self, menu, text, callback, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action

    def _create_toolbar(self):
        toolbar = QToolBar("Quick Actions")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setStyleSheet("""
            QToolBar { background: #161b22; border-bottom: 1px solid #30363d; spacing: 4px; padding: 4px; }
            QToolButton { padding: 6px 12px; color: #c9d1d9; border: none; border-radius: 4px; }
            QToolButton:hover { background: #21262d; }
        """)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search symbol (e.g. AAPL)...")
        self.search_input.setMaximumWidth(200)
        self.search_input.returnPressed.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        self.search_btn = QPushButton("Go")
        self.search_btn.setObjectName("primary")
        self.search_btn.clicked.connect(self._on_search)
        toolbar.addWidget(self.search_btn)

        toolbar.addSeparator()

        for text, callback in [("Charts", lambda: None), ("Screener", self._focus_screener),
                                ("AI", self._focus_ai), ("Portfolio", self._focus_portfolio),
                                ("Backtest", self._focus_backtest)]:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.clicked.connect(callback)
            toolbar.addWidget(btn)

        self.addToolBar(toolbar)

    def _create_status_bar(self):
        self.status = QStatusBar()
        self.status.setStyleSheet("""
            QStatusBar { background: #161b22; color: #8b949e; border-top: 1px solid #30363d; padding: 2px 8px; }
            QStatusBar::item { border: none; }
        """)
        self.status_label = QLabel("Ready")
        self.status.addWidget(self.status_label)
        self.data_status = QLabel("")
        self.status.addPermanentWidget(self.data_status)
        self.setStatusBar(self.status)

    def _create_panels(self):
        self.chart = ChartWidget()
        self.watchlist = WatchlistPanel(self.data)
        self.watchlist.symbol_selected.connect(self._load_symbol)
        self.market_overview = MarketOverviewPanel(self.data)
        self.stock_detail = StockDetailPanel(self.data)
        self.ai_chat = AIChatPanel(self.data)
        self.portfolio = PortfolioPanel(self.data)
        self.screener = StockScreenerPanel()
        self.news = NewsPanel()
        self.economic = EconomicDashboard()
        self.options = OptionsPanel(self.data)
        self.backtest = BacktestPanel()
        self.reports = ReportPanel(self.data)

    def _setup_docking(self):
        self._add_dock("Watchlist", self.watchlist, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("Market", self.market_overview, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("Chart", self.chart, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("Details", self.stock_detail, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("AI Analyst", self.ai_chat, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("Portfolio", self.portfolio, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("Screener", self.screener, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("News", self.news, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("Economics", self.economic, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("Options", self.options, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("Backtest", self.backtest, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("Reports", self.reports, Qt.DockWidgetArea.BottomDockWidgetArea)

        self.tabifyDockWidget(self._find_dock("Portfolio"), self._find_dock("Screener"))
        self.tabifyDockWidget(self._find_dock("Portfolio"), self._find_dock("Backtest"))
        self.tabifyDockWidget(self._find_dock("Portfolio"), self._find_dock("Reports"))
        self.tabifyDockWidget(self._find_dock("News"), self._find_dock("Economics"))
        self.tabifyDockWidget(self._find_dock("Chart"), self._find_dock("Details"))
        self.tabifyDockWidget(self._find_dock("Chart"), self._find_dock("Options"))

        self._find_dock("Watchlist").raise_()
        self._find_dock("Chart").raise_()
        self._find_dock("Portfolio").raise_()
        self._find_dock("News").raise_()

    def _add_dock(self, name, widget, area):
        dock = QDockWidget(name, self)
        dock.setWidget(widget)
        dock.setObjectName(f"dock_{name.lower().replace(' ', '_')}")
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setStyleSheet("""
            QDockWidget { background: #0d1117; color: #c9d1d9; }
            QDockWidget::title { background: #21262d; padding: 6px 12px;
                border-bottom: 1px solid #30363d; font-size: 12px; }
        """)
        self.addDockWidget(area, dock)
        return dock

    def _find_dock(self, name):
        key = f"dock_{name.lower().replace(' ', '_')}"
        for d in self.findChildren(QDockWidget):
            if d.objectName() == key:
                return d
        return None

    def _load_initial_data(self):
        self.status_label.setText("Loading market data...")

        df = self.data.get_historical("AAPL", period="6mo", interval="1d")
        if df is not None:
            self.chart.set_data(df)
            self.data_status.setText("AAPL · Live")
            self.status_label.setText("Ready")
        else:
            self.data_status.setText("Offline")
            self.status_label.setText("Data unavailable - check internet")

    def _start_refresh_timer(self):
        interval = self.config.get("refresh_interval", 60) * 1000
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start(interval)

    def _refresh_all(self):
        self.chart.symbol_changed.emit(self.chart.symbol)

    def _on_search(self):
        symbol = self.search_input.text().strip().upper()
        if not symbol:
            return
        self.search_input.clear()
        self._load_symbol(symbol)

    def _load_symbol(self, symbol: str):
        self.status_label.setText(f"Loading {symbol}...")
        self.chart.set_symbol(symbol)
        self.stock_detail.symbol = symbol
        self.stock_detail._refresh()

        df = self.data.get_historical(symbol, period="6mo", interval="1d")
        if df is not None:
            self.chart.set_data(df)
            self.data_status.setText(f"{symbol} · Live")
            self.status_label.setText(f"Showing {symbol}")

        quote = self.data.get_quote(symbol)
        if quote:
            self.setWindowTitle(f"NVIDIA Financial Terminal - {symbol} (${quote.price:.2f})")

    def _focus_screener(self):
        dock = self._find_dock("Screener")
        if dock:
            dock.raise_()
            dock.show()

    def _focus_ai(self):
        dock = self._find_dock("AI Analyst")
        if dock:
            dock.raise_()
            dock.show()

    def _focus_portfolio(self):
        dock = self._find_dock("Portfolio")
        if dock:
            dock.raise_()
            dock.show()

    def _focus_backtest(self):
        dock = self._find_dock("Backtest")
        if dock:
            dock.raise_()
            dock.show()

    def _on_new_watchlist(self):
        QMessageBox.information(self, "Watchlist",
                                "Right-click on Watchlist panel to manage symbols.")

    def _on_export(self):
        dock = self._find_dock("Reports")
        if dock:
            dock.raise_()
            dock.show()

    def _reset_layout(self):
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
        self._setup_docking()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _on_about(self):
        QMessageBox.about(self, "NVIDIA Financial Terminal",
                          "<h3>NVIDIA Financial Terminal v1.0</h3>"
                          "<p>GPU-accelerated financial analysis platform</p>"
                          "<p>Powered by <b>NVIDIA Nemotron AI</b></p>"
                          "<hr>"
                          "<p>Features:</p>"
                          "<ul>"
                          "<li>Real-time market data & charting</li>"
                          "<li>50+ technical indicators</li>"
                          "<li>Fundamental & ratio analysis</li>"
                          "<li>AI-powered agent analysis</li>"
                          "<li>Portfolio & risk management</li>"
                          "<li>Options chain & Greeks</li>"
                          "<li>Strategy backtesting</li>"
                          "<li>Economic & macro dashboard</li>"
                          "</ul>")

    def closeEvent(self, event):
        geo = self.saveGeometry()
        self.config.set("window_geometry", list(bytes(geo)))
        event.accept()
