from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QLabel, QComboBox, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from src.nvidia.nemotron_client import NemotronClient
from src.services.data_service import DataService


_AGENTS = {
    "General Analyst": {"desc": "A balanced financial analyst providing comprehensive market analysis with data-driven insights.", "short": "Analyst"},
    "Warren Buffett": {"desc": "Value investor focused on moats, competitive advantage, long-term holdings, and margin of safety.", "short": "Buffett"},
    "Ben Graham": {"desc": "Deep value investor seeking margin of safety, net-nets, and asset-based valuation opportunities.", "short": "Graham"},
    "Technical Analyst": {"desc": "Chartist focused on price action, indicators, support/resistance, and pattern recognition.", "short": "Technical"},
    "Risk Manager": {"desc": "Cautious portfolio risk manager specializing in position sizing, drawdown protection, and tail risk hedging.", "short": "Risk"},
    "Macro Economist": {"desc": "Top-down macro analyst focused on rates, inflation, GDP, central bank policy, and global flows.", "short": "Macro"},
}


class AgentWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, client, persona, query, market_context):
        super().__init__()
        self.client = client
        self.persona = persona
        self.query = query
        self.market_context = market_context

    def run(self):
        try:
            pdata = _AGENTS.get(self.persona, _AGENTS["General Analyst"])
            resp = self.client.get_agent_response(self.persona, pdata["desc"], self.query, self.market_context)
            self.response_ready.emit(resp)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AIChatPanel(QWidget):
    def __init__(self, data_service: DataService):
        super().__init__()
        self.data = data_service
        self.client = NemotronClient()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        title = QLabel("AI Analyst")
        title.setProperty("heading", True)
        header.addWidget(title)

        self.agent_combo = QComboBox()
        for name in _AGENTS:
            self.agent_combo.addItem(f"{name} ({_AGENTS[name]['short']})", name)
        header.addWidget(self.agent_combo)

        self.analyze_btn = QPushButton("Analyze Current")
        self.analyze_btn.clicked.connect(self._analyze_current)
        header.addWidget(self.analyze_btn)
        header.addStretch()
        layout.addLayout(header)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px; padding: 8px;")
        self.chat_display.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about markets, stocks, or strategies...")
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self._append_message("System", "AI Analyst ready. Select an agent persona and ask a question.")

    def _append_message(self, sender: str, message: str):
        self.chat_display.append(f"<b style='color:#1f6feb;'>{sender}:</b> {message}<br>")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._append_message("You", text)
        self._run_agent(text)

    def _analyze_current(self):
        self._run_agent("Analyze the current market conditions and provide trading recommendations.")

    def _get_market_context(self) -> str:
        indices = self.data.get_market_indices()
        ctx = "Market Indices:\n"
        for name, data in indices.items():
            ctx += f"{name}: ${data['price']} ({data['change_pct']:+.2f}%)\n"
        movers = self.data.get_top_movers()
        ctx += "\nTop Movers:\n"
        for q in movers[:5]:
            ctx += f"{q.symbol}: ${q.price} ({q.change_pct:+.2f}%)\n"
        return ctx

    def _run_agent(self, query: str):
        persona = self.agent_combo.currentData()
        context = self._get_market_context()

        self._append_message("Agent", "Analyzing...")
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Thinking...")

        self.worker = AgentWorker(self.client, persona, query, context)
        self.worker.response_ready.connect(self._on_response)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_response(self, response: str):
        persona = self.agent_combo.currentData()
        self._append_message(persona, response)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")

    def _on_error(self, error: str):
        self._append_message("System", f"Error: {error}")
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
