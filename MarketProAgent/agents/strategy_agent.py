"""
Strategy Agent — evaluates all enabled strategies on given data and returns signals.
"""
from typing import Dict, List, Optional
from strategies.__init__ import get_strategy
from core.models import StrategyResult, StrategySignal


class StrategyAgent:
    def __init__(self, config: dict):
        self.config = config
        self.strategies_config = config.get('strategies', {})

    def evaluate(self, df, ticker: str) -> Dict[str, StrategyResult]:
        """Evaluate all enabled strategies on data and return results dict."""
        results = {}
        strategies = self.strategies_config.get('enabled', ['supertrend', 'macd_crossover'])

        for name in strategies:
            params = self.strategies_config.get(name, {})
            try:
                strategy = get_strategy(name, params)
                result = strategy.evaluate(df, ticker)
                results[name] = result
            except Exception as e:
                results[name] = StrategyResult(
                    ticker=ticker, strategy_name=name,
                    signal=StrategySignal.NEUTRAL, confidence=0.0,
                    reason=f"Error: {e}"
                )
        return results

    def best_signal(self, results: Dict[str, StrategyResult]) -> Optional[StrategyResult]:
        """Return the most confident non-neutral signal."""
        best = None
        for result in results.values():
            if result.signal != StrategySignal.NEUTRAL and result.confidence > 0:
                if best is None or result.confidence > best.confidence:
                    best = result
        return best
