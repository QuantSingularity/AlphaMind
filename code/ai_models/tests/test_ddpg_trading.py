"""Unit tests for DDPGTradingAgent and TradingEnvironment."""

import os
import sys

import numpy as np
import pytest
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from code.ai_models.ddpg_trading import (
    Actor,
    Critic,
    DDPGTradingAgent,
    OUNoise,
    ReplayBuffer,
    TradingEnvironment,
)


# -----------------------------------------------------------------------
# ReplayBuffer
# -----------------------------------------------------------------------
class TestReplayBuffer:
    def test_add_and_len(self) -> None:
        buf = ReplayBuffer(capacity=10)
        state = np.zeros(5)
        buf.add(state, np.zeros(2), 0.0, state, False)
        assert len(buf) == 1

    def test_capacity_respected(self) -> None:
        buf = ReplayBuffer(capacity=5)
        for _ in range(10):
            buf.add(np.zeros(3), np.zeros(2), 0.0, np.zeros(3), False)
        assert len(buf) == 5

    def test_sample_returns_tensors(self) -> None:
        buf = ReplayBuffer(capacity=100)
        for _ in range(20):
            buf.add(
                np.random.randn(5),
                np.random.randn(2),
                float(np.random.randn()),
                np.random.randn(5),
                False,
            )
        states, actions, rewards, next_states, dones = buf.sample(8)
        assert states.shape == (8, 5)
        assert actions.shape == (8, 2)
        assert rewards.shape == (8, 1)
        assert dones.shape == (8, 1)

    def test_sample_smaller_than_batch(self) -> None:
        buf = ReplayBuffer(capacity=100)
        for _ in range(4):
            buf.add(np.zeros(3), np.zeros(2), 0.0, np.zeros(3), False)
        states, _, _, _, _ = buf.sample(16)
        assert states.shape[0] == 4  # only 4 available


# -----------------------------------------------------------------------
# OUNoise
# -----------------------------------------------------------------------
class TestOUNoise:
    def test_output_shape(self) -> None:
        noise = OUNoise(size=5)
        sample = noise.sample()
        assert sample.shape == (5,)

    def test_reset_returns_to_mean(self) -> None:
        noise = OUNoise(size=4, mu=0.0)
        for _ in range(100):
            noise.sample()
        noise.reset()
        assert np.allclose(noise.state, noise.mu)

    def test_samples_differ(self) -> None:
        noise = OUNoise(size=3)
        s1 = noise.sample().copy()
        s2 = noise.sample().copy()
        assert not np.array_equal(s1, s2)


# -----------------------------------------------------------------------
# Actor / Critic
# -----------------------------------------------------------------------
class TestNetworks:
    def test_actor_output_shape(self) -> None:
        actor = Actor(state_dim=16, action_dim=4)
        x = torch.randn(8, 16)
        out = actor(x)
        assert out.shape == (8, 4)

    def test_actor_output_bounded(self) -> None:
        actor = Actor(state_dim=16, action_dim=4)
        x = torch.randn(32, 16)
        out = actor(x)
        assert (out >= -1.0).all() and (out <= 1.0).all()

    def test_critic_output_shape(self) -> None:
        critic = Critic(state_dim=16, action_dim=4)
        s = torch.randn(8, 16)
        a = torch.randn(8, 4)
        out = critic(s, a)
        assert out.shape == (8, 1)


# -----------------------------------------------------------------------
# TradingEnvironment
# -----------------------------------------------------------------------
class TestTradingEnvironment:
    @pytest.fixture
    def env(self) -> TradingEnvironment:
        return TradingEnvironment(n_assets=3, window=5, n_macro=4)

    def test_reset_returns_obs_and_info(self, env: TradingEnvironment) -> None:
        obs, info = env.reset(seed=0)
        assert isinstance(obs, dict)
        assert isinstance(info, dict)

    def test_obs_keys(self, env: TradingEnvironment) -> None:
        obs, _ = env.reset()
        assert set(obs.keys()) == {"prices", "volumes", "macro"}

    def test_obs_shapes(self, env: TradingEnvironment) -> None:
        obs, _ = env.reset()
        assert obs["prices"].shape == (3, 5)
        assert obs["volumes"].shape == (3,)
        assert obs["macro"].shape == (4,)

    def test_step_returns_five_tuple(self, env: TradingEnvironment) -> None:
        env.reset()
        action = env.action_space.sample()
        result = env.step(action)
        assert len(result) == 5

    def test_reward_is_finite(self, env: TradingEnvironment) -> None:
        env.reset()
        for _ in range(10):
            action = env.action_space.sample()
            _, reward, done, _, _ = env.step(action)
            assert np.isfinite(reward)
            if done:
                break

    def test_episode_terminates(self, env: TradingEnvironment) -> None:
        env.reset()
        done = False
        steps = 0
        while not done and steps < 1000:
            _, _, done, _, _ = env.step(env.action_space.sample())
            steps += 1
        assert done, "Episode should terminate before 1000 steps"


# -----------------------------------------------------------------------
# DDPGTradingAgent
# -----------------------------------------------------------------------
class TestDDPGTradingAgent:
    @pytest.fixture
    def agent(self) -> DDPGTradingAgent:
        env = TradingEnvironment(n_assets=3, window=5)
        return DDPGTradingAgent(env=env)

    def test_select_action_shape(self, agent: DDPGTradingAgent) -> None:
        obs, _ = agent.env.reset()
        action = agent.select_action(obs, add_noise=False)
        assert action.shape == (3,)

    def test_select_action_bounded(self, agent: DDPGTradingAgent) -> None:
        obs, _ = agent.env.reset()
        action = agent.select_action(obs, add_noise=False)
        assert (action >= -1.0).all() and (action <= 1.0).all()

    def test_update_returns_none_when_buffer_too_small(
        self, agent: DDPGTradingAgent
    ) -> None:
        result = agent.update()
        assert result is None

    def test_update_returns_losses_when_buffer_full(
        self, agent: DDPGTradingAgent
    ) -> None:
        env = agent.env
        obs, _ = env.reset()
        for _ in range(agent.config["batch_size"] + 10):
            action = env.action_space.sample()
            next_obs, reward, done, _, _ = env.step(action)
            agent.replay_buffer.add(obs, action, reward, next_obs, done)
            obs = next_obs
            if done:
                obs, _ = env.reset()
        result = agent.update()
        assert result is not None
        critic_loss, actor_loss = result
        assert np.isfinite(critic_loss)
        assert np.isfinite(actor_loss)

    def test_save_and_load(self, agent: DDPGTradingAgent, tmp_path) -> None:
        agent.save_model(str(tmp_path / "model"))
        env = TradingEnvironment(n_assets=3, window=5)
        new_agent = DDPGTradingAgent(env=env)
        new_agent.load_model(str(tmp_path / "model"))
        # Weights should match after load
        for p1, p2 in zip(agent.actor.parameters(), new_agent.actor.parameters()):
            assert torch.allclose(p1, p2)
