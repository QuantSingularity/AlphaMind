"""Tests for the repository layer - covers CRUD and domain-specific queries."""

from __future__ import annotations

import pytest
from db.repositories import (
    BacktestRepository,
    OrderRepository,
    PositionRepository,
    StrategyRepository,
)
from tests.conftest import seed_positions, seed_strategies


@pytest.mark.asyncio
class TestPositionRepository:
    async def test_create_and_get(self, db_session):
        from datetime import datetime, timezone

        repo = PositionRepository(db_session)
        pos = await repo.create(
            id="pos-test-01",
            portfolio_id="port-001",
            ticker="NVDA",
            sector="Technology",
            quantity=10.0,
            entry_price=800.0,
            current_price=875.0,
            unrealized_pnl=750.0,
            realized_pnl=0.0,
            weight=0.1,
            beta=1.73,
            sharpe_contrib=0.2,
            var_95=500.0,
            status="open",
            opened_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert pos.id == "pos-test-01"
        assert pos.ticker == "NVDA"

        fetched = await repo.get("pos-test-01")
        assert fetched is not None
        assert fetched.current_price == 875.0

    async def test_get_open_positions(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        positions = await repo.get_open_positions("port-001")
        assert len(positions) == 3
        assert all(p.status == "open" for p in positions)

    async def test_get_open_positions_different_portfolio(self, db_session):
        await seed_positions(db_session, portfolio_id="port-001")
        repo = PositionRepository(db_session)
        positions = await repo.get_open_positions("port-999")
        assert len(positions) == 0

    async def test_get_by_ticker(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        pos = await repo.get_by_ticker("port-001", "AAPL")
        assert pos is not None
        assert pos.ticker == "AAPL"

    async def test_get_by_ticker_not_found(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        pos = await repo.get_by_ticker("port-001", "AMZN")
        assert pos is None

    async def test_total_market_value(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        mv = await repo.total_market_value("port-001")
        expected = 100.0 * 175.5 + 50.0 * 338.0 + 30.0 * 742.0
        assert mv == pytest.approx(expected, rel=1e-4)

    async def test_update_prices(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        updated_count = await repo.update_prices(
            "port-001", {"AAPL": 180.0, "MSFT": 350.0}
        )
        assert updated_count == 2
        aapl = await repo.get_by_ticker("port-001", "AAPL")
        assert aapl.current_price == 180.0
        assert aapl.unrealized_pnl == pytest.approx((180.0 - 150.0) * 100.0)

    async def test_delete_position(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        deleted = await repo.delete("pos-001")
        assert deleted is True
        assert await repo.get("pos-001") is None

    async def test_count(self, db_session):
        await seed_positions(db_session)
        repo = PositionRepository(db_session)
        count = await repo.count(portfolio_id="port-001", status="open")
        assert count == 3


@pytest.mark.asyncio
class TestOrderRepository:
    async def test_create_and_get_order(self, db_session):
        from datetime import datetime, timezone

        repo = OrderRepository(db_session)
        order = await repo.create(
            id="ord-test-01",
            portfolio_id="port-001",
            ticker="AAPL",
            side="BUY",
            order_type="MARKET",
            quantity=10.0,
            price=None,
            filled_price=175.6,
            status="filled",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert order.id == "ord-test-01"
        fetched = await repo.get("ord-test-01")
        assert fetched.status == "filled"

    async def test_get_pending_orders(self, db_session):
        from datetime import datetime, timezone

        repo = OrderRepository(db_session)
        now = datetime.now(timezone.utc)
        await repo.create(
            id="o1",
            portfolio_id="port-001",
            ticker="AAPL",
            side="BUY",
            order_type="LIMIT",
            quantity=5.0,
            price=170.0,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        await repo.create(
            id="o2",
            portfolio_id="port-001",
            ticker="MSFT",
            side="BUY",
            order_type="MARKET",
            quantity=2.0,
            status="filled",
            created_at=now,
            updated_at=now,
        )

        pending = await repo.get_pending("port-001")
        assert len(pending) == 1
        assert pending[0].id == "o1"

    async def test_get_by_portfolio_filtered_by_status(self, db_session):
        from datetime import datetime, timezone

        repo = OrderRepository(db_session)
        now = datetime.now(timezone.utc)
        for i, status in enumerate(["filled", "pending", "cancelled"]):
            await repo.create(
                id=f"o{i}",
                portfolio_id="port-001",
                ticker="V",
                side="BUY",
                order_type="MARKET",
                quantity=1.0,
                status=status,
                created_at=now,
                updated_at=now,
            )
        cancelled = await repo.get_by_portfolio("port-001", status="cancelled")
        assert len(cancelled) == 1


@pytest.mark.asyncio
class TestStrategyRepository:
    async def test_get_active_strategies(self, db_session):
        await seed_strategies(db_session)
        repo = StrategyRepository(db_session)
        active = await repo.get_active()
        assert len(active) == 1
        assert active[0].name == "Momentum Alpha"

    async def test_get_by_name(self, db_session):
        await seed_strategies(db_session)
        repo = StrategyRepository(db_session)
        s = await repo.get_by_name("Mean Reversion")
        assert s is not None
        assert s.id == "strat-002"

    async def test_get_by_name_not_found(self, db_session):
        repo = StrategyRepository(db_session)
        result = await repo.get_by_name("NonExistent")
        assert result is None


@pytest.mark.asyncio
class TestBacktestRepository:
    async def test_create_and_get_backtest(self, db_session):
        from datetime import datetime, timezone

        repo = BacktestRepository(db_session)
        run = await repo.create(
            id="bt-001",
            strategy_id="strat-001",
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100_000.0,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        assert run is not None
        assert run.id == "bt-001"
        fetched = await repo.get("bt-001")
        assert fetched is not None
        assert fetched.strategy_id == "strat-001"

    async def test_get_by_strategy(self, db_session):
        from datetime import datetime, timezone

        repo = BacktestRepository(db_session)
        now = datetime.now(timezone.utc)
        await repo.create(
            id="bt-a",
            strategy_id="strat-001",
            start_date="2022-01-01",
            end_date="2022-12-31",
            initial_capital=50_000.0,
            status="completed",
            created_at=now,
        )
        await repo.create(
            id="bt-b",
            strategy_id="strat-001",
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100_000.0,
            status="pending",
            created_at=now,
        )
        await repo.create(
            id="bt-c",
            strategy_id="strat-002",
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=75_000.0,
            status="completed",
            created_at=now,
        )

        runs = await repo.get_by_strategy("strat-001")
        assert len(runs) == 2

    async def test_update_backtest_to_completed(self, db_session):
        from datetime import datetime, timezone

        repo = BacktestRepository(db_session)
        now = datetime.now(timezone.utc)
        await repo.create(
            id="bt-z",
            strategy_id="strat-001",
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100_000.0,
            status="pending",
            created_at=now,
        )
        updated = await repo.update(
            "bt-z", status="completed", final_capital=138_000.0, total_return=0.38
        )
        assert updated.status == "completed"
        assert updated.final_capital == 138_000.0
