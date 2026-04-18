"""
Risk Aggregation sub-package.

Exposes portfolio-level VaR calculation, position limits enforcement,
and real-time risk monitoring.
"""

import logging
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RiskAggregator:
    """Manages and aggregates risk metrics from multiple sources."""

    def __init__(self) -> None:
        self.aggregated_data: Dict[str, Any] = {}
        logger.info("RiskAggregator initialized.")

    def aggregate_metrics(
        self, risk_reports: List[Dict[str, Union[float, str]]]
    ) -> Dict[str, Any]:
        if not risk_reports:
            return {"total_risk": 0.0, "count": 0}
        total_var = sum(report.get("VaR", 0.0) for report in risk_reports)
        self.aggregated_data = {
            "total_var": total_var,
            "number_of_reports": len(risk_reports),
            "last_aggregated_time": pd.Timestamp.now().isoformat(),
        }
        logger.info(
            f"Aggregated {len(risk_reports)} reports. Total VaR: {total_var:.2f}"
        )
        return self.aggregated_data


def calculate_portfolio_var(
    portfolio_returns: Union[pd.Series, np.ndarray],
    confidence_level: float = 0.99,
) -> float:
    """Historical Value-at-Risk for a portfolio."""
    if (
        not isinstance(portfolio_returns, (pd.Series, np.ndarray))
        or len(portfolio_returns) == 0
    ):
        logger.error("Invalid or empty portfolio returns provided for VaR calculation.")
        return 0.0
    returns_array = np.asarray(portfolio_returns)
    percentile = 1.0 - confidence_level
    var_value = -np.quantile(returns_array, percentile, method="lower")
    return max(0.0, var_value)
