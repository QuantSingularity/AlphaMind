"""
Portfolio Risk Aggregation Module.

This module provides functionality for aggregating risk across different positions
and portfolios, calculating various risk metrics, and monitoring risk limits.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RiskLimit:
    """Risk limit configuration for a portfolio or position."""

    metric_name: str
    soft_limit: float
    hard_limit: float
    description: str = ""

    def is_breached(self, value: float) -> Tuple[bool, str]:
        """
        Check if a value breaches the risk limits.

        Args:
            value: The risk metric value to check

        Returns:
            (is_breached, severity) where severity is 'none', 'soft', or 'hard'
        """
        if value > self.hard_limit:
            return (True, "hard")
        elif value > self.soft_limit:
            return (True, "soft")
        return (False, "none")


class PositionRisk:
    """Manages risk calculations for individual positions."""

    def __init__(self, position_id: str, instrument_type: str) -> None:
        """
        Initialize position risk calculator.

        Args:
            position_id: Unique identifier for the position
            instrument_type: Type of financial instrument
        """
        self.position_id = position_id
        self.instrument_type = instrument_type
        self.risk_metrics = {}
        self.risk_limits = {}

    def add_risk_limit(
        self,
        metric_name: str,
        soft_limit: float,
        hard_limit: float,
        description: str = "",
    ) -> None:
        """Add a risk limit for a specific metric."""
        self.risk_limits[metric_name] = RiskLimit(
            metric_name=metric_name,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            description=description,
        )
        logger.info(
            f"Added risk limit for {metric_name} on position {self.position_id}"
        )

    def calculate_var(
        self, returns: np.ndarray, confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Value at Risk for the position (historical/discrete method).

        Args:
            returns: Historical returns
            confidence_level: VaR confidence level

        Returns:
            Value at Risk
        """
        try:
            alpha = 100 * (1 - confidence_level)
            try:
                var = np.percentile(returns, alpha, method="lower")
            except TypeError:
                var = np.percentile(returns, alpha, interpolation="lower")

            self.risk_metrics["var"] = var
            return float(var)
        except Exception as e:
            logger.error(
                f"Error calculating VaR for position {self.position_id}: {str(e)}"
            )
            raise

    def calculate_expected_shortfall(
        self, returns: np.ndarray, confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Expected Shortfall (CVaR).

        Args:
            returns: Historical returns
            confidence_level: ES confidence level

        Returns:
            Expected Shortfall
        """
        try:
            var = self.calculate_var(returns, confidence_level)
            es = returns[returns <= var].mean()
            self.risk_metrics["expected_shortfall"] = es
            return es
        except Exception as e:
            logger.error(
                f"Error calculating Expected Shortfall for position {self.position_id}: {str(e)}"
            )
            raise

    def check_limits(self) -> Dict[str, Tuple[bool, str]]:
        """
        Check all risk metrics against their defined limits.

        Returns:
            dict: {metric_name: (is_breached, severity)}
        """
        results: Dict[str, Any] = {}
        for metric_name, value in self.risk_metrics.items():
            if metric_name in self.risk_limits:
                is_breached, severity = self.risk_limits[metric_name].is_breached(value)
                results[metric_name] = (is_breached, severity)
                if is_breached:
                    logger.warning(
                        f"Risk limit breach for {metric_name} on position {self.position_id}: {value} exceeds {severity} limit of {(self.risk_limits[metric_name].soft_limit if severity == 'soft' else self.risk_limits[metric_name].hard_limit)}"
                    )
        return results


class PortfolioRiskAggregator:
    """Aggregates risk across multiple positions in a portfolio."""

    def __init__(self, portfolio_id: str) -> None:
        """
        Initialize portfolio risk aggregator.

        Args:
            portfolio_id: Unique identifier for the portfolio
        """
        self.portfolio_id = portfolio_id
        self.positions: Dict[str, PositionRisk] = {}
        self.portfolio_risk_metrics = {}
        self.portfolio_risk_limits = {}

    def add_position(self, position: PositionRisk) -> None:
        """Add a position to the portfolio."""
        self.positions[position.position_id] = position
        logger.info(
            f"Added position {position.position_id} to portfolio {self.portfolio_id}"
        )

    def add_portfolio_risk_limit(
        self,
        metric_name: str,
        soft_limit: float,
        hard_limit: float,
        description: str = "",
    ) -> None:
        """Add a portfolio-level risk limit."""
        self.portfolio_risk_limits[metric_name] = RiskLimit(
            metric_name=metric_name,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            description=description,
        )
        logger.info(
            f"Added portfolio risk limit for {metric_name} on portfolio {self.portfolio_id}"
        )

    def calculate_portfolio_var(
        self,
        returns_matrix: pd.DataFrame,
        weights: np.ndarray,
        confidence_level: float = 0.95,
    ) -> float:
        """
        Calculate portfolio VaR considering correlations.

        Args:
            returns_matrix: DataFrame of returns for all positions
            weights: portfolio weights
            confidence_level: VaR confidence level
        """
        try:
            portfolio_returns = returns_matrix.dot(weights)
            portfolio_var = np.percentile(
                portfolio_returns, 100 * (1 - confidence_level)
            )
            self.portfolio_risk_metrics["var"] = portfolio_var
            return portfolio_var
        except Exception as e:
            logger.error(
                f"Error calculating portfolio VaR for {self.portfolio_id}: {str(e)}"
            )
            raise

    def calculate_diversification_benefit(
        self, individual_vars: np.ndarray, portfolio_var: float
    ) -> float:
        """
        Calculate diversification benefit.

        Args:
            individual_vars: VaRs of individual positions
            portfolio_var: portfolio VaR
        """
        try:
            sum_of_vars = np.sum(individual_vars)
            div_benefit = 1 - portfolio_var / sum_of_vars
            self.portfolio_risk_metrics["diversification_benefit"] = div_benefit
            return div_benefit
        except Exception as e:
            logger.error(
                f"Error calculating diversification benefit for {self.portfolio_id}: {str(e)}"
            )
            raise

    def check_portfolio_limits(self) -> Dict[str, Tuple[bool, str]]:
        """Check portfolio-level risk limits."""
        results: Dict[str, Any] = {}
        for metric_name, value in self.portfolio_risk_metrics.items():
            if metric_name in self.portfolio_risk_limits:
                is_breached, severity = self.portfolio_risk_limits[
                    metric_name
                ].is_breached(value)
                results[metric_name] = (is_breached, severity)
                if is_breached:
                    logger.warning(
                        f"Portfolio risk limit breach for {metric_name} on portfolio {self.portfolio_id}: {value} exceeds {severity} limit of {(self.portfolio_risk_limits[metric_name].soft_limit if severity == 'soft' else self.portfolio_risk_limits[metric_name].hard_limit)}"
                    )
        return results

    def generate_risk_report(self) -> Dict:
        """
        Generate a comprehensive risk report for the portfolio.

        Returns:
            dict with portfolio metrics, breaches, and position details
        """
        report = {
            "portfolio_id": self.portfolio_id,
            "portfolio_metrics": self.portfolio_risk_metrics.copy(),
            "portfolio_limit_breaches": self.check_portfolio_limits(),
            "positions": {},
        }
        for position_id, position in self.positions.items():
            report["positions"][position_id] = {
                "metrics": position.risk_metrics.copy(),
                "limit_breaches": position.check_limits(),
            }
        return report
