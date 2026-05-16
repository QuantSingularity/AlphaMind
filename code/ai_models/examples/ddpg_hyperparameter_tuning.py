"""
ddpg_hyperparameter_tuning.py
------------------------------
AlphaMind Examples | Reinforcement Learning

Systematic hyperparameter search for the DDPGAgent using:
  - Random search with configurable trial budget
  - Parallel trial execution via ThreadPoolExecutor
  - Random Forest feature importance to rank hyperparameters
  - Sensitivity scatter plots saved to disk
  - Best config validation with extended backtest
  - JSON export of the winning configuration

Usage
-----
    python ddpg_hyperparameter_tuning.py
    python ddpg_hyperparameter_tuning.py --n-trials 30 --episodes 10
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
logger = logging.getLogger("ddpg_hyperparameter_tuning")

plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]

# ---------------------------------------------------------------------------
# Try importing real AlphaMind modules; fall back to stubs
# ---------------------------------------------------------------------------
try:
    from ai_models.ddpg_trading import BacktestEngine, DDPGAgent, TradingGymEnv

    _REAL = True
    logger.info("Using real AlphaMind modules.")
except ImportError:
    _REAL = False
    logger.warning("AlphaMind package not found - using stubs.")
    from rl_trading_agent import (  # type: ignore[import]
        _DDPGAgentStub as DDPGAgent,
        _TradingGymEnvStub as TradingGymEnv,
        _BacktestEngineStub as BacktestEngine,
    )

from rl_trading_agent import generate_market_data  # type: ignore[import]

# ---------------------------------------------------------------------------
# Default search space
# ---------------------------------------------------------------------------
DEFAULT_PARAM_GRID: Dict[str, List[Any]] = {
    "actor_lr": [1e-5, 3e-5, 1e-4, 3e-4, 1e-3],
    "critic_lr": [1e-4, 3e-4, 1e-3, 3e-3, 1e-2],
    "gamma": [0.95, 0.97, 0.99],
    "tau": [0.001, 0.005, 0.01, 0.05],
    "noise_sigma": [0.10, 0.15, 0.20, 0.30],
    "batch_size": [32, 64, 128, 256],
    "buffer_capacity": [10_000, 50_000, 100_000],
    "actor_hidden_dims": [(128, 64), (256, 128), (512, 256)],
    "critic_hidden_dims": [(128, 64), (256, 128), (512, 256)],
}


# ---------------------------------------------------------------------------
# HyperparameterTuner
# ---------------------------------------------------------------------------
class HyperparameterTuner:
    """
    Random-search hyperparameter tuner for DDPGAgent.

    Parameters
    ----------
    env_creator        : zero-arg callable that returns a fresh TradingGymEnv
    param_grid         : dict mapping param name -> list of candidate values
    n_trials           : number of random configurations to try
    episodes_per_trial : training episodes per trial
    max_steps          : max steps per episode during training
    n_eval_episodes    : evaluation episodes after training
    n_workers          : parallel worker threads (1 = sequential)
    seed               : base random seed
    """

    def __init__(
        self,
        env_creator,
        param_grid: Dict[str, List[Any]],
        n_trials: int = 20,
        episodes_per_trial: int = 5,
        max_steps: int = 100,
        n_eval_episodes: int = 3,
        n_workers: int = 1,
        seed: int = 42,
    ) -> None:
        self.env_creator = env_creator
        self.param_grid = param_grid
        self.n_trials = n_trials
        self.episodes_per_trial = episodes_per_trial
        self.max_steps = max_steps
        self.n_eval_episodes = n_eval_episodes
        self.n_workers = n_workers
        self._rng = np.random.default_rng(seed)
        self.results: List[Dict[str, Any]] = []

    def _sample_config(self, trial_seed: int) -> Dict[str, Any]:
        rng = np.random.default_rng(trial_seed)
        return {k: rng.choice(v) for k, v in self.param_grid.items()}

    def _run_trial(self, trial: int) -> Dict[str, Any]:
        cfg = self._sample_config(trial_seed=1000 + trial)
        env = self.env_creator()
        agent = DDPGAgent(env, config=cfg)
        agent.train(max_episodes=self.episodes_per_trial, max_steps=self.max_steps)
        eval_reward = agent.evaluate(num_episodes=self.n_eval_episodes)
        return {"trial": trial + 1, "eval_reward": float(eval_reward), **cfg}

    def run(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Execute the random search.

        Returns
        -------
        (best_config, all_results)
        """
        logger.info(
            "Starting random search: %d trials  %d workers  "
            "%d ep/trial  %d steps/ep",
            self.n_trials,
            self.n_workers,
            self.episodes_per_trial,
            self.max_steps,
        )

        if self.n_workers > 1:
            with ThreadPoolExecutor(max_workers=self.n_workers) as pool:
                futures = {
                    pool.submit(self._run_trial, t): t for t in range(self.n_trials)
                }
                for fut in as_completed(futures):
                    result = fut.result()
                    self.results.append(result)
                    logger.info(
                        "  Trial %2d/%d  reward=%.4f",
                        result["trial"],
                        self.n_trials,
                        result["eval_reward"],
                    )
        else:
            for t in range(self.n_trials):
                result = self._run_trial(t)
                self.results.append(result)
                logger.info(
                    "  Trial %2d/%d  reward=%.4f",
                    result["trial"],
                    self.n_trials,
                    result["eval_reward"],
                )

        self.results.sort(key=lambda r: r["trial"])
        best = max(self.results, key=lambda r: r["eval_reward"])
        best_config = {k: best[k] for k in self.param_grid if k in best}
        logger.info("Best trial: #%d  reward=%.4f", best["trial"], best["eval_reward"])
        return best_config, self.results


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------
def build_results_df(results: List[Dict[str, Any]], param_grid: Dict) -> pd.DataFrame:
    """Convert raw results list to a tidy DataFrame."""
    rows = []
    for r in results:
        row = {"trial": r["trial"], "eval_reward": r["eval_reward"]}
        for k in param_grid:
            v = r.get(k)
            row[k] = str(v) if isinstance(v, (tuple, list)) else v
        rows.append(row)
    return pd.DataFrame(rows).set_index("trial")


def hyperparameter_importance(
    df: pd.DataFrame,
    param_grid: Dict,
    seed: int = 42,
) -> pd.Series:
    """
    Estimate hyperparameter importance via Random Forest regression
    on the eval_reward target.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder

    feat_df = df[[k for k in param_grid]].copy()
    for col in feat_df.columns:
        if feat_df[col].dtype == object:
            feat_df[col] = LabelEncoder().fit_transform(feat_df[col].astype(str))
        feat_df[col] = feat_df[col].astype(float)

    rf = RandomForestRegressor(n_estimators=300, random_state=seed)
    rf.fit(feat_df.values, df["eval_reward"].values)
    return pd.Series(rf.feature_importances_, index=feat_df.columns).sort_values(
        ascending=False
    )


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_sensitivity(df: pd.DataFrame, param_grid: Dict, output_dir: str) -> None:
    """Scatter plot of each hyperparameter vs eval_reward."""
    numeric_params = [
        k for k in param_grid if k not in ("actor_hidden_dims", "critic_hidden_dims")
    ]
    n = len(numeric_params)
    ncols = 3
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 5 * nrows))
    axes_flat = axes.ravel() if nrows > 1 else [axes] if n == 1 else axes.ravel()

    for ax, param in zip(axes_flat, numeric_params):
        x = pd.to_numeric(df[param], errors="coerce")
        y = df["eval_reward"]
        ax.scatter(x, y, alpha=0.6, s=40, color=COLORS[0])
        if x.notna().sum() > 2:
            m, b = np.polyfit(x.dropna(), y[x.notna()], 1)
            xr = np.linspace(x.min(), x.max(), 100)
            ax.plot(xr, m * xr + b, color=COLORS[1], linewidth=2)
        ax.set_title(param, fontsize=10, fontweight="bold")
        ax.set_xlabel(param)
        ax.set_ylabel("Eval Reward")
        if param in ("actor_lr", "critic_lr", "tau"):
            ax.set_xscale("log")

    for ax in axes_flat[len(numeric_params) :]:
        ax.set_visible(False)

    plt.suptitle(
        "Hyperparameter Sensitivity - DDPG Agent", fontsize=14, fontweight="bold"
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "parameter_sensitivity.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Sensitivity plot saved -> %s", path)


def plot_importance(importances: pd.Series, output_dir: str) -> None:
    """Horizontal bar chart of RF-based hyperparameter importance."""
    fig, ax = plt.subplots(figsize=(10, 6))
    importances.sort_values().plot.barh(
        ax=ax, color=COLORS[0], edgecolor="white", alpha=0.85
    )
    ax.set_title(
        "Hyperparameter Importance (Random Forest)", fontsize=13, fontweight="bold"
    )
    ax.set_xlabel("Importance Score")
    plt.tight_layout()
    path = os.path.join(output_dir, "parameter_importance.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Importance plot saved -> %s", path)


def plot_trial_progression(df: pd.DataFrame, output_dir: str) -> None:
    """Reward vs trial index with running best."""
    running_best = df["eval_reward"].expanding().max()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(
        df.index,
        df["eval_reward"],
        alpha=0.5,
        s=30,
        color=COLORS[0],
        label="Trial Reward",
    )
    ax.plot(df.index, running_best, color=COLORS[2], linewidth=2, label="Running Best")
    ax.axhline(
        df["eval_reward"].mean(),
        color="gray",
        linestyle="--",
        linewidth=0.8,
        label="Mean",
    )
    ax.set_xlabel("Trial")
    ax.set_ylabel("Eval Reward")
    ax.set_title("Random Search Trial Progression", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    path = os.path.join(output_dir, "trial_progression.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Trial progression plot saved -> %s", path)


# ---------------------------------------------------------------------------
# Validation backtest with the best config
# ---------------------------------------------------------------------------
def validate_best_config(
    best_config: Dict,
    data: pd.DataFrame,
    episodes: int = 20,
    max_steps: int = 252,
    output_dir: str = "tuning_output",
) -> Dict:
    """Run an extended backtest with the best discovered configuration."""
    logger.info("Validating best config with %d episodes...", episodes)
    env = TradingGymEnv(
        data_stream=data,
        window_size=10,
        transaction_cost=0.001,
        reward_scaling=1.0,
        max_steps=max_steps,
    )
    agent = DDPGAgent(env, config=best_config)
    agent.train(max_episodes=episodes, max_steps=max_steps)
    bt = BacktestEngine(env, agent)
    results = bt.run(episodes=1)
    m = results["metrics"]
    logger.info("Validation Metrics:")
    logger.info("  Total Return  : %+.2f%%", m["total_return"] * 100)
    logger.info("  Annual Return : %+.2f%%", m["annual_return"] * 100)
    logger.info("  Sharpe Ratio  :  %.3f", m["sharpe_ratio"])
    logger.info("  Volatility    :  %.2f%%", m["volatility"] * 100)
    logger.info("  Max Drawdown  : %.2f%%", m["max_drawdown"] * 100)
    return results


# ---------------------------------------------------------------------------
# Core workflow
# ---------------------------------------------------------------------------
def run(
    n_trials: int = 20,
    episodes_per_trial: int = 5,
    max_steps: int = 100,
    n_workers: int = 1,
    seed: int = 42,
    output_dir: str = "tuning_output",
    param_grid: Optional[Dict] = None,
) -> Tuple[Dict, pd.DataFrame]:
    os.makedirs(output_dir, exist_ok=True)
    grid = param_grid or DEFAULT_PARAM_GRID

    data = generate_market_data(n_assets=5, n_days=756, seed=seed)

    def make_env():
        return TradingGymEnv(
            data_stream=data.iloc[: int(len(data) * 0.75)],
            window_size=10,
            transaction_cost=0.001,
            reward_scaling=1.0,
            max_steps=max_steps,
        )

    tuner = HyperparameterTuner(
        env_creator=make_env,
        param_grid=grid,
        n_trials=n_trials,
        episodes_per_trial=episodes_per_trial,
        max_steps=max_steps,
        n_workers=n_workers,
        seed=seed,
    )
    best_config, all_results = tuner.run()

    df = build_results_df(all_results, grid)

    # Plots
    plot_trial_progression(df, output_dir)
    plot_sensitivity(df, grid, output_dir)
    try:
        importances = hyperparameter_importance(df, grid, seed)
        plot_importance(importances, output_dir)
        logger.info("Top 3 hyperparameters by importance:")
        for name, imp in importances.head(3).items():
            logger.info("  %-22s: %.4f", name, imp)
    except ImportError:
        logger.warning("scikit-learn not installed - skipping importance analysis.")

    # Validation backtest
    validate_best_config(
        best_config,
        data=data.iloc[int(len(data) * 0.75) :],
        episodes=20,
        max_steps=252,
        output_dir=output_dir,
    )

    # Export best config
    serializable = {}
    for k, v in best_config.items():
        serializable[k] = list(v) if isinstance(v, tuple) else v

    config_path = os.path.join(output_dir, "best_ddpg_config.json")
    with open(config_path, "w") as f:
        json.dump(serializable, f, indent=4)
    logger.info("Best config saved -> %s", config_path)

    return best_config, df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AlphaMind DDPG Hyperparameter Tuning")
    p.add_argument("--n-trials", type=int, default=20)
    p.add_argument("--episodes", type=int, default=5, dest="episodes_per_trial")
    p.add_argument("--max-steps", type=int, default=100)
    p.add_argument(
        "--n-workers",
        type=int,
        default=1,
        help="Parallel trial workers (default: 1 = sequential)",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="tuning_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("=" * 60)
    logger.info("AlphaMind - DDPG Hyperparameter Tuning")
    logger.info("=" * 60)
    best_config, results_df = run(
        n_trials=args.n_trials,
        episodes_per_trial=args.episodes_per_trial,
        max_steps=args.max_steps,
        n_workers=args.n_workers,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    logger.info("Tuning complete. Best config:")
    for k, v in best_config.items():
        logger.info("  %-25s: %s", k, v)
    logger.info("All outputs saved to: %s/", args.output_dir)
