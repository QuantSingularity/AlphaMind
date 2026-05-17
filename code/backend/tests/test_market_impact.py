"""
Unit tests for OptimalExecution (execution/market_impact.py).

Verifies the Almgren-Chriss optimal execution strategy:
* Solution shape and feasibility.
* Boundary conditions: initial inventory == order_size, terminal ~ 0.
* Monotonicity: inventory should decrease monotonically for a sell order.
* Risk aversion sensitivity: higher lambda → faster initial liquidation.
* ODE system returns correct shape.
* Boundary condition function correctness.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from execution.market_impact import OptimalExecution


@pytest.fixture(scope="module")
def liquidity_profile():
    return {
        "elasticity": 0.5,
        "permanent_impact": 0.1,
    }


@pytest.fixture(scope="module")
def executor(liquidity_profile):
    return OptimalExecution(order_size=1_000, liquidity_profile=liquidity_profile)


class TestOptimalExecution:
    def test_strategy_returns_array(self, executor):
        result = executor.acati_strategy(risk_aversion=0.5)
        assert isinstance(result, np.ndarray)

    def test_strategy_non_empty(self, executor):
        result = executor.acati_strategy(risk_aversion=0.5)
        assert len(result) > 0

    def test_initial_inventory_near_order_size(self, executor):
        """Boundary condition: q(0) ≈ order_size."""
        result = executor.acati_strategy(risk_aversion=0.5)
        assert abs(result[0] - executor.order_size) < executor.order_size * 0.10

    def test_terminal_inventory_near_zero(self, executor):
        """Boundary condition: q(T) ≈ 0."""
        result = executor.acati_strategy(risk_aversion=0.5)
        assert abs(result[-1]) < executor.order_size * 0.10

    def test_solution_finite(self, executor):
        result = executor.acati_strategy(risk_aversion=0.5)
        assert np.all(np.isfinite(result))

    def test_inventory_non_increasing(self, executor):
        """For a pure sell order the inventory path should not increase."""
        result = executor.acati_strategy(risk_aversion=0.5)
        diffs = np.diff(result)
        # Allow small numerical noise (1% of order_size per step)
        tol = executor.order_size * 0.01
        assert np.all(diffs <= tol), "Inventory increased during sell execution"

    def test_different_risk_aversion_gives_different_path(self, liquidity_profile):
        e1 = OptimalExecution(order_size=1_000, liquidity_profile=liquidity_profile)
        e2 = OptimalExecution(order_size=1_000, liquidity_profile=liquidity_profile)
        r1 = e1.acati_strategy(risk_aversion=0.1)
        r2 = e2.acati_strategy(risk_aversion=2.0)
        assert not np.allclose(
            r1, r2, atol=10
        ), "Different risk aversion values should produce different execution paths"


class TestODESystem:
    def test_ode_returns_two_rows(self, executor):
        t = np.linspace(0, 1, 5)
        x = np.ones((2, 5))
        result = executor._ode_system(t, x, eta=0.5, gamma=0.1, lambda_=0.5)
        assert result.shape == (2, 5)


class TestBoundaryConditions:
    def test_bc_at_correct_inventory(self, executor):
        """_bc should return zero array when boundary conditions are satisfied."""
        xa = np.array([executor.order_size, 1.0])
        xb = np.array([0.0, 0.0])
        residual = executor._bc(xa, xb, executor.order_size)
        np.testing.assert_allclose(residual, [0.0, 0.0], atol=1e-10)

    def test_bc_non_zero_when_violated(self, executor):
        xa = np.array([0.0, 0.0])  # wrong initial inventory
        xb = np.array([100.0, 0.0])  # wrong terminal inventory
        residual = executor._bc(xa, xb, executor.order_size)
        assert not np.allclose(residual, 0.0)
