"""
Unit tests for ExtremeScenarioGenerator (risk/stress_testing.py).

Covers:
* Both copula types (t and gaussian).
* Scenario shape, positivity properties.
* Dependence matrix construction with tail adjustment.
* apply_shock output structure and financial reasonableness.
* Error handling for non-square correlation matrices.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from risk.stress_testing import ExtremeScenarioGenerator


@pytest.fixture(scope="module")
def corr_3x3() -> np.ndarray:
    """A 3x3 valid correlation matrix."""
    rho = 0.40
    C = rho * np.ones((3, 3)) + (1 - rho) * np.eye(3)
    return C


@pytest.fixture(scope="module")
def weights_3() -> np.ndarray:
    return np.array([0.5, 0.3, 0.2])


class TestDependenceMatrix:
    def test_diagonal_ones(self, corr_3x3):
        gen = ExtremeScenarioGenerator(tail_dependence=0.20)
        crisis = gen._create_dependence_matrix(corr_3x3)
        np.testing.assert_allclose(np.diag(crisis), 1.0)

    def test_off_diagonal_increased(self, corr_3x3):
        """Crisis correlations should be >= base correlations."""
        gen = ExtremeScenarioGenerator(tail_dependence=0.30)
        crisis = gen._create_dependence_matrix(corr_3x3)
        mask = ~np.eye(3, dtype=bool)
        assert np.all(crisis[mask] >= corr_3x3[mask] - 1e-9)

    def test_symmetry_preserved(self, corr_3x3):
        gen = ExtremeScenarioGenerator(tail_dependence=0.25)
        crisis = gen._create_dependence_matrix(corr_3x3)
        np.testing.assert_allclose(crisis, crisis.T, atol=1e-10)

    def test_non_square_raises(self):
        gen = ExtremeScenarioGenerator()
        with pytest.raises(ValueError, match="square"):
            gen._create_dependence_matrix(np.ones((2, 3)))

    def test_zero_tail_dependence_unchanged(self, corr_3x3):
        gen = ExtremeScenarioGenerator(tail_dependence=0.0)
        crisis = gen._create_dependence_matrix(corr_3x3)
        # With tail_dependence=0, off-diag values are unchanged
        np.testing.assert_allclose(crisis, corr_3x3, atol=1e-10)

    def test_full_tail_dependence_gives_ones(self, corr_3x3):
        gen = ExtremeScenarioGenerator(tail_dependence=1.0)
        crisis = gen._create_dependence_matrix(corr_3x3)
        np.testing.assert_allclose(crisis, np.ones((3, 3)), atol=1e-10)


class TestScenarioGeneration:
    @pytest.mark.parametrize("copula", ["t", "gaussian"])
    def test_shape(self, corr_3x3, copula):
        gen = ExtremeScenarioGenerator(copula=copula)
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=500)
        assert scenarios.shape == (500, 3)

    def test_t_copula_finite(self, corr_3x3):
        gen = ExtremeScenarioGenerator(copula="t")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=200)
        assert np.all(np.isfinite(scenarios))

    def test_gaussian_copula_finite(self, corr_3x3):
        gen = ExtremeScenarioGenerator(copula="gaussian")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=200)
        assert np.all(np.isfinite(scenarios))

    def test_unknown_copula_raises(self, corr_3x3):
        gen = ExtremeScenarioGenerator(copula="frank")
        with pytest.raises(NotImplementedError):
            gen.generate_crisis_scenarios(corr_3x3)

    def test_t_copula_heavier_tails(self, corr_3x3):
        """t-copula should produce more extreme scenarios than Gaussian."""
        np.random.seed(42)
        gen_t = ExtremeScenarioGenerator(copula="t")
        gen_g = ExtremeScenarioGenerator(copula="gaussian")
        s_t = gen_t.generate_crisis_scenarios(corr_3x3, n_scenarios=5_000)
        s_g = gen_g.generate_crisis_scenarios(corr_3x3, n_scenarios=5_000)
        # Kurtosis of t(df=3) > Gaussian kurtosis
        from scipy.stats import kurtosis

        kurt_t = kurtosis(s_t[:, 0])
        kurt_g = kurtosis(s_g[:, 0])
        assert (
            kurt_t > kurt_g
        ), f"t-copula kurtosis {kurt_t:.2f} should exceed Gaussian {kurt_g:.2f}"


class TestApplyShock:
    def test_returns_dataframe(self, corr_3x3, weights_3):
        gen = ExtremeScenarioGenerator(copula="t")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=1_000)
        result = gen.apply_shock(weights_3, scenarios)
        assert isinstance(result, pd.DataFrame)

    def test_expected_columns(self, corr_3x3, weights_3):
        gen = ExtremeScenarioGenerator(copula="t")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=1_000)
        result = gen.apply_shock(weights_3, scenarios)
        for col in ["VaR_99", "Max_Drawdown", "Leverage_Impact", "Mean_Return"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_var99_le_mean_return(self, corr_3x3, weights_3):
        """VaR_99 represents the 1st percentile and should be <= mean."""
        gen = ExtremeScenarioGenerator(copula="t")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=2_000)
        result = gen.apply_shock(weights_3, scenarios)
        assert result["VaR_99"].iloc[0] <= result["Mean_Return"].iloc[0]

    def test_max_drawdown_is_minimum(self, corr_3x3, weights_3):
        gen = ExtremeScenarioGenerator(copula="t")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=2_000)
        result = gen.apply_shock(weights_3, scenarios)
        port_returns = scenarios @ weights_3
        assert result["Max_Drawdown"].iloc[0] == pytest.approx(port_returns.min())

    def test_leverage_impact_non_negative(self, corr_3x3, weights_3):
        gen = ExtremeScenarioGenerator(copula="gaussian")
        scenarios = gen.generate_crisis_scenarios(corr_3x3, n_scenarios=1_000)
        result = gen.apply_shock(weights_3, scenarios)
        assert result["Leverage_Impact"].iloc[0] >= 0.0
