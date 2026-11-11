import json, os
cfg_path = os.path.expanduser("~/.nvidia-fin-terminal/config.json")
with open(cfg_path) as f:
    data = json.load(f)
data["ai_model"] = "gemma4:e4b"
data["watchlists"] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
data.pop("window_geometry", None)
with open(cfg_path, "w") as f:
    json.dump(data, f, indent=2)
print(f"Written: ai_model = {data['ai_model']}")
# Now test it loads correctly
import sys; sys.path.insert(0, r"C:\Users\Krishna\Downloads\AI2")
from src.core.config import Config
# Reset singleton
Config._instance = None
c = Config()
print(f"Config reads: ai_model = {c.get('ai_model')}")
assert c.get("ai_model") == "gemma4:e4b"
from src.nvidia.nemotron_client import NemotronClient
n = NemotronClient()
print(f"Client model: {n.model}")
assert n.model == "gemma4:e4b"
print("OK - no stale references remain")
