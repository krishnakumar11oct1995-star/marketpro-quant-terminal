"""
MACD Crossover strategy.
"""
import pandas as pd
from strategies.base import BaseStrategy
from core.models import StrategyResult, StrategySignal


class MACDCrossoverStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        super().__init__("macd_crossover", params or {})

    def evaluate(self, df: pd.DataFrame, ticker: str) -> StrategyResult:
        macd_line, signal_line, histogram = self.compute_macd(df['Close'])
        last_macd = macd_line.iloc[-1]
        last_signal = signal_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        last_close = float(df['Close'].iloc[-1])

        # Crossover detection
        if prev_macd <= prev_signal and last_macd > last_signal:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.BUY,
                confidence=0.7, entry_price=last_close,
                stop_loss=round(last_close * 0.97, 2),
                target=round(last_close * 1.06, 2),
                reason="MACD line crossed above signal line (bullish)",
                indicators={'macd': round(last_macd, 2), 'signal': round(last_signal, 2), 'histogram': round(histogram.iloc[-1], 2)}
            )
        elif prev_macd >= prev_signal and last_macd < last_signal:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.SELL,
                confidence=0.7, entry_price=last_close,
                stop_loss=round(last_close * 1.03, 2),
                target=round(last_close * 0.94, 2),
                reason="MACD line crossed below signal line (bearish)",
                indicators={'macd': round(last_macd, 2), 'signal': round(last_signal, 2), 'histogram': round(histogram.iloc[-1], 2)}
            )
        return StrategyResult(
            ticker=ticker, strategy_name=self.name, signal=StrategySignal.NEUTRAL,
            confidence=0.3,
            indicators={'macd': round(last_macd, 2), 'signal': round(last_signal, 2), 'histogram': round(histogram.iloc[-1], 2)}
        )
