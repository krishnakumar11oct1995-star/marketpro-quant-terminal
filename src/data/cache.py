import sqlite3
import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Any
from pathlib import Path
from src.core.config import Config
from src.core.logger import Logger


class CacheService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.log = Logger()
        self.config = Config()
        self.db_path = self.config.cache_db
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS price_cache (
                symbol TEXT, timeframe TEXT, date TEXT,
                data BLOB, expires_at REAL,
                PRIMARY KEY (symbol, timeframe, date)
            );
            CREATE TABLE IF NOT EXISTS fundamental_cache (
                symbol TEXT, data_type TEXT,
                data BLOB, expires_at REAL,
                PRIMARY KEY (symbol, data_type)
            );
            CREATE TABLE IF NOT EXISTS metadata (
                symbol TEXT PRIMARY KEY,
                name TEXT, sector TEXT, industry TEXT,
                market_cap REAL, last_updated REAL
            );
            CREATE INDEX IF NOT EXISTS idx_price_expires ON price_cache(expires_at);
            CREATE INDEX IF NOT EXISTS idx_fund_expires ON fundamental_cache(expires_at);
        """)
        self._conn.commit()

    def get_price_data(self, symbol: str, timeframe: str, date: str) -> Optional[Any]:
        cur = self._conn.execute(
            "SELECT data, expires_at FROM price_cache WHERE symbol=? AND timeframe=? AND date=?",
            (symbol.upper(), timeframe, date)
        )
        row = cur.fetchone()
        if row is None:
            return None
        data, expires_at = row
        if datetime.now().timestamp() > expires_at:
            self._conn.execute(
                "DELETE FROM price_cache WHERE symbol=? AND timeframe=? AND date=?",
                (symbol.upper(), timeframe, date)
            )
            self._conn.commit()
            return None
        return pickle.loads(data)

    def set_price_data(self, symbol: str, timeframe: str, date: str, data: Any, ttl_minutes: int = 60):
        expires = (datetime.now() + timedelta(minutes=ttl_minutes)).timestamp()
        self._conn.execute(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?,?,?,?)",
            (symbol.upper(), timeframe, date, pickle.dumps(data), expires)
        )
        self._conn.commit()

    def get_fundamental(self, symbol: str, data_type: str) -> Optional[Any]:
        cur = self._conn.execute(
            "SELECT data, expires_at FROM fundamental_cache WHERE symbol=? AND data_type=?",
            (symbol.upper(), data_type)
        )
        row = cur.fetchone()
        if row is None:
            return None
        data, expires_at = row
        if datetime.now().timestamp() > expires_at:
            self._conn.execute(
                "DELETE FROM fundamental_cache WHERE symbol=? AND data_type=?",
                (symbol.upper(), data_type)
            )
            self._conn.commit()
            return None
        return pickle.loads(data)

    def set_fundamental(self, symbol: str, data_type: str, data: Any, ttl_minutes: int = 1440):
        expires = (datetime.now() + timedelta(minutes=ttl_minutes)).timestamp()
        self._conn.execute(
            "INSERT OR REPLACE INTO fundamental_cache VALUES (?,?,?,?)",
            (symbol.upper(), data_type, pickle.dumps(data), expires)
        )
        self._conn.commit()

    def get_metadata(self, symbol: str) -> Optional[dict]:
        cur = self._conn.execute(
            "SELECT name, sector, industry, market_cap, last_updated FROM metadata WHERE symbol=?",
            (symbol.upper(),)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {"symbol": symbol.upper(), "name": row[0], "sector": row[1],
                "industry": row[2], "market_cap": row[3], "last_updated": row[4]}

    def set_metadata(self, symbol: str, name: str, sector: str, industry: str, market_cap: float):
        self._conn.execute(
            "INSERT OR REPLACE INTO metadata VALUES (?,?,?,?,?,?)",
            (symbol.upper(), name, sector, industry, market_cap, datetime.now().timestamp())
        )
        self._conn.commit()

    def clear_expired(self):
        now = datetime.now().timestamp()
        self._conn.execute("DELETE FROM price_cache WHERE expires_at < ?", (now,))
        self._conn.execute("DELETE FROM fundamental_cache WHERE expires_at < ?", (now,))
        self._conn.commit()

    def close(self):
        self._conn.close()
