"""Tests for RiskService - VaR, stress scenarios, correlation, radar."""

from __future__ import annotations

import pytest
from app.services.risk_service import RiskService
from tests.conftest import seed_positions


@pytest.mark.asyncio
class TestRiskService:
    async def test_get_risk_metrics_with_positions(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        metrics = await svc.get_risk_metrics()

        required_keys = {
            "var",
            "cvar",
            "sharpeRatio",
            "sortinoRatio",
            "maxDrawdown",
            "beta",
            "correlation",
            "volatility",
        }
        assert required_keys == set(metrics.keys())

    async def test_var_is_positive(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        metrics = await svc.get_risk_metrics()
        assert metrics["var"] > 0
        assert metrics["cvar"] > metrics["var"]  # CVaR > VaR always

    async def test_beta_is_weighted_average(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        metrics = await svc.get_risk_metrics()
        # AAPL(1.21), MSFT(0.92), TSLA(1.89) - weighted; should be > 0 and reasonable
        assert 0.5 < metrics["beta"] < 2.5

    async def test_volatility_is_annualised(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        metrics = await svc.get_risk_metrics()
        # Annualised vol for an equity portfolio is typically 10–60 %
        assert 0.05 < metrics["volatility"] < 1.0

    async def test_max_drawdown_is_non_positive(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        metrics = await svc.get_risk_metrics()
        assert metrics["maxDrawdown"] <= 0.0

    async def test_empty_portfolio_returns_zero_metrics(self, db_session):
        svc = RiskService(db_session)
        metrics = await svc.get_risk_metrics()
        assert metrics["var"] == 0.0
        assert metrics["volatility"] == 0.0

    async def test_stress_scenarios_count(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        scenarios = await svc.get_stress_scenarios()
        assert len(scenarios) == 6  # matches _STRESS_SCENARIOS

    async def test_stress_scenarios_pnl_is_negative(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        scenarios = await svc.get_stress_scenarios()
        for scenario in scenarios:
            assert scenario["pnl"] < 0, f"{scenario['name']} should have negative PnL"
            assert scenario["portfolioImpact"] < 0

    async def test_stress_scenario_structure(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        scenarios = await svc.get_stress_scenarios()
        required_keys = {"name", "pnl", "duration", "recovery", "portfolioImpact"}
        for s in scenarios:
            assert required_keys == set(s.keys())

    async def test_stress_pnl_scaled_by_nav(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        scenarios = await svc.get_stress_scenarios()
        # All positions: AAPL 100*175.5 + MSFT 50*338 + TSLA 30*742
        nav = 100.0 * 175.5 + 50.0 * 338.0 + 30.0 * 742.0
        covid = next(s for s in scenarios if "COVID" in s["name"])
        assert covid["pnl"] == pytest.approx(nav * -0.339, rel=1e-3)

    async def test_correlation_matrix_shape(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        matrix = await svc.get_correlation_matrix()
        tickers = {"AAPL", "MSFT", "TSLA"}
        assert len(matrix) == 3
        for row in matrix:
            assert row["asset"] in tickers
            assert row[row["asset"]] == 1.0  # diagonal is 1

    async def test_correlation_values_in_range(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        matrix = await svc.get_correlation_matrix()
        for row in matrix:
            for key, val in row.items():
                if key != "asset":
                    assert -1.0 <= val <= 1.0

    async def test_risk_radar_has_six_metrics(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        radar = await svc.get_risk_radar()
        assert len(radar) == 6
        metric_names = {r["metric"] for r in radar}
        assert "Market Risk" in metric_names
        assert "Concentration" in metric_names

    async def test_risk_radar_values_in_range(self, db_session):
        await seed_positions(db_session)
        svc = RiskService(db_session)
        radar = await svc.get_risk_radar()
        for entry in radar:
            assert 0 <= entry["value"] <= 100
