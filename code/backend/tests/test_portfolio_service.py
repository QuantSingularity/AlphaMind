"""Tests for PortfolioService - summary, holdings, positions, performance."""

from __future__ import annotations

import pytest
from app.services.portfolio_service import PortfolioService
from tests.conftest import seed_positions


@pytest.mark.asyncio
class TestPortfolioService:

    async def test_get_portfolio_returns_summary(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        portfolio = await svc.get_portfolio()

        assert portfolio["id"] == "port-001"
        assert portfolio["totalValue"] > 0
        assert portfolio["cash"] > 0
        assert isinstance(portfolio["allocation"], list)
        assert len(portfolio["allocation"]) == 3

    async def test_portfolio_total_value_equals_positions_plus_cash(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        portfolio = await svc.get_portfolio()

        # AAPL: 100*175.5 + MSFT: 50*338 + TSLA: 30*742 = 56710, plus cash
        expected_pos_val = 100.0 * 175.5 + 50.0 * 338.0 + 30.0 * 742.0
        expected_total = round(expected_pos_val + 25_430.50, 2)
        assert portfolio["totalValue"] == pytest.approx(expected_total, rel=1e-4)

    async def test_allocation_percentages_less_than_100(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        portfolio = await svc.get_portfolio()

        total_pct = sum(a["percentage"] for a in portfolio["allocation"])
        # Positions don't include cash, so allocation < 100 %
        assert total_pct < 100.0
        assert total_pct > 50.0

    async def test_get_holdings(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        holdings = await svc.get_holdings()

        assert len(holdings) == 3
        tickers = {h["symbol"] for h in holdings}
        assert tickers == {"AAPL", "MSFT", "TSLA"}

    async def test_get_positions_returns_open_only(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        positions = await svc.get_positions()

        assert len(positions) == 3
        pos = next(p for p in positions if p["ticker"] == "AAPL")
        assert pos["entryPrice"] == 150.0
        assert pos["currentPrice"] == 175.5
        assert pos["unrealizedPnL"] == 2550.0

    async def test_get_position_by_id(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        pos = await svc.get_position("pos-001")

        assert pos is not None
        assert pos["ticker"] == "AAPL"

    async def test_get_position_not_found_returns_none(self, db_session):
        svc = PortfolioService(db_session)
        pos = await svc.get_position("nonexistent-id")
        assert pos is None

    async def test_close_position_realises_pnl(self, db_session):
        """Closing a position should realise its PnL and remove it from open positions."""
        await seed_positions(db_session)
        svc = PortfolioService(db_session)

        result = await svc.close_position("pos-002")
        assert result is not None
        assert result["realizedPnL"] == 1900.0

        open_positions = await svc.get_positions()
        open_ids = [p["id"] for p in open_positions]
        assert "pos-002" not in open_ids

    async def test_close_position_leaves_others_open(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        await svc.close_position("pos-002")

        open_positions = await svc.get_positions()
        assert len(open_positions) == 2
        tickers = {p["ticker"] for p in open_positions}
        assert "AAPL" in tickers
        assert "TSLA" in tickers

    async def test_close_nonexistent_position_returns_none(self, db_session):
        svc = PortfolioService(db_session)
        result = await svc.close_position("ghost-id")
        assert result is None

    async def test_close_already_closed_position_returns_none(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        # Close once - should succeed
        r1 = await svc.close_position("pos-001")
        assert r1 is not None
        # Close again - should return None (not open)
        r2 = await svc.close_position("pos-001")
        assert r2 is None

    async def test_performance_returns_equity_curve(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        perf = await svc.get_performance(timeframe="1M")

        assert "equityCurve" in perf
        assert "metrics" in perf
        assert len(perf["equityCurve"]) == 30

    async def test_performance_equity_curve_length_matches_timeframe(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        for tf, expected_days in [("1W", 7), ("3M", 90), ("1Y", 252)]:
            perf = await svc.get_performance(timeframe=tf)
            assert len(perf["equityCurve"]) == expected_days, f"Failed for {tf}"

    async def test_metrics_keys_present(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        perf = await svc.get_performance(timeframe="3M")
        metrics = perf["metrics"]

        for key in (
            "sharpeRatio",
            "sortinoRatio",
            "maxDrawdown",
            "volatility",
            "winRate",
            "alpha",
            "beta",
            "totalReturn",
            "annualisedReturn",
        ):
            assert key in metrics, f"Missing metric: {key}"

    async def test_win_rate_in_valid_range(self, db_session):
        await seed_positions(db_session)
        svc = PortfolioService(db_session)
        perf = await svc.get_performance(timeframe="1M")
        assert 0.0 <= perf["metrics"]["winRate"] <= 1.0

    async def test_empty_portfolio_returns_cash_only(self, db_session):
        svc = PortfolioService(db_session)
        portfolio = await svc.get_portfolio()
        assert portfolio["totalValue"] == pytest.approx(25_430.50, rel=1e-4)
        assert portfolio["allocation"] == []
