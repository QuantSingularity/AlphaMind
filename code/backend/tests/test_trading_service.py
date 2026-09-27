"""Tests for TradingService - order lifecycle: create, fetch, cancel."""

from __future__ import annotations

import pytest
from app.services.trading_service import TradingService


@pytest.mark.asyncio
class TestTradingService:

    async def test_market_order_with_price_is_filled_with_slippage(self, db_session):
        """MARKET order with a submitted price should be filled immediately with slippage."""
        svc = TradingService(db_session)
        order = await svc.create_order(
            ticker="AAPL",
            side="BUY",
            quantity=10.0,
            order_type="MARKET",
            price=175.0,
        )
        assert order["status"] == "filled"
        assert order["filledAt"] is not None
        assert order["filledPrice"] is not None
        assert order["filledPrice"] == pytest.approx(175.0 * 1.0005, rel=1e-6)

    async def test_market_order_without_price_is_filled_no_fill_price(self, db_session):
        """MARKET order without a reference price: filled but filledPrice is None."""
        svc = TradingService(db_session)
        order = await svc.create_order(
            ticker="AAPL",
            side="BUY",
            quantity=10.0,
            order_type="MARKET",
            price=None,
        )
        assert order["status"] == "filled"
        assert order["filledAt"] is not None
        assert order["filledPrice"] is None

    async def test_limit_order_remains_pending(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order(
            ticker="MSFT",
            side="BUY",
            quantity=5.0,
            order_type="LIMIT",
            price=330.0,
        )
        assert order["status"] == "pending"
        assert order["filledAt"] is None
        assert order["filledPrice"] is None

    async def test_stop_order_remains_pending(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order(
            ticker="TSLA",
            side="SELL",
            quantity=5.0,
            order_type="STOP",
            price=700.0,
        )
        assert order["status"] == "pending"

    async def test_create_sell_order(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order(
            ticker="TSLA",
            side="SELL",
            quantity=20.0,
            order_type="MARKET",
            price=740.0,
        )
        assert order["side"] == "SELL"
        assert order["status"] == "filled"

    async def test_get_order_by_id(self, db_session):
        svc = TradingService(db_session)
        created = await svc.create_order("AAPL", "BUY", 1.0, "LIMIT", 170.0)
        fetched = await svc.get_order(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["ticker"] == "AAPL"

    async def test_get_nonexistent_order_returns_none(self, db_session):
        svc = TradingService(db_session)
        result = await svc.get_order("ord-does-not-exist")
        assert result is None

    async def test_cancel_pending_order(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order("JPM", "BUY", 10.0, "LIMIT", 145.0)
        assert order["status"] == "pending"

        cancelled = await svc.cancel_order(order["id"])
        assert cancelled is not None
        assert cancelled["status"] == "cancelled"

    async def test_cancel_filled_order_returns_none(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order("AAPL", "BUY", 1.0, "MARKET", 175.0)
        assert order["status"] == "filled"
        result = await svc.cancel_order(order["id"])
        assert result is None

    async def test_cancel_nonexistent_order_returns_none(self, db_session):
        svc = TradingService(db_session)
        result = await svc.cancel_order("ord-ghost")
        assert result is None

    async def test_get_orders_returns_all(self, db_session):
        svc = TradingService(db_session)
        await svc.create_order("AAPL", "BUY", 1.0, "MARKET", 175.0)
        await svc.create_order("MSFT", "SELL", 2.0, "LIMIT", 340.0)
        await svc.create_order("TSLA", "BUY", 5.0, "STOP", 720.0)

        orders = await svc.get_orders()
        assert len(orders) == 3

    async def test_get_orders_filtered_by_status(self, db_session):
        svc = TradingService(db_session)
        await svc.create_order("AAPL", "BUY", 1.0, "MARKET", 175.0)  # filled
        await svc.create_order("MSFT", "BUY", 2.0, "LIMIT", 330.0)  # pending
        await svc.create_order("GOOGL", "BUY", 1.0, "LIMIT", 2900.0)  # pending

        pending = await svc.get_orders(status="pending")
        assert len(pending) == 2
        assert all(o["status"] == "pending" for o in pending)

        filled = await svc.get_orders(status="filled")
        assert len(filled) == 1
        assert filled[0]["ticker"] == "AAPL"

    async def test_order_ticker_and_side_uppercased(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order("aapl", "buy", 1.0, "MARKET", 175.0)
        assert order["ticker"] == "AAPL"
        assert order["side"] == "BUY"

    async def test_order_type_uppercased(self, db_session):
        svc = TradingService(db_session)
        order = await svc.create_order("AAPL", "BUY", 1.0, "limit", 170.0)
        assert order["orderType"] == "LIMIT"

    async def test_unique_order_ids(self, db_session):
        svc = TradingService(db_session)
        ids = {
            (await svc.create_order("NVDA", "BUY", 1.0, "MARKET", 870.0))["id"]
            for _ in range(10)
        }
        assert len(ids) == 10
