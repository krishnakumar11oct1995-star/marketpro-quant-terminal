import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("yfinance").disabled = True

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.main_window import MainWindow
from src.ui.theme import setup_dark_palette, DARK_THEME_STYLESHEET
from src.core.logger import Logger
from src.core.config import Config


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NVIDIA Financial Terminal")
    app.setOrganizationName("NVIDIA-Finance")
    app.setStyle("Fusion")

    setup_dark_palette(app)
    app.setStyleSheet(DARK_THEME_STYLESHEET)

    log = Logger()
    log.info("Starting NVIDIA Financial Terminal...")

    config = Config()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
