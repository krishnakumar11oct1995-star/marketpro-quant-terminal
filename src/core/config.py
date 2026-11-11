import os
import json
from pathlib import Path


APP_NAME = "NVIDIA Financial Terminal"
APP_VERSION = "1.0.0"
ORG_NAME = "NVIDIA-Finance"


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.data_dir = Path(os.path.expanduser("~")) / ".nvidia-fin-terminal"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_db = str(self.data_dir / "cache.db")
        self.config_file = self.data_dir / "config.json"
        self._load()

    def _load(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                self._data = json.load(f)
        else:
            self._data = {
                "theme": "dark",
                "api_keys": {},
                "watchlists": [],
                "window_geometry": None,
                "ai_model": "gemma4:e4b",
                "refresh_interval": 60,
                "default_exchange": "US",
            }
            self._save()

    def _save(self):
        with open(self.config_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def get_api_key(self, provider: str) -> str:
        return self._data.get("api_keys", {}).get(provider, "")

    def set_api_key(self, provider: str, key: str):
        if "api_keys" not in self._data:
            self._data["api_keys"] = {}
        self._data["api_keys"][provider] = key
        self._save()
