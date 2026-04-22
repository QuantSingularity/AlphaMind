"""Backtesting router — run and retrieve backtest results."""

import math
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BacktestRequest(BaseModel):
    strategyId: str
    startDate: str
    endDate: str
    initialCapital: float
    benchmark: str = "SPY"
    transactionCost: float = 0.0005
    slippage: float = 0.0002


class TradeRecord(BaseModel):
    date: str
    ticker: str
    side: str
    qty: float
    price: float
    pnl: float


class BacktestResult(BaseModel):
    id: str
    strategyId: str
    startDate: str
    endDate: str
    initialCapital: float
    finalCapital: float
    totalReturn: float
    annualisedReturn: float
    sharpeRatio: float
    sortinoRatio: float
    calmarRatio: float
    maxDrawdown: float
    maxDrawdownDuration: int = 0  # default so older callers don't break
    winRate: float
    profitFactor: float
    totalTrades: int
    avgWin: float
    avgLoss: float
    bestMonth: float
    worstMonth: float


# Strategy performance lookup (deterministic values)
_STRATEGY_PERF = {
    "strat-001": {
        "totalReturn": 0.487,
        "annualisedReturn": 0.384,
        "sharpeRatio": 2.31,
        "sortinoRatio": 3.18,
        "calmarRatio": 4.07,
        "maxDrawdown": -0.089,
        "winRate": 0.642,
        "profitFactor": 3.8,
        "totalTrades": 312,
        "avgWin": 1420.0,
        "avgLoss": -520.0,
        "bestMonth": 0.118,
        "worstMonth": -0.031,
    },
    "strat-002": {
        "totalReturn": 0.297,
        "annualisedReturn": 0.248,
        "sharpeRatio": 1.94,
        "sortinoRatio": 2.67,
        "calmarRatio": 2.33,
        "maxDrawdown": -0.127,
        "winRate": 0.591,
        "profitFactor": 2.9,
        "totalTrades": 421,
        "avgWin": 980.0,
        "avgLoss": -430.0,
        "bestMonth": 0.087,
        "worstMonth": -0.048,
    },
    "strat-003": {
        "totalReturn": 0.432,
        "annualisedReturn": 0.362,
        "sharpeRatio": 2.71,
        "sortinoRatio": 3.72,
        "calmarRatio": 5.59,
        "maxDrawdown": -0.077,
        "winRate": 0.674,
        "profitFactor": 4.2,
        "totalTrades": 284,
        "avgWin": 1680.0,
        "avgLoss": -490.0,
        "bestMonth": 0.132,
        "worstMonth": -0.024,
    },
    "strat-004": {
        "totalReturn": 0.226,
        "annualisedReturn": 0.192,
        "sharpeRatio": 1.72,
        "sortinoRatio": 2.31,
        "calmarRatio": 1.46,
        "maxDrawdown": -0.154,
        "winRate": 0.553,
        "profitFactor": 2.4,
        "totalTrades": 518,
        "avgWin": 760.0,
        "avgLoss": -380.0,
        "bestMonth": 0.071,
        "worstMonth": -0.062,
    },
}

_BACKTEST_STORE: List[dict] = []


def _generate_equity_curve(
    start_date: str,
    end_date: str,
    initial_capital: float,
    total_return: float,
    vol: float = 0.015,
) -> List[dict]:
    start = datetime.fromisoformat(start_date.replace("Z", ""))
    end = datetime.fromisoformat(end_date.replace("Z", ""))
    days = max((end - start).days, 1)
    daily_return = math.pow(1 + total_return, 1 / days) - 1

    equity = initial_capital
    bench = initial_capital
    points = []
    for i in range(days):
        noise = math.sin(i * 0.29) * vol + math.cos(i * 0.63) * vol * 0.5
        equity *= 1 + daily_return + noise
        bench *= 1 + math.sin(i * 0.38) * 0.004 + 0.0003
        drawdown = min(
            0.0, (equity - initial_capital * (1 + total_return * i / days)) / equity
        )
        ts = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        points.append(
            {
                "date": ts,
                "equity": round(equity, 2),
                "benchmark": round(bench, 2),
                "drawdown": round(drawdown * 100, 3),
            }
        )
    return points


@router.post("/", response_model=BacktestResult, status_code=201)
async def run_backtest(payload: BacktestRequest):
    """Run a backtest for a strategy."""
    perf = _STRATEGY_PERF.get(
        payload.strategyId,
        {
            "totalReturn": 0.15,
            "annualisedReturn": 0.13,
            "sharpeRatio": 1.2,
            "sortinoRatio": 1.5,
            "calmarRatio": 1.1,
            "maxDrawdown": -0.10,
            "winRate": 0.55,
            "profitFactor": 1.8,
            "totalTrades": 200,
            "avgWin": 800.0,
            "avgLoss": -400.0,
            "bestMonth": 0.06,
            "worstMonth": -0.04,
        },
    )

    result_id = f"bt-{uuid.uuid4().hex[:8]}"
    final_capital = round(payload.initialCapital * (1 + perf["totalReturn"]), 2)

    result = {
        "id": result_id,
        "strategyId": payload.strategyId,
        "startDate": payload.startDate,
        "endDate": payload.endDate,
        "initialCapital": payload.initialCapital,
        "finalCapital": final_capital,
        "equityCurve": _generate_equity_curve(
            payload.startDate,
            payload.endDate,
            payload.initialCapital,
            perf["totalReturn"],
        ),
        **perf,
    }
    _BACKTEST_STORE.append(result)
    return result


@router.get("/{strategy_id}", response_model=List[BacktestResult])
async def get_backtest_results(strategy_id: str):
    """Return all backtest results for a strategy."""
    return [r for r in _BACKTEST_STORE if r["strategyId"] == strategy_id]
