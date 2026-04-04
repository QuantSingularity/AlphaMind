import os
from typing import Any

import numpy as np
import pandas as pd
import pytest
import tensorflow as tf
from alpha_research.portfolio_optimization import PortfolioOptimizer

N_ASSETS = 3
LOOKBACK_WINDOW = 10
HIDDEN_UNITS = 32
N_SAMPLES = 50
N_MACRO_FACTORS = 5


@tf.keras.utils.register_keras_serializable()
def portfolio_loss(y_true: Any, y_pred: Any) -> Any:
    """Custom loss function to maximize portfolio returns."""
    portfolio_returns = tf.reduce_sum(y_true * y_pred, axis=1)
    return -tf.reduce_mean(portfolio_returns)


@pytest.fixture
def optimizer() -> Any:
    """Fixture for a PortfolioOptimizer instance."""
    opt = PortfolioOptimizer(
        n_assets=N_ASSETS, lookback_window=LOOKBACK_WINDOW, hidden_units=HIDDEN_UNITS
    )
    try:
        if opt.model.loss.__name__ != portfolio_loss.__name__:
            opt.model.compile(optimizer="adam", loss=portfolio_loss)
    except AttributeError:
        opt.model.compile(optimizer="adam", loss=portfolio_loss)
    return opt


@pytest.fixture
def sample_data() -> Any:
    """Fixture for sample input data."""
    np.random.seed(42)
    price_data = np.random.rand(N_SAMPLES, N_ASSETS) * 100 + 50
    volatility_data = np.random.rand(N_SAMPLES, N_ASSETS) * 0.2 + 0.1
    macro_data = np.random.rand(N_SAMPLES, N_MACRO_FACTORS)
    return (price_data, volatility_data, macro_data)


def test_optimizer_init(optimizer: Any) -> Any:
    """Test PortfolioOptimizer initialization."""
    assert optimizer.n_assets == N_ASSETS
    assert optimizer.lookback_window == LOOKBACK_WINDOW
    assert isinstance(optimizer.model, tf.keras.Model)
    assert isinstance(optimizer.scaler, object)
    assert optimizer.model.loss.__name__ == portfolio_loss.__name__


def test_build_model_structure(optimizer: Any) -> Any:
    """Test model structure and output shape."""
    model = optimizer.model
    assert model.output_shape == (None, N_ASSETS)


def test_portfolio_loss_calculation() -> Any:
    """Test the custom portfolio loss function directly."""
    y_true = tf.constant([[0.01, -0.005, 0.02], [0.005, 0.01, -0.01]], dtype=tf.float32)
    y_pred = tf.constant([[0.4, 0.3, 0.3], [0.5, 0.2, 0.3]], dtype=tf.float32)
    loss = portfolio_loss(y_true, y_pred)
    assert isinstance(loss, tf.Tensor)
    assert loss.shape == tf.TensorShape([])
    expected_return_1 = 0.4 * 0.01 + 0.3 * -0.005 + 0.3 * 0.02
    expected_return_2 = 0.5 * 0.005 + 0.2 * 0.01 + 0.3 * -0.01
    expected_loss = -(expected_return_1 + expected_return_2) / 2
    assert tf.experimental.numpy.isclose(loss, expected_loss)


def test_preprocess_data_shapes(optimizer: Any, sample_data: Any) -> Any:
    """Test preprocess_data output shapes."""
    price_data, volatility_data, macro_data = sample_data
    X_price, X_vol, X_macro, y = optimizer.preprocess_data(
        price_data, volatility_data, macro_data
    )
    expected_samples = N_SAMPLES - LOOKBACK_WINDOW
    assert X_price.shape == (expected_samples, LOOKBACK_WINDOW, N_ASSETS)
    assert X_vol.shape == (expected_samples, LOOKBACK_WINDOW, N_ASSETS)
    assert X_macro.shape == (expected_samples, LOOKBACK_WINDOW, N_MACRO_FACTORS)
    assert y.shape == (expected_samples, N_ASSETS)


def test_optimize_portfolio_output(optimizer: Any, sample_data: Any) -> Any:
    """Test optimize_portfolio output."""
    price_data, volatility_data, macro_data = sample_data
    recent_price = price_data[-LOOKBACK_WINDOW:]
    recent_vol = volatility_data[-LOOKBACK_WINDOW:]
    recent_macro = macro_data[-LOOKBACK_WINDOW:]
    current_weights = np.ones(N_ASSETS) / N_ASSETS
    optimal_weights = optimizer.optimize_portfolio(
        recent_price, recent_vol, recent_macro, current_weights
    )
    assert optimal_weights.shape == (N_ASSETS,)
    assert np.isclose(np.sum(optimal_weights), 1.0)
    assert np.all(optimal_weights >= 0)


def test_backtest_output_structure(optimizer: Any, sample_data: Any) -> Any:
    """Test backtest output DataFrame and metrics."""
    price_data, volatility_data, macro_data = sample_data
    optimizer.optimize_portfolio = lambda p, v, m, cw: np.ones(N_ASSETS) / N_ASSETS
    results = optimizer.backtest(price_data, volatility_data, macro_data)
    assert isinstance(results, pd.DataFrame)
    assert "portfolio_value" in results.columns
    assert "returns" in results.columns
    assert "drawdown" in results.columns
    assert len(results) == N_SAMPLES - LOOKBACK_WINDOW
    assert hasattr(optimizer, "performance_metrics")
    assert isinstance(optimizer.performance_metrics, dict)
    for metric in ["total_return", "sharpe_ratio", "max_drawdown", "volatility"]:
        assert metric in optimizer.performance_metrics


def test_save_load_model(optimizer: Any, tmp_path: Any) -> Any:
    """Test saving and loading the model."""
    model_path = os.path.join(str(tmp_path), "test_portfolio_model.keras")
    if (
        not hasattr(optimizer.model, "loss")
        or optimizer.model.loss.__name__ != portfolio_loss.__name__
    ):
        optimizer.model.compile(optimizer="adam", loss=portfolio_loss)
    optimizer.save(model_path)
    assert os.path.exists(model_path)
    loaded_keras_model = tf.keras.models.load_model(model_path)
    new_optimizer = PortfolioOptimizer(
        n_assets=N_ASSETS, lookback_window=LOOKBACK_WINDOW, hidden_units=HIDDEN_UNITS
    )
    new_optimizer.model = loaded_keras_model
    assert isinstance(new_optimizer.model, tf.keras.Model)
    assert new_optimizer.model.loss.__name__ == portfolio_loss.__name__
    dummy_price = np.random.rand(1, LOOKBACK_WINDOW, N_ASSETS)
    dummy_vol = np.random.rand(1, LOOKBACK_WINDOW, N_ASSETS)
    dummy_macro = np.random.rand(1, LOOKBACK_WINDOW, N_MACRO_FACTORS)
    dummy_weights = np.random.rand(1, N_ASSETS)
    _ = optimizer.model([dummy_price, dummy_vol, dummy_macro, dummy_weights])
    _ = new_optimizer.model([dummy_price, dummy_vol, dummy_macro, dummy_weights])
    assert len(optimizer.model.get_weights()) == len(new_optimizer.model.get_weights())
    for w1, w2 in zip(optimizer.model.get_weights(), new_optimizer.model.get_weights()):
        assert np.allclose(w1, w2)
