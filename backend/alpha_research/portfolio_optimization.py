import logging
from typing import Any, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.layers import LSTM, BatchNormalization, Dense, Dropout, Input
from tensorflow.keras.models import Model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Advanced portfolio optimization using deep reinforcement learning.
    Extends the basic RL approach with more sophisticated state representation
    and reward functions.
    """

    def __init__(
        self, n_assets: Any, lookback_window: Any = 60, hidden_units: Any = 64
    ) -> None:
        self.n_assets = n_assets
        self.lookback_window = lookback_window
        self.hidden_units = hidden_units
        self.price_scaler = StandardScaler()
        self.vol_scaler = StandardScaler()
        self.macro_scaler = StandardScaler()
        self.scaler = self.price_scaler
        self.model = self._build_model()
        self.performance_metrics = {}

    def _build_model(self) -> Any:
        """Build the portfolio optimization model architecture"""
        price_input = Input(
            shape=(self.lookback_window, self.n_assets), name="price_history"
        )
        vol_input = Input(
            shape=(self.lookback_window, self.n_assets), name="volatility_history"
        )
        macro_input = Input(shape=(self.lookback_window, 5), name="macro_factors")
        current_weights = Input(shape=(self.n_assets,), name="current_weights")
        x1 = LSTM(self.hidden_units, return_sequences=True)(price_input)
        x1 = BatchNormalization()(x1)
        x1 = LSTM(self.hidden_units)(x1)
        x2 = LSTM(self.hidden_units, return_sequences=True)(vol_input)
        x2 = BatchNormalization()(x2)
        x2 = LSTM(self.hidden_units)(x2)
        x3 = LSTM(self.hidden_units)(macro_input)
        combined = tf.keras.layers.concatenate([x1, x2, x3, current_weights])
        x = Dense(128, activation="relu")(combined)
        x = Dropout(0.3)(x)
        x = Dense(64, activation="relu")(x)
        x = Dropout(0.3)(x)
        outputs = Dense(self.n_assets, activation="softmax", name="portfolio_weights")(
            x
        )
        model = Model(
            inputs=[price_input, vol_input, macro_input, current_weights],
            outputs=outputs,
        )
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss=self._portfolio_loss,
        )
        return model

    def _portfolio_loss(self, y_true: Any, y_pred: Any) -> Any:
        """
        Custom loss function for portfolio optimization.
        Proxies the negative Sharpe ratio combined with risk penalties.

        Args:
            y_true: The true next-period asset returns (n_samples, n_assets).
            y_pred: The predicted portfolio weights (n_samples, n_assets).

        Returns:
            The loss value (scalar).
        """
        portfolio_returns = tf.reduce_sum(y_pred * y_true, axis=1)
        mean_returns = tf.reduce_mean(portfolio_returns)
        std_returns = tf.math.reduce_std(portfolio_returns)
        neg_sharpe = -mean_returns / (std_returns + 1e-06)
        concentration_penalty = tf.reduce_sum(tf.square(y_pred), axis=1)
        return neg_sharpe + 0.1 * tf.reduce_mean(concentration_penalty)

    def preprocess_data(
        self, price_data: Any, volatility_data: Any, macro_data: Any
    ) -> Any:
        """
        Preprocess input data for the model: scale and create lookback sequences.

        Args:
            price_data: Historical price data (n_samples, n_assets)
            volatility_data: Historical volatility data (n_samples, n_assets)
            macro_data: Macroeconomic factors (n_samples, n_macro_factors)

        Returns:
            X_price, X_vol, X_macro, y (next period returns)
        """
        price_scaled = self.price_scaler.fit_transform(price_data)
        vol_scaled = self.vol_scaler.fit_transform(volatility_data)
        macro_scaled = self.macro_scaler.fit_transform(macro_data)
        returns = price_data[1:] / price_data[:-1] - 1
        X_price, X_vol, X_macro, y = ([], [], [], [])
        for i in range(len(price_scaled) - self.lookback_window):
            X_price.append(price_scaled[i : i + self.lookback_window])
            X_vol.append(vol_scaled[i : i + self.lookback_window])
            X_macro.append(macro_scaled[i : i + self.lookback_window])
            y.append(returns[i + self.lookback_window - 1])
        return (np.array(X_price), np.array(X_vol), np.array(X_macro), np.array(y))

    def train(
        self,
        price_data: Any,
        volatility_data: Any,
        macro_data: Any,
        initial_weights: Optional[Any] = None,
        epochs: Any = 50,
        batch_size: Any = 32,
        validation_split: Any = 0.2,
    ) -> Any:
        """
        Train the portfolio optimization model

        Args:
            price_data: Historical price data
            volatility_data: Historical volatility data
            macro_data: Macroeconomic factors
            initial_weights: Initial portfolio weights (default: equal weights)
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation

        Returns:
            Training history
        """
        logger.info("Preprocessing data and creating sequences...")
        X_price, X_vol, X_macro, y = self.preprocess_data(
            price_data, volatility_data, macro_data
        )
        if initial_weights is None:
            initial_weights = np.ones((len(y), self.n_assets)) / self.n_assets
        logger.info("Splitting data for training and validation...")
        indices = np.arange(len(y))
        train_idx, val_idx = train_test_split(
            indices, test_size=validation_split, shuffle=False
        )
        train_X_price, train_X_vol = (X_price[train_idx], X_vol[train_idx])
        train_X_macro, train_y = (X_macro[train_idx], y[train_idx])
        train_weights = initial_weights[train_idx]
        val_X_price, val_X_vol = (X_price[val_idx], X_vol[val_idx])
        val_X_macro, val_y = (X_macro[val_idx], y[val_idx])
        val_weights = initial_weights[val_idx]
        logger.info("Starting model training...")
        history = self.model.fit(
            [train_X_price, train_X_vol, train_X_macro, train_weights],
            train_y,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=([val_X_price, val_X_vol, val_X_macro, val_weights], val_y),
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss", patience=10, restore_best_weights=True
                )
            ],
            verbose=1,
        )
        return history

    def optimize_portfolio(
        self,
        price_data: Any,
        volatility_data: Any,
        macro_data: Any,
        current_weights: Any,
    ) -> Any:
        """
        Generate optimal portfolio weights (next action) from the current state.

        Args:
            price_data: Recent price data (lookback_window, n_assets)
            volatility_data: Recent volatility data (lookback_window, n_assets)
            macro_data: Recent macroeconomic factors (lookback_window, n_macro_factors)
            current_weights: Current portfolio weights (n_assets,)

        Returns:
            Optimal portfolio weights (n_assets,)
        """

        price_scaled = self.price_scaler.fit_transform(price_data)
        volatility_scaled = self.vol_scaler.fit_transform(volatility_data)
        macro_scaled = self.macro_scaler.fit_transform(macro_data)
        price_scaled = np.array(price_scaled).reshape(
            1, self.lookback_window, self.n_assets
        )
        volatility_scaled = np.array(volatility_scaled).reshape(
            1, self.lookback_window, self.n_assets
        )
        n_macro_factors = macro_data.shape[1]
        macro_scaled = np.array(macro_scaled).reshape(
            1, self.lookback_window, n_macro_factors
        )
        current_weights = np.array(current_weights).reshape(1, self.n_assets)
        optimal_weights = self.model.predict(
            [price_scaled, volatility_scaled, macro_scaled, current_weights], verbose=0
        )
        return optimal_weights[0]

    def backtest(
        self,
        price_data: Any,
        volatility_data: Any,
        macro_data: Any,
        initial_capital: Any = 10000,
        transaction_cost: Any = 0.001,
    ) -> Any:
        """
        Backtest the portfolio optimization strategy in a sequential, walk-forward manner.

        Args:
            price_data: Historical price data
            volatility_data: Historical volatility data
            macro_data: Macroeconomic factors
            initial_capital: Starting capital for the backtest
            transaction_cost: Transaction cost as a fraction of trade value

        Returns:
            DataFrame with backtest results and performance metrics
        """
        logger.info("\nStarting backtest (walk-forward simulation)...")

        _, _, _, returns = self.preprocess_data(price_data, volatility_data, macro_data)
        n_steps = len(returns)
        portfolio_value = [initial_capital]
        portfolio_weights = np.ones(self.n_assets) / self.n_assets
        drawdown_history = [0]
        portfolio_returns: List[Any] = []

        for i in range(n_steps):

            raw_price = price_data[i : i + self.lookback_window]
            raw_vol = volatility_data[i : i + self.lookback_window]
            raw_macro = macro_data[i : i + self.lookback_window]
            optimal_weights = self.optimize_portfolio(
                raw_price, raw_vol, raw_macro, portfolio_weights
            )
            turnover = np.sum(np.abs(optimal_weights - portfolio_weights))
            transaction_costs = turnover * transaction_cost * portfolio_value[-1]
            current_return = np.sum(optimal_weights * returns[i])
            portfolio_returns.append(current_return)
            new_value = portfolio_value[-1] * (1 + current_return) - transaction_costs
            portfolio_value.append(new_value)
            portfolio_weights = optimal_weights
            peak = np.max(portfolio_value)
            drawdown_history.append((new_value - peak) / peak)

        portfolio_returns_series = pd.Series(portfolio_returns)
        sharpe_ratio = (
            portfolio_returns_series.mean()
            / portfolio_returns_series.std()
            * np.sqrt(252)
        )
        max_drawdown = np.min(drawdown_history)
        vol = portfolio_returns_series.std() * np.sqrt(252)

        self.performance_metrics = {
            "total_return": portfolio_value[-1] / initial_capital - 1,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "volatility": vol,
        }

        if hasattr(price_data, "index"):
            result_index = price_data.index[self.lookback_window :]
        else:
            result_index = range(n_steps)

        results = pd.DataFrame(
            {
                "portfolio_value": portfolio_value[1:],
                "returns": portfolio_returns,
                "drawdown": drawdown_history[1:],
            },
            index=result_index,
        )
        logger.info("Backtest Complete. Performance:")
        logger.info(pd.Series(self.performance_metrics))
        return results

    def plot_results(self, results: Any) -> Any:
        """Plot backtest results"""
        plt.figure(figsize=(14, 10))
        plt.subplot(2, 1, 1)
        plt.plot(results["portfolio_value"])
        plt.title("Portfolio Value")
        plt.ylabel("Value ($)")
        plt.grid(True)
        plt.subplot(2, 1, 2)
        plt.fill_between(results.index, 0, results["drawdown"], color="red", alpha=0.3)
        plt.title("Drawdowns")
        plt.ylabel("Drawdown (%)")
        plt.xlabel("Date")
        plt.grid(True)
        plt.tight_layout()
        return plt.gcf()

    def save(self, filepath: Any) -> Any:
        """Save the model to disk"""
        logger.info(f"Saving model to {filepath}")
        self.model.save(filepath)

    def load(self, filepath: Any) -> Any:
        """Load the model from disk"""
        logger.info(f"Loading model from {filepath}")
        self.model = tf.keras.models.load_model(
            filepath, custom_objects={"_portfolio_loss": self._portfolio_loss}
        )
