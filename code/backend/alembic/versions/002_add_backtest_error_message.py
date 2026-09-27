"""Add backtest_runs.error_message - records why a backtest failed.

Added alongside app.services.backtest_runner, which actually executes
backtests now (previously they stayed "pending" forever, so there was
never a failure to record).

Revision ID: 002
Revises: 001
Create Date: 2026-09-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column("error_message", sa.String(2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtest_runs", "error_message")
