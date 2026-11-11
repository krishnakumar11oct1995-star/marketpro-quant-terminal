"""
RSI Mean Reversion strategy.
"""
from strategies.base import BaseStrategy
from core.models import StrategyResult, StrategySignal


class RSIMeanReversionStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        super().__init__("rsi_mean_reversion", params or {"oversold": 30, "overbought": 70, "rsi_period": 14})

    def evaluate(self, df, ticker: str) -> StrategyResult:
        period = int(self.get_param('rsi_period', 14))
        oversold = float(self.get_param('oversold', 30))
        overbought = float(self.get_param('overbought', 70))

        rsi = self.compute_rsi(df['Close'], period)
        last_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        last_close = float(df['Close'].iloc[-1])
        atr = float(self.compute_atr(df).iloc[-1])

        # Oversold bounce
        if last_rsi < oversold and prev_rsi >= last_rsi:  # rsi turned up from oversold
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.BUY,
                confidence=0.65, entry_price=last_close,
                stop_loss=round(last_close - 1.5 * atr, 2),
                target=round(last_close + 3 * atr, 2),
                reason=f"RSI oversold bounce ({last_rsi:.1f} < {oversold})",
                indicators={'rsi': round(last_rsi, 2), 'atr': round(atr, 2)}
            )
        # Overbought reversal
        elif last_rsi > overbought and prev_rsi <= last_rsi:
            return StrategyResult(
                ticker=ticker, strategy_name=self.name, signal=StrategySignal.SELL,
                confidence=0.65, entry_price=last_close,
                stop_loss=round(last_close + 1.5 * atr, 2),
                target=round(last_close - 3 * atr, 2),
                reason=f"RSI overbought reversal ({last_rsi:.1f} > {overbought})",
                indicators={'rsi': round(last_rsi, 2), 'atr': round(atr, 2)}
            )
        return StrategyResult(
            ticker=ticker, strategy_name=self.name, signal=StrategySignal.NEUTRAL,
            confidence=0.3,
            indicators={'rsi': round(last_rsi, 2)}
        )
