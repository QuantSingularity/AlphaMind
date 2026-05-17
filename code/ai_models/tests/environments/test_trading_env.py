"""Unit tests for TradingEnvironment."""

import numpy as np
from ai_models.environments import TradingEnvironment


class TestTradingEnvironment:
    def test_reset_obs_keys(self, trading_env):
        obs, info = trading_env.reset(seed=0)
        assert set(obs.keys()) == {"prices", "volumes", "macro"}
        assert isinstance(info, dict)

    def test_reset_obs_shapes(self, trading_env, n_assets, window, n_macro):
        obs, _ = trading_env.reset(seed=0)
        assert obs["prices"].shape == (n_assets, window)
        assert obs["volumes"].shape == (n_assets,)
        assert obs["macro"].shape == (n_macro,)

    def test_step_returns_five_tuple(self, trading_env):
        trading_env.reset()
        result = trading_env.step(trading_env.action_space.sample())
        assert len(result) == 5

    def test_reward_is_finite(self, trading_env):
        trading_env.reset(seed=1)
        for _ in range(10):
            _, reward, done, _, _ = trading_env.step(trading_env.action_space.sample())
            assert np.isfinite(reward)
            if done:
                break

    def test_episode_terminates(self, trading_env):
        trading_env.reset()
        done, steps = False, 0
        while not done and steps < 1000:
            _, _, done, _, _ = trading_env.step(trading_env.action_space.sample())
            steps += 1
        assert done

    def test_weights_l1_norm_is_one(self, trading_env):
        """_normalize divides by |w|.sum(), so the L1 norm must be 1."""
        trading_env.reset()
        for _ in range(5):
            trading_env.step(trading_env.action_space.sample())
        w = trading_env.current_weights
        assert abs(np.abs(w).sum() - 1.0) < 1e-5

    def test_zero_action_gives_uniform_weights(self, trading_env):
        """tanh(0) = 0; fallback should give uniform weights."""
        from ai_models.config import TradingEnvConfig

        env = TradingEnvironment(config=TradingEnvConfig(n_assets=4))
        env.reset()
        env.step(np.zeros(4))
        np.testing.assert_array_almost_equal(
            env.current_weights, np.ones(4) / 4, decimal=5
        )

    def test_transaction_cost_reduces_reward(self, trading_env):
        from ai_models.config import TradingEnvConfig

        env_no_cost = TradingEnvironment(
            config=TradingEnvConfig(n_assets=3, transaction_cost=0.0)
        )
        env_with_cost = TradingEnvironment(
            config=TradingEnvConfig(n_assets=3, transaction_cost=0.01)
        )
        rng = np.random.default_rng(42)
        action = rng.standard_normal(3)
        env_no_cost.reset(seed=99)
        env_no_cost.log_returns = np.ones((50, 3)) * 0.01
        env_with_cost.reset(seed=99)
        env_with_cost.log_returns = np.ones((50, 3)) * 0.01
        _, r_no, _, _, _ = env_no_cost.step(action)
        _, r_with, _, _, _ = env_with_cost.step(action)
        assert r_no >= r_with

    def test_seed_gives_reproducible_reset(self):
        from ai_models.config import TradingEnvConfig

        cfg = TradingEnvConfig(n_assets=3)
        env = TradingEnvironment(config=cfg)
        obs1, _ = env.reset(seed=42)
        obs2, _ = env.reset(seed=42)
        np.testing.assert_array_equal(obs1["prices"], obs2["prices"])

    def test_action_space_dtype(self, trading_env):
        assert trading_env.action_space.dtype == np.float32

    def test_weights_l1_norm_preserved_across_steps(self, trading_env):
        """After every step, |w|.sum() must equal 1.0 (L1-normalised allocation)."""
        trading_env.reset()
        for _ in range(20):
            trading_env.step(trading_env.action_space.sample())
            assert abs(np.abs(trading_env.current_weights).sum() - 1.0) < 1e-5
