"""
ORM model registry - import every model module here so that Alembic's
``autogenerate`` and ``create_all_tables`` pick them all up.
"""

from db.models.backtest import BacktestRun  # noqa: F401
from db.models.order import Order  # noqa: F401
from db.models.position import Position  # noqa: F401
from db.models.strategy import Strategy  # noqa: F401

__all__ = ["Position", "Order", "Strategy", "BacktestRun"]
