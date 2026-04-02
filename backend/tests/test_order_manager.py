"""
Unit tests for the order management module.

This module contains tests for the order management functionality.
"""

import unittest
from datetime import datetime
from typing import Any

from execution_engine.order_management.order_manager import (
    Order,
    OrderFill,
    OrderManager,
    OrderSide,
    OrderStatus,
    OrderTimeInForce,
    OrderType,
    OrderValidationError,
    OrderValidator,
)


class TestOrder(unittest.TestCase):
    """Test cases for the Order class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )

    def test_is_valid(self) -> Any:
        """Test checking if an order is valid."""
        self.assertTrue(self.order.is_valid())
        self.order.validation_errors.append(
            OrderValidationError(error_code="TEST_ERROR", message="Test error")
        )
        self.assertFalse(self.order.is_valid())

    def test_remaining_quantity(self) -> Any:
        """Test calculating remaining quantity."""
        self.assertEqual(self.order.remaining_quantity(), 100)
        self.order.filled_quantity = 40
        self.assertEqual(self.order.remaining_quantity(), 60)
        self.order.filled_quantity = 100
        self.assertEqual(self.order.remaining_quantity(), 0)

    def test_is_complete(self) -> Any:
        """Test checking if an order is complete."""
        self.assertFalse(self.order.is_complete())
        self.order.status = OrderStatus.FILLED
        self.assertTrue(self.order.is_complete())
        self.order.status = OrderStatus.CANCELLED
        self.assertTrue(self.order.is_complete())
        self.order.status = OrderStatus.REJECTED
        self.assertTrue(self.order.is_complete())
        self.order.status = OrderStatus.EXPIRED
        self.assertTrue(self.order.is_complete())
        self.order.status = OrderStatus.ERROR
        self.assertTrue(self.order.is_complete())
        self.order.status = OrderStatus.PENDING
        self.assertFalse(self.order.is_complete())

    def test_update_status(self) -> Any:
        """Test updating order status."""
        old_status = self.order.status
        self.order.update_status(OrderStatus.VALIDATED)
        self.assertEqual(self.order.status, OrderStatus.VALIDATED)
        self.assertNotEqual(self.order.status, old_status)

    def test_add_fill(self) -> Any:
        """Test adding a fill to an order."""
        fill = OrderFill(
            fill_id="FILL001",
            order_id=self.order.order_id,
            timestamp=datetime.now(),
            quantity=40,
            price=149.5,
            venue="NASDAQ",
        )
        self.order.add_fill(fill)
        self.assertEqual(self.order.filled_quantity, 40)
        self.assertEqual(self.order.average_fill_price, 149.5)
        self.assertEqual(self.order.status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(len(self.order.fills), 1)
        fill2 = OrderFill(
            fill_id="FILL002",
            order_id=self.order.order_id,
            timestamp=datetime.now(),
            quantity=60,
            price=150.0,
            venue="NASDAQ",
        )
        self.order.add_fill(fill2)
        self.assertEqual(self.order.filled_quantity, 100)
        self.assertAlmostEqual(self.order.average_fill_price, 149.8)
        self.assertEqual(self.order.status, OrderStatus.FILLED)
        self.assertEqual(len(self.order.fills), 2)


class TestOrderValidator(unittest.TestCase):
    """Test cases for the OrderValidator class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.validator = OrderValidator()

    def test_validate_valid_market_order(self) -> Any:
        """Test validating a valid market order."""
        order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        errors = self.validator.validate(order)
        self.assertEqual(len(errors), 0)
        self.assertTrue(order.is_valid())
        self.assertEqual(order.status, OrderStatus.VALIDATED)

    def test_validate_valid_limit_order(self) -> Any:
        """Test validating a valid limit order."""
        order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        errors = self.validator.validate(order)
        self.assertEqual(len(errors), 0)
        self.assertTrue(order.is_valid())
        self.assertEqual(order.status, OrderStatus.VALIDATED)

    def test_validate_missing_instrument(self) -> Any:
        """Test validating an order with missing instrument."""
        order = Order(
            order_id="ORD001",
            instrument_id="",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        errors = self.validator.validate(order)
        self.assertGreater(len(errors), 0)
        self.assertFalse(order.is_valid())
        self.assertEqual(order.status, OrderStatus.REJECTED)

    def test_validate_invalid_quantity(self) -> Any:
        """Test validating an order with invalid quantity."""
        order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=0,
            order_type=OrderType.MARKET,
        )
        errors = self.validator.validate(order)
        self.assertGreater(len(errors), 0)
        self.assertFalse(order.is_valid())
        self.assertEqual(order.status, OrderStatus.REJECTED)

    def test_validate_limit_order_missing_price(self) -> Any:
        """Test validating a limit order with missing price."""
        order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=None,
        )
        errors = self.validator.validate(order)
        self.assertGreater(len(errors), 0)
        self.assertFalse(order.is_valid())
        self.assertEqual(order.status, OrderStatus.REJECTED)

    def test_validate_stop_order_missing_price(self) -> Any:
        """Test validating a stop order with missing price."""
        order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.STOP,
            stop_price=None,
        )
        errors = self.validator.validate(order)
        self.assertGreater(len(errors), 0)
        self.assertFalse(order.is_valid())
        self.assertEqual(order.status, OrderStatus.REJECTED)

    def test_validate_gtd_order_missing_expiry(self) -> Any:
        """Test validating a GTD order with missing expiry date."""
        order = Order(
            order_id="ORD001",
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
            time_in_force=OrderTimeInForce.GTD,
            expires_at=None,
        )
        errors = self.validator.validate(order)
        self.assertGreater(len(errors), 0)
        self.assertFalse(order.is_valid())
        self.assertEqual(order.status, OrderStatus.REJECTED)


class TestOrderManager(unittest.TestCase):
    """Test cases for the OrderManager class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.manager = OrderManager()

    def test_create_order(self) -> Any:
        """Test creating an order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.assertIsNotNone(order)
        self.assertIsNotNone(order.order_id)
        self.assertEqual(order.instrument_id, "AAPL")
        self.assertEqual(order.side, OrderSide.BUY)
        self.assertEqual(order.quantity, 100)
        self.assertEqual(order.order_type, OrderType.LIMIT)
        self.assertEqual(order.limit_price, 150.0)
        self.assertEqual(order.status, OrderStatus.CREATED)
        self.assertIn(order.order_id, self.manager.orders)

    def test_create_order_with_string_enums(self) -> Any:
        """Test creating an order with string enum values."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side="buy",
            quantity=100,
            order_type="limit",
            limit_price=150.0,
            time_in_force="day",
        )
        self.assertEqual(order.side, OrderSide.BUY)
        self.assertEqual(order.order_type, OrderType.LIMIT)
        self.assertEqual(order.time_in_force, OrderTimeInForce.DAY)

    def test_validate_order(self) -> Any:
        """Test validating an order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        result = self.manager.validate_order(order.order_id)
        self.assertTrue(result)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.VALIDATED
        )

    def test_validate_invalid_order(self) -> Any:
        """Test validating an invalid order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=0,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        result = self.manager.validate_order(order.order_id)
        self.assertFalse(result)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.REJECTED
        )

    def test_submit_order(self) -> Any:
        """Test submitting an order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.validate_order(order.order_id)
        result = self.manager.submit_order(order.order_id)
        self.assertTrue(result)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.PENDING
        )

    def test_submit_unvalidated_order(self) -> Any:
        """Test submitting an unvalidated order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        result = self.manager.submit_order(order.order_id)
        self.assertTrue(result)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.PENDING
        )

    def test_submit_invalid_order(self) -> Any:
        """Test submitting an invalid order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=0,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        result = self.manager.submit_order(order.order_id)
        self.assertFalse(result)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.REJECTED
        )

    def test_cancel_order(self) -> Any:
        """Test cancelling an order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.submit_order(order.order_id)
        result = self.manager.cancel_order(order.order_id)
        self.assertTrue(result)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.CANCELLED
        )

    def test_cancel_filled_order(self) -> Any:
        """Test cancelling a filled order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.submit_order(order.order_id)
        fill = OrderFill(
            fill_id="FILL001",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=100,
            price=150.0,
            venue="NASDAQ",
        )
        self.manager.add_fill(order.order_id, fill)
        result = self.manager.cancel_order(order.order_id)
        self.assertFalse(result)
        self.assertEqual(self.manager.orders[order.order_id].status, OrderStatus.FILLED)

    def test_add_fill(self) -> Any:
        """Test adding a fill to an order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.submit_order(order.order_id)
        fill = OrderFill(
            fill_id="FILL001",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=40,
            price=149.5,
            venue="NASDAQ",
        )
        result = self.manager.add_fill(order.order_id, fill)
        self.assertTrue(result)
        self.assertEqual(self.manager.orders[order.order_id].filled_quantity, 40)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.PARTIALLY_FILLED
        )

    def test_add_fill_to_cancelled_order(self) -> Any:
        """Test adding a fill to a cancelled order."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.submit_order(order.order_id)
        self.manager.cancel_order(order.order_id)
        fill = OrderFill(
            fill_id="FILL001",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=40,
            price=149.5,
            venue="NASDAQ",
        )
        result = self.manager.add_fill(order.order_id, fill)
        self.assertFalse(result)
        self.assertEqual(self.manager.orders[order.order_id].filled_quantity, 0)
        self.assertEqual(
            self.manager.orders[order.order_id].status, OrderStatus.CANCELLED
        )

    def test_add_fill_exceeding_quantity(self) -> Any:
        """Test adding a fill that exceeds order quantity."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.submit_order(order.order_id)
        fill = OrderFill(
            fill_id="FILL001",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=150,
            price=149.5,
            venue="NASDAQ",
        )
        result = self.manager.add_fill(order.order_id, fill)
        self.assertFalse(result)
        self.assertEqual(self.manager.orders[order.order_id].filled_quantity, 0)

    def test_get_order(self) -> Any:
        """Test getting an order by ID."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        retrieved_order = self.manager.get_order(order.order_id)
        self.assertEqual(retrieved_order, order)

    def test_get_nonexistent_order(self) -> Any:
        """Test getting a non-existent order."""
        retrieved_order = self.manager.get_order("NONEXISTENT")
        self.assertIsNone(retrieved_order)

    def test_get_orders_by_status(self) -> Any:
        """Test getting orders by status."""
        order1 = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        order2 = self.manager.create_order(
            instrument_id="MSFT",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.MARKET,
        )
        self.manager.submit_order(order2.order_id)
        created_orders = self.manager.get_orders_by_status(OrderStatus.CREATED)
        pending_orders = self.manager.get_orders_by_status(OrderStatus.PENDING)
        self.assertEqual(len(created_orders), 1)
        self.assertEqual(created_orders[0], order1)
        self.assertEqual(len(pending_orders), 1)
        self.assertEqual(pending_orders[0], order2)

    def test_get_orders_by_instrument(self) -> Any:
        """Test getting orders by instrument."""
        order1 = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        order2 = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.MARKET,
        )
        order3 = self.manager.create_order(
            instrument_id="MSFT",
            side=OrderSide.BUY,
            quantity=75,
            order_type=OrderType.LIMIT,
            limit_price=250.0,
        )
        aapl_orders = self.manager.get_orders_by_instrument("AAPL")
        msft_orders = self.manager.get_orders_by_instrument("MSFT")
        self.assertEqual(len(aapl_orders), 2)
        self.assertIn(order1, aapl_orders)
        self.assertIn(order2, aapl_orders)
        self.assertEqual(len(msft_orders), 1)
        self.assertEqual(msft_orders[0], order3)

    def test_get_active_orders(self) -> Any:
        """Test getting active orders."""
        order1 = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        order2 = self.manager.create_order(
            instrument_id="MSFT",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.MARKET,
        )
        self.manager.submit_order(order2.order_id)
        self.manager.cancel_order(order2.order_id)
        active_orders = self.manager.get_active_orders()
        self.assertEqual(len(active_orders), 1)
        self.assertEqual(active_orders[0], order1)

    def test_get_order_history(self) -> Any:
        """Test getting order history."""
        order = self.manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.manager.submit_order(order.order_id)
        fill1 = OrderFill(
            fill_id="FILL001",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=40,
            price=149.5,
            venue="NASDAQ",
        )
        self.manager.add_fill(order.order_id, fill1)
        fill2 = OrderFill(
            fill_id="FILL002",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=60,
            price=150.0,
            venue="NASDAQ",
        )
        self.manager.add_fill(order.order_id, fill2)
        history = self.manager.get_order_history(order.order_id)
        self.assertEqual(history["order_id"], order.order_id)
        self.assertEqual(history["instrument_id"], "AAPL")
        self.assertEqual(history["side"], "buy")
        self.assertEqual(history["quantity"], 100)
        self.assertEqual(history["status"], "filled")
        self.assertEqual(history["filled_quantity"], 100)
        self.assertAlmostEqual(history["average_fill_price"], 149.8)
        self.assertEqual(len(history["fills"]), 2)
        self.assertEqual(history["fills"][0]["fill_id"], "FILL001")
        self.assertEqual(history["fills"][0]["quantity"], 40)
        self.assertEqual(history["fills"][0]["price"], 149.5)
        self.assertEqual(history["fills"][1]["fill_id"], "FILL002")
        self.assertEqual(history["fills"][1]["quantity"], 60)
        self.assertEqual(history["fills"][1]["price"], 150.0)


if __name__ == "__main__":
    unittest.main()
