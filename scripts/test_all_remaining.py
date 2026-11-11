import sys
sys.path.insert(0, ".")
from PyQt6.QtWidgets import QApplication, QDockWidget
from PyQt6.QtCore import pyqtBoundSignal
import numpy as np

app = QApplication(sys.argv)
from src.main_window import MainWindow
w = MainWindow()

assert w.windowTitle().startswith("NVIDIA")
docks = w.findChildren(QDockWidget)
assert len(docks) == 12
print(f"Window: {w.windowTitle()}")
print(f"Docks: {len(docks)}")
print(f"Data: {w.data_status.text()}")

assert hasattr(w.watchlist, "symbol_selected")
from PyQt6.QtCore import pyqtBoundSignal
assert isinstance(w.watchlist.symbol_selected, pyqtBoundSignal)
print("Watchlist signal: OK")

from src.ui.panels.options_panel import StrategyBuilderWidget
sb = StrategyBuilderWidget()
assert sb.strategy_combo.count() == 11
sb.strategy_combo.setCurrentText("Iron Condor")
print(f"Strategy types: {sb.strategy_combo.count()}")

legs = [{"type": "call", "sign": 1, "strike": 100, "premium": 10, "qty": 1}]
rng = np.linspace(50, 150, 200)
payoff = sb._compute_payoff(legs, rng)
assert len(payoff) == 200
assert payoff[0] < 0
assert payoff[-1] > 0
print(f"Payoff: OK (min={payoff.min():.1f}, max={payoff.max():.1f})")

from src.core.config import Config
cfg = Config()
model = cfg.get("ai_model")
assert model == "gemma4:e4b"
print(f"AI model: {model}")

from src.nvidia.nemotron_client import NemotronClient
client = NemotronClient()
assert client.model == "gemma4:e4b"
print(f"Client model: {client.model}")

w.close()
print("ALL TESTS PASSED")
