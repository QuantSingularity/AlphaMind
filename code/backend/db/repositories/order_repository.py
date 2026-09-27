"""Order repository - domain queries for trading orders."""

from __future__ import annotations

from typing import Sequence

from db.models.order import Order
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Order, session)

    async def get_pending(self, portfolio_id: str) -> Sequence[Order]:
        """Return all pending orders for a portfolio."""
        stmt = (
            select(Order)
            .where(Order.portfolio_id == portfolio_id)
            .where(Order.status == "pending")
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_portfolio(
        self,
        portfolio_id: str,
        *,
        limit: int = 100,
        status: str | None = None,
    ) -> Sequence[Order]:
        """Return orders for a portfolio, optionally filtered by status."""
        stmt = (
            select(Order)
            .where(Order.portfolio_id == portfolio_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Order.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()
