from PyQt6.QtGui import QPalette, QColor, QFont


DARK_THEME_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
}
QDockWidget {
    background-color: #161b22;
    color: #c9d1d9;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}
QDockWidget::title {
    background-color: #21262d;
    padding: 6px 12px;
    border-bottom: 1px solid #30363d;
}
QMenuBar {
    background-color: #161b22;
    color: #c9d1d9;
    border-bottom: 1px solid #30363d;
}
QMenuBar::item:selected {
    background-color: #1f6feb;
}
QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
}
QMenu::item:selected {
    background-color: #1f6feb;
}
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
}
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    padding: 6px 16px;
    border-radius: 4px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}
QPushButton:pressed {
    background-color: #1f6feb;
}
QPushButton#primary {
    background-color: #1f6feb;
    border-color: #1f6feb;
    color: #ffffff;
}
QPushButton#primary:hover {
    background-color: #388bfd;
}
QLineEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #1f6feb;
}
QComboBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    padding: 4px 8px;
    border-radius: 4px;
}
QComboBox:hover {
    border-color: #8b949e;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
    border: 1px solid #30363d;
}
QTableWidget, QTreeWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    gridline-color: #21262d;
    font-size: 12px;
}
QTableWidget::item, QTreeWidget::item {
    padding: 4px 8px;
}
QTableWidget::item:selected, QTreeWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 6px;
    border: 1px solid #21262d;
    font-weight: bold;
    font-size: 11px;
}
QScrollBar:vertical {
    background-color: #0d1117;
    width: 12px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QSplitter::handle {
    background-color: #21262d;
    width: 2px;
}
QLabel {
    color: #c9d1d9;
}
QLabel[heading="true"] {
    font-size: 16px;
    font-weight: bold;
    color: #e6edf3;
}
QLabel[positive="true"] { color: #3fb950; }
QLabel[negative="true"] { color: #f85149; }
QTabWidget::pane {
    background-color: #0d1117;
    border: 1px solid #30363d;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 16px;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #e6edf3;
    border-bottom: 2px solid #1f6feb;
}
QTabBar::tab:hover:!selected {
    background-color: #21262d;
}
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 4px;
}
QToolTip {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    padding: 4px 8px;
}
"""


def setup_dark_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(13, 17, 23))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(201, 209, 217))
    palette.setColor(QPalette.ColorRole.Base, QColor(22, 27, 34))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(13, 17, 23))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(33, 38, 45))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(201, 209, 217))
    palette.setColor(QPalette.ColorRole.Text, QColor(201, 209, 217))
    palette.setColor(QPalette.ColorRole.Button, QColor(33, 38, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(201, 209, 217))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(248, 81, 73))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(31, 111, 235))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


POSITIVE_GREEN = QColor(63, 185, 80)
NEGATIVE_RED = QColor(248, 81, 73)
NEUTRAL_GRAY = QColor(139, 148, 158)
BLUE_ACCENT = QColor(31, 111, 235)
BG_DARK = QColor(13, 17, 23)
BG_PANEL = QColor(22, 27, 34)
BG_INPUT = QColor(13, 17, 23)
BORDER_COLOR = QColor(48, 54, 61)
TEXT_PRIMARY = QColor(230, 237, 243)
TEXT_SECONDARY = QColor(139, 148, 158)


def color_for_change(value: float):
    if value > 0: return POSITIVE_GREEN
    if value < 0: return NEGATIVE_RED
    return NEUTRAL_GRAY
