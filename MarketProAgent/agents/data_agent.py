"""
Data Agent — fetches OHLCV data from yfinance and other free sources.
"""
import yfinance as yf
import pandas as pd
from typing import Optional, Tuple
from datetime import datetime, timedelta


class DataAgent:
    def __init__(self, config: dict):
        self.config = config
        self.data_config = config.get('data', {})
        self.default_period = self.data_config.get('default_history_days', '6mo')
        self.cache = {}

    def fetch_ohlcv(self, ticker: str, period: str = None,
                    interval: str = '1d') -> Optional[pd.DataFrame]:
        period = period or self.default_period
        cache_key = f"{ticker}|{period}|{interval}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            hist = yf.Ticker(ticker).history(period=period, interval=interval)
            if hist.empty:
                print(f"  No data returned for {ticker}")
                return None
            self.cache[cache_key] = hist
            return hist
        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            return None

    def fetch_multiple(self, tickers: list, period: str = None) -> dict:
        result = {}
        for t in tickers:
            df = self.fetch_ohlcv(t, period)
            if df is not None:
                result[t] = df
        return result

    def clear_cache(self):
        self.cache.clear()
