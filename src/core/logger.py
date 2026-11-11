import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        log_dir = Path.home() / ".nvidia-fin-terminal" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"terminal_{datetime.now().strftime('%Y%m%d')}.log"

        self.logger = logging.getLogger("NVIDIA-FinTerminal")
        self.logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def info(self, msg): self.logger.info(msg)
    def warn(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)
