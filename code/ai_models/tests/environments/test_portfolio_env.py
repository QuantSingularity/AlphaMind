"""Unit tests for PortfolioGymEnv."""

import numpy as np
from ai_models.environments import PortfolioGymEnv


class TestPortfolioGymEnv:
    def test_reset_returns_obs_and_info(self, portfolio_env):
        obs, info = portfolio_env.reset(seed=0)
        assert isinstance(obs, dict)
        assert isinstance(info, dict)

    def test_obs_keys(self, portfolio_env):
        obs, _ = portfolio_env.reset()
        assert set(obs.keys()) == {"prices", "volumes", "macro"}

    def test_step_five_tuple(self, portfolio_env):
        portfolio_env.reset()
        result = portfolio_env.step(portfolio_env.action_space.sample())
        assert len(result) == 5

    def test_reward_is_finite(self, portfolio_env):
        portfolio_env.reset(seed=2)
        for _ in range(5):
            _, r, done, _, _ = portfolio_env.step(portfolio_env.action_space.sample())
            assert np.isfinite(r)
            if done:
                break

    def test_episode_terminates(self, portfolio_env):
        portfolio_env.reset()
        done, steps = False, 0
        while not done and steps < 1000:
            _, _, done, _, _ = portfolio_env.step(portfolio_env.action_space.sample())
            steps += 1
        assert done

    def test_sharpe_reward_cold_start(self, portfolio_env):
        """First step: _sharpe_reward returns 0.0 but reward includes -cost (≤ 0)."""
        portfolio_env.reset()
        _, r, _, _, _ = portfolio_env.step(portfolio_env.action_space.sample())
        assert r <= 0.0, "Step 1 reward should be ≤ 0 (no return, only cost)"

    def test_universe_length_matches_action_dim(self):
        universe = ["A", "B", "C", "D", "E"]
        env = PortfolioGymEnv(universe=universe)
        assert env.action_space.shape == (5,)

    def test_weights_l1_norm_is_one(self, portfolio_env):
        """_normalize divides by |w|.sum(), so the L1 norm must be 1."""
        portfolio_env.reset()
        for _ in range(10):
            portfolio_env.step(portfolio_env.action_space.sample())
        assert abs(np.abs(portfolio_env.current_weights).sum() - 1.0) < 1e-5
