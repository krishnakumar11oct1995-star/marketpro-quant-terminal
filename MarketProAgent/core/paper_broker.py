"""
Abstract broker interface + Paper trading implementation.
"""
import uuid
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from core.models import Order, OrderSide, OrderType, OrderStatus, Position, PositionSide, Trade, ProductType
from core.database import Database


class BrokerBase:
    """Abstract broker interface."""
    def place_order(self, order: Order) -> Order: ...
    def cancel_order(self, order_id: str) -> bool: ...
    def get_positions(self) -> List[Dict]: ...
    def get_order_status(self, order_id: str) -> OrderStatus: ...
    def get_account_summary(self) -> Dict: ...


class PaperBroker(BrokerBase):
    """Paper trading engine with simulated fills and slippage."""

    def __init__(self, initial_capital: float = 100000, db: Optional[Database] = None):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.db = db or Database()
        self._load_state()

    def _load_state(self):
        """Restore positions from DB on restart."""
        db_positions = self.db.get_open_positions()
        for p in db_positions:
            pos = Position(
                id=p['id'],
                ticker=p['ticker'],
                side=PositionSide(p['side']),
                entry_price=p['entry_price'],
                quantity=p['quantity'],
                current_price=p.get('current_price', p['entry_price']),
                stop_loss=p.get('stop_loss'),
                trailing_sl=p.get('trailing_sl'),
                entry_time=datetime.fromisoformat(p['entry_time']) if p.get('entry_time') else datetime.now(),
                strategy=p.get('strategy', ''),
                product=ProductType(p.get('product', 'MIS'))
            )
            self.positions[pos.id] = pos

    @property
    def equity(self) -> float:
        pos_value = sum(p.quantity * p.current_price for p in self.positions.values())
        return self.capital + pos_value

    @property
    def used_margin(self) -> float:
        return sum(p.quantity * p.entry_price for p in self.positions.values())

    @property
    def free_capital(self) -> float:
        return self.capital - self.used_margin

    def place_order(self, ticker: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: Optional[float] = None,
                    trigger_price: Optional[float] = None,
                    strategy: str = "", product: ProductType = ProductType.MIS,
                    tag: str = "") -> Order:
        order_id = f"paper_{uuid.uuid4().hex[:12]}"
        order = Order(
            id=order_id, ticker=ticker, side=side, order_type=order_type,
            quantity=quantity, price=price, trigger_price=trigger_price,
            product=product, strategy=strategy, tag=tag
        )
        self.orders[order_id] = order

        # For market orders, simulate immediate fill
        if order_type == OrderType.MARKET:
            fill_price = price or self._simulate_fill_price(ticker, side)
            self._fill_order(order, fill_price)
        elif order_type == OrderType.LIMIT and price:
            # Simulate limit fill (simplified: fills if within reasonable range)
            pass  # would be filled in check_orders loop

        self.db.save_order(order.to_dict())
        return order

    def _simulate_fill_price(self, ticker: str, side: OrderSide) -> float:
        """Simulate a realistic fill price with small slippage."""
        try:
            import yfinance as yf
            hist = yf.Ticker(ticker).history(period='1d')
            if not hist.empty:
                last = float(hist['Close'].iloc[-1])
                slippage = random.uniform(-0.001, 0.001)  # 0.1% slippage
                return round(last * (1 + slippage), 2)
        except Exception:
            pass
        return 100.0  # fallback

    def _fill_order(self, order: Order, fill_price: float):
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.filled_at = datetime.now()

        # Create or update position
        pos_id = f"pos_{order.ticker}_{order.strategy}"
        existing = self.positions.get(pos_id)

        if existing:
            # Average in
            total_qty = existing.quantity + order.quantity
            total_cost = (existing.quantity * existing.entry_price) + (order.quantity * fill_price)
            existing.entry_price = total_cost / total_qty
            existing.quantity = total_qty
            existing.current_price = fill_price
        else:
            side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            pos = Position(
                id=pos_id, ticker=order.ticker, side=side,
                entry_price=fill_price, quantity=order.quantity,
                current_price=fill_price, strategy=order.strategy,
                product=order.product
            )
            self.positions[pos_id] = pos

        self.db.save_order(order.to_dict())
        if pos_id in self.positions:
            self.db.save_position(self.positions[pos_id].to_dict())

    def close_position(self, position_id: str, exit_price: Optional[float] = None,
                       exit_reason: str = ""):
        pos = self.positions.get(position_id)
        if not pos:
            return None

        price = exit_price or pos.current_price
        pos.update_pnl(price)

        # Record trade
        trade = Trade(
            id=f"trade_{uuid.uuid4().hex[:12]}",
            ticker=pos.ticker, side=pos.side,
            entry_price=pos.entry_price, exit_price=price,
            quantity=pos.quantity,
            entry_time=pos.entry_time, exit_time=datetime.now(),
            strategy=pos.strategy, pnl=pos.pnl, pnl_pct=pos.pnl_pct,
            exit_reason=exit_reason
        )
        self.trades.append(trade)

        # Update capital
        self.capital += pos.pnl + (pos.quantity * pos.entry_price)  # return capital
        self.db.save_trade(trade.to_dict())
        self.db.delete_position(position_id)
        del self.positions[position_id]
        return trade

    def update_positions(self, current_prices: Dict[str, float]):
        """Update all open positions with latest prices."""
        for pos_id, pos in list(self.positions.items()):
            price = current_prices.get(pos.ticker)
            if price:
                pos.update_pnl(price)
                self.db.save_position(pos.to_dict())

    def check_stop_losses(self, current_prices: Dict[str, float]) -> List[Trade]:
        """Check and execute stop-loss orders."""
        closed = []
        for pos_id, pos in list(self.positions.items()):
            price = current_prices.get(pos.ticker)
            if not price:
                continue
            pos.update_pnl(price)

            if pos.is_long and pos.stop_loss and price <= pos.stop_loss:
                t = self.close_position(pos_id, exit_price=price, exit_reason="stop_loss")
                if t:
                    closed.append(t)
            elif pos.is_short and pos.stop_loss and price >= pos.stop_loss:
                t = self.close_position(pos_id, exit_price=price, exit_reason="stop_loss")
                if t:
                    closed.append(t)

            # Trailing stop
            if pos.is_long and pos.trailing_sl and price > pos.entry_price:
                if price >= pos.entry_price * (1 + 0.01):  # 1% profit threshold
                    new_sl = max(pos.trailing_sl, price * 0.95) if pos.trailing_sl else price * 0.95
                    if new_sl != pos.trailing_sl:
                        pos.trailing_sl = new_sl
                        self.db.save_position(pos.to_dict())
        return closed

    def get_positions(self) -> List[Dict]:
        return [p.to_dict() for p in self.positions.values()]

    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        o = self.orders.get(order_id)
        return o.status if o else None

    def get_account_summary(self) -> Dict:
        return {
            'initial_capital': self.initial_capital,
            'current_capital': round(self.capital, 2),
            'equity': round(self.equity, 2),
            'used_margin': round(self.used_margin, 2),
            'free_capital': round(self.free_capital, 2),
            'open_positions': len(self.positions),
            'total_trades': len(self.trades),
            'unrealized_pnl': round(sum(p.pnl for p in self.positions.values()), 2),
        }
