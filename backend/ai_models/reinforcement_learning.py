import logging
from typing import Any, Dict, Optional

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
    A custom environment for portfolio management using OpenAI Gym.
    The agent learns to allocate capital (weights) to maximize a risk-adjusted return (Sharpe Ratio).
    """

    metadata = {"render_modes": ["human"], "render_fps": 30}

    def __init__(self, universe: Any, transaction_cost: Any = 0.001) -> None:
        super().__init__()
        self.universe = universe
        self.n_assets = len(universe)
        self.transaction_cost = transaction_cost
        self.action_space = spaces.Box(-1, 1, (self.n_assets,), dtype=np.float32)
        self.observation_space = spaces.Dict(
            {
                "prices": spaces.Box(
                    -np.inf, np.inf, (self.n_assets, 10), dtype=np.float32
                ),
                "volumes": spaces.Box(0, np.inf, (self.n_assets,), dtype=np.float32),
                "macro": spaces.Box(-np.inf, np.inf, (5,), dtype=np.float32),
            }
        )
        self.current_step = 0
        self.returns = np.zeros((100, self.n_assets), dtype=np.float32)
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets

    def step(self, action: Any) -> Any:
        """Execute one time step within the environment."""
        action = np.asarray(action, dtype=np.float32).reshape(self.n_assets)
        new_weights = self._normalize_weights(action)
        cost = self._transaction_cost(new_weights)
        reward = self._sharpe_ratio(new_weights) - cost
        self.current_step += 1
        done = self.current_step >= len(self.returns) - 1
        observation = self._get_obs()
        return (observation, reward, done, False, {})

    def _sharpe_ratio(self, weights: Any) -> Any:
        """
        Calculate the portfolio's Sharpe Ratio.
        NOTE: This is a placeholder using static returns data. In a real environment,
        this would use the returns realized *after* taking the action.
        """
        if self.current_step == 0:
            return 0.0
        start = max(0, self.current_step - 10)
        window = self.returns[start : self.current_step]
        returns = np.dot(window, weights)
        risk_free_rate = 0.02 / 252
        std = np.std(returns)
        if std == 0 or np.isnan(std):
            return -1.0
        return (np.mean(returns) - risk_free_rate) / std

    def _normalize_weights(self, action: Any) -> Any:
        """Normalize actions to valid portfolio weights (e.g., sum to 1)."""
        weights = np.tanh(action)
        sum_abs_weights = np.sum(np.abs(weights))
        if sum_abs_weights == 0:
            return (np.ones(self.n_assets, dtype=np.float32) / self.n_assets).astype(
                np.float32
            )
        weights = weights / sum_abs_weights
        return weights.astype(np.float32)

    def _transaction_cost(self, new_weights: Any) -> Any:
        """Calculate transaction costs from rebalancing (based on turnover)."""
        turnover = np.sum(np.abs(new_weights - self.current_weights))
        cost = turnover * self.transaction_cost
        self.current_weights = new_weights
        return cost

    def _get_obs(self) -> Any:
        """Get current market observation (placeholder)."""
        return {
            "prices": np.random.normal(0, 1, (self.n_assets, 10)).astype(np.float32),
            "volumes": np.abs(np.random.normal(1000, 500, (self.n_assets,))).astype(
                np.float32
            ),
            "macro": np.random.normal(0, 1, (5,)).astype(np.float32),
        }

    def reset(self, seed: Optional[Any] = None, options: Optional[Any] = None) -> Any:
        """Reset environment to initial state."""
        super().reset(seed=seed)
        self.current_step = 0
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        self.returns = np.random.normal(0.0005, 0.01, (100, self.n_assets)).astype(
            np.float32
        )
        observation = self._get_obs()
        info: Dict[str, Any] = {}
        return (observation, info)


class PPOAgent:
    """
    A Proximal Policy Optimization (PPO) agent for training in the PortfolioGymEnv.
    """

    def __init__(self, env: Any) -> None:
        self.model = PPO(
            "MultiInputPolicy",
            env,
            learning_rate=0.0003,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            verbose=1,
        )

    def train(self, timesteps: Any = 1000000.0) -> Any:
        """Start the training process for a specified number of time steps."""
        logger.info(
            f"Starting PPO training for {timesteps / 1000000.0} million steps..."
        )
        self.model.learn(total_timesteps=int(timesteps))
        logger.info("Training complete.")


if __name__ == "__main__":
    asset_universe = ["StockA", "StockB", "StockC", "StockD", "Cash"]
    env = PortfolioGymEnv(universe=asset_universe)
    logger.info(f"Action Space Shape: {env.action_space.shape}")
    logger.info(f"Observation Space Keys: {env.observation_space.spaces.keys()}")
    agent = PPOAgent(env)
    agent.train(timesteps=10000)
    obs, info = env.reset()
    done = False
    episode_reward = 0
    logger.info("\n--- Running Test Episode ---")
    while not done:
        action, _ = agent.model.predict(obs, deterministic=True)
        obs, reward, done, _, info = env.step(action)
        episode_reward += reward
    logger.info(f"Episode finished after {env.current_step} steps.")
    logger.info(f"Total Episode Reward: {episode_reward:.4f}")
