"""
PPO PortfolioGymEnv
-------------------
Gymnasium environment for multi-asset portfolio management.
Reward is a rolling Sharpe-ratio approximation minus transaction costs.

Price dynamics use correlated Geometric Brownian Motion (same engine as
``TradingEnvironment``) so that serial correlations, volatility clustering
proxies, and realistic volume/macro co-movements are present during training.
This replaces the previous i.i.d. Gaussian draws, which gave agents no
exploitable structure and produced over-optimistic out-of-sample metrics.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from ai_models.config import PortfolioEnvConfig
from ai_models.environments.base import BaseTradingEnv
from ai_models.environments.trading_env import (
    _cholesky_returns,
    _macro_path,
    _volume_path,
)
from gymnasium import spaces

logger = logging.getLogger(__name__)


class PortfolioGymEnv(BaseTradingEnv, gym.Env):
    """
    Gymnasium portfolio environment compatible with Stable-Baselines3.

    Parameters
    ----------
    universe : List of asset ticker symbols.
    config   : ``PortfolioEnvConfig`` instance.

    Observation
    -----------
    Dict with keys ``prices`` (n_assets x window), ``volumes`` (n_assets,),
    and ``macro`` (n_macro,).

    Action
    ------
    Continuous vector in [-1, 1]^n_assets, normalised to long-only weights.

    Reward
    ------
    Rolling Sharpe approximation over the last 20 steps minus transaction cost.
    """

    metadata: Dict = {"render_modes": ["human"], "render_fps": 30}

    # Annualised GBM parameters
    _DEFAULT_MU: float = 0.08
    _DEFAULT_SIGMA: float = 0.20
    _DEFAULT_CORR: float = 0.30

    def __init__(
        self,
        universe: List[str],
        config: Optional[PortfolioEnvConfig] = None,
    ) -> None:
        super().__init__()
        self.universe = universe
        self.n_assets = len(universe)
        cfg = config or PortfolioEnvConfig()
        self.cfg = cfg

        self.action_space = spaces.Box(-1.0, 1.0, (self.n_assets,), dtype=np.float32)
        self.observation_space = spaces.Dict(
            {
                "prices": spaces.Box(
                    -np.inf, np.inf, (self.n_assets, cfg.window), dtype=np.float32
                ),
                "volumes": spaces.Box(0.0, np.inf, (self.n_assets,), dtype=np.float32),
                "macro": spaces.Box(-np.inf, np.inf, (cfg.n_macro,), dtype=np.float32),
            }
        )

        self._mu = np.full(self.n_assets, self._DEFAULT_MU, dtype=np.float32)
        self._sigma = np.full(self.n_assets, self._DEFAULT_SIGMA, dtype=np.float32)
        self._corr = self._DEFAULT_CORR * np.ones(
            (self.n_assets, self.n_assets), dtype=np.float32
        ) + (1 - self._DEFAULT_CORR) * np.eye(self.n_assets, dtype=np.float32)

        # Paths allocated in reset()
        self.log_returns: np.ndarray = np.zeros(
            (cfg.max_steps, self.n_assets), dtype=np.float32
        )
        self.prices: np.ndarray = np.zeros(
            (cfg.max_steps + 1, self.n_assets), dtype=np.float32
        )
        self.volumes: np.ndarray = np.zeros(
            (cfg.max_steps, self.n_assets), dtype=np.float32
        )
        self.macro: np.ndarray = np.zeros(
            (cfg.max_steps, cfg.n_macro), dtype=np.float32
        )
        self.current_step = 0
        self.max_steps = cfg.max_steps
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict]:
        super().reset(seed=seed)
        rng = np.random.default_rng(seed)
        self.current_step = 0
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets

        self.log_returns, self.prices = _cholesky_returns(
            rng,
            self.max_steps,
            self.n_assets,
            self._mu,
            self._sigma,
            self._corr,
        )
        self.volumes = _volume_path(rng, self.max_steps, self.n_assets)
        self.macro = _macro_path(rng, self.max_steps, self.cfg.n_macro)
        return self._get_obs(), {}

    def step(
        self, action: np.ndarray
    ) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict]:
        action = np.asarray(action, dtype=np.float32).flatten()
        new_weights = self._normalize(action)
        cost = self._tc(new_weights)
        reward = float(self._sharpe_reward(new_weights) - cost)
        self.current_step += 1
        done = self.current_step >= self.max_steps - 1
        return self._get_obs(), reward, done, False, {}

    def _sharpe_reward(self, weights: np.ndarray) -> float:
        if self.current_step < 2:
            return 0.0
        start = max(0, self.current_step - 20)
        window = self.log_returns[start : self.current_step]
        port_r = np.dot(window, weights)
        rf = 0.02 / 252
        std = float(np.std(port_r))
        if std < 1e-9 or np.isnan(std):
            return -1.0
        return float((np.mean(port_r) - rf) / std)

    def _normalize(self, action: np.ndarray) -> np.ndarray:
        w = np.tanh(action)
        denom = np.abs(w).sum()
        if denom < 1e-8:
            return np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        return (w / denom).astype(np.float32)

    def _tc(self, new_weights: np.ndarray) -> float:
        to = float(np.abs(new_weights - self.current_weights).sum())
        self.current_weights = new_weights.copy()
        return to * self.cfg.transaction_cost

    def _get_obs(self) -> Dict[str, np.ndarray]:
        t = self.current_step
        start = max(0, t - self.cfg.window + 1)
        window_prices = self.prices[start : t + 1]
        if len(window_prices) < self.cfg.window:
            pad = np.zeros(
                (self.cfg.window - len(window_prices), self.n_assets), dtype=np.float32
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
