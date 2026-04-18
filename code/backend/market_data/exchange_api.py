"""
## Exchange API Integration Module for AlphaMind
## This module provides integration with various cryptocurrency and traditional exchanges,
## enabling real-time trading, order management, and account operations.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import websockets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported by exchange API."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    """Order sides supported by exchange API."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order statuses in exchange API."""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(Enum):
    """Time in force options for orders."""

    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    DAY = "day"


class ExchangeCredentials:
    """Credentials for exchange API authentication."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        additional_params: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize exchange credentials.

        Args:
            api_key: API key
            api_secret: API secret
            passphrase: API passphrase (required for some exchanges)
            additional_params: Additional parameters required by specific exchanges
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.additional_params = additional_params or {}


class ExchangeConfig:
    """Configuration for exchange API connections."""

    def __init__(
        self, exchange_id: str, credentials: Optional[ExchangeCredentials] = None
    ) -> None:
        """
        Initialize exchange configuration.

        Args:
            exchange_id: Exchange identifier (e.g., 'binance', 'coinbase', 'alpaca')
            credentials: Exchange API credentials
        """
        self.exchange_id = exchange_id.lower()
        self.credentials = credentials
        self.endpoints = self._get_default_endpoints()
        self.rate_limits = self._get_default_rate_limits()
        self.options = self._get_default_options()

    def _get_default_endpoints(self) -> Dict[str, str]:
        """
        Get default API endpoints for the exchange.

        Returns:
            Dictionary of endpoint types to URLs
        """
        endpoints = {
            "binance": {
                "rest": "https://api.binance.com",
                "websocket": "wss://stream.binance.com:9443/ws",
                "test": "https://testnet.binance.vision",
            },
            "coinbase": {
                "rest": "https://api.exchange.coinbase.com",
                "websocket": "wss://ws-feed.exchange.coinbase.com",
                "test": "https://api-public.sandbox.exchange.coinbase.com",
            },
            "alpaca": {
                "rest": "https://api.alpaca.markets",
                "websocket": "wss://stream.data.alpaca.markets/v2",
                "test": "https://paper-api.alpaca.markets",
            },
            "kraken": {
                "rest": "https://api.kraken.com",
                "websocket": "wss://ws.kraken.com",
                "test": "https://demo-futures.kraken.com",
            },
            "ftx": {
                "rest": "https://ftx.com/api",
                "websocket": "wss://ftx.com/ws",
                "test": "https://ftx.com/api",
            },
            "kucoin": {
                "rest": "https://api.kucoin.com",
                "websocket": "wss://push.kucoin.com",
                "test": "https://openapi-sandbox.kucoin.com",
            },
            "interactive_brokers": {
                "rest": "http://localhost:5000",
                "websocket": "ws://localhost:5000/ws",
                "test": "http://localhost:5000",
            },
        }
        return endpoints.get(
            self.exchange_id, {"rest": "", "websocket": "", "test": ""}
        )

    def _get_default_rate_limits(self) -> Dict[str, Any]:
        """
        Get default rate limits for the exchange.

        Returns:
            Dictionary of rate limit settings
        """
        rate_limits = {
            "binance": {
                "requests_per_minute": 1200,
                "orders_per_second": 10,
                "orders_per_day": 100000,
            },
            "coinbase": {
                "requests_per_minute": 300,
                "orders_per_second": 5,
                "orders_per_day": 50000,
            },
            "alpaca": {
                "requests_per_minute": 200,
                "orders_per_second": 5,
                "orders_per_day": 10000,
            },
            "kraken": {
                "requests_per_minute": 60,
                "orders_per_second": 1,
                "orders_per_day": 5000,
            },
            "ftx": {
                "requests_per_minute": 300,
                "orders_per_second": 5,
                "orders_per_day": 50000,
            },
            "kucoin": {
                "requests_per_minute": 180,
                "orders_per_second": 3,
                "orders_per_day": 30000,
            },
            "interactive_brokers": {
                "requests_per_minute": 100,
                "orders_per_second": 5,
                "orders_per_day": 10000,
            },
        }
        return rate_limits.get(
            self.exchange_id,
            {
                "requests_per_minute": 100,
                "orders_per_second": 1,
                "orders_per_day": 1000,
            },
        )

    def _get_default_options(self) -> Dict[str, Any]:
        """
        Get default options for the exchange.

        Returns:
            Dictionary of exchange-specific options
        """
        options = {
            "binance": {
                "recv_window": 5000,
                "use_test_net": False,
                "default_type": "spot",
            },
            "coinbase": {"sandbox_mode": False},
            "alpaca": {"paper_trading": True},
            "kraken": {"validate_only": False},
            "ftx": {"subaccount": None},
            "kucoin": {"passphrase_as_header": True},
            "interactive_brokers": {"client_id": 0, "timeout": 60},
        }
        return options.get(self.exchange_id, {})

    def use_testnet(self, enabled: bool = True) -> Any:
        """
        Configure to use test network instead of production.

        Args:
            enabled: Whether to enable test network
        """
        if self.exchange_id == "binance":
            self.options["use_test_net"] = enabled
        elif self.exchange_id == "coinbase":
            self.options["sandbox_mode"] = enabled
        elif self.exchange_id == "alpaca":
            self.options["paper_trading"] = enabled
        elif self.exchange_id == "kraken":
            self.options["validate_only"] = enabled
        elif self.exchange_id == "kucoin":
            self.options["use_sandbox"] = enabled
        logger.info(f"Set test network mode to {enabled} for {self.exchange_id}")

    def get_api_url(self, endpoint_type: str = "rest") -> str:
        """
        Get API URL for the specified endpoint type.

        Args:
            endpoint_type: Endpoint type (rest, websocket, test)

        Returns:
            API URL
        """
        if endpoint_type not in self.endpoints:
            raise ValueError(f"Unknown endpoint type: {endpoint_type}")
        if endpoint_type == "rest" and any(
            [
                self.exchange_id == "binance" and self.options.get("use_test_net"),
                self.exchange_id == "coinbase" and self.options.get("sandbox_mode"),
                self.exchange_id == "alpaca" and self.options.get("paper_trading"),
                self.exchange_id == "kucoin" and self.options.get("use_sandbox"),
            ]
        ):
            return self.endpoints["test"]
        return self.endpoints[endpoint_type]


class ExchangeAPIError(Exception):
    """Exception raised for exchange API errors."""

    def __init__(
        self, message: str, code: Optional[int] = None, response: Optional[Any] = None
    ) -> None:
        """
        Initialize exchange API error.

        Args:
            message: Error message
            code: Error code
            response: Raw API response
        """
        self.message = message
        self.code = code
        self.response = response
        super().__init__(self.message)


class Order:
    """Represents an order in the exchange API."""

    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        exchange_id: Optional[str] = None,
        exchange_order_id: Optional[str] = None,
    ) -> None:
        """
        Initialize an order.

        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            order_type: Order type (market, limit, etc.)
            quantity: Order quantity
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            client_order_id: Client-assigned order ID
            time_in_force: Time in force
            exchange_id: Exchange identifier
            exchange_order_id: Exchange-assigned order ID
        """
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.client_order_id = client_order_id or f"order_{int(time.time() * 1000)}"
        self.time_in_force = time_in_force
        self.exchange_id = exchange_id
        self.exchange_order_id = exchange_order_id
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.remaining_quantity = quantity
        self.average_price = 0.0
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.fills = []
        self._validate()

    def _validate(self) -> Any:
        """Validate order parameters."""
        if (
            self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]
            and self.price is None
        ):
            raise ValueError(f"Price is required for {self.order_type.value} orders")
        if (
            self.order_type
            in [OrderType.STOP, OrderType.STOP_LIMIT, OrderType.TRAILING_STOP]
            and self.stop_price is None
        ):
            raise ValueError(
                f"Stop price is required for {self.order_type.value} orders"
            )

    def update_from_exchange(self, exchange_data: Dict[str, Any]) -> Any:
        """
        Update order with data from exchange.

        Args:
            exchange_data: Order data from exchange
        """
        if "status" in exchange_data:
            status_str = exchange_data["status"].lower()
            for status in OrderStatus:
                if status.value == status_str:
                    self.status = status
                    break
        if "filled_quantity" in exchange_data:
            self.filled_quantity = float(exchange_data["filled_quantity"])
            self.remaining_quantity = self.quantity - self.filled_quantity
        if "average_price" in exchange_data:
            self.average_price = (
                float(exchange_data["average_price"])
                if exchange_data["average_price"]
                else 0.0
            )
        if "exchange_order_id" in exchange_data:
            self.exchange_order_id = exchange_data["exchange_order_id"]
        if "updated_at" in exchange_data:
            self.updated_at = exchange_data["updated_at"]
        if "fills" in exchange_data:
            self.fills = exchange_data["fills"]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert order to dictionary.

        Returns:
            Order as dictionary
        """
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "client_order_id": self.client_order_id,
            "time_in_force": self.time_in_force.value,
            "exchange_id": self.exchange_id,
            "exchange_order_id": self.exchange_order_id,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "average_price": self.average_price,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "fills": self.fills,
        }


class ExchangeAPI:
    """Base class for exchange API implementations."""

    def __init__(self, config: ExchangeConfig) -> None:
        """
        Initialize exchange API.

        Args:
            config: Exchange configuration
        """
        self.config = config
        self.session = None
        self.ws_connections = {}
        self.order_updates_callbacks = []
        self.trade_updates_callbacks = []
        self.balance_updates_callbacks = []
        self.market_data_callbacks = {}

    async def initialize(self):
        """Initialize HTTP session and connections."""
        self.session = aiohttp.ClientSession()
        logger.info(f"Initialized {self.config.exchange_id} API")

    async def close(self):
        """Close all connections and resources."""
        if self.session:
            await self.session.close()
        for ws in self.ws_connections.values():
            if ws and (not ws.closed):
                await ws.close()
        logger.info(f"Closed {self.config.exchange_id} API")

    async def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information.

        Returns:
            Exchange information
        """
        logger.warning(
            f"get_exchange_info not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return {
            "exchange_id": self.config.exchange_id,
            "status": "operational",
            "server_time": int(time.time() * 1000),
            "symbols_count": 0,
            "rate_limits": self.config.rate_limits,
        }

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.

        Returns:
            Account information
        """
        logger.warning(
            f"get_account_info not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return {
            "can_trade": True,
            "can_withdraw": True,
            "can_deposit": True,
            "update_time": int(time.time() * 1000),
            "account_type": "SPOT",
            "balances": {},
        }

    async def get_balances(self) -> Dict[str, Dict[str, float]]:
        """
        Get account balances.

        Returns:
            Dictionary of asset -> balance information
        """
        logger.warning(
            f"get_balances not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return {"USD": {"free": 10000.0, "locked": 0.0, "total": 10000.0}}

    async def get_order(
        self, order_id: str, client_order_id: Optional[str] = None
    ) -> Order:
        """
        Get order by ID.

        Args:
            order_id: Exchange order ID
            client_order_id: Client order ID

        Returns:
            Order object
        """

        symbol: str

        logger.warning(
            f"get_order not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return Order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=100.0,
            exchange_id=self.config.exchange_id,
            exchange_order_id=order_id,
            status=OrderStatus.FILLED,
        )

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get open orders.

        Args:
            symbol: Trading symbol (optional)

        Returns:
            List of open orders
        """
        logger.warning(
            f"get_open_orders not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return []

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Order]:
        """
        Get order history.

        Args:
            symbol: Trading symbol (optional)
            limit: Maximum number of orders to return
            start_time: Start time in milliseconds
            end_time: End time in milliseconds

        Returns:
            List of historical orders
        """
        logger.warning(
            f"get_order_history not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return []

    async def create_order(self, order: Order) -> Order:
        """
        Create a new order.

        Args:
            order: Order to create

        Returns:
            Created order with exchange information
        """
        logger.warning(
            f"create_order not implemented for {self.config.exchange_id}. Returning mock data."
        )
        order.exchange_order_id = f"MOCK_{int(time.time() * 1000)}"
        order.status = OrderStatus.OPEN
        return order

    async def cancel_order(
        self, order_id: Optional[str] = None, client_order_id: Optional[str] = None
    ) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Exchange order ID
            client_order_id: Client order ID

        Returns:
            True if order was canceled, False otherwise
        """
        logger.warning(
            f"cancel_order not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return True

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all open orders.

        Args:
            symbol: Trading symbol (optional)

        Returns:
            Number of orders canceled
        """
        logger.warning(
            f"cancel_all_orders not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return 0

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker information
        """
        logger.warning(
            f"get_ticker not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return {"symbol": symbol, "last": 100.0, "bid": 99.9, "ask": 100.1}

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get orderbook for a symbol.

        Args:
            symbol: Trading symbol
            limit: Maximum number of bids/asks to return

        Returns:
            Orderbook information
        """
        logger.warning(
            f"get_orderbook not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return {"symbol": symbol, "bids": [[99.9, 1.0]], "asks": [[100.1, 1.0]]}

    async def get_recent_trades(
        self, symbol: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades for a symbol.

        Args:
            symbol: Trading symbol
            limit: Maximum number of trades to return

        Returns:
            List of recent trades
        """
        logger.warning(
            f"get_recent_trades not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return []

    async def subscribe_to_order_updates(self, callback: Callable[[Order], None]):
        """
        Subscribe to order updates.

        Args:
            callback: Callback function for order updates
        """
        self.order_updates_callbacks.append(callback)

    async def subscribe_to_trade_updates(
        self, callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to trade updates.

        Args:
            callback: Callback function for trade updates
        """
        self.trade_updates_callbacks.append(callback)

    async def subscribe_to_balance_updates(
        self, callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to balance updates.

        Args:
            callback: Callback function for balance updates
        """
        self.balance_updates_callbacks.append(callback)

    async def subscribe_to_market_data(
        self,
        symbol: str,
        channels: List[str],
        callback: Callable[[Dict[str, Any]], None],
    ):
        """
        Subscribe to market data.

        Args:
            symbol: Trading symbol
            channels: List of channels to subscribe to (e.g., trades, orderbook, ticker)
            callback: Callback function for market data
        """
        key = f"{symbol}:{','.join(channels)}"
        if key not in self.market_data_callbacks:
            self.market_data_callbacks[key] = []
        self.market_data_callbacks[key].append(callback)

    def _handle_order_update(self, order_data: Dict[str, Any]) -> Any:
        """
        Handle order update from exchange.

        Args:
            order_data: Order data from exchange
        """
        order = self._parse_order_from_exchange(order_data)
        for callback in self.order_updates_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"Error in order update callback: {e}")

    def _handle_trade_update(self, trade_data: Dict[str, Any]) -> Any:
        """
        Handle trade update from exchange.

        Args:
            trade_data: Trade data from exchange
        """
        for callback in self.trade_updates_callbacks:
            try:
                callback(trade_data)
            except Exception as e:
                logger.error(f"Error in trade update callback: {e}")

    def _handle_balance_update(self, balance_data: Dict[str, Any]) -> Any:
        """
        Handle balance update from exchange.

        Args:
            balance_data: Balance data from exchange
        """
        for callback in self.balance_updates_callbacks:
            try:
                callback(balance_data)
            except Exception as e:
                logger.error(f"Error in balance update callback: {e}")

    def _handle_market_data(
        self, symbol: str, channel: str, data: Dict[str, Any]
    ) -> Any:
        """
        Handle market data from exchange.

        Args:
            symbol: Trading symbol
            channel: Data channel
            data: Market data
        """
        for key, callbacks in self.market_data_callbacks.items():
            key_symbol, key_channels = key.split(":", 1)
            key_channels = key_channels.split(",")
            if key_symbol == symbol and channel in key_channels:
                for callback in callbacks:
                    try:
                        callback({"symbol": symbol, "channel": channel, "data": data})
                    except Exception as e:
                        logger.error(f"Error in market data callback: {e}")

    def _parse_order_from_exchange(self, order_data: Dict[str, Any]) -> Order:
        """
        Parse order data from exchange.

        Args:
            order_data: Order data from exchange

        Returns:
            Order object
        """
        logger.warning(
            f"_parse_order_from_exchange not implemented for {self.config.exchange_id}. Returning mock data."
        )
        return Order(
            symbol="MOCK/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            exchange_id=self.config.exchange_id,
            status=OrderStatus.FILLED,
        )


class BinanceAPI(ExchangeAPI):
    """Binance exchange API implementation."""

    def __init__(self, config: ExchangeConfig) -> None:
        """
        Initialize Binance API.

        Args:
            config: Exchange configuration
        """
        super().__init__(config)
        self.ws_listen_key = None
        self.ws_listen_key_timer = None

    async def initialize(self):
        """Initialize HTTP session and connections."""
        await super().initialize()
        if self.config.credentials:
            await self._get_listen_key()
            await self._start_user_data_stream()

    async def close(self):
        """Close all connections and resources."""
        if self.ws_listen_key:
            await self._close_listen_key()
        await super().close()

    async def _get_listen_key(self):
        """Get listen key for user data stream."""
        if not self.config.credentials:
            return
        endpoint = "/api/v3/userDataStream"
        headers = {"X-MBX-APIKEY": self.config.credentials.api_key}
        try:
            async with self.session.post(
                f"{self.config.get_api_url()}{endpoint}", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.ws_listen_key = data["listenKey"]
                    logger.info("Obtained Binance listen key")
                    if self.ws_listen_key_timer:
                        self.ws_listen_key_timer.cancel()
                    self.ws_listen_key_timer = asyncio.create_task(
                        self._keep_listen_key_alive()
                    )
                else:
                    logger.error(f"Failed to get listen key: {response.status}")
        except Exception as e:
            logger.error(f"Error getting listen key: {e}")

    async def _keep_listen_key_alive(self):
        """Keep listen key alive by sending periodic requests."""
        while True:
            try:
                await asyncio.sleep(30 * 60)
                await self._ping_listen_key()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error keeping listen key alive: {e}")

    async def _ping_listen_key(self):
        """Ping listen key to keep it alive."""
        if not self.ws_listen_key:
            return
        endpoint = "/api/v3/userDataStream"
        headers = {"X-MBX-APIKEY": self.config.credentials.api_key}
        params = {"listenKey": self.ws_listen_key}
        try:
            async with self.session.put(
                f"{self.config.get_api_url()}{endpoint}", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    logger.debug("Pinged Binance listen key")
                else:
                    logger.error(f"Failed to ping listen key: {response.status}")
                    await self._get_listen_key()
        except Exception as e:
            logger.error(f"Error pinging listen key: {e}")

    async def _close_listen_key(self):
        """Close listen key."""
        if not self.ws_listen_key:
            return
        endpoint = "/api/v3/userDataStream"
        headers = {"X-MBX-APIKEY": self.config.credentials.api_key}
        params = {"listenKey": self.ws_listen_key}
        try:
            async with self.session.delete(
                f"{self.config.get_api_url()}{endpoint}", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    logger.info("Closed Binance listen key")
                else:
                    logger.error(f"Failed to close listen key: {response.status}")
        except Exception as e:
            logger.error(f"Error closing listen key: {e}")
        if self.ws_listen_key_timer:
            self.ws_listen_key_timer.cancel()
            self.ws_listen_key_timer = None
        self.ws_listen_key = None

    async def _start_user_data_stream(self):
        """Start user data stream for real-time updates."""
        if not self.ws_listen_key:
            return
        ws_url = f"{self.config.get_api_url('websocket')}/{self.ws_listen_key}"
        try:
            self.ws_connections["user_data"] = await websockets.connect(ws_url)
            logger.info("Connected to Binance user data stream")
            asyncio.create_task(self._listen_user_data_stream())
        except Exception as e:
            logger.error(f"Error connecting to user data stream: {e}")

    async def _listen_user_data_stream(self):
        """Listen for messages from user data stream."""
        ws = self.ws_connections.get("user_data")
        if not ws:
            return
        try:
            while not ws.closed:
                message = await ws.recv()
                data = json.loads(message)
                event_type = data.get("e")
                if event_type == "executionReport":
                    self._handle_order_update(data)
                elif event_type == "outboundAccountPosition":
                    self._handle_balance_update(data)
                elif event_type == "balanceUpdate":
                    self._handle_balance_update(data)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Binance user data stream connection closed")
        except Exception as e:
            logger.error(f"Error in user data stream: {e}")
        await asyncio.sleep(5)
        await self._start_user_data_stream()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        auth: bool = False,
    ) -> Dict[str, Any]:
        """
        Send request to Binance API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            auth: Whether authentication is required

        Returns:
            API response
        """
