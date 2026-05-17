"""
Unit tests for all configuration dataclasses in ai_models.config.

Validates default values, field types, mutability, and field-level constraints
so that accidental changes to training hyperparameters are caught immediately.
"""

from __future__ import annotations

import pytest
from ai_models.config import (
    DDPGConfig,
    GANConfig,
    PortfolioEnvConfig,
    PPOConfig,
    TradingEnvConfig,
    TransformerConfig,
)


class TestDDPGConfig:
    def test_defaults_are_sensible(self):
        cfg = DDPGConfig()
        assert 0 < cfg.actor_lr < 1e-2
        assert 0 < cfg.critic_lr < 1e-2
        assert 0.9 <= cfg.gamma <= 1.0
        assert 0 < cfg.tau < 1
        assert cfg.batch_size > 0
        assert cfg.buffer_size >= cfg.batch_size
        assert cfg.warmup_steps >= 0
        assert cfg.noise_sigma > 0
        assert cfg.noise_theta > 0
        assert 0 < cfg.noise_decay <= 1.0
        assert len(cfg.actor_hidden) >= 1
        assert len(cfg.critic_hidden) >= 1
        assert cfg.grad_clip > 0

    def test_field_mutation(self):
        cfg = DDPGConfig()
        cfg.actor_lr = 5e-5
        assert cfg.actor_lr == pytest.approx(5e-5)

    def test_hidden_layers_independent(self):
        c1 = DDPGConfig()
        c2 = DDPGConfig()
        c1.actor_hidden.append(512)
        assert (
            512 not in c2.actor_hidden
        ), "Mutable default_factory must produce independent lists per instance"

    def test_custom_construction(self):
        cfg = DDPGConfig(batch_size=128, gamma=0.95, use_cuda=False)
        assert cfg.batch_size == 128
        assert cfg.gamma == pytest.approx(0.95)
        assert cfg.use_cuda is False


class TestPPOConfig:
    def test_defaults_are_sensible(self):
        cfg = PPOConfig()
        assert cfg.learning_rate > 0
        assert cfg.n_steps > 0
        assert cfg.batch_size > 0
        assert cfg.n_epochs > 0
        assert 0.9 <= cfg.gamma <= 1.0
        assert 0 < cfg.gae_lambda <= 1.0
        assert 0 < cfg.clip_range < 1.0
        assert cfg.ent_coef >= 0
        assert cfg.vf_coef > 0
        assert cfg.max_grad_norm > 0

    def test_custom_clip_range(self):
        cfg = PPOConfig(clip_range=0.1)
        assert cfg.clip_range == pytest.approx(0.1)


class TestTransformerConfig:
    def test_defaults(self):
        cfg = TransformerConfig()
        assert cfg.num_layers >= 1
        assert cfg.d_model > 0
        assert cfg.num_heads > 0
        assert (
            cfg.d_model % cfg.num_heads == 0
        ), "d_model must be divisible by num_heads for multi-head attention"
        assert cfg.dff > cfg.d_model
        assert cfg.input_seq_length > 0
        assert cfg.output_seq_length > 0
        assert 0 < cfg.dropout_rate < 1
        assert cfg.learning_rate > 0

    def test_head_divisibility_invariant(self):
        cfg = TransformerConfig(d_model=64, num_heads=8)
        assert cfg.d_model % cfg.num_heads == 0


class TestGANConfig:
    def test_defaults(self):
        cfg = GANConfig()
        assert cfg.seq_length > 0
        assert cfg.n_features > 0
        assert cfg.latent_dim > 0
        assert cfg.g_lr > 0
        assert cfg.d_lr > 0
        assert cfg.n_regimes >= 2
        assert cfg.batch_size > 0

    def test_custom_regimes(self):
        cfg = GANConfig(n_regimes=5)
        assert cfg.n_regimes == 5


class TestTradingEnvConfig:
    def test_defaults(self):
        cfg = TradingEnvConfig()
        assert cfg.n_assets > 0
        assert cfg.window > 0
        assert cfg.n_macro >= 0
        assert 0 <= cfg.transaction_cost < 1
        assert cfg.max_steps > cfg.window

    def test_custom(self):
        cfg = TradingEnvConfig(n_assets=10, window=20, transaction_cost=0.005)
        assert cfg.n_assets == 10
        assert cfg.window == 20
        assert cfg.transaction_cost == pytest.approx(0.005)


class TestPortfolioEnvConfig:
    def test_defaults(self):
        cfg = PortfolioEnvConfig()
        assert 0 <= cfg.transaction_cost < 1
        assert cfg.window > 0
        assert cfg.n_macro >= 0
        assert cfg.max_steps > cfg.window

    def test_custom_transaction_cost(self):
        cfg = PortfolioEnvConfig(transaction_cost=0.002)
        assert cfg.transaction_cost == pytest.approx(0.002)
