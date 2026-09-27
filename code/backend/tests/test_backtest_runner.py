"""
Tests for app.services.backtest_runner.

Previously StrategyService.create_backtest only ever wrote a "pending" DB
row - nothing in the codebase ever actually ran a simulation, and nothing
in the backend ever imported ai_models at all. These tests exercise
run_backtest for real, for every strategy_type the Strategy model
supports, to prove the ai_models integration (rl_agent, ml_alpha) and the
BacktestEngine wiring (momentum, mean_reversion) both genuinely work end
to end - not mocked.
"""

from __future__ import annotations

import pytest
from app.services.backtest_runner import run_backtest, run_backtest_detailed

_RESULT_KEYS = {
    "final_capital",
    "total_return",
    "sharpe_ratio",
    "max_drawdown",
    "total_trades",
    "win_rate",
}


class TestRuleBasedBacktests:
    """momentum / mean_reversion - fast, no ML, deterministic given a seed."""

    def test_momentum_backtest_runs(self) -> None:
        result = run_backtest(
            strategy_type="momentum",
            parameters={
                "symbol": "AAPL",
                "lookback": 10,
                "threshold": 0.01,
                "seed": 42,
            },
            start_date="2023-01-01",
            end_date="2023-06-30",
            initial_capital=100_000.0,
        )
        assert _RESULT_KEYS.issubset(result.keys())
        assert result["final_capital"] > 0

    def test_mean_reversion_backtest_runs(self) -> None:
        result = run_backtest(
            strategy_type="mean_reversion",
            parameters={
                "symbol": "MSFT",
                "lookback": 15,
                "z_threshold": 1.2,
                "seed": 7,
            },
            start_date="2023-01-01",
            end_date="2023-06-30",
            initial_capital=50_000.0,
        )
        assert _RESULT_KEYS.issubset(result.keys())
        assert result["final_capital"] > 0

    def test_same_seed_is_deterministic(self) -> None:
        params = {"symbol": "AAPL", "lookback": 10, "threshold": 0.01, "seed": 99}
        r1 = run_backtest("momentum", params, "2023-01-01", "2023-04-01", 10_000.0)
        r2 = run_backtest("momentum", params, "2023-01-01", "2023-04-01", 10_000.0)
        assert r1 == r2

    def test_short_date_range_still_runs(self) -> None:
        """A short window with a lookback longer than the window shouldn't crash -
        signals should just come back "flat" until there's enough history."""
        result = run_backtest(
            strategy_type="momentum",
            parameters={"symbol": "AAPL", "lookback": 20, "seed": 1},
            start_date="2023-01-01",
            end_date="2023-01-15",
            initial_capital=10_000.0,
        )
        assert result["final_capital"] == pytest.approx(10_000.0, rel=0.05)


class TestRLAgentBacktest:
    """rl_agent - genuinely trains an ai_models.agents agent."""

    def test_ddpg_backtest_runs(self) -> None:
        result = run_backtest(
            strategy_type="rl_agent",
            parameters={
                "algorithm": "ddpg",
                "n_assets": 2,
                "episodes": 2,
                "max_steps": 15,
                "seed": 1,
            },
            start_date="2023-01-01",
            end_date="2023-03-01",
            initial_capital=10_000.0,
        )
        assert _RESULT_KEYS.issubset(result.keys())
        assert result["algorithm"] == "ddpg"
        assert result["final_capital"] > 0
        assert result["total_trades"] >= 0

    def test_unknown_algorithm_falls_back_to_ddpg(self) -> None:
        result = run_backtest(
            strategy_type="rl_agent",
            parameters={
                "algorithm": "ppo",  # requires stable-baselines3; not installed in CI
                "n_assets": 2,
                "episodes": 1,
                "max_steps": 10,
                "seed": 1,
            },
            start_date="2023-01-01",
            end_date="2023-02-01",
            initial_capital=10_000.0,
        )
        assert result["algorithm"] == "ddpg"


class TestMLAlphaBacktest:
    """ml_alpha - genuinely trains ai_models.forecasting.AdvancedTimeSeriesForecaster."""

    def test_ml_alpha_backtest_runs(self) -> None:
        result = run_backtest(
            strategy_type="ml_alpha",
            parameters={
                "symbol": "GOOG",
                "input_seq_length": 10,
                "epochs": 1,
                "d_model": 8,
                "num_heads": 2,
                "num_layers": 1,
                "dff": 16,
                "seed": 3,
            },
            start_date="2023-01-01",
            end_date="2023-08-01",
            initial_capital=100_000.0,
        )
        assert _RESULT_KEYS.issubset(result.keys())
        assert result["final_capital"] > 0

    def test_ml_alpha_too_short_range_raises(self) -> None:
        with pytest.raises(ValueError):
            run_backtest(
                strategy_type="ml_alpha",
                parameters={"symbol": "AAPL", "input_seq_length": 60},
                start_date="2023-01-01",
                end_date="2023-01-20",
                initial_capital=10_000.0,
            )


class TestUnsupportedStrategyType:
    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError):
            run_backtest(
                strategy_type="not_a_real_type",
                parameters={},
                start_date="2023-01-01",
                end_date="2023-06-01",
                initial_capital=10_000.0,
            )


class TestRunBacktestDetailed:
    """run_backtest_detailed - the full field set + equity curve that
    POST /api/v1/backtest/ (app/api/v1/routers/backtest.py) returns."""

    _FULL_KEYS = {
        "finalCapital",
        "totalReturn",
        "annualisedReturn",
        "sharpeRatio",
        "sortinoRatio",
        "calmarRatio",
        "maxDrawdown",
        "maxDrawdownDuration",
        "winRate",
        "profitFactor",
        "totalTrades",
        "avgWin",
        "avgLoss",
        "bestMonth",
        "worstMonth",
        "equityCurve",
    }

    def test_momentum_detailed_has_all_fields(self) -> None:
        result = run_backtest_detailed(
            strategy_type="momentum",
            parameters={"symbol": "AAPL", "lookback": 10, "seed": 1},
            start_date="2023-01-01",
            end_date="2023-06-30",
            initial_capital=100_000.0,
        )
        assert self._FULL_KEYS.issubset(result.keys())
        assert len(result["equityCurve"]) > 0
        point = result["equityCurve"][0]
        assert {"date", "equity", "benchmark", "drawdown"} == set(point.keys())

    def test_rl_agent_detailed_has_equity_curve(self) -> None:
        result = run_backtest_detailed(
            strategy_type="rl_agent",
            parameters={"n_assets": 2, "episodes": 2, "max_steps": 15, "seed": 1},
            start_date="2023-01-01",
            end_date="2023-03-01",
            initial_capital=10_000.0,
        )
        assert self._FULL_KEYS.issubset(result.keys())
        assert len(result["equityCurve"]) > 0
        assert result["equityCurve"][0]["equity"] == pytest.approx(10_000.0, rel=0.01)

    def test_equity_curve_first_point_is_initial_capital(self) -> None:
        result = run_backtest_detailed(
            strategy_type="mean_reversion",
            parameters={"symbol": "MSFT", "lookback": 10, "seed": 2},
            start_date="2023-01-01",
            end_date="2023-04-01",
            initial_capital=50_000.0,
        )
        assert result["equityCurve"][0]["equity"] == pytest.approx(50_000.0, abs=1.0)

    def test_default_rl_parameters_stay_fast(self) -> None:
        """The demo 'rl_agent' strategy seeded by app.main has no
        episodes/max_steps in its parameters at all - the defaults must be
        small enough that this still runs synchronously in a reasonable
        time inside an HTTP request."""
        import time

        t0 = time.time()
        run_backtest_detailed(
            strategy_type="rl_agent",
            parameters={"actor_lr": 0.0001, "critic_lr": 0.001, "gamma": 0.99},
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=100_000.0,
        )
        assert time.time() - t0 < 15.0
