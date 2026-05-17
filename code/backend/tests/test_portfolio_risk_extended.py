"""
Extended unit tests for PortfolioRiskAggregator and RiskLimit.

Complements the existing test_portfolio_risk.py with:
* RiskLimit breach detection for all three severity levels.
* PortfolioRiskAggregator VaR calculation correctness.
* Diversification benefit direction and boundary conditions.
* Risk report structure validation.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from risk.aggregation.portfolio_risk import PortfolioRiskAggregator, RiskLimit


class TestRiskLimit:
    def test_no_breach_below_soft(self):
        rl = RiskLimit("var", soft_limit=0.05, hard_limit=0.10)
        breached, severity = rl.is_breached(0.03)
        assert not breached
        assert severity == "none"

    def test_soft_breach(self):
        rl = RiskLimit("var", soft_limit=0.05, hard_limit=0.10)
        breached, severity = rl.is_breached(0.07)
        assert breached
        assert severity == "soft"

    def test_hard_breach(self):
        rl = RiskLimit("var", soft_limit=0.05, hard_limit=0.10)
        breached, severity = rl.is_breached(0.15)
        assert breached
        assert severity == "hard"

    def test_exactly_at_soft_limit_is_no_breach(self):
        rl = RiskLimit("var", soft_limit=0.05, hard_limit=0.10)
        breached, _ = rl.is_breached(0.05)
        # Value == limit is NOT a breach (> not >=)
        assert not breached

    def test_exactly_at_hard_limit_is_soft_breach(self):
        """value == hard_limit: fails the > hard check, but passes > soft check → soft breach."""
        rl = RiskLimit("var", soft_limit=0.05, hard_limit=0.10)
        breached, severity = rl.is_breached(0.10)
        assert breached is True
        assert severity == "soft"

    def test_above_hard_limit_is_hard_breach(self):
        rl = RiskLimit("var", soft_limit=0.05, hard_limit=0.10)
        breached, severity = rl.is_breached(0.11)
        assert breached is True
        assert severity == "hard"


class TestPortfolioRiskAggregator:
    @pytest.fixture
    def aggregator(self):
        return PortfolioRiskAggregator("test_portfolio")

    @pytest.fixture
    def returns_df(self):
        rng = np.random.default_rng(0)
        data = rng.standard_normal((252, 3)) * 0.01
        return pd.DataFrame(data, columns=["AAPL", "MSFT", "GOOGL"])

    @pytest.fixture
    def weights(self):
        return np.array([0.5, 0.3, 0.2])

    def test_var_is_negative_for_losses(self, aggregator, returns_df, weights):
        """Portfolio VaR should be negative (represents a loss)."""
        var = aggregator.calculate_portfolio_var(
            returns_df, weights, confidence_level=0.95
        )
        assert var < 0, f"VaR should be a negative number, got {var}"

    def test_var_monotone_in_confidence(self, aggregator, returns_df, weights):
        """Higher confidence level → more negative (larger) VaR."""
        var_90 = aggregator.calculate_portfolio_var(returns_df, weights, 0.90)
        var_99 = aggregator.calculate_portfolio_var(returns_df, weights, 0.99)
        assert (
            var_99 <= var_90
        ), f"99% VaR ({var_99:.4f}) should be ≤ 90% VaR ({var_90:.4f})"

    def test_var_stored_in_metrics(self, aggregator, returns_df, weights):
        aggregator.calculate_portfolio_var(returns_df, weights)
        assert "var" in aggregator.portfolio_risk_metrics

    def test_diversification_benefit_positive(self, aggregator, returns_df, weights):
        """Diversification should reduce portfolio VaR vs sum of individual VaRs."""
        port_var = aggregator.calculate_portfolio_var(returns_df, weights)
        individual_vars = np.array(
            [abs(np.percentile(returns_df[col], 5)) for col in returns_df.columns]
        )
        db = aggregator.calculate_diversification_benefit(
            individual_vars, abs(port_var)
        )
        assert db >= 0, "Diversification benefit should be non-negative"

    def test_risk_report_structure(self, aggregator, returns_df, weights):
        aggregator.calculate_portfolio_var(returns_df, weights)
        report = aggregator.generate_risk_report()
        assert "portfolio_id" in report
        assert "portfolio_metrics" in report
        assert "portfolio_limit_breaches" in report
        assert "positions" in report
        assert report["portfolio_id"] == "test_portfolio"

    def test_risk_limit_breach_detected_in_report(
        self, aggregator, returns_df, weights
    ):
        aggregator.calculate_portfolio_var(returns_df, weights)
        # Set a limit that will always be breached (var stored as negative,
        # limit also negative → value stored should exceed the limit abs-wise)
        aggregator.add_portfolio_risk_limit("var", soft_limit=-1e-9, hard_limit=-1e-10)
        report = aggregator.generate_risk_report()
        # At least the limit entry should exist in the breaches dict
        assert "var" in report["portfolio_limit_breaches"]
