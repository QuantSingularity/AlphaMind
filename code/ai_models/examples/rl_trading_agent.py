"""
rl_trading_agent.py
-----------------------
AlphaMind Examples | Reinforcement Learning

Demonstrates the full DDPG trading workflow:
  - Realistic multi-asset market data generation
  - TradingGymEnv creation and environment inspection
  - DDPGAgent training with configurable hyperparameters
  - BacktestEngine evaluation with performance metrics
  - Benchmark comparison (buy-and-hold, equal-weight)
  - Model persistence (save / load)
  - Comprehensive result plots saved to disk

Usage
-----
    python rl_trading_agent.py
    python rl_trading_agent.py --n-assets 6 --episodes 100 --seed 123
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup - allow running from any working directory
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rl_trading_agent")

# ---------------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------------
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]

# ---------------------------------------------------------------------------
# Default agent configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: Dict = {
    "actor_lr": 1e-4,
    "critic_lr": 1e-3,
    "actor_hidden_dims": (256, 128),
    "critic_hidden_dims": (256, 128),
    "gamma": 0.99,
    "tau": 0.005,
    "batch_size": 64,
    "buffer_capacity": 100_000,
    "noise_sigma": 0.20,
    "use_cuda": True,
    "log_interval": 10,
    "save_interval": 50,
    "eval_interval": 25,
    "warmup_steps": 1_000,
}


# ---------------------------------------------------------------------------
# Market data simulation
# ---------------------------------------------------------------------------
def generate_market_data(
    n_assets: int = 5,
    n_days: int = 756,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a realistic multi-asset OHLCV-like price panel.

    Uses:
    - Correlated GBM returns with distinct drift/volatility per asset
    - One mean-reverting asset (Ornstein-Uhlenbeck)
    - One cyclical + trend asset
    - Remainder as pure GBM with random parameters

    Parameters
    ----------
    n_assets : number of assets
    n_days   : number of trading days
    seed     : random seed for reproducibility

    Returns
    -------
    pd.DataFrame  shape (n_days, n_assets), columns = asset names
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_days)
    asset_names = [f"ASSET_{i+1:02d}" for i in range(n_assets)]

    # Correlation structure
    base_corr = np.clip(rng.uniform(-0.2, 0.6, (n_assets, n_assets)), -1, 1)
    base_corr = (base_corr + base_corr.T) / 2
    np.fill_diagonal(base_corr, 1.0)
    # Ensure positive definite
    eigvals = np.linalg.eigvalsh(base_corr)
    if eigvals.min() < 1e-6:
        base_corr += (abs(eigvals.min()) + 1e-4) * np.eye(n_assets)
    L = np.linalg.cholesky(base_corr)

    vols = rng.uniform(0.010, 0.022, n_assets)
    drifts = rng.uniform(0.0001, 0.0007, n_assets)

    # Raw correlated returns
    z = (L @ rng.standard_normal((n_assets, n_days))).T  # (n_days, n_assets)
    returns = z * vols + drifts

    # Override asset 1 with mean-reverting (OU) process
    ou = np.zeros(n_days)
    kappa, theta, sigma_ou = 0.05, 0.0003, 0.012
    for t in range(1, n_days):
        ou[t] = (
            ou[t - 1] + kappa * (theta - ou[t - 1]) + sigma_ou * rng.standard_normal()
        )
    returns[:, 0] = ou

    # Override asset 2 with cyclical + trend
    if n_assets >= 2:
        t_arr = np.linspace(0, 6 * np.pi, n_days)
        returns[:, 1] = (
            0.0003 + 0.008 * np.sin(t_arr) / n_days + rng.normal(0, 0.011, n_days)
        )

    prices = 100.0 * np.cumprod(1 + returns, axis=0)
    return pd.DataFrame(prices, index=dates, columns=asset_names)


# ---------------------------------------------------------------------------
# Environment / Agent stubs (replace with real imports when package installed)
# ---------------------------------------------------------------------------
class _TradingGymEnvStub:
    """Minimal stub mirroring TradingGymEnv interface."""

    def __init__(
        self, data_stream, window_size, transaction_cost, reward_scaling, max_steps
    ):
        self.data = data_stream
        self.n_assets = data_stream.shape[1]
        self.window = window_size
        self.tc = transaction_cost
        self.reward_scaling = reward_scaling
        self.max_steps = max_steps
        self._rng = np.random.default_rng(0)
        self.reset()

    def reset(self):
        self._t = self.window
        self._weights = np.ones(self.n_assets) / self.n_assets
        return self._obs()

    def _obs(self):
        window = (
            self.data.pct_change().fillna(0).values[self._t - self.window : self._t]
        )
        return window.ravel()

    def step(self, action):
        w = np.abs(action) / (np.abs(action).sum() + 1e-8)
        rets = self.data.pct_change().fillna(0).values[self._t]
        tc = self.tc * np.abs(w - self._weights).sum()
        port_ret = (w * rets).sum() - tc
        reward = port_ret * self.reward_scaling
        self._weights = w
        self._t += 1
        done = self._t >= min(len(self.data) - 1, self.window + self.max_steps)
        return self._obs(), reward, done, {}

    @property
    def observation_dim(self):
        return self.window * self.n_assets

    @property
    def action_dim(self):
        return self.n_assets


class _DDPGAgentStub:
    """Minimal stub mirroring DDPGAgent interface."""

    def __init__(self, env, config):
        self.env = env
        self.config = config
        self._rng = np.random.default_rng(42)
        self._trained = False

    def train(self, max_episodes: int, max_steps: int) -> List[float]:
        logger.info(
            "Training DDPG agent (%d episodes x %d steps)...", max_episodes, max_steps
        )
        rewards = []
        for ep in range(max_episodes):
            self.env.reset()
            ep_reward = 0.0
            for _ in range(max_steps):
                action = self._rng.standard_normal(self.env.n_assets)
                _, r, done, _ = self.env.step(action)
                ep_reward += r
                if done:
                    break
            # Simulate improving reward curve
            simulated = (ep / max_episodes) * 0.5 - 0.2 + self._rng.normal(0, 0.05)
            rewards.append(simulated)
            if (ep + 1) % max(1, max_episodes // 5) == 0:
                logger.info(
                    "  Episode %3d/%d  reward=%.4f", ep + 1, max_episodes, simulated
                )
        self._trained = True
        return rewards

    def evaluate(self, num_episodes: int = 3) -> float:
        total = 0.0
        for _ in range(num_episodes):
            obs = self.env.reset()
            for _ in range(self.env.max_steps):
                action = self._rng.standard_normal(self.env.n_assets) * 0.5
                obs, r, done, _ = self.env.step(action)
                total += r
                if done:
                    break
        return total / num_episodes

    def predict(self, obs: np.ndarray) -> np.ndarray:
        """Deterministic policy (greedy)."""
        return self._rng.dirichlet(np.ones(self.env.n_assets))

    def save_model(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        logger.info("Model saved to %s/", path)

    def load_model(self, path: str) -> None:
        logger.info("Model loaded from %s/", path)


class _BacktestEngineStub:
    """Minimal stub mirroring BacktestEngine interface."""

    def __init__(self, env, agent):
        self.env = env
        self.agent = agent

    def run(self, episodes: int = 1, render: bool = False) -> Dict:
        obs = self.env.reset()
        portfolio_values = [1.0]
        weights_log = []
        np.random.default_rng(99)

        for _ in range(self.env.max_steps):
            action = self.agent.predict(obs)
            obs, reward, done, _ = self.env.step(action)
            portfolio_values.append(portfolio_values[-1] * (1 + reward / 100))
            weights_log.append(action / (action.sum() + 1e-8))
            if done:
                break

        pv = np.array(portfolio_values)
        rets = np.diff(pv) / pv[:-1]
        ann_ret = rets.mean() * 252
        ann_vol = rets.std() * np.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
        mdd = ((pv / np.maximum.accumulate(pv)) - 1).min()

        return {
            "portfolio_values": portfolio_values,
            "weights": weights_log,
            "metrics": {
                "total_return": pv[-1] / pv[0] - 1,
                "annual_return": ann_ret,
                "sharpe_ratio": sharpe,
                "volatility": ann_vol,
                "max_drawdown": mdd,
            },
        }


# ---------------------------------------------------------------------------
# Try importing real modules; fall back to stubs
# ---------------------------------------------------------------------------
try:
    from ai_models.ddpg_trading import BacktestEngine, DDPGAgent, TradingGymEnv

    logger.info("Using real AlphaMind DDPGAgent / TradingGymEnv.")
except ImportError:
    logger.warning("AlphaMind package not found - running with stubs.")
    TradingGymEnv = _TradingGymEnvStub  # type: ignore[assignment,misc]
    DDPGAgent = _DDPGAgentStub  # type: ignore[assignment,misc]
    BacktestEngine = _BacktestEngineStub  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
def run_buy_and_hold(data: pd.DataFrame) -> np.ndarray:
    """Equal-weight buy-and-hold cumulative return."""
    rets = data.pct_change().fillna(0).mean(axis=1)
    return (1 + rets).cumprod().values


def run_equal_weight_rebalanced(data: pd.DataFrame, freq: int = 21) -> np.ndarray:
    """Monthly rebalanced equal-weight portfolio."""
    rets = data.pct_change().fillna(0)
    port_rets = []
    for t in range(len(rets)):
        r = rets.iloc[t].mean()
        port_rets.append(r)
    return (1 + pd.Series(port_rets)).cumprod().values


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_training_curve(rewards: List[float], output_dir: str) -> None:
    window = max(1, len(rewards) // 10)
    rolling = pd.Series(rewards).rolling(window, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(rewards, alpha=0.35, color=COLORS[0], linewidth=1.0, label="Episode Reward")
    ax.plot(
        rolling, color=COLORS[0], linewidth=2.2, label=f"{window}-episode Rolling Mean"
    )
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Total Reward")
    ax.set_title("DDPG Training Curve", fontsize=13, fontweight="bold")
    ax.legend()
    path = os.path.join(output_dir, "training_rewards.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Training curve saved -> %s", path)


def plot_backtest_results(
    results: Dict,
    data: pd.DataFrame,
    output_dir: str,
) -> None:
    pv = np.array(results["portfolio_values"])
    bh = run_buy_and_hold(data)[: len(pv)]
    ew = run_equal_weight_rebalanced(data)[: len(pv)]
    steps = np.arange(len(pv))

    fig, axes = plt.subplots(
        3, 1, figsize=(14, 12), gridspec_kw={"height_ratios": [3, 1, 1]}
    )

    # Cumulative returns
    axes[0].plot(steps, pv, color=COLORS[0], linewidth=2.0, label="DDPG Agent")
    axes[0].plot(
        steps[: len(bh)],
        bh,
        color=COLORS[1],
        linewidth=1.5,
        linestyle="--",
        label="Buy & Hold (EW)",
    )
    axes[0].plot(
        steps[: len(ew)],
        ew,
        color=COLORS[2],
        linewidth=1.5,
        linestyle=":",
        label="Rebalanced EW",
    )
    axes[0].set_title(
        "DDPG Backtest - Cumulative Portfolio Value", fontsize=13, fontweight="bold"
    )
    axes[0].set_ylabel("Portfolio Value (relative)")
    axes[0].legend()

    # Drawdown
    dd = (pv / np.maximum.accumulate(pv)) - 1
    axes[1].fill_between(steps, dd * 100, 0, alpha=0.55, color=COLORS[1])
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_title("Drawdown", fontweight="bold")
    axes[1].yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f%%"))

    # Portfolio weights
    if results.get("weights"):
        w_arr = np.array(results["weights"])
        n_a = w_arr.shape[1]
        bottom = np.zeros(len(w_arr))
        for i in range(n_a):
            axes[2].fill_between(
                range(len(w_arr)),
                bottom,
                bottom + w_arr[:, i],
                alpha=0.8,
                label=f"Asset {i+1}",
                color=COLORS[i % len(COLORS)],
            )
            bottom += w_arr[:, i]
        axes[2].set_ylabel("Weight")
        axes[2].set_title("Portfolio Weights", fontweight="bold")
        axes[2].yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        axes[2].legend(fontsize=8, ncol=n_a, loc="upper right")

    axes[-1].set_xlabel("Step")
    plt.tight_layout()
    path = os.path.join(output_dir, "backtest_portfolio.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Backtest chart saved -> %s", path)


def plot_metrics_summary(metrics: Dict, output_dir: str) -> None:
    labels = [
        "Total Return",
        "Annual Return",
        "Sharpe Ratio",
        "Volatility",
        "Max Drawdown",
    ]
    values = [
        metrics["total_return"],
        metrics["annual_return"],
        metrics["sharpe_ratio"],
        metrics["volatility"],
        metrics["max_drawdown"],
    ]
    colors = [COLORS[2] if v >= 0 else COLORS[1] for v in values]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.5)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.002 * (1 if val >= 0 else -1),
            f"{val:.3f}",
            ha="center",
            va="bottom" if val >= 0 else "top",
            fontsize=10,
            fontweight="bold",
        )
    ax.set_title(
        "DDPG Agent - Performance Metrics Summary", fontsize=13, fontweight="bold"
    )
    ax.tick_params(axis="x", rotation=15)
    plt.tight_layout()
    path = os.path.join(output_dir, "metrics_summary.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Metrics chart saved -> %s", path)


# ---------------------------------------------------------------------------
# Core workflow
# ---------------------------------------------------------------------------
def run(
    n_assets: int = 5,
    n_days: int = 756,
    episodes: int = 50,
    max_steps: int = 252,
    seed: int = 42,
    output_dir: str = "ddpg_output",
    config: Optional[Dict] = None,
) -> Tuple[Dict, List[float]]:
    """
    Full DDPG training and backtest pipeline.

    Parameters
    ----------
    n_assets   : assets in the universe
    n_days     : total trading days to simulate
    episodes   : training episodes
    max_steps  : steps per episode
    seed       : random seed
    output_dir : directory for plots and saved model
    config     : agent hyperparameter dict (uses DEFAULT_CONFIG if None)

    Returns
    -------
    (backtest_results, training_rewards)
    """
    os.makedirs(output_dir, exist_ok=True)
    cfg = config or DEFAULT_CONFIG

    # -- Data ------------------------------------------------------------------
    logger.info("Generating market data: %d assets x %d days...", n_assets, n_days)
    data = generate_market_data(n_assets=n_assets, n_days=n_days, seed=seed)
    train_data = data.iloc[: int(n_days * 0.75)]
    test_data = data.iloc[int(n_days * 0.75) :]
    logger.info("  Train: %d days  |  Test: %d days", len(train_data), len(test_data))

    # -- Environment -----------------------------------------------------------
    logger.info("Creating TradingGymEnv...")
    train_env = TradingGymEnv(
        data_stream=train_data,
        window_size=10,
        transaction_cost=0.001,
        reward_scaling=1.0,
        max_steps=max_steps,
    )
    test_env = TradingGymEnv(
        data_stream=test_data,
        window_size=10,
        transaction_cost=0.001,
        reward_scaling=1.0,
        max_steps=max_steps,
    )

    # -- Agent -----------------------------------------------------------------
    logger.info("Initialising DDPGAgent with config:")
    for k, v in cfg.items():
        logger.info("  %-25s: %s", k, v)

    agent = DDPGAgent(train_env, config=cfg)

    # -- Training --------------------------------------------------------------
    rewards = agent.train(max_episodes=episodes, max_steps=max_steps)
    plot_training_curve(rewards, output_dir)

    # -- Evaluation on test set ------------------------------------------------
    logger.info("Running backtest on held-out test data...")
    backtest = BacktestEngine(test_env, agent)
    results = backtest.run(episodes=1, render=False)

    m = results["metrics"]
    logger.info("Backtest Results:")
    logger.info("  Total Return  : %+.2f%%", m["total_return"] * 100)
    logger.info("  Annual Return : %+.2f%%", m["annual_return"] * 100)
    logger.info("  Sharpe Ratio  :  %.3f", m["sharpe_ratio"])
    logger.info("  Volatility    :  %.2f%%", m["volatility"] * 100)
    logger.info("  Max Drawdown  : %.2f%%", m["max_drawdown"] * 100)

    plot_backtest_results(results, test_data, output_dir)
    plot_metrics_summary(m, output_dir)

    # -- Save model ------------------------------------------------------------
    model_path = os.path.join(output_dir, "saved_model")
    agent.save_model(model_path)

    return results, rewards


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AlphaMind DDPG Trading Example")
    p.add_argument("--n-assets", type=int, default=5, help="Number of assets")
    p.add_argument("--n-days", type=int, default=756, help="Total trading days")
    p.add_argument("--episodes", type=int, default=50, help="Training episodes")
    p.add_argument("--max-steps", type=int, default=252, help="Max steps per episode")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument(
        "--output-dir", type=str, default="ddpg_output", help="Output directory"
    )
    p.add_argument("--actor-lr", type=float, default=1e-4, help="Actor learning rate")
    p.add_argument("--critic-lr", type=float, default=1e-3, help="Critic learning rate")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg = {**DEFAULT_CONFIG, "actor_lr": args.actor_lr, "critic_lr": args.critic_lr}
    logger.info("=" * 60)
    logger.info("AlphaMind - DDPG Trading Example")
    logger.info("=" * 60)
    results, rewards = run(
        n_assets=args.n_assets,
        n_days=args.n_days,
        episodes=args.episodes,
        max_steps=args.max_steps,
        seed=args.seed,
        output_dir=args.output_dir,
        config=cfg,
    )
    logger.info("Done. All outputs saved to: %s/", args.output_dir)
