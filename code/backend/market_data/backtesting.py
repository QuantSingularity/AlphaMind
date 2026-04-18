import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported in backtesting."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides supported in backtesting."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order statuses in backtesting."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BacktestOrder:
    """Represents an order in the backtesting system."""

    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
        order_id: Optional[str] = None,
    ) -> None:
        """"""
        ""
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.order_id = order_id or f"order_{datetime.now().timestamp():.6f}"
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.filled_price = 0.0
        self.filled_time = None
        self.created_time = datetime.now()
        self.updated_time = self.created_time
        self.commission = 0.0
        self.slippage = 0.0
        self._validate()

    def _validate(self) -> Any:
        """Validate order parameters."""
        if (
            self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]
            and self.price is None
        ):
            raise ValueError(f"Price is required for {self.order_type.value} orders")
        if (
            self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]
            and self.stop_price is None
        ):
            raise ValueError(
                f"Stop price is required for {self.order_type.value} orders"
            )

    def fill(
        self,
        price: float,
        quantity: Optional[float] = None,
        time: Optional[datetime] = None,
    ) -> Any:
        """"""
        ""
        fill_qty = quantity or self.quantity - self.filled_quantity
        fill_qty = min(fill_qty, self.quantity - self.filled_quantity)
        if fill_qty <= 0:
            return
        self.filled_quantity += fill_qty
        if self.filled_price > 0:
            self.filled_price = (
                self.filled_price * (self.filled_quantity - fill_qty) + price * fill_qty
            ) / self.filled_quantity
        else:
            self.filled_price = price
        self.filled_time = time or datetime.now()
        self.updated_time = self.filled_time
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> Any:
        """Cancel the order if not filled."""
        if self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
            self.status = OrderStatus.CANCELED
            self.updated_time = datetime.now()

    def reject(self, reason: str = "") -> Any:
        """"""
        ""
        self.status = OrderStatus.REJECTED
        self.updated_time = datetime.now()
        logger.warning(f"Order {self.order_id} rejected: {reason}")

    def to_dict(self) -> Dict:
        """"""
        ""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "created_time": self.created_time.isoformat(),
            "updated_time": self.updated_time.isoformat(),
            "commission": self.commission,
            "slippage": self.slippage,
        }


class Position:
    """Represents a trading position in the backtesting system."""

    def __init__(
        self, symbol: str, quantity: float = 0.0, avg_price: float = 0.0
    ) -> None:
        """"""
        ""
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.last_price = avg_price
        self.trades = []

    def update(self, price: float) -> Any:
        """"""
        ""
        self.last_price = price
        self.unrealized_pnl = self.quantity * (price - self.avg_price)

    def apply_trade(
        self, side: OrderSide, quantity: float, price: float, commission: float = 0.0
    ) -> Any:
        """"""
        ""
        trade_qty = quantity
        if side == OrderSide.SELL:
            trade_qty = -quantity
        realized_pnl = 0.0
        if self.quantity > 0 and trade_qty < 0 or (self.quantity < 0 and trade_qty > 0):
            reduction_qty = min(abs(self.quantity), abs(trade_qty))
            if self.quantity > 0:
                realized_pnl = reduction_qty * (price - self.avg_price) - commission
            else:
                realized_pnl = reduction_qty * (self.avg_price - price) - commission
        new_quantity = self.quantity + trade_qty
        if (
            self.quantity >= 0
            and trade_qty > 0
            or (self.quantity <= 0 and trade_qty < 0)
        ):
            self.avg_price = (
                abs(self.quantity) * self.avg_price + abs(trade_qty) * price
            ) / (abs(self.quantity) + abs(trade_qty))
        if self.quantity * new_quantity < 0:
            self.avg_price = price
        self.quantity = new_quantity
        self.realized_pnl += realized_pnl
        self.trades.append(
            {
                "time": datetime.now(),
                "side": side.value,
                "quantity": quantity,
                "price": price,
                "commission": commission,
                "realized_pnl": realized_pnl,
            }
        )
        return realized_pnl

    def to_dict(self) -> Dict:
        """"""
        ""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_price": self.avg_price,
            "last_price": self.last_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_pnl": self.realized_pnl + self.unrealized_pnl,
            "trades_count": len(self.trades),
        }


class Portfolio:
    """Represents a portfolio in the backtesting system."""

    def __init__(self, initial_cash: float = 100000.0) -> None:
        """"""
        ""
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {}
        self.equity = initial_cash
        self.history = []

    def get_position(self, symbol: str) -> Position:
        """"""
        ""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        return self.positions[symbol]

    def update(self, prices: Dict[str, float]) -> Any:
        """"""
        ""
        portfolio_value = self.cash
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.update(prices[symbol])
                portfolio_value += position.quantity * position.last_price
        self.equity = portfolio_value
        self.history.append(
            {
                "time": datetime.now(),
                "cash": self.cash,
                "equity": self.equity,
                "positions": {s: p.to_dict() for s, p in self.positions.items()},
            }
        )

    def apply_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        commission: float = 0.0,
    ) -> Any:
        """"""
        ""
        position = self.get_position(symbol)
        if side == OrderSide.BUY:
            cost = quantity * price + commission
            if cost > self.cash:
                logger.warning(f"Insufficient cash for trade: {cost} > {self.cash}")
                return False
            self.cash -= cost
        position.apply_trade(side, quantity, price, commission)
        if side == OrderSide.SELL:
            self.cash += quantity * price - commission
        if position.quantity == 0:
            self.positions.pop(symbol, None)
        return True

    def to_dict(self) -> Dict:
        """"""
        ""
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "equity": self.equity,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "positions_count": len(self.positions),
        }


class MarketSimulator:
    """Simulates market behavior for backtesting."""

    def __init__(
        self,
        data: Dict[str, pd.DataFrame],
        commission_rate: float = 0.001,
        slippage_model: str = "fixed",
        slippage_params: Optional[Dict] = None,
    ) -> None:
        """"""
        ""
        self.data = data
        self.commission_rate = commission_rate
        self.slippage_model = slippage_model
        self.slippage_params = slippage_params or {}
        if self.slippage_model == "fixed" and "value" not in self.slippage_params:
            self.slippage_params["value"] = 0.0001
        elif self.slippage_model == "normal" and "std" not in self.slippage_params:
            self.slippage_params["std"] = 0.0005
        elif (
            self.slippage_model == "proportional"
            and "factor" not in self.slippage_params
        ):
            self.slippage_params["factor"] = 0.1

    def get_price_for_order(self, order: BacktestOrder, bar: pd.Series) -> float:
        """"""
        ""
        if order.order_type == OrderType.MARKET:
            base_price = bar["close"]
        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and bar["low"] <= order.price:
                base_price = min(bar["open"], order.price)
            elif order.side == OrderSide.SELL and bar["high"] >= order.price:
                base_price = max(bar["open"], order.price)
            else:
                return None
        elif order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if order.side == OrderSide.BUY and bar["high"] >= order.stop_price:
                if order.order_type == OrderType.STOP:
                    base_price = max(bar["open"], order.stop_price)
                elif bar["low"] <= order.price:
                    base_price = min(max(bar["open"], order.stop_price), order.price)
                else:
                    return None
            elif order.side == OrderSide.SELL and bar["low"] <= order.stop_price:
                if order.order_type == OrderType.STOP:
                    base_price = min(bar["open"], order.stop_price)
                elif bar["high"] >= order.price:
                    base_price = max(min(bar["open"], order.stop_price), order.price)
                else:
                    return None
            else:
                return None
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")
        price_with_slippage = self._apply_slippage(base_price, order.side, bar)
        return price_with_slippage

    def _apply_slippage(self, price: float, side: OrderSide, bar: pd.Series) -> float:
        """"""
        ""
        if self.slippage_model == "fixed":
            slippage_value = price * self.slippage_params["value"]
            if side == OrderSide.BUY:
                return price * (1 + self.slippage_params["value"])
            else:
                return price * (1 - self.slippage_params["value"])
        elif self.slippage_model == "normal":
            std = self.slippage_params["std"]
            slippage_value = price * np.random.normal(0, std)
            if side == OrderSide.BUY:
                return price + abs(slippage_value)
            else:
                return price - abs(slippage_value)
        elif self.slippage_model == "proportional":
            factor = self.slippage_params["factor"]
            volatility = (bar["high"] - bar["low"]) / bar["close"]
            slippage_value = price * volatility * factor
            if side == OrderSide.BUY:
                return price + slippage_value
            else:
                return price - slippage_value
        else:
            return price

    def calculate_commission(self, price: float, quantity: float) -> float:
        """"""
        ""
        return price * quantity * self.commission_rate


class BacktestEngine:
    """Main backtesting engine."""

    def __init__(
        self,
        data: Dict[str, pd.DataFrame],
        initial_cash: float = 100000.0,
        commission_rate: float = 0.001,
        slippage_model: str = "fixed",
        slippage_params: Optional[Dict] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        """"""
        ""
        self.data = data
        self.portfolio = Portfolio(initial_cash)
        self.market_simulator = MarketSimulator(
            data, commission_rate, slippage_model, slippage_params
        )
        self._prepare_data(start_date, end_date)
        self.current_time = None
        self.current_bar = {}
        self.pending_orders = []
        self.filled_orders = []
        self.canceled_orders = []
        self.rejected_orders = []
        self.performance = {
            "equity_curve": [],
            "returns": [],
            "drawdowns": [],
            "trades": [],
        }

    def _prepare_data(self, start_date: Optional[str], end_date: Optional[str]) -> Any:
        """"""
        ""
        for symbol, df in self.data.items():
            if not isinstance(df.index, pd.DatetimeIndex):
                if "timestamp" in df.columns:
                    df.set_index("timestamp", inplace=True)
                else:
                    raise ValueError(
                        f"DataFrame for {symbol} must have datetime index or timestamp column"
                    )
        if start_date or end_date:
            for symbol, df in self.data.items():
                if start_date:
                    self.data[symbol] = df[df.index >= pd.to_datetime(start_date)]
                if end_date:
                    self.data[symbol] = df[df.index <= pd.to_datetime(end_date)]
        all_dates = set()
        for df in self.data.values():
            all_dates.update(df.index)
        self.dates = sorted(all_dates)
        if not self.dates:
            raise ValueError("No data available for the specified date range")

    def place_order(self, order: BacktestOrder) -> str:
        """"""
        ""
        self.pending_orders.append(order)
        return order.order_id

    def cancel_order(self, order_id: str) -> bool:
        """"""
        ""
        for i, order in enumerate(self.pending_orders):
            if order.order_id == order_id:
                order.cancel()
                self.canceled_orders.append(order)
                self.pending_orders.pop(i)
                return True
        return False

    def _process_orders(self) -> Any:
        """Process pending orders with current bar data."""
        remaining_orders: List[Any] = []
        for order in self.pending_orders:
            if order.symbol not in self.current_bar:
                remaining_orders.append(order)
                continue
            bar = self.current_bar[order.symbol]
            execution_price = self.market_simulator.get_price_for_order(order, bar)
            if execution_price is not None:
                commission = self.market_simulator.calculate_commission(
                    execution_price, order.quantity
                )
                success = self.portfolio.apply_trade(
                    order.symbol,
                    order.side,
                    order.quantity,
                    execution_price,
                    commission,
                )
                if success:
                    order.fill(execution_price, time=self.current_time)
                    order.commission = commission
                    self.filled_orders.append(order)
                    self.performance["trades"].append(
                        {
                            "time": self.current_time,
                            "symbol": order.symbol,
                            "side": order.side.value,
                            "quantity": order.quantity,
                            "price": execution_price,
                            "commission": commission,
                            "order_type": order.order_type.value,
                        }
                    )
                else:
                    order.reject("Insufficient funds")
                    self.rejected_orders.append(order)
            else:
                remaining_orders.append(order)
        self.pending_orders = remaining_orders

    def _update_performance(self) -> Any:
        """Update performance metrics."""
        self.performance["equity_curve"].append(
            {
                "time": self.current_time,
                "equity": self.portfolio.equity,
                "cash": self.portfolio.cash,
            }
        )
        if len(self.performance["equity_curve"]) > 1:
            prev_equity = self.performance["equity_curve"][-2]["equity"]
            curr_equity = self.performance["equity_curve"][-1]["equity"]
            returns = curr_equity / prev_equity - 1
            self.performance["returns"].append(
                {"time": self.current_time, "returns": returns}
            )
        equity_series = [p["equity"] for p in self.performance["equity_curve"]]
        if equity_series:
            max_equity = max(equity_series)
            current_equity = equity_series[-1]
            drawdown = (
                (max_equity - current_equity) / max_equity if max_equity > 0 else 0
            )
            self.performance["drawdowns"].append(
                {"time": self.current_time, "drawdown": drawdown}
            )

    def run(
        self, strategy_fn: Callable[[Dict, Portfolio, BacktestEngine], None]
    ) -> Any:
        """"""
        ""
        for date in self.dates:
            self.current_time = date
            self.current_bar = {}
            for symbol, df in self.data.items():
                if date in df.index:
                    self.current_bar[symbol] = df.loc[date]
            current_prices = {s: bar["close"] for s, bar in self.current_bar.items()}
            self.portfolio.update(current_prices)
            strategy_fn(self.current_bar, self.portfolio, self)
            self._process_orders()
            self._update_performance()
        self._calculate_performance_stats()

    def _calculate_performance_stats(self) -> Any:
        """Calculate performance statistics after backtest completion."""
        equity_df = pd.DataFrame(self.performance["equity_curve"])
        if not equity_df.empty:
            equity_df.set_index("time", inplace=True)
            returns_df = pd.DataFrame(self.performance["returns"])
            if not returns_df.empty:
                returns_df.set_index("time", inplace=True)
                total_return = (
                    equity_df["equity"].iloc[-1] / self.portfolio.initial_cash - 1
                )
                annual_return = (
                    (1 + total_return) ** (252 / len(returns_df)) - 1
                    if len(returns_df) > 0
                    else 0
                )
                daily_returns = returns_df["returns"]
                volatility = (
                    daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
                )
                annual_return / volatility if volatility > 0 else 0
                drawdown_df = pd.DataFrame(self.performance["drawdowns"])
                (drawdown_df["drawdown"].max() if not drawdown_df.empty else 0)
                trades_df = pd.DataFrame(self.performance["trades"])
                if not trades_df.empty:
                    trades_df["position"] = (
                        trades_df["side"].apply(lambda x: 1 if x == "buy" else -1)
                        * trades_df["quantity"]
                    )
                    trades_by_symbol = trades_df.groupby("symbol")
                    for symbol, group in trades_by_symbol:
                        position = 0
                        avg_price = 0
                        trade_pnls: List[Any] = []
                        for _, trade in group.iterrows():
                            trade_qty = trade["quantity"]
                            trade_price = trade["price"]
                            trade_side = trade["side"]
                            commission = trade["commission"]
                            if trade_side == "buy":
                                if position >= 0:
                                    avg_price = (
                                        position * avg_price + trade_qty * trade_price
                                    ) / (position + trade_qty)
                                    position += trade_qty
                                    trade_pnls.append(-commission)
