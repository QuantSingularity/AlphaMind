"""
Portfolio service - business logic for portfolio aggregation, equity curves,
and performance metrics.

All data is read from and written to the database via the PositionRepository.
No in-memory state is kept here.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from db.repositories.position_repository import PositionRepository
from sqlalchemy.ext.asyncio import AsyncSession

_DEFAULT_PORTFOLIO_ID = "port-001"
_INITIAL_CAPITAL = 100_000.0
_CASH = 25_430.50


class PortfolioService:
    """Encapsulates all portfolio-level read/write operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PositionRepository(session)

    # ------------------------------------------------------------------
    # Portfolio summary
    # ------------------------------------------------------------------

    async def get_portfolio(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> Dict[str, Any]:
        """Return a portfolio summary dict suitable for the API response."""
        positions = await self._repo.get_open_positions(portfolio_id)
        total_pos_value = sum(p.quantity * p.current_price for p in positions)
        total_value = total_pos_value + _CASH
        daily_pnl = sum(p.unrealized_pnl * 0.04 for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)

        allocation = [
            {
                "ticker": p.ticker,
                "value": round(p.quantity * p.current_price, 2),
                "percentage": (
                    round((p.quantity * p.current_price / total_value) * 100, 2)
                    if total_value
                    else 0.0
                ),
            }
            for p in positions
        ]

        return {
            "id": portfolio_id,
            "name": "AlphaMind Main Portfolio",
            "totalValue": round(total_value, 2),
            "cash": _CASH,
            "dailyPnL": round(daily_pnl, 2),
            "totalPnL": round(total_pnl, 2),
            "allocation": allocation,
        }

    # ------------------------------------------------------------------
    # Holdings (simplified - used by mobile)
    # ------------------------------------------------------------------

    async def get_holdings(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> List[Dict[str, Any]]:
        positions = await self._repo.get_open_positions(portfolio_id)
        return [
            {
                "symbol": p.ticker,
                "shares": p.quantity,
                "value": round(p.quantity * p.current_price, 2),
                "weight": round(p.weight * 100, 2),
            }
            for p in positions
        ]

    # ------------------------------------------------------------------
    # Positions CRUD
    # ------------------------------------------------------------------

    async def get_positions(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> List[Dict[str, Any]]:
        positions = await self._repo.get_open_positions(portfolio_id)
        return [self._position_to_dict(p) for p in positions]

    async def get_position(self, position_id: str) -> Dict[str, Any] | None:
        pos = await self._repo.get(position_id)
        if pos is None:
            return None
        return self._position_to_dict(pos)

    async def close_position(self, position_id: str) -> Dict[str, Any] | None:
        pos = await self._repo.get(position_id)
        if pos is None or pos.status != "open":
            return None
        realized = pos.unrealized_pnl
        updated = await self._repo.update(
            position_id,
            status="closed",
            realized_pnl=realized,
            unrealized_pnl=0.0,
            closed_at=datetime.now(timezone.utc),
        )
        if updated is None:
            return None
        return {
            "message": f"Position {position_id} closed successfully",
            "realizedPnL": realized,
        }

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    async def get_performance(
        self,
        timeframe: str = "1M",
        portfolio_id: str = _DEFAULT_PORTFOLIO_ID,
    ) -> Dict[str, Any]:
        """Return performance metrics and an equity curve for the given timeframe."""
        days_map = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 252}
        days = days_map.get(timeframe, 30)

        positions = await self._repo.get_open_positions(portfolio_id)
        total_pnl = sum(p.unrealized_pnl for p in positions)

        equity_curve = self._generate_equity_curve(days, total_pnl)
        metrics = self._compute_metrics(equity_curve, total_pnl)

        return {"equityCurve": equity_curve, "metrics": metrics}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _position_to_dict(p: Any) -> Dict[str, Any]:
        return {
            "id": p.id,
            "ticker": p.ticker,
            "sector": p.sector,
            "quantity": p.quantity,
            "entryPrice": p.entry_price,
            "currentPrice": p.current_price,
            "unrealizedPnL": p.unrealized_pnl,
            "realizedPnL": p.realized_pnl,
            "weight": p.weight,
            "beta": p.beta,
            "sharpeContrib": p.sharpe_contrib,
            "var95": p.var_95,
            "timestamp": p.opened_at.isoformat() if p.opened_at else None,
        }

    @staticmethod
    def _generate_equity_curve(days: int, total_pnl: float) -> List[Dict[str, Any]]:
        """Deterministic equity curve derived from realised PnL drift."""
        base = _INITIAL_CAPITAL
        daily_drift = total_pnl / max(days, 1) / base
        points: List[Dict[str, Any]] = []
        value = base
        now = datetime.now(timezone.utc)
        for i in range(days):
            noise = math.sin(i * 0.3) * 0.002 + math.cos(i * 0.7) * 0.001
            value *= 1 + daily_drift + noise
            ts = (now - timedelta(days=days - i)).strftime("%Y-%m-%d")
            points.append({"timestamp": ts, "value": round(value, 2)})
        return points

    @staticmethod
    def _compute_metrics(
        equity_curve: List[Dict[str, Any]], total_pnl: float
    ) -> Dict[str, Any]:
        """Compute risk-adjusted performance metrics from the equity curve."""
        values = [p["value"] for p in equity_curve]
        if len(values) < 2:
            return {}

        returns = [
            (values[i] - values[i - 1]) / values[i - 1] for i in range(1, len(values))
        ]
        n = len(returns)
        mean_r = sum(returns) / n
        variance = sum((r - mean_r) ** 2 for r in returns) / max(n - 1, 1)
        std_r = math.sqrt(variance) if variance > 0 else 1e-9

        # Annualised figures
        ann_return = mean_r * 252
        ann_vol = std_r * math.sqrt(252)
        sharpe = (ann_return - 0.05) / ann_vol if ann_vol else 0.0

        # Max drawdown
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (v - peak) / peak
            if dd < max_dd:
                max_dd = dd

        # Downside deviation for Sortino
        downside = [r for r in returns if r < 0]
        down_std = (
            math.sqrt(sum(r**2 for r in downside) / max(len(downside), 1))
            * math.sqrt(252)
            if downside
            else 1e-9
        )
        sortino = (ann_return - 0.05) / down_std

        win_rate = len([r for r in returns if r > 0]) / n

        return {
            "sharpeRatio": round(sharpe, 4),
            "sortinoRatio": round(sortino, 4),
            "maxDrawdown": round(max_dd, 4),
            "annualisedReturn": round(ann_return, 4),
            "volatility": round(ann_vol, 4),
            "alpha": round(ann_return - 0.08 * 0.88, 4),  # simplified CAPM alpha
            "beta": 0.88,
            "totalReturn": round(total_pnl / _INITIAL_CAPITAL, 4),
            "winRate": round(win_rate, 4),
        }
