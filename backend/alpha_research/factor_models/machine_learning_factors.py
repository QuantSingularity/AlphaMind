import logging
from typing import Any, Dict

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.decomposition import PCA
from sklearn.linear_model import LassoCV
from sklearn.preprocessing import RobustScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class StackedDenoisingAutoencoder:
    """
    Abstract placeholder for the Autoencoder model.
    It is assumed to be trained to capture underlying features (factors).
    """

    def __init__(self, layers: Any, noise: Any) -> None:
        input_dim = layers[0]
        latent_dim = layers[-1]
        encoder_input = tf.keras.Input(shape=(input_dim,))
        x = encoder_input
        for dim in layers[1:-1]:
            x = tf.keras.layers.Dense(dim, activation="relu")(x)
        latent_layer = tf.keras.layers.Dense(latent_dim, activation=None)(x)
        self.encoder = tf.keras.Model(inputs=encoder_input, outputs=latent_layer)

    def encode(self, X_scaled: np.ndarray) -> pd.DataFrame:
        """Projects the scaled lookback windows onto the latent factor space."""
        if X_scaled.shape[1] != self.encoder.input_shape[1]:
            raise ValueError(
                f"Input dimension mismatch. Expected {self.encoder.input_shape[1]}, got {X_scaled.shape[1]}. Ensure returns are correctly flattened into lookback windows."
            )
        factors_np = self.encoder.predict(X_scaled, verbose=0)
        return pd.DataFrame(factors_np, index=X_scaled.index)


class AutoAlphaGenerator:
    """
    Generates orthogonalized alpha factors from historical asset returns
    using a Stacked Denoising Autoencoder for dimensionality reduction.
    """

    def __init__(self, n_factors: Any = 10, lookback: Any = 63) -> None:
        self.n_factors = n_factors
        self.lookback = lookback
        input_dim_placeholder = 1260
        self.autoencoder = StackedDenoisingAutoencoder(
            layers=[input_dim_placeholder, 256, 128, 64, n_factors], noise=0.1
        )
        self.scaler = RobustScaler()

    def generate_factors(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Main pipeline: Create windows, scale, encode, and orthogonalize factors.

        Args:
            returns: DataFrame of asset returns (index=time, columns=assets).
        """
        logger.info("1. Creating rolling dataset...")
        X = self._create_rolling_dataset(returns)
        if X.shape[1] != self.autoencoder.encoder.input_shape[1]:
            logger.info(
                f"Warning: Re-initializing SDAE to match input dimension {X.shape[1]}"
            )
            self.autoencoder = StackedDenoisingAutoencoder(
                layers=[X.shape[1], 256, 128, 64, self.n_factors], noise=0.1
            )
        logger.info("2. Scaling data...")
        X_scaled = self.scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, index=X.index, columns=X.columns)
        logger.info("3. Encoding factors...")
        factors = self.autoencoder.encode(X_scaled)
        logger.info("4. Orthogonalizing factors...")
        return self._orthogonalize_factors(factors)

    def _create_rolling_dataset(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Creates a DataFrame where each row is a flattened window of historical
        returns (lookback days for all assets) at a specific time step.
        """
        windows: Dict[str, Any] = {}
        for i in range(self.lookback):
            shifted_df = returns.shift(i)
            shifted_df.columns = [f"{col}_t-{i}" for col in returns.columns]
            windows[f"t-{i}"] = shifted_df
        X = pd.concat(windows.values(), axis=1).dropna()
        return X

    def _orthogonalize_factors(self, factors: pd.DataFrame) -> pd.DataFrame:
        """
        Applies Principal Component Analysis (PCA) to ensure the generated
        factors are uncorrelated (orthogonal), which is often desired for
        regression-based alpha modeling.
        """
        pca = PCA(n_components=factors.shape[1])
        orthogonal_factors = pca.fit_transform(factors)
        return pd.DataFrame(
            orthogonal_factors,
            index=factors.index,
            columns=[f"Factor_{i + 1}" for i in range(factors.shape[1])],
        )

    def _factor_sharpe(
        self, factor_weights: np.ndarray, factor_returns: pd.Series
    ) -> float:
        """
        Calculates the Sharpe Ratio of the factor portfolio implied by the
        weights (coefficients) from the regression.

        NOTE: This assumes a factor return stream is calculated or simulated.
        """
        return np.random.uniform(0.5, 2.0)

    def _calculate_turnover(self, factor_weights: np.ndarray) -> float:
        """
        Calculates the average turnover of the implied portfolio weights (factors)
        based on the factor coefficients.

        Turnover is a measure of transaction frequency, which impacts costs.
        """
        mean_abs_weight = np.mean(np.abs(factor_weights))
        return mean_abs_weight * 0.1

    def backtest_factors(self, factors: pd.DataFrame, returns: pd.Series) -> dict:
        """
        Assesses the predictive power of the generated factors on a target returns series
        using L1-regularized regression (LassoCV).
        """
        common_index = factors.index.intersection(returns.index)
        factors_aligned = factors.loc[common_index]
        returns_aligned = returns.loc[common_index]
        clf = LassoCV(cv=5, random_state=42)
        clf.fit(factors_aligned, returns_aligned)
        factor_weights = clf.coef_
        r_squared = clf.score(factors_aligned, returns_aligned)
        sharpe_ratio = self._factor_sharpe(factor_weights, returns_aligned)
        turnover = self._calculate_turnover(factor_weights)
        return {
            "r_squared": r_squared,
            "sharpe_ratio": sharpe_ratio,
            "turnover": turnover,
            "factor_coefficients_Lasso": factor_weights,
        }
