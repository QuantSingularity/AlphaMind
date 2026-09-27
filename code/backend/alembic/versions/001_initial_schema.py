"""Initial schema - create positions, orders, strategies, backtest_runs tables.

Revision ID: 001
Revises: (none)
Create Date: 2025-01-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # positions                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "positions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("sector", sa.String(64), nullable=False, server_default="Unknown"),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("current_price", sa.Float, nullable=False),
        sa.Column("unrealized_pnl", sa.Float, nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Float, nullable=False, server_default="0"),
        sa.Column("weight", sa.Float, nullable=False, server_default="0"),
        sa.Column("beta", sa.Float, nullable=False, server_default="1"),
        sa.Column("sharpe_contrib", sa.Float, nullable=False, server_default="0"),
        sa.Column("var_95", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_positions_portfolio_id", "positions", ["portfolio_id"])
    op.create_index(
        "ix_positions_portfolio_status", "positions", ["portfolio_id", "status"]
    )
    op.create_index("ix_positions_ticker", "positions", ["ticker"])

    # ------------------------------------------------------------------ #
    # orders                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("filled_price", sa.Float, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_portfolio_id", "orders", ["portfolio_id"])
    op.create_index("ix_orders_portfolio_status", "orders", ["portfolio_id", "status"])
    op.create_index("ix_orders_ticker", "orders", ["ticker"])

    # ------------------------------------------------------------------ #
    # strategies                                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("strategy_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="paused"),
        sa.Column("parameters_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("sharpe_ratio", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_drawdown", sa.Float, nullable=False, server_default="0"),
        sa.Column("profit_factor", sa.Float, nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_return", sa.Float, nullable=False, server_default="0"),
        sa.Column("volatility", sa.Float, nullable=False, server_default="0"),
        sa.Column("alpha", sa.Float, nullable=False, server_default="0"),
        sa.Column("beta", sa.Float, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_strategies_status", "strategies", ["status"])

    # ------------------------------------------------------------------ #
    # backtest_runs                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("strategy_id", sa.String(36), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=False),
        sa.Column("end_date", sa.String(10), nullable=False),
        sa.Column("initial_capital", sa.Float, nullable=False),
        sa.Column("final_capital", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_return", sa.Float, nullable=False, server_default="0"),
        sa.Column("sharpe_ratio", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_drawdown", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_backtest_runs_strategy_id", "backtest_runs", ["strategy_id"])


def downgrade() -> None:
    op.drop_table("backtest_runs")
    op.drop_table("strategies")
    op.drop_table("orders")
    op.drop_table("positions")
