"""
Unit tests for the multi_horizon forecast evaluation utilities.
"""

from __future__ import annotations

import numpy as np
import pytest
from ai_models.forecasting.multi_horizon import evaluate_multi_horizon


class TestEvaluateMultiHorizon:
    """Tests for evaluate_multi_horizon()."""

    @pytest.fixture(scope="class")
    def perfect_predictions(self):
        rng = np.random.default_rng(0)
        y = rng.standard_normal((200, 5)).astype(np.float32)
        return y, y.copy()  # pred == true

    @pytest.fixture(scope="class")
    def random_predictions(self):
        rng = np.random.default_rng(42)
        y_true = rng.standard_normal((200, 5)).astype(np.float32)
        y_pred = rng.standard_normal((200, 5)).astype(np.float32)
        return y_pred, y_true

    def test_returns_dict(self, random_predictions):
        y_pred, y_true = random_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1, 3, 5])
        assert isinstance(result, dict)

    def test_keys_match_horizons(self, random_predictions):
        y_pred, y_true = random_predictions
        horizons = [1, 2, 4]
        result = evaluate_multi_horizon(y_pred, y_true, horizons=horizons)
        assert set(result.keys()) == {str(h) for h in horizons}

    def test_metric_keys_present(self, random_predictions):
        y_pred, y_true = random_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1])
        metrics = result["1"]
        assert "ic" in metrics
        assert "r2" in metrics
        assert "mse" in metrics
        assert "hit_rate" in metrics

    def test_perfect_ic(self, perfect_predictions):
        y_pred, y_true = perfect_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1])
        assert result["1"]["ic"] == pytest.approx(1.0, abs=1e-4)

    def test_perfect_r2(self, perfect_predictions):
        y_pred, y_true = perfect_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1])
        assert result["1"]["r2"] == pytest.approx(1.0, abs=1e-4)

    def test_perfect_mse_is_zero(self, perfect_predictions):
        y_pred, y_true = perfect_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[2])
        assert result["2"]["mse"] == pytest.approx(0.0, abs=1e-6)

    def test_hit_rate_bounded(self, random_predictions):
        y_pred, y_true = random_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1, 3])
        for h in ["1", "3"]:
            hr = result[h]["hit_rate"]
            assert 0.0 <= hr <= 1.0

    def test_out_of_range_horizon_skipped(self, random_predictions):
        y_pred, y_true = random_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1, 999])
        assert "1" in result
        assert "999" not in result

    def test_mse_non_negative(self, random_predictions):
        y_pred, y_true = random_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1, 2, 3, 4, 5])
        for metrics in result.values():
            assert metrics["mse"] >= 0.0

    def test_all_metrics_finite(self, random_predictions):
        y_pred, y_true = random_predictions
        result = evaluate_multi_horizon(y_pred, y_true, horizons=[1, 5])
        for metrics in result.values():
            for val in metrics.values():
                assert np.isfinite(val), f"Non-finite metric value: {val}"
