"""BacktestRun repository - domain queries for backtest results."""

from __future__ import annotations

from typing import Sequence

from db.models.backtest import BacktestRun
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BacktestRepository(BaseRepository[BacktestRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BacktestRun, session)

    async def get_by_strategy(self, strategy_id: str) -> Sequence[BacktestRun]:
        """Return all backtest runs for a given strategy, newest first."""
        stmt = (
            select(BacktestRun)
            .where(BacktestRun.strategy_id == strategy_id)
            .order_by(BacktestRun.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest(self, strategy_id: str) -> BacktestRun | None:
        """Return the most recent completed backtest for a strategy."""
        stmt = (
            select(BacktestRun)
            .where(BacktestRun.strategy_id == strategy_id)
            .where(BacktestRun.status == "completed")
            .order_by(BacktestRun.completed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
