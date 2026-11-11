"""
Risk manager — position sizing, circuit breakers, stop-loss rules.
"""
from typing import Optional, Dict, Any
from core.models import OrderSide, OrderType, ProductType, PositionSide
from core.paper_broker import PaperBroker


class RiskManager:
    def __init__(self, config: Dict, broker: PaperBroker):
        self.config = config
        self.broker = broker
        trading = config.get('trading', {})
        self.risk_per_trade_pct = trading.get('risk_per_trade_pct', 1.0) / 100.0
        self.max_trades_per_day = trading.get('max_trades_per_day', 5)
        self.max_daily_loss_pct = trading.get('max_daily_loss_pct', 3.0) / 100.0
        self.max_positions = trading.get('max_positions', 3)
        self.stop_loss_default_pct = trading.get('stop_loss_default_pct', 15.0) / 100.0
        self.daily_trades = 0
        self.daily_start_equity = broker.equity

    def reset_daily(self):
        self.daily_trades = 0
        self.daily_start_equity = self.broker.equity

    def can_take_trade(self) -> tuple[bool, str]:
        """Check if we're allowed to take a new trade."""
        # Max positions
        if len(self.broker.positions) >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"

        # Max daily trades
        if self.daily_trades >= self.max_trades_per_day:
            return False, f"Max daily trades reached ({self.max_trades_per_day})"

        # Circuit breaker: max daily loss
        daily_loss_pct = (self.broker.equity - self.daily_start_equity) / self.daily_start_equity
        if abs(daily_loss_pct) >= self.max_daily_loss_pct:
            return False, f"Circuit breaker: daily loss {abs(daily_loss_pct)*100:.1f}% >= {self.max_daily_loss_pct*100:.0f}%"

        return True, ""

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """Calculate position size based on risk per trade (Kelly-approximate)."""
        capital = self.broker.capital
        risk_amount = capital * self.risk_per_trade_pct
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit <= 0:
            return 0
        size = int(risk_amount / risk_per_unit)
        return max(1, size)

    def calculate_stop_loss(self, entry_price: float, side: PositionSide,
                            atr: Optional[float] = None) -> float:
        """Calculate stop-loss price based on ATR or fixed percentage."""
        if atr and atr > 0:
            multiplier = 2  # 2x ATR
            if side == PositionSide.LONG:
                return round(entry_price - (atr * multiplier), 2)
            else:
                return round(entry_price + (atr * multiplier), 2)
        else:
            if side == PositionSide.LONG:
                return round(entry_price * (1 - self.stop_loss_default_pct), 2)
            else:
                return round(entry_price * (1 + self.stop_loss_default_pct), 2)

    def calculate_take_profit(self, entry_price: float, side: PositionSide,
                              risk_reward: float = 2.0) -> float:
        """Calculate take-profit based on risk-reward ratio."""
        if side == PositionSide.LONG:
            return round(entry_price * (1 + risk_reward * self.stop_loss_default_pct), 2)
        else:
            return round(entry_price * (1 - risk_reward * self.stop_loss_default_pct), 2)

    def check_capital_available(self, required: float) -> bool:
        return self.broker.free_capital >= required
