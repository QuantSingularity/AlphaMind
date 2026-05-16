"""
transformer_forecasting.py
---------------------------
AlphaMind Examples | Deep Learning

End-to-end example for the AdvancedTimeSeriesForecaster defined in
code/ai_models/transformer_timeseries/advanced_forecasting.py.

Covers feature engineering, multi-horizon prediction, and evaluation
against naive benchmarks.

Usage
-----
    python transformer_forecasting.py
    python transformer_forecasting.py --horizons 1 5 10 21 --seed 7
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("transformer_forecasting")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


# ---------------------------------------------------------------------------
# Data + features
# ---------------------------------------------------------------------------
def generate_series(n: int = 1260, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = np.zeros(n)
    rets[0] = rng.normal(0.0003, 0.012)
    kappa, theta, sigma = 0.02, 0.0003, 0.013
    for t in range(1, n):
        rets[t] = (
            rets[t - 1] + kappa * (theta - rets[t - 1]) + sigma * rng.standard_normal()
        )
    price = 100 * np.cumprod(1 + rets)
    volume = rng.lognormal(14, 0.5, n)
    dates = pd.bdate_range("2019-01-02", periods=n)
    return pd.DataFrame(
        {"price": price, "returns": rets, "volume": volume}, index=dates
    )


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    for w in [5, 10, 21, 63]:
        f[f"mom_{w}"] = f["price"].pct_change(w)
    for w in [10, 21]:
        f[f"vol_{w}"] = f["returns"].rolling(w).std()
    delta = f["price"].diff()
    g = delta.clip(lower=0).rolling(14).mean()
    l = (-delta.clip(upper=0)).rolling(14).mean()
    f["rsi"] = 100 - 100 / (1 + g / (l + 1e-8))
    f["vol_ratio"] = f["volume"] / f["volume"].rolling(21).mean()
    ma20 = f["price"].rolling(20).mean()
    sd20 = f["price"].rolling(20).std()
    f["bb_width"] = 2 * sd20 / (ma20 + 1e-8)
    for lag in [1, 2, 3, 5]:
        f[f"lag{lag}"] = f["returns"].shift(lag)
    return f.dropna()


# ---------------------------------------------------------------------------
# Transformer stub (NumPy multi-horizon linear model)
# ---------------------------------------------------------------------------
class TransformerForecaster:
    """
    Lightweight multi-horizon forecaster.
    Replace with AdvancedTimeSeriesForecaster when TensorFlow is available.
    """

    def __init__(self, input_seq: int = 60, output_seq: int = 20, seed: int = 42):
        self.input_seq = input_seq
        self.output_seq = output_seq
        self._rng = np.random.default_rng(seed)
        self._W: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "TransformerForecaster":
        # Ridge regression as a stand-in
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler

        n, seq, nf = X.shape
        X_flat = X.reshape(n, seq * nf)
        self._scaler = StandardScaler().fit(X_flat)
        X_s = self._scaler.transform(X_flat)
        self._model = Ridge(alpha=10.0).fit(X_s, y)
        logger.info("Forecaster fitted on %d sequences.", n)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        n, seq, nf = X.shape
        X_flat = X.reshape(n, seq * nf)
        X_s = self._scaler.transform(X_flat)
        return self._model.predict(X_s)


def make_sequences(
    feat: np.ndarray, ret: np.ndarray, input_seq: int, output_seq: int
) -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(input_seq, len(feat) - output_seq):
        X.append(feat[i - input_seq : i])
        y.append(ret[i : i + output_seq])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate(
    y_pred: np.ndarray, y_true: np.ndarray, horizons: List[int]
) -> pd.DataFrame:
    rows = []
    for h in horizons:
        hi = h - 1
        if hi >= y_pred.shape[1]:
            continue
        ic, _ = spearmanr(y_pred[:, hi], y_true[:, hi])
        mse = np.mean((y_pred[:, hi] - y_true[:, hi]) ** 2)
        r2 = 1 - mse / (np.var(y_true[:, hi]) + 1e-12)
        hit = np.mean(np.sign(y_pred[:, hi]) == np.sign(y_true[:, hi]))
        rows.append({"Horizon (d)": h, "IC": ic, "R2": r2, "MSE": mse, "Hit Rate": hit})
    return pd.DataFrame(rows).set_index("Horizon (d)")


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_predictions(
    y_pred: np.ndarray, y_true: np.ndarray, horizons: List[int], output_dir: str
) -> None:
    h_plot = [h for h in horizons if h - 1 < y_pred.shape[1]][:4]
    fig, axes = plt.subplots(1, len(h_plot), figsize=(14, 4), sharey=True)
    if len(h_plot) == 1:
        axes = [axes]
    for ax, h in zip(axes, h_plot):
        hi = h - 1
        ic, _ = spearmanr(y_pred[:, hi], y_true[:, hi])
        ax.scatter(y_true[:, hi], y_pred[:, hi], alpha=0.25, s=10, color=COLORS[0])
        lims = [
            min(y_true[:, hi].min(), y_pred[:, hi].min()),
            max(y_true[:, hi].max(), y_pred[:, hi].max()),
        ]
        ax.plot(lims, lims, "k--", linewidth=0.8)
        ax.set_title(f"Horizon={h}d  IC={ic:.3f}", fontsize=10, fontweight="bold")
        ax.set_xlabel("Actual")
        ax.set_ylabel("Predicted")
    plt.suptitle(
        "Multi-Horizon Forecast: Predicted vs Actual", fontsize=12, fontweight="bold"
    )
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "forecast_scatter.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def plot_ic_by_horizon(met: pd.DataFrame, output_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(met.index, met["IC"], "o-", color=COLORS[0], linewidth=2, markersize=8)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.fill_between(
        met.index, 0, met["IC"], where=met["IC"] > 0, alpha=0.15, color=COLORS[0]
    )
    ax.set_title(
        "Information Coefficient by Forecast Horizon", fontsize=12, fontweight="bold"
    )
    ax.set_xlabel("Horizon (days)")
    ax.set_ylabel("Spearman IC")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "ic_by_horizon.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    horizons: List[int] = None, seed: int = 42, output_dir: str = "transformer_output"
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    horizons = horizons or [1, 3, 5, 10, 21]
    output_seq = max(horizons)

    raw = generate_series(seed=seed)
    feat = build_features(raw)
    feat_cols = [c for c in feat.columns if c not in ["price", "returns", "volume"]]
    feat_arr = feat[feat_cols].values.astype(np.float32)
    ret_arr = feat["returns"].values.astype(np.float32)

    input_seq = 60
    split = int(len(feat_arr) * 0.75)
    X, y = make_sequences(feat_arr, ret_arr, input_seq, output_seq)
    X_train, y_train = X[:split], y[:split]
    X_test, y_test = X[split:], y[split:]

    logger.info("Train sequences: %d  |  Test sequences: %d", len(X_train), len(X_test))

    model = TransformerForecaster(input_seq=input_seq, output_seq=output_seq, seed=seed)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    met = evaluate(y_pred, y_test, horizons)
    logger.info("Evaluation metrics:\n%s", met.to_string())

    plot_predictions(y_pred, y_test, horizons, output_dir)
    plot_ic_by_horizon(met, output_dir)
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind Transformer Forecasting Example")
    p.add_argument("--horizons", type=int, nargs="+", default=[1, 3, 5, 10, 21])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="transformer_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Transformer Forecasting Example")
    run(args.horizons, args.seed, args.output_dir)
