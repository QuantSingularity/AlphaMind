"""Portfolio management router."""

import math
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic models matching the TypeScript types in web-frontend/src/types
# ---------------------------------------------------------------------------


class AssetAllocation(BaseModel):
    ticker: str
    value: float
    percentage: float


class Position(BaseModel):
    id: str
    ticker: str
    sector: str
    quantity: float
    entryPrice: float
    currentPrice: float
    unrealizedPnL: float
    realizedPnL: float
    weight: float
    beta: float
    sharpeContrib: float
    var95: float
    timestamp: str


class Portfolio(BaseModel):
    id: str
    name: str
    totalValue: float
    cash: float
    dailyPnL: float
    totalPnL: float
    allocation: List[AssetAllocation]


# ---------------------------------------------------------------------------
# In-memory store (replace with DB layer in production)
# ---------------------------------------------------------------------------

_POSITIONS: List[dict] = [
    {
        "id": "pos-001",
        "ticker": "AAPL",
        "sector": "Technology",
        "quantity": 100.0,
        "entryPrice": 150.0,
        "currentPrice": 175.5,
        "unrealizedPnL": 2550.0,
        "realizedPnL": 0.0,
        "weight": 0.28,
        "beta": 1.21,
        "sharpeContrib": 0.42,
        "var95": 1240.0,
        "timestamp": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z",
    },
    {
        "id": "pos-002",
        "ticker": "MSFT",
        "sector": "Technology",
        "quantity": 50.0,
        "entryPrice": 300.0,
        "currentPrice": 338.0,
        "unrealizedPnL": 1900.0,
        "realizedPnL": 0.0,
        "weight": 0.27,
        "beta": 0.92,
        "sharpeContrib": 0.38,
        "var95": 980.0,
        "timestamp": (datetime.utcnow() - timedelta(days=25)).isoformat() + "Z",
    },
    {
        "id": "pos-003",
        "ticker": "GOOGL",
        "sector": "Communication",
        "quantity": 25.0,
        "entryPrice": 2800.0,
        "currentPrice": 2950.0,
        "unrealizedPnL": 3750.0,
        "realizedPnL": 0.0,
        "weight": 0.19,
        "beta": 1.05,
        "sharpeContrib": 0.29,
        "var95": 1560.0,
        "timestamp": (datetime.utcnow() - timedelta(days=20)).isoformat() + "Z",
    },
    {
        "id": "pos-004",
        "ticker": "TSLA",
        "sector": "Consumer Disc.",
        "quantity": 30.0,
        "entryPrice": 700.0,
        "currentPrice": 742.0,
        "unrealizedPnL": 1260.0,
        "realizedPnL": 0.0,
        "weight": 0.11,
        "beta": 1.89,
        "sharpeContrib": 0.14,
        "var95": 2100.0,
        "timestamp": (datetime.utcnow() - timedelta(days=15)).isoformat() + "Z",
    },
    {
        "id": "pos-005",
        "ticker": "JPM",
        "sector": "Financials",
        "quantity": 80.0,
        "entryPrice": 130.0,
        "currentPrice": 148.25,
        "unrealizedPnL": 1460.0,
        "realizedPnL": 0.0,
        "weight": 0.15,
        "beta": 0.78,
        "sharpeContrib": 0.22,
        "var95": 680.0,
        "timestamp": (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z",
    },
]


def _compute_portfolio() -> dict:
    total_pos_value = sum(p["quantity"] * p["currentPrice"] for p in _POSITIONS)
    cash = 25430.50
    total_value = total_pos_value + cash
    daily_pnl = sum(p["unrealizedPnL"] * 0.04 for p in _POSITIONS)
    total_pnl = sum(p["unrealizedPnL"] for p in _POSITIONS)
    allocation = [
        {
            "ticker": p["ticker"],
            "value": round(p["quantity"] * p["currentPrice"], 2),
            "percentage": round(
                (p["quantity"] * p["currentPrice"] / total_value) * 100, 2
            ),
        }
        for p in _POSITIONS
    ]
    return {
        "id": "port-001",
        "name": "AlphaMind Main Portfolio",
        "totalValue": round(total_value, 2),
        "cash": cash,
        "dailyPnL": round(daily_pnl, 2),
        "totalPnL": round(total_pnl, 2),
        "allocation": allocation,
    }


def _generate_equity_curve(days: int = 90) -> List[dict]:
    """Generate deterministic equity curve from portfolio drift."""
    base = 100_000.0
    total_pnl = sum(p["unrealizedPnL"] for p in _POSITIONS)
    daily_drift = total_pnl / max(days, 1) / base
    points = []
    value = base
    for i in range(days):
        noise = math.sin(i * 0.3) * 0.002 + math.cos(i * 0.7) * 0.001
        value *= 1 + daily_drift + noise
        ts = (datetime.utcnow() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        points.append({"timestamp": ts, "value": round(value, 2)})
    return points


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=Portfolio)
async def get_portfolio():
    """Return current portfolio summary."""
    return _compute_portfolio()


@router.get("/holdings")
async def get_holdings():
    """Return simplified holdings list (used by mobile)."""
    return [
        {
            "symbol": p["ticker"],
            "shares": p["quantity"],
            "value": round(p["quantity"] * p["currentPrice"], 2),
            "weight": round(p["weight"] * 100, 2),
        }
        for p in _POSITIONS
    ]


@router.get("/performance")
async def get_performance(timeframe: str = Query("1M")):
    """Return portfolio performance metrics and equity curve."""
    days_map = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 252}
    days = days_map.get(timeframe, 30)
    return {
        "equityCurve": _generate_equity_curve(days),
        "metrics": {
            "sharpeRatio": 2.31,
            "maxDrawdown": -0.089,
            "annualisedReturn": 0.384,
            "volatility": 0.142,
            "alpha": 0.094,
            "beta": 0.88,
            "totalReturn": round(
                sum(p["unrealizedPnL"] for p in _POSITIONS) / 100_000, 4
            ),
            "winRate": 0.64,
        },
    }


@router.get("/positions", response_model=List[Position])
async def get_positions():
    """Return all open positions."""
    return _POSITIONS


@router.get("/positions/{position_id}", response_model=Position)
async def get_position(position_id: str):
    """Return a single position by ID."""
    pos = next((p for p in _POSITIONS if p["id"] == position_id), None)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return pos


@router.post("/positions/{position_id}/close")
async def close_position(position_id: str):
    """Close a position."""
    global _POSITIONS
    pos = next((p for p in _POSITIONS if p["id"] == position_id), None)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    _POSITIONS = [p for p in _POSITIONS if p["id"] != position_id]
    return {
        "message": f"Position {position_id} closed successfully",
        "realizedPnL": pos["unrealizedPnL"],
    }
