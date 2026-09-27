"""Position repository - domain-specific queries on top of BaseRepository."""

from __future__ import annotations

from typing import Sequence

from db.models.position import Position
from db.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PositionRepository(BaseRepository[Position]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Position, session)

    async def get_open_positions(self, portfolio_id: str) -> Sequence[Position]:
        """Return all open positions for a portfolio."""
        stmt = (
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .where(Position.status == "open")
            .order_by(Position.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_ticker(self, portfolio_id: str, ticker: str) -> Position | None:
        """Return the open position for a specific ticker in a portfolio."""
        stmt = (
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .where(Position.ticker == ticker.upper())
            .where(Position.status == "open")
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def total_market_value(self, portfolio_id: str) -> float:
        """Return the sum of market values of all open positions."""
        positions = await self.get_open_positions(portfolio_id)
        return sum(p.quantity * p.current_price for p in positions)

    async def update_prices(self, portfolio_id: str, prices: dict[str, float]) -> int:
        """
        Batch-update ``current_price`` and ``unrealized_pnl`` for every
        ticker present in *prices*.  Returns the number of positions updated.
        """
        positions = await self.get_open_positions(portfolio_id)
        updated = 0
        for pos in positions:
            new_price = prices.get(pos.ticker)
            if new_price is None:
                continue
            pos.current_price = new_price
            pos.unrealized_pnl = round((new_price - pos.entry_price) * pos.quantity, 2)
            self.session.add(pos)
            updated += 1
        await self.session.flush()
        return updated
