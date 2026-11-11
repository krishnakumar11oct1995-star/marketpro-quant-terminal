"""
Volume Breakout strategy — detects breakouts on high volume.
"""
from strategies.base import BaseStrategy
from core.models import StrategyResult, StrategySignal


class BreakoutStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        super().__init__("breakout", params or {"volume_multiplier": 1.5, "lookback": 20})

    def evaluate(self, df, ticker: str) -> StrategyResult:
        mult = float(self.get_param('volume_multiplier', 1.5))
        lookback = int(self.get_param('lookback', 20))

        if len(df) < lookback + 5:
            return StrategyResult(ticker=ticker, strategy_name=self.name, signal=StrategySignal.NEUTRAL, confidence=0.0)

        avg_volume = df['Volume'].rolling(lookback).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        current_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        highest_20 = float(df['High'].rolling(lookback).max().iloc[-1])
        lowest_20 = float(df['Low'].rolling(lookback).min().iloc[-1])
        atr = float(self.compute_atr(df).iloc[-1])

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Bullish breakout: price above 20-day high + high volume
        if current_close > highest_20 and volume_ratio > mult:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.BUY,
                confidence=0.7, entry_price=current_close,
                stop_loss=round(current_close - 1.5 * atr, 2),
                target=round(current_close + 3 * atr, 2),
                reason=f"Bullish breakout above {lookback}-day high (vol: {volume_ratio:.1f}x avg)",
                indicators={'volume_ratio': round(volume_ratio, 2), 'highest_20': highest_20, 'atr': round(atr, 2)}
            )
        # Bearish breakdown: price below 20-day low + high volume
        elif current_close < lowest_20 and volume_ratio > mult:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.SELL,
                confidence=0.7, entry_price=current_close,
                stop_loss=round(current_close + 1.5 * atr, 2),
                target=round(current_close - 3 * atr, 2),
                reason=f"Bearish breakdown below {lookback}-day low (vol: {volume_ratio:.1f}x avg)",
                indicators={'volume_ratio': round(volume_ratio, 2), 'lowest_20': lowest_20, 'atr': round(atr, 2)}
            )
        return StrategyResult(
            ticker=ticker, strategy_name=self.name, signal=StrategySignal.NEUTRAL,
            confidence=0.2,
            indicators={'volume_ratio': round(volume_ratio, 2)}
        )
