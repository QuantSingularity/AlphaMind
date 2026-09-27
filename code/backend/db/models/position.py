"""Position ORM model - represents an open or closed trading position."""

from __future__ import annotations

from datetime import datetime, timezone

from db.base import Base
from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column


class Position(Base):
    """Single position in a portfolio."""

    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    sector: Mapped[str] = mapped_column(String(64), nullable=False, default="Unknown")

    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)

    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Risk metrics - refreshed by the risk service
    beta: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    sharpe_contrib: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    var_95: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open"
    )  # open | closed

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_positions_portfolio_status", "portfolio_id", "status"),
        Index("ix_positions_ticker", "ticker"),
    )

    def market_value(self) -> float:
        return round(self.quantity * self.current_price, 2)

    def __repr__(self) -> str:
        return f"<Position {self.ticker} qty={self.quantity} @ {self.current_price}>"
