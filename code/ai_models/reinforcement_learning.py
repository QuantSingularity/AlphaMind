import logging
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PortfolioGymEnv(gym.Env):
    """
    Custom Gymnasium environment for portfolio management.
    The agent learns to allocate capital (weights) to maximise a
    risk-adjusted return (Sharpe Ratio) while accounting for
    transaction costs and rebalancing friction.
    """

    metadata: Dict = {"render_modes": ["human"], "render_fps": 30}

    def __init__(
        self,
        universe: List[str],
        transaction_cost: float = 0.001,
        window: int = 10,
        n_macro: int = 5,
    ) -> None:
        super().__init__()
        self.universe = universe
        self.n_assets: int = len(universe)
        self.transaction_cost = transaction_cost
        self.window = window
        self.n_macro = n_macro

        self.action_space = spaces.Box(-1.0, 1.0, (self.n_assets,), dtype=np.float32)
        self.observation_space = spaces.Dict(
            {
                "prices": spaces.Box(
                    -np.inf, np.inf, (self.n_assets, window), dtype=np.float32
                ),
                "volumes": spaces.Box(0.0, np.inf, (self.n_assets,), dtype=np.float32),
                "macro": spaces.Box(-np.inf, np.inf, (n_macro,), dtype=np.float32),
            }
        )
        self.current_step: int = 0
        self.max_steps: int = 252
        self.returns: np.ndarray = np.zeros(
            (self.max_steps, self.n_assets), dtype=np.float32
        )
        self.current_weights: np.ndarray = (
            np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        )

    def step(
        self, action: np.ndarray
    ) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict]:
        """Execute one time step within the environment."""
        action = np.asarray(action, dtype=np.float32).reshape(self.n_assets)
        new_weights = self._normalize_weights(action)
        cost = self._transaction_cost(new_weights)
        reward = self._sharpe_reward(new_weights) - cost
        self.current_step += 1
        done = self.current_step >= self.max_steps - 1
        return self._get_obs(), float(reward), done, False, {}

    def _sharpe_reward(self, weights: np.ndarray) -> float:
        """
        One-step Sharpe-ratio-based reward using a rolling window of returns.
        Falls back to raw portfolio return outside the warm-up window.
        """
        if self.current_step < 2:
            return 0.0
        start = max(0, self.current_step - 20)
        window_returns = self.returns[start : self.current_step]
        port_returns = np.dot(window_returns, weights)
        risk_free_rate = 0.02 / 252
        std = float(np.std(port_returns))
        if std < 1e-9 or np.isnan(std):
            return -1.0
        return float((np.mean(port_returns) - risk_free_rate) / std)

    def _normalize_weights(self, action: np.ndarray) -> np.ndarray:
        """Normalise raw actions → valid long-only portfolio weights."""
        weights = np.tanh(action)
        denom = np.sum(np.abs(weights))
        if denom < 1e-8:
            return np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        return (weights / denom).astype(np.float32)

    def _transaction_cost(self, new_weights: np.ndarray) -> float:
        """Proportional transaction cost based on L1 turnover."""
        turnover = float(np.sum(np.abs(new_weights - self.current_weights)))
        self.current_weights = new_weights.copy()
        return turnover * self.transaction_cost

    def _get_obs(self) -> Dict[str, np.ndarray]:
        """Return the current market observation dictionary."""
        start = max(0, self.current_step - self.window)
        price_slice = self.returns[start : self.current_step + 1]
        if len(price_slice) < self.window:
            pad = np.zeros(
                (self.window - len(price_slice), self.n_assets), dtype=np.float32
            )
            price_slice = np.vstack([pad, price_slice])
        return {
            "prices": price_slice[-self.window :].T.astype(np.float32),
            "volumes": np.abs(np.random.normal(1000.0, 500.0, (self.n_assets,))).astype(
                np.float32
            ),
            "macro": np.random.normal(0.0, 1.0, (self.n_macro,)).astype(np.float32),
        }

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict]:
        """Reset the environment to the initial state."""
        super().reset(seed=seed)
        self.current_step = 0
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        self.returns = np.random.normal(
            0.0005, 0.01, (self.max_steps, self.n_assets)
        ).astype(np.float32)
        return self._get_obs(), {}


class PPOAgent:
    """
    Proximal Policy Optimization (PPO) agent wrapping Stable-Baselines3.
    Designed for multi-asset portfolio management in PortfolioGymEnv.
    """

    def __init__(
        self,
        env: gym.Env,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> None:
        self.model = PPO(
            "MultiInputPolicy",
            env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=gamma,
            gae_lambda=gae_lambda,
            verbose=1,
        )

    def train(self, timesteps: int = 1_000_000) -> None:
        """Train the PPO agent for a given number of environment timesteps."""
        logger.info(f"Starting PPO training for {timesteps:,} timesteps...")
        self.model.learn(total_timesteps=timesteps)
        logger.info("PPO training complete.")

    def predict(
        self, obs: Dict[str, np.ndarray], deterministic: bool = True
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Return a (action, state) tuple for the given observation."""
        return self.model.predict(obs, deterministic=deterministic)

    def save(self, path: str) -> None:
        """Persist model weights to disk."""
        self.model.save(path)
        logger.info(f"PPO model saved to {path}")

    @classmethod
    def load(cls, path: str, env: gym.Env) -> "PPOAgent":
        """Load a previously saved PPO model."""
        agent = cls.__new__(cls)
        agent.model = PPO.load(path, env=env)
        return agent


if __name__ == "__main__":
    asset_universe: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    env = PortfolioGymEnv(universe=asset_universe)
    logger.info(f"Action Space: {env.action_space}")
    logger.info(f"Observation Space keys: {list(env.observation_space.spaces.keys())}")
    agent = PPOAgent(env)
    agent.train(timesteps=10_000)
    obs, _ = env.reset()
    done = False
    episode_reward = 0.0
    logger.info("\n--- Running Evaluation Episode ---")
    while not done:
        action, _ = agent.predict(obs, deterministic=True)
        obs, reward, done, _, _ = env.step(action)
        episode_reward += float(reward)
    logger.info(f"Episode finished after {env.current_step} steps.")
    logger.info(f"Total Episode Reward: {episode_reward:.4f}")
