"""
Supertrend strategy — trend following using ATR-based bands.
"""
import pandas as pd
import numpy as np
from strategies.base import BaseStrategy
from core.models import StrategyResult, StrategySignal


class SupertrendStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        super().__init__("supertrend", params or {"period": 10, "multiplier": 3.0})

    def evaluate(self, df: pd.DataFrame, ticker: str) -> StrategyResult:
        period = int(self.get_param('period', 10))
        multiplier = float(self.get_param('multiplier', 3.0))

        supertrend, direction = self.compute_supertrend(df, period, multiplier)

        if len(direction) < 2:
            return StrategyResult(ticker=ticker, strategy_name=self.name, signal=StrategySignal.NEUTRAL, confidence=0.0)

        curr = direction.iloc[-1]
        prev = direction.iloc[-2]
        last_close = float(df['Close'].iloc[-1])
        atr = float(self.compute_atr(df, period).iloc[-1])

        # Trend change detection
        if prev == -1 and curr == 1:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.BUY,
                confidence=0.75, entry_price=last_close,
                stop_loss=round(last_close - 2 * atr, 2),
                target=round(last_close + 4 * atr, 2),
                reason=f"Supertrend turned UP (period={period}, mult={multiplier})",
                indicators={'supertrend_direction': int(curr), 'atr': round(atr, 2)}
            )
        elif prev == 1 and curr == -1:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.SELL,
                confidence=0.75, entry_price=last_close,
                stop_loss=round(last_close + 2 * atr, 2),
                target=round(last_close - 4 * atr, 2),
                reason=f"Supertrend turned DOWN (period={period}, mult={multiplier})",
                indicators={'supertrend_direction': int(curr), 'atr': round(atr, 2)}
            )
        else:
            direction_label = "UP" if curr == 1 else "DOWN"
            return StrategyResult(
                ticker=ticker, strategy_name=self.name,
                signal=StrategySignal.STRONG_BUY if curr == 1 else StrategySignal.STRONG_SELL,
                confidence=0.6 if curr == 1 else 0.6,
                entry_price=last_close,
                stop_loss=round(last_close - 2 * atr, 2) if curr == 1 else round(last_close + 2 * atr, 2),
                target=round(last_close + 4 * atr, 2) if curr == 1 else round(last_close - 4 * atr, 2),
                reason=f"Continuation: trend is {direction_label}",
                indicators={'supertrend_direction': int(curr), 'atr': round(atr, 2)}
            )
