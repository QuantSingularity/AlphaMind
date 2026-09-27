"""Trading strategies router - full CRUD + activate/deactivate + backtests."""

from typing import Any, Dict, List, Optional

from app.services import StrategyService, get_strategy_service
from app.services.strategy_service import run_backtest_in_background
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class StrategyCreate(BaseModel):
    name: str
    description: str
    type: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class BacktestRequest(BaseModel):
    strategyId: str
    startDate: str
    endDate: str
    initialCapital: float


# ---------------------------------------------------------------------------
# Strategy routes
# ---------------------------------------------------------------------------


@router.get("/")
async def list_strategies(
    svc: StrategyService = Depends(get_strategy_service),
) -> List[Dict[str, Any]]:
    """Return all trading strategies."""
    return await svc.list_strategies()


@router.post("/", status_code=201)
async def create_strategy(
    payload: StrategyCreate,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Create a new trading strategy."""
    return await svc.create_strategy(
        name=payload.name,
        description=payload.description,
        strategy_type=payload.type,
        parameters=payload.parameters,
    )


@router.post("/backtest", status_code=202)
async def run_backtest(
    payload: BacktestRequest,
    background_tasks: BackgroundTasks,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """
    Submit a backtest job.

    The run is created with status 'pending' and actually executed by
    run_backtest_in_background as a FastAPI background task, moving it
    through 'running' to 'completed'/'failed'. Returns the backtest
    record immediately (HTTP 202 Accepted); poll GET /backtests/{id} for
    the result.
    """
    strategy = await svc.get_strategy(payload.strategyId)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    backtest = await svc.create_backtest(
        strategy_id=payload.strategyId,
        start_date=payload.startDate,
        end_date=payload.endDate,
        initial_capital=payload.initialCapital,
    )
    background_tasks.add_task(
        run_backtest_in_background,
        backtest_id=backtest["id"],
        strategy_id=payload.strategyId,
        start_date=payload.startDate,
        end_date=payload.endDate,
        initial_capital=payload.initialCapital,
    )
    return backtest


@router.get("/backtests/{backtest_id}")
async def get_backtest(
    backtest_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Return a single backtest run by ID."""
    run = await svc.get_backtest(backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


# NOTE: Routes with path parameters must come AFTER all fixed-path routes
# at the same segment depth so FastAPI never shadows them.


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Return a single strategy by ID."""
    s = await svc.get_strategy(strategy_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@router.patch("/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdate,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Partially update a strategy's metadata or parameters."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    result = await svc.update_strategy(strategy_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return result


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> None:
    """Permanently delete a strategy."""
    deleted = await svc.delete_strategy(strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")


@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Set strategy status to active."""
    result = await svc.activate_strategy(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return result


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Set strategy status to paused."""
    result = await svc.deactivate_strategy(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return result


@router.get("/{strategy_id}/backtests")
async def get_backtests(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> List[Dict[str, Any]]:
    """Return all backtest runs for a strategy."""
    return await svc.get_backtests(strategy_id)


@router.get("/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Return the performance metrics block for a strategy."""
    perf = await svc.get_performance(strategy_id)
    if perf is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return perf


@router.get("/{strategy_id}/equity-curve")
async def get_strategy_equity_curve(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> Dict[str, Any]:
    """Return a deterministic equity curve (value + benchmark) for a strategy."""
    curve = await svc.get_equity_curve(strategy_id)
    if curve is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return curve
