import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from src.data.yahoo_provider import YahooFinanceProvider
from src.data.cache import CacheService
from src.models.market import Quote, FinancialStatements, Ratios
from src.core.logger import Logger


class DataService:
    def __init__(self):
        self.yahoo = YahooFinanceProvider()
        self.cache = CacheService()
        self.log = Logger()

    def get_quote(self, symbol: str) -> Optional[Quote]:
        return self.yahoo.get_quote(symbol)

    def get_historical(self, symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        return self.yahoo.get_historical(symbol, period, interval)

    def get_financials(self, symbol: str) -> Optional[FinancialStatements]:
        return self.yahoo.get_financials(symbol)

    def get_ratios(self, symbol: str) -> Optional[Ratios]:
        return self.yahoo.get_ratios(symbol)

    def search(self, query: str) -> list[dict]:
        return self.yahoo.search_symbols(query)

    def get_sector_performance(self) -> pd.DataFrame:
        return self.yahoo.get_sector_performance()

    def get_earnings_calendar(self, days: int = 7) -> pd.DataFrame:
        return self.yahoo.get_earnings_calendar(days)

    def get_market_indices(self) -> dict:
        indices = {"^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ",
                   "^VIX": "VIX", "^RUT": "Russell 2000", "DX-Y.NYB": "DXY"}
        result = {}
        for sym, name in indices.items():
            q = self.yahoo.get_quote(sym)
            if q:
                result[name] = {"price": q.price, "change": q.change, "change_pct": q.change_pct}
        return result

    def get_top_movers(self) -> list[Quote]:
        top_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                       "BRK-B", "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH"]
        quotes = []
        for s in top_symbols:
            q = self.get_quote(s)
            if q:
                quotes.append(q)
        quotes.sort(key=lambda x: abs(x.change_pct), reverse=True)
        return quotes[:10]
