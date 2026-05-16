"""
attention_mechanism.py
-----------------------
AlphaMind Examples | Deep Learning

Demonstrates MultiHeadAttention and TemporalAttentionBlock from
code/ai_models/attention_mechanism.py applied to financial time series.

Usage
-----
    python attention_mechanism.py
    python attention_mechanism.py --d-model 128 --n-heads 8
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("attention_mechanism")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


# ---------------------------------------------------------------------------
# Pure-NumPy attention primitives
# ---------------------------------------------------------------------------
def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    e = np.exp(x - x.max(axis=axis, keepdims=True))
    return e / (e.sum(axis=axis, keepdims=True) + 1e-8)


def scaled_dot_product_attention(Q, K, V, mask=None):
    d_k = Q.shape[-1]
    scores = Q @ K.swapaxes(-2, -1) / np.sqrt(d_k)
    if mask is not None:
        scores += (1.0 - mask) * -1e9
    weights = softmax(scores)
    return weights @ V, weights


def positional_encoding(seq_len: int, d_model: int) -> np.ndarray:
    pe = np.zeros((seq_len, d_model))
    pos = np.arange(seq_len)[:, None]
    dim = np.arange(d_model)[None, :]
    ang = pos / np.power(10000.0, (2 * (dim // 2)) / d_model)
    pe[:, 0::2] = np.sin(ang[:, 0::2])
    pe[:, 1::2] = np.cos(ang[:, 1::2])
    return pe


class MultiHeadAttention:
    """Pure-NumPy multi-head attention matching the AlphaMind interface."""

    def __init__(self, d_model: int, num_heads: int, seed: int = 42):
        assert d_model % num_heads == 0
        r = np.random.default_rng(seed)
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        self.d_model = d_model
        s = 0.02
        self.Wq = r.standard_normal((d_model, d_model)) * s
        self.Wk = r.standard_normal((d_model, d_model)) * s
        self.Wv = r.standard_normal((d_model, d_model)) * s
        self.Wo = r.standard_normal((d_model, d_model)) * s

    def forward(self, x: np.ndarray) -> tuple:
        B, T, D = x.shape
        Q = x @ self.Wq
        K = x @ self.Wk
        V = x @ self.Wv

        def split(m):
            return m.reshape(B, T, self.num_heads, self.d_k).transpose(0, 2, 1, 3)

        out, w = scaled_dot_product_attention(split(Q), split(K), split(V))
        # Merge heads
        out = out.transpose(0, 2, 1, 3).reshape(B, T, self.d_model)
        return out @ self.Wo, w


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_attention_heads(attn_weights: np.ndarray, output_dir: str) -> None:
    n_heads = attn_weights.shape[1]
    fig, axes = plt.subplots(2, n_heads // 2, figsize=(14, 7))
    for ax, hi in zip(axes.ravel(), range(n_heads)):
        sns.heatmap(
            attn_weights[0, hi],
            cmap="Blues",
            ax=ax,
            cbar=False,
            xticklabels=False,
            yticklabels=False,
        )
        ax.set_title(f"Head {hi+1}", fontsize=9, fontweight="bold")
        ax.set_xlabel("Key")
        ax.set_ylabel("Query")
    plt.suptitle("Multi-Head Self-Attention Weights", fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "attention_heads.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def plot_positional_encoding(pe: np.ndarray, output_dir: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    im = axes[0].imshow(pe, aspect="auto", cmap="RdBu", vmin=-1, vmax=1)
    axes[0].set_title("Positional Encoding Matrix", fontweight="bold")
    axes[0].set_xlabel("Dimension")
    axes[0].set_ylabel("Position")
    fig.colorbar(im, ax=axes[0], fraction=0.04)
    for i, color in enumerate(COLORS[:4]):
        axes[1].plot(pe[:, i * 8], linewidth=1.5, label=f"dim={i*8}", color=color)
    axes[1].set_title("Encoding Values by Dimension", fontweight="bold")
    axes[1].set_xlabel("Sequence Position")
    axes[1].legend()
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "positional_encoding.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_temporal_attention(mean_attn: np.ndarray, output_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.bar(
        range(len(mean_attn)), mean_attn, color=COLORS[0], alpha=0.8, edgecolor="none"
    )
    ax.set_title(
        "Mean Attention by Sequence Position (All Heads)",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_xlabel("Sequence Position (0=oldest, right=most recent)")
    ax.set_ylabel("Mean Attention Weight")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "temporal_attention.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Latency benchmark
# ---------------------------------------------------------------------------
def benchmark_inference(
    d_model: int, num_heads: int, batch_sizes: list, seq_len: int = 60
) -> pd.DataFrame:
    mha = MultiHeadAttention(d_model, num_heads)
    rows = []
    for bs in batch_sizes:
        x = np.random.randn(bs, seq_len, d_model).astype(np.float32)
        mha.forward(x)  # warm-up
        t0 = time.perf_counter()
        for _ in range(10):
            mha.forward(x)
        ms = (time.perf_counter() - t0) / 10 * 1000
        rows.append(
            {"batch_size": bs, "latency_ms": ms, "us_per_sample": ms / bs * 1000}
        )
        logger.info("  batch=%4d  %.2f ms  (%.1f us/sample)", bs, ms, ms / bs * 1000)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    d_model: int = 64,
    num_heads: int = 4,
    seq_len: int = 60,
    seed: int = 42,
    output_dir: str = "attention_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    mha = MultiHeadAttention(d_model, num_heads, seed)
    x_in = rng.standard_normal((1, seq_len, d_model)).astype(np.float32)
    _, attn_w = mha.forward(x_in)
    plot_attention_heads(attn_w, output_dir)

    pe = positional_encoding(seq_len, d_model)
    plot_positional_encoding(pe, output_dir)

    # Simulate temporal attention with recency bias
    attn_sim = rng.dirichlet(np.ones(seq_len), size=(10, num_heads, seq_len))
    attn_sim[:, :, -10:] *= 3.0
    attn_sim /= attn_sim.sum(axis=-1, keepdims=True)
    mean_attn = attn_sim.mean(axis=(0, 1))
    plot_temporal_attention(mean_attn, output_dir)

    logger.info("Running inference latency benchmark...")
    bm = benchmark_inference(d_model, num_heads, [1, 8, 32, 64, 128], seq_len)
    logger.info("Benchmark results:\n%s", bm.to_string(index=False))
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind Attention Mechanism Example")
    p.add_argument("--d-model", type=int, default=64)
    p.add_argument("--n-heads", type=int, default=4)
    p.add_argument("--seq-len", type=int, default=60)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="attention_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Attention Mechanism Example")
    run(args.d_model, args.n_heads, args.seq_len, args.seed, args.output_dir)
