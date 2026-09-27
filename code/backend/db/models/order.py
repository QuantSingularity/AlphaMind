"""Order ORM model - represents a buy/sell order submission."""

from __future__ import annotations

from datetime import datetime, timezone

from db.base import Base
from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column


class Order(Base):
    """Trading order record."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY | SELL
    order_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # MARKET | LIMIT | STOP
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    filled_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # pending | filled | cancelled | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    filled_at: Mapped[datetime | None] = mapped_column(
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
        Index("ix_orders_portfolio_status", "portfolio_id", "status"),
        Index("ix_orders_ticker", "ticker"),
    )

    def __repr__(self) -> str:
        return f"<Order {self.side} {self.quantity}x{self.ticker} [{self.status}]>"
