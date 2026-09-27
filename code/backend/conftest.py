"""
Root conftest.py - code/backend/conftest.py

Responsibilities
----------------
1. Add the backend root to sys.path (fixes ModuleNotFoundError for all tests).
2. Create a file-based SQLite test database with ALL tables and demo seed data
   ONCE per session via a pytest_configure hook (before pytest-asyncio starts
   its own event loop, so asyncio.run() is safe to call here).
3. Override FastAPI's get_db dependency to point every TestClient request at
   the pre-seeded test database - no "no such table" errors.
4. Provide function-scoped in-memory DB fixtures for the service-layer unit
   tests (test_portfolio_service, test_trading_service, etc.).
5. Expose seed helpers used by the unit tests.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. sys.path fix - MUST be first
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

_backend_root = str(Path(__file__).parent.resolve())
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# ---------------------------------------------------------------------------
# Standard-library and third-party imports (db.session intentionally excluded
# at module level - importing it creates the production engine immediately).
# ---------------------------------------------------------------------------
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import db.models  # side-effect: registers Position, Order, Strategy, BacktestRun with Base
import pytest
import pytest_asyncio
from db.base import Base
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

# ---------------------------------------------------------------------------
# 2. File-based SQLite engine for TestClient (API integration) tests
#
# NullPool is critical here: it ensures there is NO connection-pool affinity
# to an event loop.  Tables are created in pytest_configure (asyncio.run,
# fresh loop), then each TestClient request opens its own fresh connection in
# pytest-asyncio's loop - both see the same on-disk file.
# ---------------------------------------------------------------------------
_API_DB_PATH = os.path.join(os.path.dirname(__file__), "test_api.db")
_API_DB_URL = f"sqlite+aiosqlite:///{_API_DB_PATH}"

_api_engine = create_async_engine(
    _API_DB_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"check_same_thread": False},
)
_api_session_factory = async_sessionmaker(
    _api_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# 3. Async helpers for one-time DB setup / teardown
# ---------------------------------------------------------------------------


async def _setup_api_db() -> None:
    """Create all tables then seed demo positions and strategies."""
    from db.models.position import Position
    from db.models.strategy import Strategy

    # Create tables (idempotent - checkfirst=True is the SQLAlchemy default)
    async with _api_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc)

    async with _api_session_factory() as session:
        count = (
            await session.execute(select(func.count()).select_from(Position))
        ).scalar_one()

        if count > 0:
            return  # already seeded

        # ---- positions ----
        session.add_all(
            [
                Position(
                    id="pos-001",
                    portfolio_id="port-001",
                    ticker="AAPL",
                    sector="Technology",
                    quantity=100.0,
                    entry_price=150.0,
                    current_price=175.5,
                    unrealized_pnl=2550.0,
                    realized_pnl=0.0,
                    weight=0.28,
                    beta=1.21,
                    sharpe_contrib=0.42,
                    var_95=1240.0,
                    status="open",
                    opened_at=now - timedelta(days=30),
                    updated_at=now,
                ),
                Position(
                    id="pos-002",
                    portfolio_id="port-001",
                    ticker="MSFT",
                    sector="Technology",
                    quantity=50.0,
                    entry_price=300.0,
                    current_price=338.0,
                    unrealized_pnl=1900.0,
                    realized_pnl=0.0,
                    weight=0.27,
                    beta=0.92,
                    sharpe_contrib=0.38,
                    var_95=980.0,
                    status="open",
                    opened_at=now - timedelta(days=25),
                    updated_at=now,
                ),
                Position(
                    id="pos-003",
                    portfolio_id="port-001",
                    ticker="GOOGL",
                    sector="Communication",
                    quantity=25.0,
                    entry_price=2800.0,
                    current_price=2950.0,
                    unrealized_pnl=3750.0,
                    realized_pnl=0.0,
                    weight=0.19,
                    beta=1.05,
                    sharpe_contrib=0.29,
                    var_95=1560.0,
                    status="open",
                    opened_at=now - timedelta(days=20),
                    updated_at=now,
                ),
                Position(
                    id="pos-004",
                    portfolio_id="port-001",
                    ticker="TSLA",
                    sector="Consumer Disc.",
                    quantity=30.0,
                    entry_price=700.0,
                    current_price=742.0,
                    unrealized_pnl=1260.0,
                    realized_pnl=0.0,
                    weight=0.11,
                    beta=1.89,
                    sharpe_contrib=0.14,
                    var_95=2100.0,
                    status="open",
                    opened_at=now - timedelta(days=15),
                    updated_at=now,
                ),
                Position(
                    id="pos-005",
                    portfolio_id="port-001",
                    ticker="JPM",
                    sector="Financials",
                    quantity=80.0,
                    entry_price=130.0,
                    current_price=148.25,
                    unrealized_pnl=1460.0,
                    realized_pnl=0.0,
                    weight=0.15,
                    beta=0.78,
                    sharpe_contrib=0.22,
                    var_95=680.0,
                    status="open",
                    opened_at=now - timedelta(days=10),
                    updated_at=now,
                ),
            ]
        )

        # ---- strategies ----
        session.add_all(
            [
                Strategy(
                    id="strat-001",
                    name="Momentum Alpha",
                    description="Cross-sectional momentum with ML signal filtering",
                    strategy_type="momentum",
                    status="active",
                    parameters_json='{"lookback": 12, "rebalance": "monthly"}',
                    sharpe_ratio=2.31,
                    max_drawdown=-0.089,
                    profit_factor=1.84,
                    win_rate=0.64,
                    total_return=0.384,
                    volatility=0.142,
                    alpha=0.094,
                    beta=0.88,
                    created_at=now,
                    updated_at=now,
                ),
                Strategy(
                    id="strat-002",
                    name="Mean Reversion",
                    description="Statistical arbitrage using cointegrated pairs",
                    strategy_type="mean_reversion",
                    status="paused",
                    parameters_json='{"z_entry": 2.0, "z_exit": 0.5}',
                    sharpe_ratio=1.87,
                    max_drawdown=-0.054,
                    profit_factor=2.12,
                    win_rate=0.71,
                    total_return=0.221,
                    volatility=0.098,
                    alpha=0.067,
                    beta=0.34,
                    created_at=now,
                    updated_at=now,
                ),
                Strategy(
                    id="strat-003",
                    name="RL Trading Agent",
                    description="DDPG-based adaptive execution agent",
                    strategy_type="rl_agent",
                    status="paused",
                    parameters_json='{"actor_lr": 0.0001, "gamma": 0.99}',
                    sharpe_ratio=1.54,
                    max_drawdown=-0.127,
                    profit_factor=1.61,
                    win_rate=0.58,
                    total_return=0.298,
                    volatility=0.189,
                    alpha=0.052,
                    beta=1.12,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )

        await session.commit()


async def _teardown_api_db() -> None:
    await _api_engine.dispose()


# ---------------------------------------------------------------------------
# 4. pytest hooks - run BEFORE pytest-asyncio creates its own event loop,
#    so asyncio.run() is safe.
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """
    Create API test DB tables and seed demo data.

    Called very early in pytest startup - before test collection and before
    pytest-asyncio initialises its event loop - so asyncio.run() has no
    'already-running loop' conflict.
    """
    asyncio.run(_setup_api_db())


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Remove the API test DB file after the entire test session finishes."""
    asyncio.run(_teardown_api_db())
    try:
        os.remove(_API_DB_PATH)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# 5. Session-scoped autouse fixture - wire the get_db override into the app
#
# The TestClient is created at module level in test_api.py / test_basic_api.py
# BEFORE any fixture runs.  That is fine: FastAPI evaluates dependency_overrides
# at REQUEST time, not at client-creation time.  As long as the override is set
# before the first HTTP request, all DB calls go through the test engine.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _override_app_get_db() -> None:
    """
    Replace the production get_db dependency with one backed by the pre-seeded
    test_api.db.  Applies to every TestClient request for the whole test session.
    """
    # Lazy import keeps db.session (and its production engine) out of module
    # level - we only need it now, when tests are actually about to run.
    from app.main import app
    from db.session import get_db

    async def _test_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with _api_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _test_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# 6. Function-scoped in-memory fixtures for service / repository unit tests
#
# Each unit test gets its own isolated in-memory database.  StaticPool ensures
# the same underlying SQLite connection is reused within one test, so tables
# created in engine.begin() are immediately visible to db_session queries.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Fresh in-memory SQLite engine for each unit-test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # reuse same connection → same in-memory DB
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async session bound to the test engine, rolled back after each test."""
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# 7. Seed helpers - used by unit tests directly (not fixtures)
# ---------------------------------------------------------------------------


async def seed_positions(session: AsyncSession, portfolio_id: str = "port-001"):
    """Insert 3 open demo positions into the unit-test DB."""
    from db.models.position import Position

    now = datetime.now(timezone.utc)
    positions = [
        Position(
            id="pos-001",
            portfolio_id=portfolio_id,
            ticker="AAPL",
            sector="Technology",
            quantity=100.0,
            entry_price=150.0,
            current_price=175.5,
            unrealized_pnl=2550.0,
            realized_pnl=0.0,
            weight=0.28,
            beta=1.21,
            sharpe_contrib=0.42,
            var_95=1240.0,
            status="open",
            opened_at=now - timedelta(days=30),
            updated_at=now,
        ),
        Position(
            id="pos-002",
            portfolio_id=portfolio_id,
            ticker="MSFT",
            sector="Technology",
            quantity=50.0,
            entry_price=300.0,
            current_price=338.0,
            unrealized_pnl=1900.0,
            realized_pnl=0.0,
            weight=0.27,
            beta=0.92,
            sharpe_contrib=0.38,
            var_95=980.0,
            status="open",
            opened_at=now - timedelta(days=25),
            updated_at=now,
        ),
        Position(
            id="pos-003",
            portfolio_id=portfolio_id,
            ticker="TSLA",
            sector="Consumer Disc.",
            quantity=30.0,
            entry_price=700.0,
            current_price=742.0,
            unrealized_pnl=1260.0,
            realized_pnl=0.0,
            weight=0.11,
            beta=1.89,
            sharpe_contrib=0.14,
            var_95=2100.0,
            status="open",
            opened_at=now - timedelta(days=15),
            updated_at=now,
        ),
    ]
    session.add_all(positions)
    await session.commit()
    return positions


async def seed_strategies(session: AsyncSession):
    """Insert 2 demo strategies into the unit-test DB."""
    from db.models.strategy import Strategy

    now = datetime.now(timezone.utc)
    strategies = [
        Strategy(
            id="strat-001",
            name="Momentum Alpha",
            description="Cross-sectional momentum",
            strategy_type="momentum",
            status="active",
            parameters_json='{"lookback": 12}',
            sharpe_ratio=2.31,
            max_drawdown=-0.089,
            profit_factor=1.84,
            win_rate=0.64,
            total_return=0.384,
            volatility=0.142,
            alpha=0.094,
            beta=0.88,
            created_at=now,
            updated_at=now,
        ),
        Strategy(
            id="strat-002",
            name="Mean Reversion",
            description="Stat arb",
            strategy_type="mean_reversion",
            status="paused",
            parameters_json='{"z_entry": 2.0}',
            sharpe_ratio=1.87,
            max_drawdown=-0.054,
            profit_factor=2.12,
            win_rate=0.71,
            total_return=0.221,
            volatility=0.098,
            alpha=0.067,
            beta=0.34,
            created_at=now,
            updated_at=now,
        ),
    ]
    session.add_all(strategies)
    await session.commit()
    return strategies
