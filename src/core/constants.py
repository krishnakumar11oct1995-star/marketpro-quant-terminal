from enum import Enum


class Timeframe(Enum):
    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1wk"
    MONTH_1 = "1mo"

    @property
    def pandas_freq(self):
        return {
            "1m": "1min", "5m": "5min", "15m": "15min",
            "30m": "30min", "1h": "1h", "4h": "4h",
            "1d": "1d", "1wk": "1wk", "1mo": "1mo"
        }[self.value]


class ChartType(Enum):
    CANDLESTICK = "candlestick"
    LINE = "line"
    AREA = "area"
    RENKO = "renko"
    HEIKIN_ASHI = "heikin_ashi"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class AssetClass(Enum):
    STOCK = "stock"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"
    FX = "fx"
    BOND = "bond"
    COMMODITY = "commodity"


SECTORS = [
    "Technology", "Healthcare", "Financials", "Consumer Cyclical",
    "Consumer Defensive", "Energy", "Industrials", "Basic Materials",
    "Real Estate", "Utilities", "Communication Services"
]

INDICATORS = {
    "sma": {"name": "Simple Moving Average", "params": {"period": 20}},
    "ema": {"name": "Exponential Moving Average", "params": {"period": 20}},
    "rsi": {"name": "Relative Strength Index", "params": {"period": 14}},
    "macd": {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}},
    "bbands": {"name": "Bollinger Bands", "params": {"period": 20, "std": 2}},
    "atr": {"name": "Average True Range", "params": {"period": 14}},
    "vwap": {"name": "Volume Weighted Avg Price", "params": {}},
    "stoch": {"name": "Stochastic Oscillator", "params": {"k": 14, "d": 3}},
    "adx": {"name": "Average Directional Index", "params": {"period": 14}},
    "ichimoku": {"name": "Ichimoku Cloud", "params": {}},
    "obv": {"name": "On-Balance Volume", "params": {}},
    "mfi": {"name": "Money Flow Index", "params": {"period": 14}},
    "williams": {"name": "Williams %R", "params": {"period": 14}},
    "sar": {"name": "Parabolic SAR", "params": {"step": 0.02, "max_step": 0.2}},
}
