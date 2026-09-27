"""Risk management router - VaR, stress tests, correlation, and radar."""

from typing import Any, Dict, List, Optional

from app.services import RiskService, get_risk_service
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RiskMetrics(BaseModel):
    var: float
    cvar: float
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=RiskMetrics)
async def get_risk_metrics(
    portfolioId: Optional[str] = Query(None),
    svc: RiskService = Depends(get_risk_service),
) -> Dict[str, Any]:
    """Return dynamically computed portfolio risk metrics."""
    return await svc.get_risk_metrics(portfolio_id=portfolioId or "port-001")


@router.get("/stress-scenarios", response_model=List[StressScenario])
async def get_stress_scenarios(
    portfolioId: Optional[str] = Query(None),
    svc: RiskService = Depends(get_risk_service),
) -> List[Dict[str, Any]]:
    """Return stress test results applied to current NAV."""
    return await svc.get_stress_scenarios(portfolio_id=portfolioId or "port-001")


@router.get("/correlation-matrix")
async def get_correlation_matrix(
    portfolioId: Optional[str] = Query(None),
    svc: RiskService = Depends(get_risk_service),
) -> List[Dict[str, Any]]:
    """Return pairwise correlation matrix for all held assets."""
    return await svc.get_correlation_matrix(portfolio_id=portfolioId or "port-001")


@router.get("/radar")
async def get_risk_radar(
    portfolioId: Optional[str] = Query(None),
    svc: RiskService = Depends(get_risk_service),
) -> List[Dict[str, Any]]:
    """Return risk radar chart data computed from live positions."""
    return await svc.get_risk_radar(portfolio_id=portfolioId or "port-001")
