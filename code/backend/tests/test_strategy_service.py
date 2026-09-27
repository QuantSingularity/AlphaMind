"""Tests for StrategyService - CRUD, activate/deactivate, backtest lifecycle."""

from __future__ import annotations

import pytest
from app.services.strategy_service import StrategyService
from tests.conftest import seed_strategies


@pytest.mark.asyncio
class TestStrategyService:
    async def test_list_strategies(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        strategies = await svc.list_strategies()
        assert len(strategies) == 2

    async def test_get_strategy_by_id(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        s = await svc.get_strategy("strat-001")
        assert s is not None
        assert s["name"] == "Momentum Alpha"
        assert s["type"] == "momentum"
        assert s["status"] == "active"

    async def test_get_nonexistent_strategy_returns_none(self, db_session):
        svc = StrategyService(db_session)
        result = await svc.get_strategy("ghost-strat")
        assert result is None

    async def test_create_strategy(self, db_session):
        svc = StrategyService(db_session)
        s = await svc.create_strategy(
            name="RL Agent v2",
            description="PPO-based portfolio manager",
            strategy_type="rl_agent",
            parameters={"gamma": 0.99, "lr": 0.0003},
        )
        assert s["id"].startswith("strat-")
        assert s["name"] == "RL Agent v2"
        assert s["status"] == "paused"
        assert s["parameters"]["gamma"] == 0.99

    async def test_create_strategy_default_performance_zeros(self, db_session):
        svc = StrategyService(db_session)
        s = await svc.create_strategy(
            name="New Strategy",
            description="Test",
            strategy_type="momentum",
        )
        perf = s["performance"]
        assert perf["sharpeRatio"] == 0.0
        assert perf["winRate"] == 0.0
        assert perf["beta"] == 1.0

    async def test_activate_strategy(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        result = await svc.activate_strategy("strat-002")
        assert result is not None
        assert result["status"] == "active"

    async def test_deactivate_strategy(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        result = await svc.deactivate_strategy("strat-001")
        assert result is not None
        assert result["status"] == "paused"

    async def test_update_strategy_parameters(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        updated = await svc.update_strategy(
            "strat-001", parameters={"lookback": 24, "rebalance": "weekly"}
        )
        assert updated is not None
        assert updated["parameters"]["lookback"] == 24

    async def test_update_nonexistent_strategy_returns_none(self, db_session):
        svc = StrategyService(db_session)
        result = await svc.update_strategy("ghost", description="nope")
        assert result is None

    async def test_delete_strategy(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        deleted = await svc.delete_strategy("strat-001")
        assert deleted is True
        assert await svc.get_strategy("strat-001") is None

    async def test_delete_nonexistent_returns_false(self, db_session):
        svc = StrategyService(db_session)
        result = await svc.delete_strategy("nobody")
        assert result is False

    async def test_create_backtest(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        run = await svc.create_backtest(
            strategy_id="strat-001",
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100_000.0,
        )
        assert run["id"].startswith("bt-")
        assert run["status"] == "pending"
        assert run["strategyId"] == "strat-001"
        assert run["initialCapital"] == 100_000.0

    async def test_complete_backtest(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        run = await svc.create_backtest(
            "strat-001", "2023-01-01", "2023-12-31", 100_000.0
        )

        completed = await svc.complete_backtest(
            run["id"],
            final_capital=138_400.0,
            total_return=0.384,
            sharpe_ratio=2.31,
            max_drawdown=-0.089,
            total_trades=147,
            win_rate=0.64,
        )
        assert completed is not None
        assert completed["status"] == "completed"
        assert completed["finalCapital"] == 138_400.0
        assert completed["totalTrades"] == 147

    async def test_get_backtests_for_strategy(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        await svc.create_backtest("strat-001", "2022-01-01", "2022-12-31", 50_000.0)
        await svc.create_backtest("strat-001", "2023-01-01", "2023-12-31", 100_000.0)
        await svc.create_backtest("strat-002", "2023-01-01", "2023-12-31", 75_000.0)

        runs = await svc.get_backtests("strat-001")
        assert len(runs) == 2
        assert all(r["strategyId"] == "strat-001" for r in runs)

    async def test_strategy_performance_dict_keys(self, db_session):
        await seed_strategies(db_session)
        svc = StrategyService(db_session)
        s = await svc.get_strategy("strat-001")
        expected_keys = {
            "sharpeRatio",
            "maxDrawdown",
            "profitFactor",
            "winRate",
            "totalReturn",
            "volatility",
            "alpha",
            "beta",
        }
        assert expected_keys == set(s["performance"].keys())
