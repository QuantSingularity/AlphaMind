"""
Performance metrics for financial machine learning models.

This module provides a comprehensive set of metrics for evaluating
financial machine learning models, including risk-adjusted returns,
drawdown analysis, and prediction quality metrics.
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sample_weights: Optional[np.ndarray] = None,
    task_type: str = "regression",
    custom_metrics: Optional[Dict[str, callable]] = None,
) -> Dict[str, float]:
    """
    Calculate a comprehensive set of performance metrics based on task type.

    Parameters
    ----------
    y_true : array-like
        Ground truth (correct) target values.
    y_pred : array-like
        Estimated target values.
    sample_weights : array-like, optional
        Sample weights.
    task_type : str, default="regression"
        Type of machine learning task. Options: "regression", "classification", "ranking".
    custom_metrics : dict, optional
        Dictionary of custom metric functions with names as keys.

    Returns
    -------
    metrics : dict
        Dictionary containing calculated metrics.
    """
    metrics: Dict[str, Any] = {}
    if task_type == "regression":
        metrics["mse"] = mean_squared_error(
            y_true, y_pred, sample_weight=sample_weights
        )
        metrics["rmse"] = np.sqrt(metrics["mse"])
        metrics["mae"] = mean_absolute_error(
            y_true, y_pred, sample_weight=sample_weights
        )
        metrics["r2"] = r2_score(y_true, y_pred, sample_weight=sample_weights)

        # Financial-specific metrics for regression
        if np.std(y_true) > 0:
            metrics["information_ratio"] = np.mean(y_pred) / np.std(y_pred)

    elif task_type == "classification":
        # For binary classification
        if len(np.unique(y_true)) <= 2:
            metrics["accuracy"] = accuracy_score(
                y_true, np.round(y_pred), sample_weight=sample_weights
            )
            metrics["precision"] = precision_score(
                y_true, np.round(y_pred), sample_weight=sample_weights
            )
            metrics["recall"] = recall_score(
                y_true, np.round(y_pred), sample_weight=sample_weights
            )
            metrics["f1"] = f1_score(
                y_true, np.round(y_pred), sample_weight=sample_weights
            )

            # AUC and log loss require probability estimates
            if np.all((y_pred >= 0) & (y_pred <= 1)):
                metrics["auc"] = roc_auc_score(
                    y_true, y_pred, sample_weight=sample_weights
                )
                metrics["log_loss"] = log_loss(
                    y_true, y_pred, sample_weight=sample_weights
                )

        # For multi-class classification
        else:
            metrics["accuracy"] = accuracy_score(
                y_true, np.argmax(y_pred, axis=1), sample_weight=sample_weights
            )
            metrics["precision_macro"] = precision_score(
                y_true,
                np.argmax(y_pred, axis=1),
                average="macro",
                sample_weight=sample_weights,
            )
            metrics["recall_macro"] = recall_score(
                y_true,
                np.argmax(y_pred, axis=1),
                average="macro",
                sample_weight=sample_weights,
            )
            metrics["f1_macro"] = f1_score(
                y_true,
                np.argmax(y_pred, axis=1),
                average="macro",
                sample_weight=sample_weights,
            )

    elif task_type == "ranking":
        # Spearman rank correlation
        metrics["spearman_corr"] = pd.Series(y_pred).corr(
            pd.Series(y_true), method="spearman"
        )

        # Information coefficient (IC)
        metrics["ic"] = information_coefficient(y_true, y_pred)

        # Rank IC
        metrics["rank_ic"] = information_coefficient(y_true, y_pred, rank=True)

    # Add custom metrics if provided
    if custom_metrics:
        for name, metric_fn in custom_metrics.items():
            metrics[name] = metric_fn(y_true, y_pred, sample_weight=sample_weights)

    return metrics


def sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    period: str = "daily",
    annualization: Optional[float] = None,
) -> float:
    """
    Calculate the Sharpe ratio of a returns series.

    Parameters
    ----------
    returns : array-like
        Returns series.
    risk_free_rate : float, default=0.0
        Risk-free rate.
    period : str, default='daily'
        Frequency of returns. Options: 'daily', 'weekly', 'monthly', 'quarterly', 'annual'.
    annualization : float, optional
        Number of periods in a year. If None, inferred from period.

    Returns
    -------
    sharpe : float
        Sharpe ratio.
    """
    if annualization is None:
        if period == "daily":
            annualization = 252
        elif period == "weekly":
            annualization = 52
        elif period == "monthly":
            annualization = 12
        elif period == "quarterly":
            annualization = 4
        elif period == "annual":
            annualization = 1
        else:
            raise ValueError(f"Unknown period: {period}")

    excess_returns = returns - risk_free_rate
    return np.sqrt(annualization) * np.mean(excess_returns) / np.std(excess_returns)


def sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    period: str = "daily",
    annualization: Optional[float] = None,
    target_return: float = 0.0,
) -> float:
    """
    Calculate the Sortino ratio of a returns series.

    Parameters
    ----------
    returns : array-like
        Returns series.
    risk_free_rate : float, default=0.0
        Risk-free rate.
    period : str, default='daily'
        Frequency of returns. Options: 'daily', 'weekly', 'monthly', 'quarterly', 'annual'.
    annualization : float, optional
        Number of periods in a year. If None, inferred from period.
    target_return : float, default=0.0
        Minimum acceptable return.

    Returns
    -------
    sortino : float
        Sortino ratio.
    """
    if annualization is None:
        if period == "daily":
            annualization = 252
        elif period == "weekly":
            annualization = 52
        elif period == "monthly":
            annualization = 12
        elif period == "quarterly":
            annualization = 4
        elif period == "annual":
            annualization = 1
        else:
            raise ValueError(f"Unknown period: {period}")

    excess_returns = returns - risk_free_rate
    downside_returns = excess_returns.copy()
    downside_returns[downside_returns > target_return] = 0

    downside_deviation = np.sqrt(np.mean(downside_returns**2))

    if downside_deviation == 0:
        return np.inf if np.mean(excess_returns) >= 0 else -np.inf

    return np.sqrt(annualization) * np.mean(excess_returns) / downside_deviation


def calmar_ratio(
    returns: np.ndarray, period: str = "daily", annualization: Optional[float] = None
) -> float:
    """
    Calculate the Calmar ratio of a returns series.

    Parameters
    ----------
    returns : array-like
        Returns series.
    period : str, default='daily'
        Frequency of returns. Options: 'daily', 'weekly', 'monthly', 'quarterly', 'annual'.
    annualization : float, optional
        Number of periods in a year. If None, inferred from period.

    Returns
    -------
    calmar : float
        Calmar ratio.
    """
    if annualization is None:
        if period == "daily":
            annualization = 252
        elif period == "weekly":
            annualization = 52
        elif period == "monthly":
            annualization = 12
        elif period == "quarterly":
            annualization = 4
        elif period == "annual":
            annualization = 1
        else:
            raise ValueError(f"Unknown period: {period}")

    max_dd = maximum_drawdown(returns)

    if max_dd == 0:
        return np.inf if np.mean(returns) >= 0 else -np.inf

    return annualization * np.mean(returns) / abs(max_dd)


def maximum_drawdown(returns: np.ndarray) -> float:
    """
    Calculate the maximum drawdown of a returns series.

    Parameters
    ----------
    returns : array-like
        Returns series.

    Returns
    -------
    max_dd : float
        Maximum drawdown.
    """
    # Convert returns to cumulative returns
    cum_returns = (1 + np.array(returns)).cumprod()

    # Calculate running maximum
    running_max = np.maximum.accumulate(cum_returns)

    # Calculate drawdown
    drawdown = cum_returns / running_max - 1

    # Return the minimum (maximum drawdown)
    return np.min(drawdown)


def information_coefficient(
    factor_values: np.ndarray, forward_returns: np.ndarray, rank: bool = False
) -> float:
    """
    Calculate the Information Coefficient (IC) between factor values and forward returns.

    Parameters
    ----------
    factor_values : array-like
        Factor values.
    forward_returns : array-like
        Forward returns.
    rank : bool, default=False
        Whether to use rank correlation (Spearman) instead of Pearson correlation.

    Returns
    -------
    ic : float
        Information Coefficient.
    """
    if len(factor_values) != len(forward_returns):
        raise ValueError("factor_values and forward_returns must have the same length")

    # Remove NaN values
    mask = ~(np.isnan(factor_values) | np.isnan(forward_returns))
    factor_values = factor_values[mask]
    forward_returns = forward_returns[mask]

    if len(factor_values) == 0:
        return np.nan

    if rank:
        # Spearman rank correlation
        return pd.Series(factor_values).corr(
            pd.Series(forward_returns), method="spearman"
        )
    else:
        # Pearson correlation
        return np.corrcoef(factor_values, forward_returns)[0, 1]
