"""
Unit tests for PortfolioOptimizer (analytics/alpha_research/portfolio_optimization.py).

Focuses on model construction, preprocessing, and weight output properties —
avoiding full training loops to keep the test suite fast.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import tensorflow as tf

    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TF_AVAILABLE, reason="TensorFlow not installed")


@pytest.fixture(scope="module")
def optimizer():
    from analytics.alpha_research.portfolio_optimization import PortfolioOptimizer

    return PortfolioOptimizer(n_assets=4, lookback_window=10, hidden_units=16)


@pytest.fixture(scope="module")
def dummy_data():
    """Small synthetic dataset for preprocessing/inference tests."""
    rng = np.random.default_rng(0)
    T = 50
    n_assets = 4
    prices = 100 * np.exp(
        np.cumsum(rng.standard_normal((T, n_assets)) * 0.01, axis=0)
    ).astype(np.float32)
    vols = np.abs(rng.standard_normal((T, n_assets)) * 0.01 + 0.015).astype(np.float32)
    macro = rng.standard_normal((T, 5)).astype(np.float32)
    return prices, vols, macro


class TestModelConstruction:
    def test_model_is_keras(self, optimizer):
        assert isinstance(optimizer.model, tf.keras.Model)

    def test_output_units_match_n_assets(self, optimizer):
        last_layer = optimizer.model.layers[-1]
        assert last_layer.units == optimizer.n_assets

    def test_output_activation_softmax(self, optimizer):
        config = optimizer.model.layers[-1].get_config()
        assert "softmax" in config.get("activation", "")

    def test_model_has_four_inputs(self, optimizer):
        assert len(optimizer.model.inputs) == 4

    def test_model_has_one_output(self, optimizer):
        assert len(optimizer.model.outputs) == 1


class TestWeightProperties:
    def test_output_sums_to_one(self, optimizer, dummy_data):
        prices, vols, macro = dummy_data
        lw = optimizer.lookback_window

        price_seq = prices[:lw][np.newaxis]  # (1, lw, n_assets)
        vol_seq = vols[:lw][np.newaxis]
        macro_seq = macro[:lw][np.newaxis]
        curr_w = np.ones((1, optimizer.n_assets), dtype=np.float32) / optimizer.n_assets

        weights = optimizer.model.predict(
            [price_seq, vol_seq, macro_seq, curr_w], verbose=0
        )
        np.testing.assert_allclose(weights.sum(axis=1), 1.0, atol=1e-5)

    def test_output_non_negative(self, optimizer, dummy_data):
        prices, vols, macro = dummy_data
        lw = optimizer.lookback_window

        price_seq = prices[:lw][np.newaxis]
        vol_seq = vols[:lw][np.newaxis]
        macro_seq = macro[:lw][np.newaxis]
        curr_w = np.ones((1, optimizer.n_assets), dtype=np.float32) / optimizer.n_assets

        weights = optimizer.model.predict(
            [price_seq, vol_seq, macro_seq, curr_w], verbose=0
        )
        assert np.all(weights >= 0)

    def test_output_shape(self, optimizer, dummy_data):
        prices, vols, macro = dummy_data
        lw = optimizer.lookback_window
        batch = 3

        price_seq = np.stack([prices[:lw]] * batch)
        vol_seq = np.stack([vols[:lw]] * batch)
        macro_seq = np.stack([macro[:lw]] * batch)
        curr_w = np.tile(
            np.ones(optimizer.n_assets) / optimizer.n_assets, (batch, 1)
        ).astype(np.float32)

        weights = optimizer.model.predict(
            [price_seq, vol_seq, macro_seq, curr_w], verbose=0
        )
        assert weights.shape == (batch, optimizer.n_assets)
