"""
DDPG TradingEnvironment
-----------------------
A discrete-step gym.Env where the agent submits a continuous weight vector
and receives a portfolio return minus transaction costs as reward.

Price dynamics are simulated via correlated Geometric Brownian Motion so that
the environment presents statistically realistic market microstructure:

* Asset log-returns are correlated via a Cholesky-decomposed covariance matrix.
* Price levels follow GBM: S_{t+1} = S_t * exp((mu - 0.5*sigma^2)*dt + sigma*dW_t)
* Volume follows a log-normal AR(1) process (mean-reverting, always positive).
* Macro factors follow a vector AR(1) process.

These dynamics replace the previous i.i.d. Gaussian draws in ``reset()``,
eliminating spurious serial independence and making the learned policies
transferable to real data feeds.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
from ai_models.config import TradingEnvConfig
from ai_models.environments.base import BaseTradingEnv
from gymnasium import spaces


def _cholesky_returns(
    rng: np.random.Generator,
    n_steps: int,
    n_assets: int,
    mu: np.ndarray,
    sigma: np.ndarray,
    corr: np.ndarray,
    dt: float = 1 / 252,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulate correlated GBM log-returns and price levels.

    Parameters
    ----------
    rng     : NumPy random Generator (seeded for reproducibility).
    n_steps : Number of time steps to simulate.
    n_assets: Number of assets.
    mu      : Annual drift per asset, shape ``(n_assets,)``.
    sigma   : Annual volatility per asset, shape ``(n_assets,)``.
    corr    : Correlation matrix, shape ``(n_assets, n_assets)``.
    dt      : Time step in years (default: 1 trading day = 1/252).

    Returns
    -------
    log_returns : ``(n_steps, n_assets)`` array of per-step log-returns.
    prices      : ``(n_steps + 1, n_assets)`` array of price levels (S_0 = 100).
    """
    cov = np.outer(sigma, sigma) * corr
    L = np.linalg.cholesky(cov * dt)
    Z = rng.standard_normal((n_steps, n_assets))
    dW = Z @ L.T
    drift = (mu - 0.5 * sigma**2) * dt
    log_returns = drift + dW
    prices = np.zeros((n_steps + 1, n_assets), dtype=np.float32)
    prices[0] = 100.0
    for t in range(n_steps):
        prices[t + 1] = prices[t] * np.exp(log_returns[t])
    return log_returns.astype(np.float32), prices


def _volume_path(
    rng: np.random.Generator,
    n_steps: int,
    n_assets: int,
    mean_vol: float = 1_000_000.0,
    phi: float = 0.85,
    noise_scale: float = 0.15,
) -> np.ndarray:
    """
    Simulate log-normal AR(1) volume path.

    Parameters
    ----------
    phi         : AR(1) coefficient (mean-reversion speed).
    noise_scale : Std-dev of log-volume innovations.

    Returns
    -------
    ``(n_steps, n_assets)`` array of positive volume values.
    """
    log_mean = np.log(mean_vol)
    log_vols = np.zeros((n_steps, n_assets), dtype=np.float32)
    log_vols[0] = log_mean
    for t in range(1, n_steps):
        log_vols[t] = (
            phi * log_vols[t - 1]
            + (1 - phi) * log_mean
            + rng.normal(0, noise_scale, n_assets)
        )
    return np.exp(log_vols)


def _macro_path(
    rng: np.random.Generator,
    n_steps: int,
    n_macro: int,
    phi: float = 0.95,
) -> np.ndarray:
    """
    Simulate a vector AR(1) macro factor path.

    Parameters
    ----------
    phi : Diagonal AR(1) coefficient (same for all factors).

    Returns
    -------
    ``(n_steps, n_macro)`` array of macro observations.
    """
    macro = np.zeros((n_steps, n_macro), dtype=np.float32)
    macro[0] = rng.standard_normal(n_macro)
    noise_scale = np.sqrt(1 - phi**2)
    for t in range(1, n_steps):
        macro[t] = phi * macro[t - 1] + noise_scale * rng.standard_normal(n_macro)
    return macro


class TradingEnvironment(BaseTradingEnv, gym.Env):
    """
    Single-step portfolio trading environment compatible with OpenAI Gym.

    Observation
    -----------
    Dict with keys ``prices`` (n_assets x window), ``volumes`` (n_assets,),
    and ``macro`` (n_macro,).

    Action
    ------
    Continuous vector in [-1, 1]^n_assets, normalised to portfolio weights.

    Reward
    ------
    ``portfolio_return - transaction_cost``
    """

    metadata: Dict = {"render_modes": ["human"]}

    # Annualised GBM parameters (realistic equity-like defaults)
    _DEFAULT_MU: float = 0.08
    _DEFAULT_SIGMA: float = 0.20
    _DEFAULT_CORR: float = 0.30  # pairwise correlation between assets

    def __init__(self, config: Optional[TradingEnvConfig] = None, **kwargs) -> None:
        super().__init__()
        cfg = config or TradingEnvConfig(
            **{
                k: v
                for k, v in kwargs.items()
                if k in TradingEnvConfig.__dataclass_fields__
            }
        )
        self.cfg = cfg
        self.n_assets = cfg.n_assets
        self.window = cfg.window
        self.n_macro = cfg.n_macro
        self.transaction_cost = cfg.transaction_cost
        self.max_steps = cfg.max_steps
        self.current_step = 0

        # Drift / vol / correlation (fixed per instance, randomised per reset)
        self._mu = np.full(cfg.n_assets, self._DEFAULT_MU, dtype=np.float32)
        self._sigma = np.full(cfg.n_assets, self._DEFAULT_SIGMA, dtype=np.float32)
        self._corr = self._DEFAULT_CORR * np.ones(
            (cfg.n_assets, cfg.n_assets), dtype=np.float32
        ) + (1 - self._DEFAULT_CORR) * np.eye(cfg.n_assets, dtype=np.float32)

        # Paths allocated in reset()
        self.log_returns: np.ndarray = np.zeros(
            (cfg.max_steps, cfg.n_assets), dtype=np.float32
        )
        self.prices: np.ndarray = np.zeros(
            (cfg.max_steps + 1, cfg.n_assets), dtype=np.float32
        )
        self.volumes: np.ndarray = np.zeros(
            (cfg.max_steps, cfg.n_assets), dtype=np.float32
        )
        self.macro: np.ndarray = np.zeros(
            (cfg.max_steps, cfg.n_macro), dtype=np.float32
        )
        self.current_weights = np.ones(cfg.n_assets, dtype=np.float32) / cfg.n_assets

        self.action_space = spaces.Box(-1.0, 1.0, (cfg.n_assets,), dtype=np.float32)
        self.observation_space = spaces.Dict(
            {
                "prices": spaces.Box(
                    -np.inf, np.inf, (cfg.n_assets, cfg.window), dtype=np.float32
                ),
                "volumes": spaces.Box(0.0, np.inf, (cfg.n_assets,), dtype=np.float32),
                "macro": spaces.Box(-np.inf, np.inf, (cfg.n_macro,), dtype=np.float32),
            }
        )

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict]:
        super().reset(seed=seed)
        rng = np.random.default_rng(seed)
        self.current_step = 0
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets

        # Simulate full correlated GBM episode upfront
        self.log_returns, self.prices = _cholesky_returns(
            rng,
            self.max_steps,
            self.n_assets,
            self._mu,
            self._sigma,
            self._corr,
        )
        self.volumes = _volume_path(rng, self.max_steps, self.n_assets)
        self.macro = _macro_path(rng, self.max_steps, self.n_macro)
        return self._get_obs(), {}

    def step(
        self, action: np.ndarray
    ) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict]:
        action = np.asarray(action, dtype=np.float32).flatten()
        new_weights = self._normalize(action)
        cost = self._tc(new_weights)
        reward = float(self._port_return(new_weights) - cost)
        self.current_step += 1
        done = self.current_step >= self.max_steps - 1
        return self._get_obs(), reward, done, False, {}

    def _port_return(self, weights: np.ndarray) -> float:
        if self.current_step >= len(self.log_returns):
            return 0.0
        return float(np.dot(self.log_returns[self.current_step], weights))

    def _normalize(self, action: np.ndarray) -> np.ndarray:
        w = np.tanh(action)
        denom = np.abs(w).sum()
        if denom < 1e-8:
            return np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        return (w / denom).astype(np.float32)

    def _tc(self, new_weights: np.ndarray) -> float:
        turnover = float(np.abs(new_weights - self.current_weights).sum())
        self.current_weights = new_weights.copy()
        return turnover * self.transaction_cost

    def _get_obs(self) -> Dict[str, np.ndarray]:
        t = self.current_step
        # Return price-level window (normalised to starting price for stationarity)
        start = max(0, t - self.window + 1)
        window_prices = self.prices[start : t + 1]  # shape (<=window, n_assets)
        if len(window_prices) < self.window:
            pad = np.zeros(
                (self.window - len(window_prices), self.n_assets), dtype=np.float32
            )
            window_prices = np.vstack([pad, window_prices])
        normalised = window_prices / (window_prices[-1:] + 1e-8)
        vol_idx = min(t, len(self.volumes) - 1)
        macro_idx = min(t, len(self.macro) - 1)
        return {
            "prices": normalised.T.astype(np.float32),
            "volumes": self.volumes[vol_idx].astype(np.float32),
            "macro": self.macro[macro_idx].astype(np.float32),
        }
