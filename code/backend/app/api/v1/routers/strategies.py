"""Trading strategies router — full CRUD + activate/deactivate + performance."""

import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class StrategyPerformance(BaseModel):
    sharpeRatio: float
    maxDrawdown: float
    profitFactor: float
    winRate: float
    totalReturn: float
    volatility: float
    alpha: float
    beta: float


class StrategyParameters(BaseModel):
    class Config:
        extra = "allow"


class Strategy(BaseModel):
    id: str
    name: str
    description: str
    type: str
    status: str
    performance: StrategyPerformance
    parameters: Dict[str, Any]
    createdAt: str
    updatedAt: str


class StrategyCreate(BaseModel):
    name: str
    description: str
    type: str
    parameters: Optional[Dict[str, Any]] = {}


class BacktestRequest(BaseModel):
    strategyId: str
    startDate: str
    endDate: str
    initialCapital: float


class BacktestResult(BaseModel):
    id: str
    strategyId: str
    startDate: str
    endDate: str
    initialCapital: float
    finalCapital: float
    totalReturn: float
    sharpeRatio: float
    maxDrawdown: float
    totalTrades: int
    winRate: float


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_STRATEGIES: List[dict] = [
    {
        "id": "strat-001",
        "name": "TFT Alpha Strategy",
        "description": (
            "Temporal Fusion Transformer multi-horizon forecasting with "
            "attention-based feature selection across 47 financial indicators."
        ),
        "type": "TFT",
        "status": "active",
        "performance": {
            "sharpeRatio": 2.31,
            "maxDrawdown": -0.089,
            "profitFactor": 3.8,
            "winRate": 0.64,
            "totalReturn": 0.487,
            "volatility": 0.142,
            "alpha": 0.094,
            "beta": 0.88,
        },
        "parameters": {
            "lookback": 60,
            "horizon": 5,
            "n_heads": 8,
            "dropout": 0.1,
            "lr": 0.0003,
        },
        "createdAt": "2023-11-01T00:00:00Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
    },
    {
        "id": "strat-002",
        "name": "RL Portfolio Optimizer",
        "description": (
            "Deep Deterministic Policy Gradient (DDPG) agent optimizing "
            "continuous portfolio weights across 20 liquid equities with "
            "transaction cost awareness."
        ),
        "type": "RL",
        "status": "active",
        "performance": {
            "sharpeRatio": 1.94,
            "maxDrawdown": -0.127,
            "profitFactor": 2.9,
            "winRate": 0.59,
            "totalReturn": 0.297,
            "volatility": 0.168,
            "alpha": 0.071,
            "beta": 0.93,
        },
        "parameters": {
            "actor_lr": 0.0001,
            "critic_lr": 0.001,
            "gamma": 0.99,
            "tau": 0.005,
            "buffer_size": 100000,
        },
        "createdAt": "2023-09-15T00:00:00Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
    },
    {
        "id": "strat-003",
        "name": "Hybrid ML Ensemble",
        "description": (
            "Ensemble of TFT, DDPG, and gradient-boosted trees with dynamic "
            "weight allocation via Bayesian model averaging."
        ),
        "type": "HYBRID",
        "status": "active",
        "performance": {
            "sharpeRatio": 2.71,
            "maxDrawdown": -0.077,
            "profitFactor": 4.2,
            "winRate": 0.674,
            "totalReturn": 0.432,
            "volatility": 0.131,
            "alpha": 0.118,
            "beta": 0.85,
        },
        "parameters": {
            "n_models": 3,
            "rebalance_freq": "weekly",
            "min_weight": 0.1,
            "max_weight": 0.6,
        },
        "createdAt": "2024-01-10T00:00:00Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
    },
    {
        "id": "strat-004",
        "name": "Sentiment Momentum",
        "description": (
            "NLP-driven momentum strategy combining SEC 8-K filings sentiment, "
            "social media signals, and price momentum for signal generation."
        ),
        "type": "SENTIMENT",
        "status": "inactive",
        "performance": {
            "sharpeRatio": 1.72,
            "maxDrawdown": -0.154,
            "profitFactor": 2.4,
            "winRate": 0.553,
            "totalReturn": 0.226,
            "volatility": 0.189,
            "alpha": 0.052,
            "beta": 1.02,
        },
        "parameters": {
            "sentiment_window": 5,
            "momentum_lookback": 20,
            "min_sentiment_score": 0.6,
            "position_size": 0.05,
        },
        "createdAt": "2024-03-01T00:00:00Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
    },
]

_BACKTEST_RESULTS: List[dict] = []


def _generate_equity_curve(
    total_return: float, volatility: float, days: int = 252
) -> List[dict]:
    """Generate deterministic equity curve for a strategy."""
    equity = 100.0
    bench = 100.0
    daily_return = math.pow(1 + total_return, 1 / days) - 1
    points = []
    for i in range(days):
        noise = (
            math.sin(i * 0.25) * volatility * 0.15
            + math.cos(i * 0.6) * volatility * 0.1
        )
        equity *= 1 + daily_return + noise
        bench *= 1 + math.sin(i * 0.4) * 0.004 + 0.0003
        ts = (datetime.utcnow() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        points.append(
            {
                "day": i,
                "value": round(equity, 2),
                "benchmark": round(bench, 2),
            }
        )
    return points


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[Strategy])
async def get_strategies():
    """Return all trading strategies."""
    return _STRATEGIES


@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy(strategy_id: str):
    """Return a single strategy with performance and equity curve."""
    s = next((s for s in _STRATEGIES if s["id"] == strategy_id), None)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@router.get("/{strategy_id}/equity-curve")
async def get_strategy_equity_curve(strategy_id: str):
    """Return equity curve data for chart rendering."""
    s = next((s for s in _STRATEGIES if s["id"] == strategy_id), None)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {
        "strategyId": strategy_id,
        "equityCurve": _generate_equity_curve(
            s["performance"]["totalReturn"],
            s["performance"]["volatility"],
        ),
    }


@router.post("/", response_model=Strategy, status_code=201)
async def create_strategy(payload: StrategyCreate):
    """Create a new strategy."""
    new_id = f"strat-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat() + "Z"
    strategy = {
        "id": new_id,
        "name": payload.name,
        "description": payload.description,
        "type": payload.type,
        "status": "inactive",
        "performance": {
            "sharpeRatio": 0.0,
            "maxDrawdown": 0.0,
            "profitFactor": 0.0,
            "winRate": 0.0,
            "totalReturn": 0.0,
            "volatility": 0.0,
            "alpha": 0.0,
            "beta": 1.0,
        },
        "parameters": payload.parameters or {},
        "createdAt": now,
        "updatedAt": now,
    }
    _STRATEGIES.append(strategy)
    return strategy


@router.put("/{strategy_id}", response_model=Strategy)
async def update_strategy(strategy_id: str, payload: StrategyCreate):
    """Update an existing strategy."""
    s = next((s for s in _STRATEGIES if s["id"] == strategy_id), None)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    s["name"] = payload.name
    s["description"] = payload.description
    s["type"] = payload.type
    if payload.parameters:
        s["parameters"] = payload.parameters
    s["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    return s


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: str):
    """Delete a strategy."""
    global _STRATEGIES
    if not any(s["id"] == strategy_id for s in _STRATEGIES):
        raise HTTPException(status_code=404, detail="Strategy not found")
    _STRATEGIES = [s for s in _STRATEGIES if s["id"] != strategy_id]


@router.post("/{strategy_id}/activate", response_model=Strategy)
async def activate_strategy(strategy_id: str):
    """Set strategy status to active."""
    s = next((s for s in _STRATEGIES if s["id"] == strategy_id), None)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    s["status"] = "active"
    s["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    return s


@router.post("/{strategy_id}/deactivate", response_model=Strategy)
async def deactivate_strategy(strategy_id: str):
    """Set strategy status to inactive."""
    s = next((s for s in _STRATEGIES if s["id"] == strategy_id), None)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    s["status"] = "inactive"
    s["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    return s
