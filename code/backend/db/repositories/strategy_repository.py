"""Strategy repository - domain queries for trading strategies."""

from __future__ import annotations

from typing import Sequence

from db.models.strategy import Strategy
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class StrategyRepository(BaseRepository[Strategy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Strategy, session)

    async def get_active(self) -> Sequence[Strategy]:
        """Return all strategies with status == 'active'."""
        stmt = (
            select(Strategy)
            .where(Strategy.status == "active")
            .order_by(Strategy.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Strategy | None:
        """Return a strategy by its unique name."""
        stmt = select(Strategy).where(Strategy.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()
