"""
generative_finance.py
----------------------
AlphaMind Examples | Deep Learning

Demonstrates FinancialTimeSeriesGAN and RegimeClassifier from
code/ai_models/generative_finance.py.

Usage
-----
    python generative_finance.py
    python generative_finance.py --n 3000 --epochs 50
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("generative_finance")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


# ---------------------------------------------------------------------------
# Real data simulation
# ---------------------------------------------------------------------------
def simulate_real_data(n: int = 2000, seed: int = 42) -> np.ndarray:
    np.random.default_rng(seed)
    raw = stats.t.rvs(df=5, scale=0.012, size=n, random_state=seed)
    sigma2 = np.zeros(n)
    sigma2[0] = 0.012**2
    for t in range(1, n):
        sigma2[t] = 1e-5 + 0.08 * raw[t - 1] ** 2 + 0.90 * sigma2[t - 1]
    return (raw * np.sqrt(sigma2) / 0.012).astype(np.float32)


# ---------------------------------------------------------------------------
# NumPy GAN stub
# ---------------------------------------------------------------------------
class FinancialGAN:
    """
    Simplified GAN for synthetic financial return generation.
    Replace with FinancialTimeSeriesGAN when TensorFlow is available.
    """

    def __init__(self, latent_dim: int = 32, seq_len: int = 50, seed: int = 42):
        self.latent_dim = latent_dim
        self.seq_len = seq_len
        self._rng = np.random.default_rng(seed)
        self._g_weights = self._rng.standard_normal((latent_dim, seq_len)) * 0.1

    def train(
        self, real_data: np.ndarray, epochs: int = 30, batch: int = 64
    ) -> Tuple[list, list]:
        n = len(real_data)
        g_losses, d_losses = [], []
        for epoch in range(epochs):
            idx = self._rng.integers(0, n - self.seq_len, batch)
            real = np.stack([real_data[i : i + self.seq_len] for i in idx])
            noise = self._rng.standard_normal((batch, self.latent_dim))
            fake = noise @ self._g_weights

            # Discriminator: mean output should converge to 0.5
            d_real = 1 / (1 + np.exp(-real.mean(axis=1)))
            d_fake = 1 / (1 + np.exp(-fake.mean(axis=1)))
            d_loss = -(np.log(d_real + 1e-8).mean() + np.log(1 - d_fake + 1e-8).mean())

            # Generator gradient nudge
            g_grad = -fake.mean(axis=0)
            self._g_weights -= 2e-3 * np.outer(noise.mean(axis=0), g_grad)

            g_loss = -np.log(d_fake + 1e-8).mean()
            g_losses.append(float(g_loss))
            d_losses.append(float(d_loss))

            if (epoch + 1) % max(1, epochs // 5) == 0:
                logger.info(
                    "  Epoch %3d/%d  G=%.4f  D=%.4f", epoch + 1, epochs, g_loss, d_loss
                )
        return g_losses, d_losses

    def generate(self, n_samples: int = 500) -> np.ndarray:
        noise = self._rng.standard_normal((n_samples, self.latent_dim))
        return (noise @ self._g_weights).astype(np.float32)


# ---------------------------------------------------------------------------
# Stylised facts
# ---------------------------------------------------------------------------
def stylised_facts(ret: np.ndarray, label: str) -> dict:
    r = pd.Series(ret)
    return {
        "Label": label,
        "Mean": ret.mean(),
        "Std": ret.std(),
        "Skewness": stats.skew(ret),
        "Excess Kurt": stats.kurtosis(ret),
        "Autocorr(1)": r.autocorr(1),
        "Abs AC(1)": np.abs(r).autocorr(1),
        "% Positive": (ret > 0).mean(),
    }


# ---------------------------------------------------------------------------
# Regime classifier
# ---------------------------------------------------------------------------
def classify_regimes(ret: np.ndarray, window: int = 21) -> np.ndarray:
    r = pd.Series(ret)
    r.rolling(window).std().fillna(r.std())
    trend = r.rolling(window).mean().fillna(0)
    labels = np.where(trend > 0.0005, 0, np.where(trend < -0.0005, 2, 1))
    return labels


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_gan_loss(g_losses, d_losses, output_dir):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(g_losses, color=COLORS[0], linewidth=2, label="Generator Loss")
    ax.plot(d_losses, color=COLORS[1], linewidth=2, label="Discriminator Loss")
    ax.set_title("GAN Training Loss", fontsize=12, fontweight="bold")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.legend()
    fig.savefig(os.path.join(output_dir, "gan_loss.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_distribution(real, fake, output_dir):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(
        real * 100, bins=70, density=True, alpha=0.6, color=COLORS[0], label="Real"
    )
    axes[0].hist(
        fake.ravel() * 100,
        bins=70,
        density=True,
        alpha=0.6,
        color=COLORS[1],
        label="Synthetic",
    )
    axes[0].set_title("Return Distribution", fontweight="bold")
    axes[0].legend()
    qs = np.linspace(0.01, 0.99, 100)
    axes[1].scatter(
        np.quantile(real, qs),
        np.quantile(fake.ravel(), qs),
        s=15,
        alpha=0.7,
        color=COLORS[2],
    )
    lims = [
        min(np.quantile(real, 0.01), np.quantile(fake.ravel(), 0.01)),
        max(np.quantile(real, 0.99), np.quantile(fake.ravel(), 0.99)),
    ]
    axes[1].plot(lims, lims, "k--", linewidth=0.8)
    axes[1].set_title("QQ Plot (Real vs Synthetic)", fontweight="bold")
    axes[1].set_xlabel("Real Quantile")
    axes[1].set_ylabel("Synthetic Quantile")
    plt.suptitle("Synthetic Data Quality Validation", fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "gan_distribution.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    n: int = 2000,
    seq_len: int = 50,
    latent_dim: int = 32,
    epochs: int = 30,
    seed: int = 42,
    output_dir: str = "gan_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    real = simulate_real_data(n, seed)
    gan = FinancialGAN(latent_dim=latent_dim, seq_len=seq_len, seed=seed)
    g_losses, d_losses = gan.train(real, epochs=epochs)
    plot_gan_loss(g_losses, d_losses, output_dir)

    fake = gan.generate(500)
    fake_flat = fake.ravel()
    plot_distribution(real, fake, output_dir)

    ks, pval = ks_2samp(real, fake_flat)
    logger.info("KS test: statistic=%.4f  p-value=%.4f", ks, pval)

    sf = pd.DataFrame(
        [stylised_facts(real, "Real"), stylised_facts(fake_flat, "Synthetic")]
    ).set_index("Label")
    logger.info("Stylised facts comparison:\n%s", sf.to_string())

    regimes = classify_regimes(real)
    for r, lbl in {0: "Bull", 1: "Neutral", 2: "Bear"}.items():
        pct = (regimes == r).mean()
        logger.info("  Regime %-8s: %.1f%%", lbl, pct * 100)
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind Generative Finance Example")
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--seq-len", type=int, default=50)
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="gan_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Generative Finance Example")
    run(args.n, args.seq_len, args.latent_dim, args.epochs, args.seed, args.output_dir)
