import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from src.models.market import Quote, FinancialStatements, Ratios, OHLCV
from src.data.cache import CacheService
from src.core.logger import Logger


class YahooFinanceProvider:
    def __init__(self):
        self.cache = CacheService()
        self.log = Logger()

    def get_quote(self, symbol: str) -> Optional[Quote]:
        try:
            tk = yf.Ticker(symbol)
            info = tk.info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            prev_close = info.get("previousClose", price)
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            return Quote(
                symbol=symbol.upper(),
                price=price,
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=info.get("volume", 0),
                avg_volume=info.get("averageVolume", 0),
                market_cap=info.get("marketCap", 0),
                pe_ratio=info.get("trailingPE"),
                dividend_yield=info.get("dividendYield"),
                high_52w=info.get("fiftyTwoWeekHigh"),
                low_52w=info.get("fiftyTwoWeekLow"),
                bid=info.get("bid"),
                ask=info.get("ask")
            )
        except Exception as e:
            self.log.error(f"YF quote error {symbol}: {e}")
            return None

    def get_historical(self, symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        try:
            cache_date = f"{period}_{interval}"
            cached = self.cache.get_price_data(symbol, cache_date, "hist")
            if cached is not None:
                return cached

            tk = yf.Ticker(symbol)
            df = tk.history(period=period, interval=interval)
            if df.empty:
                return None
            df.columns = [c.lower() for c in df.columns]
            df.reset_index(inplace=True)

            ttl = {"1m": 5, "5m": 15, "15m": 30, "30m": 60, "1h": 120, "4h": 240, "1d": 1440}
            ttl_mins = min(ttl.get(interval, 1440), 1440)
            self.cache.set_price_data(symbol, cache_date, "hist", df, ttl_mins)
            return df
        except Exception as e:
            self.log.error(f"YF hist error {symbol}: {e}")
            return None

    def get_financials(self, symbol: str) -> Optional[FinancialStatements]:
        try:
            cached = self.cache.get_fundamental(symbol, "financials")
            if cached:
                return cached

            tk = yf.Ticker(symbol)
            inc = tk.income_stmt
            bal = tk.balance_sheet
            cf = tk.cash_flow

            result = FinancialStatements(
                symbol=symbol.upper(),
                income_statement=inc,
                balance_sheet=bal,
                cash_flow=cf
            )
            self.cache.set_fundamental(symbol, "financials", result, 1440)
            return result
        except Exception as e:
            self.log.error(f"YF financials error {symbol}: {e}")
            return None

    def get_ratios(self, symbol: str) -> Optional[Ratios]:
        try:
            cached = self.cache.get_fundamental(symbol, "ratios")
            if cached:
                return cached

            tk = yf.Ticker(symbol)
            info = tk.info or {}

            ratios = Ratios(
                pe_ratio=info.get("trailingPE"),
                pb_ratio=info.get("priceToBook"),
                ps_ratio=info.get("priceToSalesTrailing12Months"),
                ev_ebitda=info.get("enterpriseToEbitda"),
                de_ratio=info.get("debtToEquity"),
                current_ratio=info.get("currentRatio"),
                roe=info.get("returnOnEquity"),
                roa=info.get("returnOnAssets"),
                gross_margin=info.get("grossMargins"),
                operating_margin=info.get("operatingMargins"),
                net_margin=info.get("profitMargins"),
                eps=info.get("trailingEps"),
                eps_growth=info.get("earningsQuarterlyGrowth"),
                dividend_yield=info.get("dividendYield"),
                fcf_yield=info.get("freeCashflowYield"),
            )
            self.cache.set_fundamental(symbol, "ratios", ratios, 1440)
            return ratios
        except Exception as e:
            self.log.error(f"YF ratios error {symbol}: {e}")
            return None

    def search_symbols(self, query: str, limit: int = 10) -> list[dict]:
        try:
            tk = yf.Ticker(query)
            info = tk.info or {}
            if info and info.get("symbol"):
                return [{
                    "symbol": info["symbol"],
                    "name": info.get("longName", info.get("shortName", "")),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "market_cap": info.get("marketCap", 0),
                    "type": info.get("quoteType", "EQUITY")
                }]
        except:
            pass
        return []

    def get_sector_performance(self) -> pd.DataFrame:
        try:
            sectors = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLRE", "XLU", "XLC"]
            data = []
            for s in sectors:
                tk = yf.Ticker(s)
                hist = tk.history(period="5d")
                if not hist.empty:
                    ret = ((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100
                    data.append({"symbol": s, "performance": round(ret, 2)})
            return pd.DataFrame(data)
        except Exception as e:
            self.log.error(f"Sector perf error: {e}")
            return pd.DataFrame()

    def get_earnings_calendar(self, days: int = 7) -> pd.DataFrame:
        try:
            data = []
            start = datetime.now().strftime("%Y-%m-%d")
            end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
            for s in symbols:
                tk = yf.Ticker(s)
                try:
                    cal = tk.earnings_dates
                    if cal is not None and not cal.empty:
                        for idx, row in cal.iterrows():
                            data.append({
                                "symbol": s,
                                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx),
                                "eps_estimate": row.get("EPS Estimate", ""),
                                "eps_actual": row.get("EPS Actual", ""),
                                "revenue_estimate": row.get("Revenue Estimate", ""),
                            })
                except:
                    continue
            return pd.DataFrame(data)
        except Exception as e:
            self.log.error(f"Earnings calendar error: {e}")
            return pd.DataFrame()
