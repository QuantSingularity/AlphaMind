"""Strategy ORM model - stores trading strategy definitions and live performance."""

from __future__ import annotations

from datetime import datetime, timezone

from db.base import Base
from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class Strategy(Base):
    """Quantitative trading strategy record."""

    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    strategy_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # momentum | mean_reversion | ml_alpha | rl_agent

    # active | paused | archived
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="paused")

    # Serialised JSON blob - strategy-specific hyper-parameters
    parameters_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # Performance metrics (refreshed by strategy service)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    volatility: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    beta: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    __table_args__ = (Index("ix_strategies_status", "status"),)

    def __repr__(self) -> str:
        return f"<Strategy {self.name} [{self.status}]>"
