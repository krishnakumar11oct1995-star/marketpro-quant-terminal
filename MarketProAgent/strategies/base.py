"""
Abstract base class for all trading strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from core.models import StrategyResult, StrategySignal


class BaseStrategy(ABC):
    def __init__(self, name: str, params: Optional[Dict] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, ticker: str) -> StrategyResult:
        """Evaluate strategy on OHLCV data and return signal."""
        ...

    def get_param(self, key: str, default=None):
        return self.params.get(key, default)

    def compute_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def compute_macd(self, series: pd.Series) -> tuple:
        ema12 = series.ewm(span=12).mean()
        ema26 = series.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def compute_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift(1)).abs()
        low_close = (df['Low'] - df['Close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def compute_supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple:
        atr = self.compute_atr(df, period)
        hl_avg = (df['High'] + df['Low']) / 2
        upper_band = hl_avg + multiplier * atr
        lower_band = hl_avg - multiplier * atr
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(0, index=df.index, dtype=float)
        for i in range(1, len(df)):
            if i < period or pd.isna(upper_band.iloc[i - 1]) or pd.isna(lower_band.iloc[i - 1]):
                continue
            if df['Close'].iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1.0
            elif df['Close'].iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1.0
            else:
                direction.iloc[i] = direction.iloc[i - 1] if direction.iloc[i - 1] != 0 else 0.0
            if direction.iloc[i] == 1.0:
                supertrend.iloc[i] = lower_band.iloc[i]
            elif direction.iloc[i] == -1.0:
                supertrend.iloc[i] = upper_band.iloc[i]
        return supertrend, direction
