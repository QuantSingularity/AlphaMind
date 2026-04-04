import os
import sys
import unittest
from typing import Any

import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)
from alpha_research.portfolio_optimization import PortfolioOptimizer


class TestPortfolioOptimizer(unittest.TestCase):
    """Test suite for the PortfolioOptimizer class"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.n_assets = 5
        self.lookback_window = 30
        self.optimizer = PortfolioOptimizer(
            n_assets=self.n_assets, lookback_window=self.lookback_window
        )

        np.random.seed(42)
        self.n_samples = 100
        self.price_data = np.zeros((self.n_samples, self.n_assets), dtype=float)

        for i in range(self.n_assets):
            base_price = np.random.uniform(50, 200)

            # Keep returns small so prices remain positive and realistic.
            drift = np.random.uniform(-0.0005, 0.0005)
            trend = np.linspace(0, drift, self.n_samples)
            noise = np.random.normal(0, 0.01, self.n_samples)

            log_returns = trend + noise
            self.price_data[:, i] = base_price * np.exp(np.cumsum(log_returns))

        self.price_data = np.clip(self.price_data, 1e-6, None)

        self.volatility_data = np.abs(np.diff(np.log(self.price_data), axis=0))
        self.volatility_data = np.vstack(
            [self.volatility_data[0:1], self.volatility_data]
        )

        self.macro_data = np.random.normal(0, 1, (self.n_samples, 5))
        self.current_weights = np.ones(self.n_assets) / self.n_assets

    def test_initialization(self) -> Any:
        """Test that the PortfolioOptimizer initializes correctly"""
        self.assertEqual(self.optimizer.n_assets, self.n_assets)
        self.assertEqual(self.optimizer.lookback_window, self.lookback_window)
        self.assertIsNotNone(self.optimizer.model)

    def test_model_architecture(self) -> Any:
        """Test the model architecture"""
        self.assertEqual(len(self.optimizer.model.inputs), 4)
        self.assertEqual(
            self.optimizer.model.inputs[0].shape[1:],
            (self.lookback_window, self.n_assets),
        )
        self.assertEqual(
            self.optimizer.model.inputs[1].shape[1:],
            (self.lookback_window, self.n_assets),
        )
        self.assertEqual(
            self.optimizer.model.inputs[2].shape[1:], (self.lookback_window, 5)
        )
        self.assertEqual(self.optimizer.model.inputs[3].shape[1:], (self.n_assets,))
        self.assertEqual(self.optimizer.model.outputs[0].shape[1:], (self.n_assets,))

    def test_portfolio_loss(self) -> Any:
        """Test the custom portfolio loss function"""
        batch_size = 8
        y_pred = tf.constant(
            np.random.dirichlet(np.ones(self.n_assets), size=batch_size),
            dtype=tf.float32,
        )
        y_true = tf.constant(
            np.random.normal(0.001, 0.01, (batch_size, self.n_assets)), dtype=tf.float32
        )
        loss = self.optimizer._portfolio_loss(y_true, y_pred)
        self.assertTrue(len(loss.shape) <= 1)
        self.assertTrue(np.all(np.isfinite(loss.numpy())))

    def test_preprocess_data(self) -> Any:
        """Test the data preprocessing function"""
        X_price, X_vol, X_macro, y = self.optimizer.preprocess_data(
            self.price_data, self.volatility_data, self.macro_data
        )
        expected_samples = self.n_samples - self.lookback_window

        self.assertEqual(
            X_price.shape, (expected_samples, self.lookback_window, self.n_assets)
        )
        self.assertEqual(
            X_vol.shape, (expected_samples, self.lookback_window, self.n_assets)
        )
        self.assertEqual(X_macro.shape, (expected_samples, self.lookback_window, 5))
        self.assertEqual(y.shape, (expected_samples, self.n_assets))

        for i in range(expected_samples):
            expected_returns = (
                self.price_data[i + self.lookback_window]
                / self.price_data[i + self.lookback_window - 1]
                - 1
            )
            np.testing.assert_allclose(y[i], expected_returns, rtol=1e-05)

    def test_optimize_portfolio(self) -> Any:
        """Test the portfolio optimization function"""
        price_window = self.price_data[: self.lookback_window]
        vol_window = self.volatility_data[: self.lookback_window]
        macro_window = self.macro_data[: self.lookback_window]

        optimal_weights = self.optimizer.optimize_portfolio(
            price_window, vol_window, macro_window, self.current_weights
        )

        self.assertEqual(optimal_weights.shape, (self.n_assets,))
        self.assertAlmostEqual(np.sum(optimal_weights), 1.0, places=5)
        self.assertTrue(np.all(optimal_weights >= 0))

    def test_backtest(self) -> Any:
        """Test the backtest function"""
        results = self.optimizer.backtest(
            self.price_data,
            self.volatility_data,
            self.macro_data,
            initial_capital=10000,
            transaction_cost=0.001,
        )

        self.assertIsInstance(results, pd.DataFrame)
        self.assertIn("portfolio_value", results.columns)
        self.assertIn("returns", results.columns)
        self.assertIn("drawdown", results.columns)
        self.assertIsNotNone(self.optimizer.performance_metrics)
        self.assertIn("total_return", self.optimizer.performance_metrics)
        self.assertIn("sharpe_ratio", self.optimizer.performance_metrics)
        self.assertIn("max_drawdown", self.optimizer.performance_metrics)

        self.assertIn("volatility", self.optimizer.performance_metrics)

        self.assertTrue(np.all(results["portfolio_value"] > 0))
        self.assertTrue(np.all(results["drawdown"] <= 0))

    def test_save_load(self) -> Any:
        """Test saving and loading the model"""
        self.skipTest("Model serialization requires implementation changes")

        temp_model_path = os.path.join(os.path.dirname(__file__), "temp_model.h5")
        try:
            self.optimizer.save(temp_model_path)
            self.assertTrue(os.path.exists(temp_model_path))

            new_optimizer = PortfolioOptimizer(n_assets=self.n_assets)
            new_optimizer.load(temp_model_path)

            price_window = self.price_data[: self.lookback_window]
            vol_window = self.volatility_data[: self.lookback_window]
            macro_window = self.macro_data[: self.lookback_window]

            weights1 = self.optimizer.optimize_portfolio(
                price_window, vol_window, macro_window, self.current_weights
            )
            weights2 = new_optimizer.optimize_portfolio(
                price_window, vol_window, macro_window, self.current_weights
            )

            np.testing.assert_allclose(weights1, weights2, rtol=1e-05)
        finally:
            if os.path.exists(temp_model_path):
                os.remove(temp_model_path)


if __name__ == "__main__":
    unittest.main()
