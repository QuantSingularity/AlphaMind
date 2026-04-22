"""Risk management router — VaR, stress tests, and portfolio risk metrics."""

from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class RiskMetrics(BaseModel):
    var: float  # 1-day 95% Value at Risk (% of NAV)
    cvar: float  # Conditional VaR
    sharpeRatio: float
    sortinoRatio: float
    maxDrawdown: float
    beta: float
    correlation: float
    volatility: float


class StressScenario(BaseModel):
    name: str
    pnl: float
    duration: str
    recovery: str
    portfolioImpact: float


class CorrelationEntry(BaseModel):
    asset: str
    AAPL: float
    MSFT: float
    GOOGL: float
    TSLA: float
    JPM: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=RiskMetrics)
async def get_risk_metrics(portfolioId: Optional[str] = Query(None)):
    """Return current portfolio risk metrics."""
    return {
        "var": 1.38,
        "cvar": 1.92,
        "sharpeRatio": 2.31,
        "sortinoRatio": 3.18,
        "maxDrawdown": -0.089,
        "beta": 0.88,
        "correlation": 0.76,
        "volatility": 0.142,
    }


@router.get("/stress-scenarios", response_model=List[StressScenario])
async def get_stress_scenarios():
    """Return stress test results for historical scenarios."""
    return [
        {
            "name": "2020 COVID Crash",
            "pnl": -18420,
            "duration": "33 days",
            "recovery": "5 months",
            "portfolioImpact": -14.7,
        },
        {
            "name": "2022 Rate Shock",
            "pnl": -12810,
            "duration": "180 days",
            "recovery": "14 months",
            "portfolioImpact": -10.2,
        },
        {
            "name": "2008 GFC",
            "pnl": -44200,
            "duration": "512 days",
            "recovery": "4.5 years",
            "portfolioImpact": -35.3,
        },
        {
            "name": "2000 Dot-com",
            "pnl": -31900,
            "duration": "929 days",
            "recovery": "7 years",
            "portfolioImpact": -25.5,
        },
        {
            "name": "1987 Black Monday",
            "pnl": -9870,
            "duration": "1 day",
            "recovery": "2 years",
            "portfolioImpact": -7.9,
        },
        {
            "name": "+3σ Vol Spike",
            "pnl": -7240,
            "duration": "5 days",
            "recovery": "3 weeks",
            "portfolioImpact": -5.8,
        },
    ]


@router.get("/correlation-matrix", response_model=List[CorrelationEntry])
async def get_correlation_matrix():
    """Return asset correlation matrix."""
    return [
        {
            "asset": "AAPL",
            "AAPL": 1.0,
            "MSFT": 0.82,
            "GOOGL": 0.76,
            "TSLA": 0.58,
            "JPM": 0.41,
        },
        {
            "asset": "MSFT",
            "AAPL": 0.82,
            "MSFT": 1.0,
            "GOOGL": 0.79,
            "TSLA": 0.52,
            "JPM": 0.45,
        },
        {
            "asset": "GOOGL",
            "AAPL": 0.76,
            "MSFT": 0.79,
            "GOOGL": 1.0,
            "TSLA": 0.49,
            "JPM": 0.39,
        },
        {
            "asset": "TSLA",
            "AAPL": 0.58,
            "MSFT": 0.52,
            "GOOGL": 0.49,
            "TSLA": 1.0,
            "JPM": 0.28,
        },
        {
            "asset": "JPM",
            "AAPL": 0.41,
            "MSFT": 0.45,
            "GOOGL": 0.39,
            "TSLA": 0.28,
            "JPM": 1.0,
        },
    ]


@router.get("/radar")
async def get_risk_radar():
    """Return risk radar chart data."""
    return [
        {"metric": "Market Risk", "value": 72},
        {"metric": "Liquidity Risk", "value": 31},
        {"metric": "Concentration", "value": 58},
        {"metric": "Leverage", "value": 20},
        {"metric": "Tail Risk", "value": 44},
        {"metric": "Counterparty", "value": 15},
    ]
