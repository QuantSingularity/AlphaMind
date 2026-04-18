"""
Unit tests for the risk aggregation module.

This module contains tests for the portfolio risk aggregation functionality.
"""

import unittest
from typing import Any

import numpy as np
import pandas as pd
from risk.aggregation.portfolio_risk import (
    PortfolioRiskAggregator,
    PositionRisk,
    RiskLimit,
)


class TestRiskLimit(unittest.TestCase):
    """Test cases for the RiskLimit class."""

    def test_is_breached_no_breach(self) -> Any:
        """Test that is_breached returns False when value is below limits."""
        limit = RiskLimit(metric_name="var", soft_limit=5.0, hard_limit=10.0)
        is_breached, severity = limit.is_breached(3.0)
        self.assertFalse(is_breached)
        self.assertEqual(severity, "none")

    def test_is_breached_soft_breach(self) -> Any:
        """Test that is_breached returns True with 'soft' when value exceeds soft limit."""
        limit = RiskLimit(metric_name="var", soft_limit=5.0, hard_limit=10.0)
        is_breached, severity = limit.is_breached(7.0)
        self.assertTrue(is_breached)
        self.assertEqual(severity, "soft")

    def test_is_breached_hard_breach(self) -> Any:
        """Test that is_breached returns True with 'hard' when value exceeds hard limit."""
        limit = RiskLimit(metric_name="var", soft_limit=5.0, hard_limit=10.0)
        is_breached, severity = limit.is_breached(12.0)
        self.assertTrue(is_breached)
        self.assertEqual(severity, "hard")


class TestPositionRisk(unittest.TestCase):
    """Test cases for the PositionRisk class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.position = PositionRisk(position_id="TEST001", instrument_type="equity")

    def test_add_risk_limit(self) -> Any:
        """Test adding a risk limit to a position."""
        self.position.add_risk_limit("var", 5.0, 10.0, "VaR limit")
        self.assertIn("var", self.position.risk_limits)
        self.assertEqual(self.position.risk_limits["var"].soft_limit, 5.0)
        self.assertEqual(self.position.risk_limits["var"].hard_limit, 10.0)

    def test_calculate_var(self) -> Any:
        """Test calculating VaR for a position."""
        returns = np.array([-0.01, -0.02, -0.03, 0.01, 0.02, 0.03])
        var = self.position.calculate_var(returns, confidence_level=0.95)
        self.assertAlmostEqual(var, -0.03, places=6)
        self.assertIn("var", self.position.risk_metrics)
        self.assertEqual(self.position.risk_metrics["var"], var)

    def test_calculate_expected_shortfall(self) -> Any:
        """Test calculating Expected Shortfall for a position."""
        returns = np.array([-0.03, -0.02, -0.01, 0.01, 0.02, 0.03])
        es = self.position.calculate_expected_shortfall(returns, confidence_level=0.95)
        self.assertAlmostEqual(es, -0.03, places=6)
        self.assertIn("expected_shortfall", self.position.risk_metrics)
        self.assertEqual(self.position.risk_metrics["expected_shortfall"], es)

    def test_check_limits_no_breach(self) -> Any:
        """Test checking limits with no breaches."""
        self.position.add_risk_limit("var", 5.0, 10.0)
        self.position.risk_metrics["var"] = 3.0
        results = self.position.check_limits()
        self.assertIn("var", results)
        self.assertFalse(results["var"][0])
        self.assertEqual(results["var"][1], "none")

    def test_check_limits_with_breach(self) -> Any:
        """Test checking limits with a breach."""
        self.position.add_risk_limit("var", 5.0, 10.0)
        self.position.risk_metrics["var"] = 7.0
        results = self.position.check_limits()
        self.assertIn("var", results)
        self.assertTrue(results["var"][0])
        self.assertEqual(results["var"][1], "soft")


class TestPortfolioRiskAggregator(unittest.TestCase):
    """Test cases for the PortfolioRiskAggregator class."""

    def setUp(self) -> Any:
        """Set up test fixtures."""
        self.portfolio = PortfolioRiskAggregator(portfolio_id="PORT001")
        self.position1 = PositionRisk(position_id="POS001", instrument_type="equity")
        self.position2 = PositionRisk(position_id="POS002", instrument_type="equity")

    def test_add_position(self) -> Any:
        """Test adding a position to the portfolio."""
        self.portfolio.add_position(self.position1)
        self.assertIn(self.position1.position_id, self.portfolio.positions)
        self.assertEqual(
            self.portfolio.positions[self.position1.position_id], self.position1
        )

    def test_add_portfolio_risk_limit(self) -> Any:
        """Test adding a risk limit at the portfolio level."""
        self.portfolio.add_portfolio_risk_limit(
            "var", 10.0, 20.0, "Portfolio VaR limit"
        )
        self.assertIn("var", self.portfolio.portfolio_risk_limits)
        self.assertEqual(self.portfolio.portfolio_risk_limits["var"].soft_limit, 10.0)
        self.assertEqual(self.portfolio.portfolio_risk_limits["var"].hard_limit, 20.0)

    def test_calculate_portfolio_var(self) -> Any:
        """Test calculating portfolio VaR."""
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
        self.assertIn("var", self.portfolio.portfolio_risk_metrics)
        self.assertEqual(self.portfolio.portfolio_risk_metrics["var"], var)

    def test_calculate_diversification_benefit(self) -> Any:
        """Test calculating diversification benefit."""
        individual_vars = np.array([5.0, 4.0])
        portfolio_var = 7.0
        div_benefit = self.portfolio.calculate_diversification_benefit(
            individual_vars, portfolio_var
        )
        expected_benefit = 1 - 7.0 / 9.0
        self.assertAlmostEqual(div_benefit, expected_benefit, places=6)
        self.assertIn("diversification_benefit", self.portfolio.portfolio_risk_metrics)
        self.assertEqual(
            self.portfolio.portfolio_risk_metrics["diversification_benefit"],
            div_benefit,
        )

    def test_check_portfolio_limits_no_breach(self) -> Any:
        """Test checking portfolio limits with no breaches."""
        self.portfolio.add_portfolio_risk_limit("var", 10.0, 20.0)
        self.portfolio.portfolio_risk_metrics["var"] = 8.0
        results = self.portfolio.check_portfolio_limits()
        self.assertIn("var", results)
        self.assertFalse(results["var"][0])
        self.assertEqual(results["var"][1], "none")

    def test_check_portfolio_limits_with_breach(self) -> Any:
        """Test checking portfolio limits with a breach."""
        self.portfolio.add_portfolio_risk_limit("var", 10.0, 20.0)
        self.portfolio.portfolio_risk_metrics["var"] = 15.0
        results = self.portfolio.check_portfolio_limits()
        self.assertIn("var", results)
        self.assertTrue(results["var"][0])
        self.assertEqual(results["var"][1], "soft")

    def test_generate_risk_report(self) -> Any:
        """Test generating a comprehensive risk report."""
        self.portfolio.add_position(self.position1)
        self.portfolio.add_position(self.position2)
        self.portfolio.portfolio_risk_metrics["var"] = 12.0
        self.portfolio.portfolio_risk_metrics["diversification_benefit"] = 0.2
        self.position1.risk_metrics["var"] = 8.0
        self.position2.risk_metrics["var"] = 7.0
        self.portfolio.add_portfolio_risk_limit("var", 10.0, 20.0)
        self.position1.add_risk_limit("var", 5.0, 10.0)
        self.position2.add_risk_limit("var", 5.0, 10.0)
        report = self.portfolio.generate_risk_report()
        self.assertEqual(report["portfolio_id"], "PORT001")
        self.assertIn("portfolio_metrics", report)
        self.assertIn("portfolio_limit_breaches", report)
        self.assertIn("positions", report)
        self.assertEqual(report["portfolio_metrics"]["var"], 12.0)
        self.assertEqual(report["portfolio_metrics"]["diversification_benefit"], 0.2)
        self.assertTrue(report["portfolio_limit_breaches"]["var"][0])
        self.assertEqual(report["portfolio_limit_breaches"]["var"][1], "soft")
        self.assertIn("POS001", report["positions"])
        self.assertIn("POS002", report["positions"])
        self.assertEqual(report["positions"]["POS001"]["metrics"]["var"], 8.0)
        self.assertEqual(report["positions"]["POS002"]["metrics"]["var"], 7.0)
        self.assertTrue(report["positions"]["POS001"]["limit_breaches"]["var"][0])
        self.assertTrue(report["positions"]["POS002"]["limit_breaches"]["var"][0])


if __name__ == "__main__":
    unittest.main()
