from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QDialogButtonBox, QLabel, QComboBox,
                             QSpinBox, QGroupBox)
from PyQt6.QtCore import Qt
from src.core.config import Config


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        ai_group = QGroupBox("AI Settings")
        ai_layout = QFormLayout(ai_group)

        self.model_input = QLineEdit(self.config.get("ai_model", "gemma4:e4b"))
        ai_layout.addRow("Ollama Model:", self.model_input)

        self.url_input = QLineEdit(self.config.get("ollama_url", "http://localhost:11434"))
        ai_layout.addRow("Ollama URL:", self.url_input)
        layout.addWidget(ai_group)

        data_group = QGroupBox("Data Settings")
        data_layout = QFormLayout(data_group)

        self.refresh_input = QSpinBox()
        self.refresh_input.setRange(10, 3600)
        self.refresh_input.setValue(self.config.get("refresh_interval", 60))
        self.refresh_input.setSuffix(" sec")
        data_layout.addRow("Refresh Interval:", self.refresh_input)

        self.api_key_input = QLineEdit(self.config.get_api_key("polygon"))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        data_layout.addRow("Polygon API Key:", self.api_key_input)
        layout.addWidget(data_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        self.config.set("ai_model", self.model_input.text())
        self.config.set("ollama_url", self.url_input.text())
        self.config.set("refresh_interval", self.refresh_input.value())
        if self.api_key_input.text():
            self.config.set_api_key("polygon", self.api_key_input.text())
        self.accept()
