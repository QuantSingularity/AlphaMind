"""
data_pipeline.py
-----------------
AlphaMind Examples | Data Engineering

Demonstrates the AlphaMind DataPipeline from
code/backend/data_processing/ including ingestion, transformation,
parallel processing, caching, and quality monitoring.

Usage
-----
    python data_pipeline.py
    python data_pipeline.py --symbols AAPL MSFT GOOGL --n-days 504
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("data_pipeline")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


# ---------------------------------------------------------------------------
# Data simulation
# ---------------------------------------------------------------------------
def simulate_ohlcv(symbol: str, n_days: int = 252, seed: int = 0) -> pd.DataFrame:
    r = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + r.normal(0.0005, 0.015, n_days))
    high = close * (1 + r.uniform(0.001, 0.020, n_days))
    low = close * (1 - r.uniform(0.001, 0.020, n_days))
    open_ = close * (1 + r.normal(0, 0.005, n_days))
    vol = r.lognormal(14, 0.5, n_days).astype(int)
    dates = pd.bdate_range("2023-01-02", periods=n_days)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=dates,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dataclass
class PipelineStage:
    name: str
    fn: Callable
    enabled: bool = True


class DataPipeline:
    def __init__(self):
        self.stages: List[PipelineStage] = []
        self.metrics: Dict[str, Dict[str, float]] = {}

    def add_stage(
        self, name: str, fn: Callable, enabled: bool = True
    ) -> "DataPipeline":
        self.stages.append(PipelineStage(name, fn, enabled))
        return self

    def run(self, df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
        result = df.copy()
        times = {}
        for stage in self.stages:
            if not stage.enabled:
                continue
            t0 = time.perf_counter()
            result = stage.fn(result)
            times[stage.name] = (time.perf_counter() - t0) * 1000
        self.metrics[symbol] = times
        return result


def _validate(df):
    return df.dropna()


def _split_adjust(df):
    return df  # placeholder


def _compute_returns(df):
    df["ret"] = df["close"].pct_change()
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    return df.dropna()


def _add_technicals(df):
    df["sma_10"] = df["close"].rolling(10).mean()
    df["sma_21"] = df["close"].rolling(21).mean()
    df["vol_21"] = df["ret"].rolling(21).std() * np.sqrt(252)
    delta = df["close"].diff()
    g = delta.clip(lower=0).rolling(14).mean()
    l = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - 100 / (1 + g / (l + 1e-8))
    df["atr"] = (
        pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift()).abs(),
                (df["low"] - df["close"].shift()).abs(),
            ],
            axis=1,
        )
        .max(axis=1)
        .rolling(14)
        .mean()
    )
    return df.dropna()


def _normalise(df):
    cols = ["sma_10", "sma_21", "vol_21", "rsi", "atr"]
    cols = [c for c in cols if c in df.columns]
    df[cols] = (df[cols] - df[cols].mean()) / (df[cols].std() + 1e-8)
    return df


def build_pipeline() -> DataPipeline:
    return (
        DataPipeline()
        .add_stage("validate", _validate)
        .add_stage("split_adjust", _split_adjust)
        .add_stage("returns", _compute_returns)
        .add_stage("technicals", _add_technicals)
        .add_stage("normalise", _normalise)
    )


# ---------------------------------------------------------------------------
# LRU Cache
# ---------------------------------------------------------------------------
class LRUCache:
    def __init__(self, maxsize: int = 128, ttl: float = 300.0):
        self._cache: Dict[str, Any] = {}
        self._times: Dict[str, float] = {}
        self._hits = self._misses = 0
        self.maxsize = maxsize
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and time.time() - self._times[key] < self.ttl:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.maxsize:
            oldest = min(self._times, key=self._times.get)
            del self._cache[oldest], self._times[oldest]
        self._cache[key] = value
        self._times[key] = time.time()

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total else 0.0


# ---------------------------------------------------------------------------
# Quality monitor
# ---------------------------------------------------------------------------
def quality_report(df: pd.DataFrame, symbol: str) -> dict:
    return {
        "Symbol": symbol,
        "Rows": len(df),
        "Missing (%)": df.isnull().mean().mean() * 100,
        "Neg Prices": (df["close"] < 0).sum() if "close" in df else 0,
        "Vol Spikes": (df["ret"].abs() > 0.10).sum() if "ret" in df else 0,
        "Start": str(df.index[0].date()),
        "End": str(df.index[-1].date()),
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_stage_latency(metrics: Dict, output_dir: str) -> None:
    df = pd.DataFrame(metrics).T
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    df.mean().plot.bar(ax=axes[0], color=COLORS[0], edgecolor="white")
    axes[0].set_title("Mean Stage Latency (ms)", fontweight="bold")
    axes[0].set_ylabel("ms")
    axes[0].tick_params(axis="x", rotation=30)
    df.sum(axis=1).sort_values().plot.barh(
        ax=axes[1], color=COLORS[2], edgecolor="white"
    )
    axes[1].set_title("Total Latency per Symbol (ms)", fontweight="bold")
    axes[1].set_xlabel("ms")
    plt.suptitle("Pipeline Performance", fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "pipeline_latency.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    symbols: List[str],
    n_days: int = 252,
    n_workers: int = 4,
    seed: int = 42,
    output_dir: str = "pipeline_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    pipeline = build_pipeline()
    raw = {s: simulate_ohlcv(s, n_days, seed + i) for i, s in enumerate(symbols)}

    # Sequential
    t0 = time.perf_counter()
    seq = {s: pipeline.run(raw[s], s) for s in symbols}
    t_seq = (time.perf_counter() - t0) * 1000

    # Parallel
    t0 = time.perf_counter()
    par: Dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futs = {pool.submit(pipeline.run, raw[s], s): s for s in symbols}
        for fut in as_completed(futs):
            par[futs[fut]] = fut.result()
    t_par = (time.perf_counter() - t0) * 1000

    logger.info(
        "Sequential: %.1f ms  |  Parallel (%d workers): %.1f ms  |  Speedup: %.2fx",
        t_seq,
        n_workers,
        t_par,
        t_seq / t_par,
    )

    # Quality report
    qr = pd.DataFrame([quality_report(seq[s], s) for s in symbols]).set_index("Symbol")
    logger.info("Quality report:\n%s", qr.to_string())

    plot_stage_latency(pipeline.metrics, output_dir)

    # Cache demo
    cache = LRUCache(maxsize=50, ttl=60)
    for s in symbols:
        cache.set(s, seq[s].tail(5).to_dict())
    for s in symbols:
        cache.get(s)
    logger.info("Cache hit rate: %.1f%%", cache.hit_rate * 100)
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind Data Pipeline Example")
    p.add_argument(
        "--symbols", nargs="+", default=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    )
    p.add_argument("--n-days", type=int, default=252)
    p.add_argument("--n-workers", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="pipeline_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Data Pipeline Example")
    run(args.symbols, args.n_days, args.n_workers, args.seed, args.output_dir)
