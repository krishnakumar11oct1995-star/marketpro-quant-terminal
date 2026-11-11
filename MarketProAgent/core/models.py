"""
Core data models for MarketProAgent.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    SL_MARKET = "SL_MARKET"


class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ProductType(Enum):
    MIS = "MIS"      # intraday
    NRML = "NRML"     # delivery / carry forward


class StrategySignal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class Bar:
    """Single OHLCV bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self):
        return asdict(self)


@dataclass
class Order:
    """Represents a single order."""
    id: str
    ticker: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    product: ProductType = ProductType.MIS
    strategy: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    tag: str = ""  # free-form tag for grouping

    def to_dict(self):
        d = asdict(self)
        d['side'] = self.side.value
        d['order_type'] = self.order_type.value
        d['status'] = self.status.value
        d['product'] = self.product.value
        d['created_at'] = self.created_at.isoformat()
        if self.filled_at:
            d['filled_at'] = self.filled_at.isoformat()
        return d


@dataclass
class Position:
    """Open position."""
    id: str
    ticker: str
    side: PositionSide
    entry_price: float
    quantity: int
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    trailing_sl: Optional[float] = None
    entry_time: datetime = field(default_factory=datetime.now)
    strategy: str = ""
    product: ProductType = ProductType.MIS
    pnl: float = 0.0
    pnl_pct: float = 0.0

    @property
    def is_long(self):
        return self.side == PositionSide.LONG

    @property
    def is_short(self):
        return self.side == PositionSide.SHORT

    def update_pnl(self, current_price: float):
        self.current_price = current_price
        if self.is_long:
            self.pnl = (current_price - self.entry_price) * self.quantity
            self.pnl_pct = (current_price / self.entry_price - 1) * 100
        else:
            self.pnl = (self.entry_price - current_price) * self.quantity
            self.pnl_pct = (self.entry_price / current_price - 1) * 100

    def to_dict(self):
        d = asdict(self)
        d['side'] = self.side.value
        d['product'] = self.product.value
        d['entry_time'] = self.entry_time.isoformat()
        d['pnl'] = round(self.pnl, 2)
        d['pnl_pct'] = round(self.pnl_pct, 2)
        return d


@dataclass
class Trade:
    """A completed trade (opened + closed position)."""
    id: str
    ticker: str
    side: PositionSide
    entry_price: float
    exit_price: float
    quantity: int
    entry_time: datetime
    exit_time: datetime
    strategy: str
    pnl: float
    pnl_pct: float
    exit_reason: str = ""  # stop_loss, take_profit, signal, manual

    def to_dict(self):
        d = asdict(self)
        d['side'] = self.side.value
        d['entry_time'] = self.entry_time.isoformat()
        d['exit_time'] = self.exit_time.isoformat()
        d['pnl'] = round(self.pnl, 2)
        d['pnl_pct'] = round(self.pnl_pct, 2)
        return d


@dataclass
class StrategyResult:
    """Output from a strategy evaluation."""
    ticker: str
    strategy_name: str
    signal: StrategySignal
    confidence: float  # 0.0 to 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    reason: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        d = asdict(self)
        d['signal'] = self.signal.value
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class AgentState:
    """Overall agent state machine."""
    current_ticker: str = ""
    mode: str = "paper"
    status: str = "idle"  # idle | scanning | analyzing | in_position | error
    active_positions: int = 0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    last_signal: Optional[StrategyResult] = None
    current_strategy: str = ""
    uptime: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        d = asdict(self)
        d['uptime'] = self.uptime.isoformat()
        if self.last_signal:
            d['last_signal'] = self.last_signal.to_dict()
        return d
