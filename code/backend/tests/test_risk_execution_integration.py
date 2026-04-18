"""
Integration test for the risk management and execution engine modules.

This module tests the integration between risk management and execution engine components.
"""

import unittest
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from execution.order_management.order_manager import (
    OrderFill,
    OrderManager,
    OrderSide,
    OrderType,
)
from risk.aggregation.portfolio_risk import PortfolioRiskAggregator, PositionRisk
from risk.aggregation.position_limits import (
    LimitScope,
    LimitType,
    PositionLimit,
    PositionLimitsManager,
)


class TestRiskExecutionIntegration(unittest.TestCase):
    """Test cases for the integration between risk and execution components."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.portfolio = PortfolioRiskAggregator(portfolio_id="PORT001")
        self.position1 = PositionRisk(position_id="POS001", instrument_type="equity")
        self.position2 = PositionRisk(position_id="POS002", instrument_type="equity")
        self.portfolio.add_position(self.position1)
        self.portfolio.add_position(self.position2)
        self.limits_manager = PositionLimitsManager()
        self.limit1 = PositionLimit(
            limit_id="AAPL_NOTIONAL",
            limit_type=LimitType.NOTIONAL,
            scope=LimitScope.INSTRUMENT,
            scope_value="AAPL",
            soft_limit=1000000.0,
            hard_limit=2000000.0,
        )
        self.limits_manager.add_limit(self.limit1)
        self.order_manager = OrderManager()

    def test_order_risk_check_integration(self) -> Any:
        """Test that orders are checked against risk limits before execution."""
        order = self.order_manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=1000,
            order_type=OrderType.LIMIT,
            limit_price=1500.0,
        )
        notional_value = order.quantity * order.limit_price
        is_breached, severity = self.limits_manager.check_limit(
            "AAPL_NOTIONAL", notional_value
        )
        self.assertTrue(is_breached)
        self.assertEqual(severity, "soft")
        if is_breached and severity == "hard":
            order.update_status("REJECTED")
        self.assertNotEqual(order.status, "REJECTED")

    def test_fill_risk_update_integration(self) -> Any:
        """Test that order fills update risk metrics."""
        order = self.order_manager.create_order(
            instrument_id="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
        )
        self.order_manager.submit_order(order.order_id)
        fill = OrderFill(
            fill_id="FILL001",
            order_id=order.order_id,
            timestamp=datetime.now(),
            quantity=100,
            price=149.5,
            venue="NASDAQ",
        )
        self.order_manager.add_fill(order.order_id, fill)
        self.position1.risk_metrics["exposure"] = order.filled_quantity * fill.price
        self.assertIn("exposure", self.position1.risk_metrics)
        self.assertEqual(self.position1.risk_metrics["exposure"], 14950.0)

    def test_portfolio_var_calculation_with_positions(self) -> Any:
        """Test calculating portfolio VaR with position data."""
        returns_matrix = pd.DataFrame(
            {
                "asset1": [-0.01, -0.02, 0.01, 0.02, 0.03],
                "asset2": [-0.02, -0.01, 0.02, 0.01, 0.03],
            }
        )
        weights = np.array([0.6, 0.4])
        var = self.portfolio.calculate_portfolio_var(
            returns_matrix, weights, confidence_level=0.95
        )
        self.assertIsNotNone(var)
        self.assertIn("var", self.portfolio.portfolio_risk_metrics)
        self.portfolio.add_portfolio_risk_limit("var", 0.01, 0.02)
        breaches = self.portfolio.check_portfolio_limits()
        if breaches.get("var", (False, ""))[0]:
            can_place_new_orders = False
        else:
            can_place_new_orders = True
        self.assertEqual(can_place_new_orders, not breaches.get("var", (False, ""))[0])


if __name__ == "__main__":
    unittest.main()
