import pandas as pd
import numpy as np
from typing import Optional


class TechnicalService:
    @staticmethod
    def sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        return df["close"].rolling(window=period).mean()

    @staticmethod
    def ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
        return df["close"].ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2):
        middle = df["close"].rolling(window=period).mean()
        std_dev = df["close"].rolling(window=period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper, middle, lower

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
        low_min = df["low"].rolling(window=k_period).min()
        high_max = df["high"].rolling(window=k_period).max()
        k = 100 * ((df["close"] - low_min) / (high_max - low_min).replace(0, np.nan))
        d = k.rolling(window=d_period).mean()
        return k, d

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (abs(minus_dm).rolling(window=period).mean() / atr.replace(0, np.nan))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        return dx.rolling(window=period).mean()

    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        obv = (df["volume"] * (~df["close"].diff().le(0) * 2 - 1)).cumsum()
        return obv

    @staticmethod
    def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = typical_price * df["volume"]
        positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)
        pos_mf = positive_flow.rolling(window=period).sum()
        neg_mf = negative_flow.rolling(window=period).sum()
        ratio = pos_mf / neg_mf.replace(0, np.nan)
        return 100 - (100 / (1 + ratio))

    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_max = df["high"].rolling(window=period).max()
        low_min = df["low"].rolling(window=period).min()
        return -100 * ((high_max - df["close"]) / (high_max - low_min).replace(0, np.nan))

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        return (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)

    @staticmethod
    def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
        ha = df.copy()
        ha["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        ha["open"] = ((df["open"].shift() + df["close"].shift()) / 2).fillna(method="bfill")
        ha["high"] = df[["high", "open", "close"]].max(axis=1)
        ha["low"] = df[["low", "open", "close"]].min(axis=1)
        return ha

    @staticmethod
    def detect_patterns(df: pd.DataFrame) -> dict:
        patterns = {}
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        body = abs(c - o)
        upper_wick = h - o.where(c > o, c)
        lower_wick = o.where(c > o, c) - l
        avg_body = body.rolling(20).mean()

        patterns["doji"] = body < (0.1 * (h - l))
        patterns["hammer"] = (lower_wick > 2 * body) & (upper_wick < body)
        patterns["engulfing_bull"] = (c.shift() < o.shift()) & (c > o) & (c >= o.shift()) & (o <= c.shift())
        patterns["engulfing_bear"] = (c.shift() > o.shift()) & (c < o) & (o >= c.shift()) & (c <= o.shift())

        last = {k: v.iloc[-1] if isinstance(v, pd.Series) else v for k, v in patterns.items()}
        return last

    def compute_indicator(self, name: str, df: pd.DataFrame, **params) -> pd.Series:
        name = name.lower()
        if name == "sma":
            return self.sma(df, params.get("period", 20))
        elif name == "ema":
            return self.ema(df, params.get("period", 20))
        elif name == "rsi":
            return self.rsi(df, params.get("period", 14))
        elif name == "macd":
            return self.macd(df, params.get("fast", 12), params.get("slow", 26), params.get("signal", 9))
        elif name == "bbands":
            return self.bollinger_bands(df, params.get("period", 20), params.get("std", 2))
        elif name == "atr":
            return self.atr(df, params.get("period", 14))
        elif name == "stoch":
            return self.stochastic(df, params.get("k", 14), params.get("d", 3))
        elif name == "adx":
            return self.adx(df, params.get("period", 14))
        elif name == "obv":
            return self.obv(df)
        elif name == "mfi":
            return self.mfi(df, params.get("period", 14))
        elif name == "williams":
            return self.williams_r(df, params.get("period", 14))
        elif name == "vwap":
            return self.vwap(df)
        return pd.Series(dtype=float)
