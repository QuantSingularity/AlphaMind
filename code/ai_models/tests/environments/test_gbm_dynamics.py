"""
Tests for the GBM simulation helpers and resulting environment dynamics.

Verifies that:
* The Cholesky factorisation produces the target correlation structure.
* Price paths are strictly positive (GBM invariant).
* Volume paths are strictly positive and mean-reverting.
* Macro paths satisfy the AR(1) stationarity condition.
* Observations from the environment contain no stale/stochastic cross-step leakage.
"""

from __future__ import annotations

import numpy as np
import pytest
from ai_models.environments.trading_env import (
    _cholesky_returns,
    _macro_path,
    _volume_path,
)


class TestCholeskySim:
    """Statistical tests on the GBM return simulation."""

    N_STEPS = 10_000
    N_ASSETS = 6
    TARGET_CORR = 0.40
    MU = np.full(N_ASSETS, 0.08, dtype=np.float64)
    SIGMA = np.full(N_ASSETS, 0.20, dtype=np.float64)

    @pytest.fixture(scope="class")
    def corr(self):
        return self.TARGET_CORR * np.ones((self.N_ASSETS, self.N_ASSETS)) + (
            1 - self.TARGET_CORR
        ) * np.eye(self.N_ASSETS)

    @pytest.fixture(scope="class")
    def sim(self, corr):
        rng = np.random.default_rng(0)
        log_ret, prices = _cholesky_returns(
            rng, self.N_STEPS, self.N_ASSETS, self.MU, self.SIGMA, corr
        )
        return log_ret, prices

    def test_prices_positive(self, sim):
        _, prices = sim
        assert np.all(prices > 0), "GBM price levels must always be positive"

    def test_prices_start_at_100(self, sim):
        _, prices = sim
        np.testing.assert_allclose(prices[0], 100.0)

    def test_return_shape(self, sim):
        log_ret, prices = sim
        assert log_ret.shape == (self.N_STEPS, self.N_ASSETS)
        assert prices.shape == (self.N_STEPS + 1, self.N_ASSETS)

    def test_empirical_correlation(self, sim, corr):
        """Empirical correlation should be within 0.05 of target for 10k steps."""
        log_ret, _ = sim
        emp_corr = np.corrcoef(log_ret.T)
        off_diag_mask = ~np.eye(self.N_ASSETS, dtype=bool)
        mean_emp = emp_corr[off_diag_mask].mean()
        assert abs(mean_emp - self.TARGET_CORR) < 0.05, (
            f"Mean off-diagonal correlation {mean_emp:.3f} deviates from "
            f"target {self.TARGET_CORR} by more than 0.05"
        )

    def test_annualised_vol(self, sim):
        """Daily vol * sqrt(252) should be within 2 pp of target 20%."""
        log_ret, _ = sim
        daily_vol = log_ret.std(axis=0)
        ann_vol = daily_vol * np.sqrt(252)
        np.testing.assert_allclose(ann_vol, 0.20, atol=0.02)

    def test_reproducibility_with_same_seed(self, corr):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        r1, _ = _cholesky_returns(rng1, 100, self.N_ASSETS, self.MU, self.SIGMA, corr)
        r2, _ = _cholesky_returns(rng2, 100, self.N_ASSETS, self.MU, self.SIGMA, corr)
        np.testing.assert_array_equal(r1, r2)

    def test_different_seeds_differ(self, corr):
        rng1 = np.random.default_rng(1)
        rng2 = np.random.default_rng(2)
        r1, _ = _cholesky_returns(rng1, 100, self.N_ASSETS, self.MU, self.SIGMA, corr)
        r2, _ = _cholesky_returns(rng2, 100, self.N_ASSETS, self.MU, self.SIGMA, corr)
        assert not np.array_equal(r1, r2)


class TestVolumePath:
    def test_strictly_positive(self):
        rng = np.random.default_rng(7)
        vols = _volume_path(rng, 500, 5)
        assert np.all(vols > 0)

    def test_shape(self):
        rng = np.random.default_rng(0)
        vols = _volume_path(rng, 200, 4)
        assert vols.shape == (200, 4)

    def test_mean_roughly_correct(self):
        """Long-run mean of log-normal AR(1) should be close to mean_vol."""
        rng = np.random.default_rng(0)
        mean_vol = 1_000_000.0
        vols = _volume_path(rng, 5_000, 1, mean_vol=mean_vol)
        assert abs(vols.mean() / mean_vol - 1.0) < 0.20


class TestMacroPath:
    def test_shape(self):
        rng = np.random.default_rng(0)
        m = _macro_path(rng, 300, 5)
        assert m.shape == (300, 5)

    def test_stationarity_variance(self):
        """AR(1) with |phi| < 1 should have bounded variance."""
        rng = np.random.default_rng(0)
        m = _macro_path(rng, 5_000, 3, phi=0.95)
        # Theoretical variance = noise_var / (1 - phi^2) ≈ 10.3 for phi=0.95
        assert m.var(axis=0).max() < 50, "Macro path variance exploded"

    def test_mean_reversion(self):
        """Long-run mean should be close to 0."""
        rng = np.random.default_rng(0)
        m = _macro_path(rng, 10_000, 1, phi=0.90)
        assert abs(m.mean()) < 0.5


class TestTradingEnvDynamics:
    """End-to-end environment dynamics tests."""

    @pytest.fixture
    def env(self):
        from ai_models.config import TradingEnvConfig
        from ai_models.environments import TradingEnvironment

        cfg = TradingEnvConfig(n_assets=3, window=5, n_macro=2, max_steps=60)
        return TradingEnvironment(config=cfg)

    def test_obs_keys(self, env):
        obs, _ = env.reset(seed=0)
        assert set(obs.keys()) == {"prices", "volumes", "macro"}

    def test_obs_shapes(self, env):
        obs, _ = env.reset(seed=0)
        assert obs["prices"].shape == (env.n_assets, env.window)
        assert obs["volumes"].shape == (env.n_assets,)
        assert obs["macro"].shape == (env.n_macro,)

    def test_volumes_positive_throughout_episode(self, env):
        obs, _ = env.reset(seed=1)
        done = False
        while not done:
            action = env.action_space.sample()
            obs, _, done, _, _ = env.step(action)
            assert np.all(obs["volumes"] > 0), "Volumes must be strictly positive"

    def test_price_window_deterministic_given_seed(self, env):
        """Same seed → identical price windows at step 0."""
        obs1, _ = env.reset(seed=99)
        obs2, _ = env.reset(seed=99)
        np.testing.assert_array_equal(obs1["prices"], obs2["prices"])

    def test_different_seeds_differ(self, env):
        # At step 0 the window is pure padding so obs look identical;
        # take one step to expose the actual GBM prices.
        obs1, _ = env.reset(seed=10)
        env.step(env.action_space.sample())
        obs1_step1, _, _, _, _ = env.step(env.action_space.sample())
        obs2, _ = env.reset(seed=20)
        env.step(env.action_space.sample())
        obs2_step1, _, _, _, _ = env.step(env.action_space.sample())
        assert not np.array_equal(obs1_step1["prices"], obs2_step1["prices"])

    def test_reward_is_finite(self, env):
        env.reset(seed=5)
        for _ in range(10):
            action = env.action_space.sample()
            _, reward, done, _, _ = env.step(action)
            assert np.isfinite(reward)
            if done:
                break

    def test_episode_length(self, env):
        env.reset(seed=0)
        steps = 0
        done = False
        while not done:
            _, _, done, _, _ = env.step(env.action_space.sample())
            steps += 1
        assert steps == env.max_steps - 1


class TestPortfolioEnvDynamics:
    """End-to-end PortfolioGymEnv dynamics tests."""

    @pytest.fixture
    def env(self):
        from ai_models.config import PortfolioEnvConfig
        from ai_models.environments import PortfolioGymEnv

        cfg = PortfolioEnvConfig(window=5, n_macro=2, max_steps=60)
        return PortfolioGymEnv(
            universe=["AAPL", "MSFT", "GOOGL"],
            config=cfg,
        )

    def test_reset_returns_correct_obs(self, env):
        obs, info = env.reset(seed=0)
        assert isinstance(obs, dict)
        assert isinstance(info, dict)

    def test_sharpe_reward_after_warmup(self, env):
        env.reset(seed=0)
        rewards = []
        for _ in range(25):
            action = env.action_space.sample()
            _, r, done, _, _ = env.step(action)
            rewards.append(r)
            if done:
                break
        assert all(np.isfinite(r) for r in rewards)

    def test_weights_l1_norm_is_one(self, env):
        env.reset(seed=0)
        for _ in range(5):
            action = env.action_space.sample()
            env.step(action)
        np.testing.assert_allclose(np.abs(env.current_weights).sum(), 1.0, atol=1e-6)
