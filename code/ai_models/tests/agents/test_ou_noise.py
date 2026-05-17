"""
Unit tests for OUNoise and ReplayBuffer.

Extended coverage beyond the existing test_replay_buffer.py:
* OUNoise reset behaviour, stationarity, temporal correlation.
* ReplayBuffer capacity overflow (circular eviction).
* ReplayBuffer sampling with dict states.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
from ai_models.agents.replay_buffer import OUNoise, ReplayBuffer


class TestOUNoise:
    def test_initial_state_equals_mu(self):
        noise = OUNoise(size=4, mu=0.0)
        np.testing.assert_array_equal(noise.state, np.zeros(4))

    def test_sample_shape(self):
        noise = OUNoise(size=6)
        s = noise.sample()
        assert s.shape == (6,)

    def test_reset_restores_mu(self):
        noise = OUNoise(size=3, mu=0.5)
        for _ in range(20):
            noise.sample()
        noise.reset()
        np.testing.assert_array_equal(noise.state, 0.5 * np.ones(3))

    def test_long_run_mean_near_mu(self):
        """After many steps the time-averaged sample should be near mu."""
        noise = OUNoise(size=1, mu=0.0, theta=0.15, sigma=0.10)
        samples = np.array([noise.sample()[0] for _ in range(50_000)])
        assert abs(samples.mean()) < 0.05

    def test_temporal_correlation_positive(self):
        """Consecutive samples should be positively correlated (OU property)."""
        noise = OUNoise(size=1, theta=0.10, sigma=0.05)
        samples = np.array([noise.sample()[0] for _ in range(1000)])
        corr = np.corrcoef(samples[:-1], samples[1:])[0, 1]
        assert corr > 0.5, f"Expected positive autocorrelation, got {corr:.3f}"

    def test_repr(self):
        noise = OUNoise(size=4)
        assert "OUNoise" in repr(noise)
        assert "4" in repr(noise)


class TestReplayBufferExtended:
    def test_capacity_overflow_evicts_oldest(self):
        buf = ReplayBuffer(capacity=5)
        for i in range(10):
            buf.add(
                np.array([float(i)]),
                np.array([0.0]),
                float(i),
                np.array([float(i + 1)]),
                False,
            )
        assert len(buf) == 5

    def test_sample_size_capped_at_buffer_length(self):
        buf = ReplayBuffer(capacity=100)
        for i in range(3):
            buf.add(np.array([0.0]), np.array([0.0]), 0.0, np.array([0.0]), False)
        states, *_ = buf.sample(batch_size=50)
        assert states.shape[0] == 3

    def test_reward_dtype_is_float(self):
        buf = ReplayBuffer(capacity=10)
        buf.add(np.array([1.0]), np.array([0.0]), 1, np.array([2.0]), False)
        _, _, rewards, _, _ = buf.sample(1)
        assert rewards.dtype == torch.float32

    def test_done_flag_stored_correctly(self):
        buf = ReplayBuffer(capacity=10)
        buf.add(np.array([1.0]), np.array([0.0]), 0.0, np.array([2.0]), True)
        _, _, _, _, dones = buf.sample(1)
        assert dones[0].item() == pytest.approx(1.0)

    def test_dict_state_flattened(self):
        buf = ReplayBuffer(capacity=20)
        state = {"a": np.array([1.0, 2.0]), "b": np.array([3.0])}
        buf.add(state, np.array([0.0]), 0.0, state, False)
        states, *_ = buf.sample(1)
        assert states.shape == (1, 3)  # 2 + 1 after flatten

    def test_empty_buffer_repr(self):
        buf = ReplayBuffer(capacity=50)
        assert "0" in repr(buf)
        assert "50" in repr(buf)
