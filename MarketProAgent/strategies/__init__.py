"""
Strategy registry — allows dynamic discovery of strategies by name.
"""
from strategies.base import BaseStrategy
from strategies.supertrend import SupertrendStrategy
from strategies.macd_crossover import MACDCrossoverStrategy
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.breakout import BreakoutStrategy

STRATEGY_MAP = {
    'supertrend': SupertrendStrategy,
    'macd_crossover': MACDCrossoverStrategy,
    'rsi_mean_reversion': RSIMeanReversionStrategy,
    'breakout': BreakoutStrategy,
}

def get_strategy(name: str, params: dict = None) -> BaseStrategy:
    cls = STRATEGY_MAP.get(name)
    if not cls:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_MAP.keys())}")
    return cls(params)

def list_strategies() -> list:
    return list(STRATEGY_MAP.keys())
