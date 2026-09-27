"""
Integration tests for app.services.strategy_service.run_backtest_in_background.

Exercises the full pending -> running -> completed/failed lifecycle against
a real (in-memory) database, proving create_backtest's result isn't stuck
at "pending" forever anymore.
"""

from __future__ import annotations

import pytest
from app.services.strategy_service import StrategyService, run_backtest_in_background
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.conftest import seed_strategies


def _session_factory_for(db_engine) -> async_sessionmaker:
    """A sessionmaker bound to the same test engine as the db_session
    fixture, so run_backtest_in_background's own session sees the same
    (committed) data instead of touching the real production database."""
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest.mark.asyncio
class TestRunBacktestInBackground:
    async def test_momentum_backtest_completes(self, db_session, db_engine) -> None:
        await seed_strategies(db_session)  # strat-001 is a "momentum" strategy
        svc = StrategyService(db_session)
        run = await svc.create_backtest(
            "strat-001", "2023-01-01", "2023-06-30", 100_000.0
        )
        assert run["status"] == "pending"

        await run_backtest_in_background(
            backtest_id=run["id"],
            strategy_id="strat-001",
            start_date="2023-01-01",
            end_date="2023-06-30",
            initial_capital=100_000.0,
            session_factory=_session_factory_for(db_engine),
        )

        # Fresh session/query - db_session's own identity map could mask a
        # write made through the background task's separate session.
        async with _session_factory_for(db_engine)() as verify_session:
            result = await StrategyService(verify_session).get_backtest(run["id"])
        assert result["status"] == "completed"
        assert result["errorMessage"] is None
        assert result["finalCapital"] is not None
        assert result["sharpeRatio"] is not None

    async def test_rl_agent_backtest_completes(self, db_session, db_engine) -> None:
        svc = StrategyService(db_session)
        strategy = await svc.create_strategy(
            name="Tiny RL Agent",
            description="test",
            strategy_type="rl_agent",
            parameters={
                "algorithm": "ddpg",
                "n_assets": 2,
                "episodes": 1,
                "max_steps": 10,
            },
        )
        run = await svc.create_backtest(
            strategy["id"], "2023-01-01", "2023-02-01", 10_000.0
        )

        await run_backtest_in_background(
            backtest_id=run["id"],
            strategy_id=strategy["id"],
            start_date="2023-01-01",
            end_date="2023-02-01",
            initial_capital=10_000.0,
            session_factory=_session_factory_for(db_engine),
        )

        async with _session_factory_for(db_engine)() as verify_session:
            result = await StrategyService(verify_session).get_backtest(run["id"])
        assert result["status"] == "completed"
        assert result["finalCapital"] > 0

    async def test_missing_strategy_fails_gracefully(
        self, db_session, db_engine
    ) -> None:
        svc = StrategyService(db_session)
        # create_backtest doesn't itself validate the strategy exists (the
        # router does that before calling it) - simulate a strategy that
        # gets deleted between the request and the background task running.
        run = await svc.create_backtest(
            "does-not-exist", "2023-01-01", "2023-06-30", 100_000.0
        )

        await run_backtest_in_background(
            backtest_id=run["id"],
            strategy_id="does-not-exist",
            start_date="2023-01-01",
            end_date="2023-06-30",
            initial_capital=100_000.0,
            session_factory=_session_factory_for(db_engine),
        )

        async with _session_factory_for(db_engine)() as verify_session:
            result = await StrategyService(verify_session).get_backtest(run["id"])
        assert result["status"] == "failed"
        assert "does-not-exist" in result["errorMessage"]

    async def test_unsupported_strategy_type_fails_gracefully(
        self, db_session, db_engine
    ) -> None:
        svc = StrategyService(db_session)
        strategy = await svc.create_strategy(
            name="Bogus",
            description="test",
            strategy_type="not_a_real_type",
            parameters={},
        )
        run = await svc.create_backtest(
            strategy["id"], "2023-01-01", "2023-06-30", 100_000.0
        )

        await run_backtest_in_background(
            backtest_id=run["id"],
            strategy_id=strategy["id"],
            start_date="2023-01-01",
            end_date="2023-06-30",
            initial_capital=100_000.0,
            session_factory=_session_factory_for(db_engine),
        )

        async with _session_factory_for(db_engine)() as verify_session:
            result = await StrategyService(verify_session).get_backtest(run["id"])
        assert result["status"] == "failed"
        assert result["errorMessage"]
