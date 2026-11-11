from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import pandas as pd


@dataclass
class OHLCV:
    open: float
    high: float
    low: float
    close: float
    volume: int
    datetime: datetime

    def to_dict(self):
        return {
            "open": self.open, "high": self.high, "low": self.low,
            "close": self.close, "volume": self.volume,
            "datetime": self.datetime.isoformat()
        }


@dataclass
class Quote:
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    avg_volume: int
    market_cap: float
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FinancialStatements:
    symbol: str
    income_statement: pd.DataFrame = field(default_factory=pd.DataFrame)
    balance_sheet: pd.DataFrame = field(default_factory=pd.DataFrame)
    cash_flow: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class Ratios:
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    de_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    eps: Optional[float] = None
    eps_growth: Optional[float] = None
    dividend_yield: Optional[float] = None
    fcf_yield: Optional[float] = None


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0

    def update_price(self, price: float):
        self.current_price = price
        self.pnl = (price - self.avg_cost) * self.quantity
        self.pnl_pct = ((price - self.avg_cost) / self.avg_cost) * 100


@dataclass
class Portfolio:
    name: str
    positions: list[Position] = field(default_factory=list)
    cash: float = 0.0
    total_value: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0


@dataclass
class OptionContract:
    symbol: str
    expiration: str
    strike: float
    option_type: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_vol: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
