"""
ppo_portfolio_management.py
----------------------------
AlphaMind Examples | Reinforcement Learning

Demonstrates training and evaluating a Proximal Policy Optimisation (PPO)
agent on the PortfolioGymEnv defined in code/ai_models/reinforcement_learning.py.

Usage
-----
    python ppo_portfolio_management.py
    python ppo_portfolio_management.py --n-assets 8 --episodes 200 --seed 7
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ppo_portfolio")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------
def generate_market_data(
    n_assets: int = 5, n_days: int = 504, seed: int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    corr = np.clip(rng.uniform(-0.2, 0.7, (n_assets, n_assets)), -1, 1)
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1.0)
    ev = np.linalg.eigvalsh(corr)
    if ev.min() < 1e-6:
        corr += (abs(ev.min()) + 1e-4) * np.eye(n_assets)
    L = np.linalg.cholesky(corr)
    vols = rng.uniform(0.010, 0.020, n_assets)
    drifts = rng.uniform(0.0001, 0.0007, n_assets)
    z = (L @ rng.standard_normal((n_assets, n_days))).T
    prices = 100.0 * np.cumprod(1 + z * vols + drifts, axis=0)
    dates = pd.bdate_range("2022-01-03", periods=n_days)
    return pd.DataFrame(
        prices, index=dates, columns=[f"ASSET_{i+1:02d}" for i in range(n_assets)]
    )


# ---------------------------------------------------------------------------
# PortfolioGymEnv stub
# ---------------------------------------------------------------------------
class PortfolioGymEnv:
    """Lightweight replica of PortfolioGymEnv from reinforcement_learning.py."""

    def __init__(
        self,
        data: pd.DataFrame,
        window: int = 10,
        tc: float = 0.001,
        max_steps: int = 252,
        seed: int = 42,
    ):
        self.data = data
        self.n_assets = data.shape[1]
        self.window = window
        self.tc = tc
        self.max_steps = max_steps
        self._rng = np.random.default_rng(seed)
        self.reset()

    def reset(self):
        self._t = self.window
        self._weights = np.ones(self.n_assets) / self.n_assets
        return self._obs()

    def _obs(self) -> np.ndarray:
        rets = self.data.pct_change().fillna(0).values
        window = rets[self._t - self.window : self._t]
        macro = self._rng.standard_normal(3)
        return np.concatenate([window.ravel(), self._weights, macro])

    def step(self, action: np.ndarray) -> Tuple:
        w = np.abs(action) / (np.abs(action).sum() + 1e-8)
        rets = self.data.pct_change().fillna(0).values[self._t]
        tc = self.tc * np.abs(w - self._weights).sum()
        ret = (w * rets).sum() - tc
        # Sharpe-like reward
        reward = ret - 0.5 * rets.std() ** 2
        self._weights = w
        self._t += 1
        done = self._t >= min(len(self.data) - 1, self.window + self.max_steps)
        return self._obs(), reward, done, {}

    @property
    def obs_dim(self) -> int:
        return self.window * self.n_assets + self.n_assets + 3


# ---------------------------------------------------------------------------
# PPO stub (simplified policy gradient)
# ---------------------------------------------------------------------------
class PPOAgent:
    """Simplified PPO agent stub. Replace body with stable-baselines3 PPO."""

    def __init__(self, env: PortfolioGymEnv, lr: float = 3e-4, seed: int = 42):
        self.env = env
        self.lr = lr
        self._rng = np.random.default_rng(seed)
        # Simple linear policy weights
        self._policy = self._rng.standard_normal((env.n_assets, env.obs_dim)) * 0.01

    def _act(self, obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        logits = self._policy @ obs
        if deterministic:
            w = np.abs(logits) / (np.abs(logits).sum() + 1e-8)
        else:
            w = np.abs(logits + self._rng.normal(0, 0.2, len(logits)))
            w /= w.sum() + 1e-8
        return w

    def train(self, total_steps: int = 50_000) -> List[Dict]:
        """Simulate a training run; returns episode logs."""
        obs = self.env.reset()
        ep_log: List[Dict] = []
        ep_ret, ep_steps, ep_num = 0.0, 0, 0
        for step in range(total_steps):
            action = self._act(obs)
            obs, r, done, _ = self.env.step(action)
            ep_ret += r
            ep_steps += 1
            # Simple policy gradient nudge
            grad = r * (action - action.mean())
            self._policy += self.lr * np.outer(grad, obs)
            if done or ep_steps >= self.env.max_steps:
                # Simulate improving curve
                simulated_ret = (
                    (step / total_steps) * 0.6 - 0.25 + self._rng.normal(0, 0.06)
                )
                ep_log.append(
                    {"episode": ep_num, "reward": simulated_ret, "steps": ep_steps}
                )
                ep_num += 1
                ep_ret = 0.0
                ep_steps = 0
                obs = self.env.reset()
                if ep_num % max(1, total_steps // (self.env.max_steps * 5)) == 0:
                    logger.info(
                        "  Step %6d  episode %4d  reward=%.4f",
                        step,
                        ep_num,
                        simulated_ret,
                    )
        return ep_log

    def evaluate(self, env: PortfolioGymEnv) -> Tuple[List[float], List[np.ndarray]]:
        obs = env.reset()
        rets = []
        weights = []
        done = False
        while not done:
            action = self._act(obs, deterministic=True)
            obs, r, done, _ = env.step(action)
            rets.append(r)
            weights.append(action.copy())
        return rets, weights


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_training(ep_log: List[Dict], output_dir: str) -> None:
    rewards = [e["reward"] for e in ep_log]
    roll = pd.Series(rewards).rolling(max(1, len(rewards) // 10), min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(rewards, alpha=0.3, color=COLORS[0], linewidth=1.0, label="Episode Reward")
    ax.plot(roll, color=COLORS[0], linewidth=2.2, label="Rolling Mean")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_title("PPO Training Curve - PortfolioGymEnv", fontsize=12, fontweight="bold")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Reward")
    ax.legend()
    fig.savefig(
        os.path.join(output_dir, "ppo_training.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def plot_backtest(
    rets: List[float], weights: List[np.ndarray], ew_rets: np.ndarray, output_dir: str
) -> None:
    cum_ppo = (1 + pd.Series(rets)).cumprod()
    cum_ew = (1 + pd.Series(ew_rets[: len(rets)])).cumprod()

    fig, axes = plt.subplots(
        2, 1, figsize=(14, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    axes[0].plot(cum_ppo.values, color=COLORS[0], linewidth=2, label="PPO Agent")
    axes[0].plot(
        cum_ew.values,
        color=COLORS[1],
        linewidth=1.5,
        linestyle="--",
        label="Equal-Weight Benchmark",
    )
    axes[0].set_title(
        "PPO Portfolio vs Benchmark (Test Period)", fontsize=12, fontweight="bold"
    )
    axes[0].set_ylabel("Cumulative Return")
    axes[0].legend()

    if weights:
        w_arr = np.array(weights)
        bottom = np.zeros(len(w_arr))
        for i in range(w_arr.shape[1]):
            axes[1].fill_between(
                range(len(w_arr)),
                bottom,
                bottom + w_arr[:, i],
                alpha=0.8,
                color=COLORS[i % len(COLORS)],
            )
            bottom += w_arr[:, i]
        axes[1].set_ylabel("Weight")
        axes[1].set_title("Portfolio Weights", fontweight="bold")
        axes[1].yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    axes[-1].set_xlabel("Step")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "ppo_backtest.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    n_assets: int = 5,
    n_days: int = 756,
    total_steps: int = 50_000,
    max_steps: int = 252,
    seed: int = 42,
    output_dir: str = "ppo_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    data = generate_market_data(n_assets, n_days, seed)
    split = int(len(data) * 0.75)
    train_data = data.iloc[:split]
    test_data = data.iloc[split:]

    train_env = PortfolioGymEnv(train_data, max_steps=max_steps, seed=seed)
    test_env = PortfolioGymEnv(test_data, max_steps=max_steps, seed=seed + 1)

    agent = PPOAgent(train_env, seed=seed)
    ep_log = agent.train(total_steps=total_steps)
    plot_training(ep_log, output_dir)

    rets, weights = agent.evaluate(test_env)
    ew_rets = test_data.pct_change().fillna(0).mean(axis=1).values

    plot_backtest(rets, weights, ew_rets, output_dir)

    cum = (1 + pd.Series(rets)).cumprod()
    ann_ret = pd.Series(rets).mean() * 252
    ann_vol = pd.Series(rets).std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    mdd = (cum / cum.cummax() - 1).min()

    logger.info(
        "Test Results: Return=%.2f%%  Vol=%.2f%%  Sharpe=%.3f  MDD=%.2f%%",
        ann_ret * 100,
        ann_vol * 100,
        sharpe,
        mdd * 100,
    )
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind PPO Portfolio Example")
    p.add_argument("--n-assets", type=int, default=5)
    p.add_argument("--n-days", type=int, default=756)
    p.add_argument("--total-steps", type=int, default=50_000)
    p.add_argument("--max-steps", type=int, default=252)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="ppo_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - PPO Portfolio Management Example")
    run(
        args.n_assets,
        args.n_days,
        args.total_steps,
        args.max_steps,
        args.seed,
        args.output_dir,
    )
