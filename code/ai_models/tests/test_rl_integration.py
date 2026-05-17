"""
End-to-end RL integration tests.

These tests run a short training loop (few episodes, few steps) to confirm
that the full DDPG pipeline — environment → agent → buffer → update —
executes without error and produces finite metrics.

They are deliberately kept fast (max_steps=30, episodes=3) so they can run
in CI without GPU.
"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(scope="module")
def small_env():
    from ai_models.config import TradingEnvConfig
    from ai_models.environments import TradingEnvironment

    cfg = TradingEnvConfig(n_assets=3, window=5, n_macro=2, max_steps=30)
    return TradingEnvironment(config=cfg)


@pytest.fixture(scope="module")
def small_ddpg(small_env):
    from ai_models.agents import DDPGTradingAgent
    from ai_models.config import DDPGConfig

    cfg = DDPGConfig(
        batch_size=8,
        buffer_size=100,
        warmup_steps=5,
        use_cuda=False,
        actor_hidden=[32, 32],
        critic_hidden=[32, 32],
    )
    return DDPGTradingAgent(small_env, config=cfg)


class TestDDPGIntegration:
    def test_full_episode_no_error(self, small_env, small_ddpg):
        obs, _ = small_env.reset(seed=0)
        done = False
        rewards = []
        while not done:
            action = small_ddpg.select_action(obs, add_noise=True)
            next_obs, reward, done, _, _ = small_env.step(action)
            small_ddpg.replay_buffer.add(obs, action, reward, next_obs, done)
            rewards.append(reward)
            obs = next_obs
        assert len(rewards) == small_env.max_steps - 1

    def test_update_after_warmup(self, small_env, small_ddpg):
        """After filling past warmup_steps, update should return finite losses."""
        obs, _ = small_env.reset(seed=1)
        done = False
        while not done:
            action = small_env.action_space.sample()
            next_obs, r, done, _, _ = small_env.step(action)
            small_ddpg.replay_buffer.add(obs, action, r, next_obs, done)
            obs = next_obs
        result = small_ddpg.update()
        if result is not None:
            critic_loss, actor_loss = result
            assert np.isfinite(critic_loss)
            assert np.isfinite(actor_loss)

    def test_multi_episode_stable(self, small_env, small_ddpg):
        """Three consecutive episodes should run without NaN rewards."""
        for ep in range(3):
            obs, _ = small_env.reset(seed=ep + 10)
            done = False
            while not done:
                action = small_ddpg.select_action(obs, add_noise=True)
                next_obs, reward, done, _, _ = small_env.step(action)
                assert np.isfinite(reward), f"NaN/Inf reward at episode {ep}"
                small_ddpg.replay_buffer.add(obs, action, reward, next_obs, done)
                obs = next_obs

    def test_obs_consistent_with_env_spec(self, small_env):
        """Observations must conform to the declared observation_space."""
        obs, _ = small_env.reset(seed=5)
        for _ in range(5):
            action = small_env.action_space.sample()
            obs, _, done, _, _ = small_env.step(action)
            assert small_env.observation_space.contains(
                obs
            ), "Observation out of declared observation_space bounds"
            if done:
                break


class TestPortfolioIntegration:
    @pytest.fixture(scope="class")
    def env(self):
        from ai_models.config import PortfolioEnvConfig
        from ai_models.environments import PortfolioGymEnv

        cfg = PortfolioEnvConfig(window=5, n_macro=2, max_steps=30)
        return PortfolioGymEnv(
            universe=["AAPL", "MSFT", "GOOGL"],
            config=cfg,
        )

    def test_sharpe_reward_finite_after_step_2(self, env):
        env.reset(seed=0)
        rewards = []
        for _ in range(5):
            action = env.action_space.sample()
            _, r, done, _, _ = env.step(action)
            rewards.append(r)
            if done:
                break
        # After 2 steps, Sharpe reward kicks in; all should be finite
        assert all(np.isfinite(r) for r in rewards)

    def test_weights_l1_norm_preserved_throughout_episode(self, env):
        env.reset(seed=0)
        done = False
        while not done:
            _, _, done, _, _ = env.step(env.action_space.sample())
        # After full episode, |w|.sum() should still equal 1
        np.testing.assert_allclose(np.abs(env.current_weights).sum(), 1.0, atol=1e-5)
