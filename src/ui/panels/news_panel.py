from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QTextBrowser, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import feedparser
import requests
from datetime import datetime, timedelta
from src.ui.theme import TEXT_SECONDARY, BG_PANEL


class NewsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load_news()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        title = QLabel("News & Sentiment")
        title.setProperty("heading", True)
        header.addWidget(title)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["All", "Yahoo Finance", "MarketWatch", "Seeking Alpha", "Benzinga"])
        self.source_combo.currentIndexChanged.connect(self._load_news)
        header.addWidget(self.source_combo)
        header.addStretch()
        layout.addLayout(header)

        self.news_browser = QTextBrowser()
        self.news_browser.setOpenExternalLinks(True)
        self.news_browser.setStyleSheet(
            "background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px; padding: 8px;")
        layout.addWidget(self.news_browser)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_news)
        self._timer.start(300000)

    def _load_news(self):
        try:
            feeds = [
                ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance"),
                ("https://feeds.marketwatch.com/marketwatch/topstories", "MarketWatch"),
                ("https://seekingalpha.com/feed.xml", "Seeking Alpha"),
            ]
            source_filter = self.source_combo.currentText()

            html = "<div style='font-family: Segoe UI;'>"
            count = 0
            for url, source in feeds:
                if source_filter != "All" and source_filter != source:
                    continue
                try:
                    feed = feedparser.parse(url)
                    html += f"<h3 style='color:#1f6feb; margin-top:16px;'>{source}</h3>"
                    for entry in feed.entries[:5]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        summary = entry.get("summary", "")[:200]
                        html += f"""
                        <div style='padding:8px; margin:4px 0; border:1px solid #21262d; border-radius:4px;'>
                            <a href='{link}' style='color:#e6edf3; font-size:13px; text-decoration:none;'>{title}</a>
                            <div style='color:#8b949e; font-size:11px;'>{published}</div>
                            <div style='color:#c9d1d9; font-size:12px; margin-top:4px;'>{summary}...</div>
                        </div>
                        """
                        count += 1
                except:
                    continue
            html += "</div>"
            self.news_browser.setHtml(html)

            if count == 0:
                self.news_browser.setHtml(
                    "<div style='color:#8b949e; text-align:center; padding:40px;'>"
                    "News feeds temporarily unavailable. Retrying in 5 minutes.</div>")
        except Exception as e:
            self.news_browser.setHtml(
                f"<div style='color:#f85149; padding:20px;'>Error loading news: {e}</div>")
