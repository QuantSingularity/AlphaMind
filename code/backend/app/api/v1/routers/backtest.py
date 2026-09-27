"""Backtesting router - run and retrieve backtest results.

POST /api/v1/backtest/ is the endpoint the web/mobile frontends actually
call. It used to return entirely canned numbers from a hardcoded
per-strategy lookup table (_STRATEGY_PERF below) - no simulation of any
kind ran, and ai_models was never touched. It's now backed by
app.services.backtest_runner.run_backtest_detailed, which genuinely
simulates the strategy (training a real ai_models agent/forecaster for
rl_agent/ml_alpha, or running rule-based logic for momentum/mean_reversion)
and returns real results, including the equityCurve the frontend's
Backtest page charts (see BacktestResult below - equityCurve was missing
from this model entirely, so even though the old canned implementation
computed one via _generate_equity_curve, FastAPI's response_model
filtering silently dropped it from every response and the chart never had
data).
"""

import uuid
from typing import List

from app.services import StrategyService, get_strategy_service
from app.services.backtest_runner import run_backtest_detailed
from fastapi import APIRouter, Depends, HTTPException
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


class EquityPoint(BaseModel):
    date: str
    equity: float
    benchmark: float
    drawdown: float


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
    equityCurve: List[EquityPoint] = []


_BACKTEST_STORE: List[dict] = []


@router.post("/", response_model=BacktestResult, status_code=201)
async def run_backtest(
    payload: BacktestRequest,
    svc: StrategyService = Depends(get_strategy_service),
):
    """Run a backtest for a strategy.

    This is synchronous - training a small ai_models agent/forecaster for
    rl_agent/ml_alpha strategies takes anywhere from under a second to
    tens of seconds depending on the strategy's `episodes`/`epochs`
    parameters, so this call can be slow. For a fire-and-forget flow with
    polling instead, see POST /api/v1/strategies/backtest.
    """
    strategy = await svc.get_strategy(payload.strategyId)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    try:
        metrics = run_backtest_detailed(
            strategy_type=strategy["type"],
            parameters=strategy["parameters"],
            start_date=payload.startDate,
            end_date=payload.endDate,
            initial_capital=payload.initialCapital,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = {
        "id": f"bt-{uuid.uuid4().hex[:8]}",
        "strategyId": payload.strategyId,
        "startDate": payload.startDate,
        "endDate": payload.endDate,
        "initialCapital": payload.initialCapital,
        **metrics,
    }
    _BACKTEST_STORE.append(result)
    return result


@router.get("/{strategy_id}", response_model=List[BacktestResult])
async def get_backtest_results(strategy_id: str):
    """Return all backtest results for a strategy."""
    return [r for r in _BACKTEST_STORE if r["strategyId"] == strategy_id]
