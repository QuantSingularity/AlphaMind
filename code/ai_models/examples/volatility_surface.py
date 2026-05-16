"""
volatility_surface.py
----------------------
AlphaMind Examples | Derivatives / Infrastructure

Demonstrates implied volatility surface construction, SVI calibration,
arbitrage checks, and Greeks computation from
code/backend/infrastructure/pricing/volatility_surface.py.

Usage
-----
    python volatility_surface.py
    python volatility_surface.py --spot 4500 --r 0.05
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import minimize
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("volatility_surface")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


# ---------------------------------------------------------------------------
# SVI parametrisation
# ---------------------------------------------------------------------------
def svi_total_var(k, a, b, rho, m, sigma):
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma**2))


def fit_svi(k_arr, iv_arr, T):
    w_mkt = iv_arr**2 * T

    def obj(p):
        a, b, rho, m, sig = p
        if b < 0 or sig <= 0 or abs(rho) >= 1:
            return 1e9
        return np.sum((svi_total_var(k_arr, a, b, rho, m, sig) - w_mkt) ** 2)

    res = minimize(
        obj,
        [0.04, 0.1, -0.3, 0.0, 0.2],
        method="L-BFGS-B",
        bounds=[(0, None), (0.001, None), (-0.999, 0.999), (None, None), (0.001, None)],
    )
    return res.x


# ---------------------------------------------------------------------------
# Black-Scholes Greeks
# ---------------------------------------------------------------------------
def bs_greeks(S, K, T, r, q, sigma):
    if T <= 0 or sigma <= 0:
        return {}
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return {
        "delta": np.exp(-q * T) * norm.cdf(d1),
        "gamma": np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T)),
        "vega": S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100,
        "theta": (
            -(S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T)))
            - r * K * np.exp(-r * T) * norm.cdf(d2)
            + q * S * np.exp(-q * T) * norm.cdf(d1)
        )
        / 365,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_smile(EXPIRIES, STRIKES, vol_matrix, svi_params, output_dir):
    k_arr = np.log(STRIKES)
    k_fine = np.linspace(k_arr.min(), k_arr.max(), 200)
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharex=True, sharey=True)
    for ax, T_days in zip(axes.ravel(), EXPIRIES):
        T = T_days / 365
        idx = list(EXPIRIES).index(T_days)
        p = svi_params[T_days]
        iv_fit = np.sqrt(np.maximum(svi_total_var(k_fine, *p) / T, 0))
        ax.scatter(k_arr, vol_matrix[idx] * 100, s=30, color=COLORS[1], zorder=5)
        ax.plot(k_fine, iv_fit * 100, color=COLORS[0], linewidth=2)
        ax.set_title(f"T={T_days}d", fontsize=9, fontweight="bold")
        ax.set_xlabel("Log-moneyness")
    plt.suptitle("SVI Fit to Implied Volatility Smile", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "vol_smile.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_surface(spline, EXPIRIES, STRIKES, output_dir):
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    T_fine = np.linspace(min(EXPIRIES) / 365, max(EXPIRIES) / 365, 60)
    K_fine = np.linspace(STRIKES.min(), STRIKES.max(), 60)
    IV_fine = spline(T_fine, K_fine)
    TT, KK = np.meshgrid(K_fine, T_fine)
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(
        KK, TT * 365, IV_fine * 100, cmap="RdYlGn_r", alpha=0.85, edgecolor="none"
    )
    ax.set_xlabel("Strike/Spot")
    ax.set_ylabel("Days to Expiry")
    ax.set_zlabel("IV (%)")
    ax.set_title("Implied Volatility Surface", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "vol_surface.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def plot_term_structure(EXPIRIES, atm_ivs, output_dir):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(
        EXPIRIES,
        np.array(atm_ivs) * 100,
        "o-",
        color=COLORS[0],
        linewidth=2,
        markersize=8,
    )
    ax.set_title(
        "ATM Implied Volatility Term Structure", fontsize=12, fontweight="bold"
    )
    ax.set_xlabel("Days to Expiry")
    ax.set_ylabel("ATM IV (%)")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "term_structure.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(
    spot: float = 4500.0,
    r: float = 0.05,
    q: float = 0.015,
    seed: int = 42,
    output_dir: str = "vol_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    EXPIRIES = [7, 14, 30, 60, 90, 180, 270, 365]
    STRIKES = np.array(
        [
            0.70,
            0.75,
            0.80,
            0.85,
            0.90,
            0.92,
            0.95,
            0.97,
            1.00,
            1.03,
            1.05,
            1.08,
            1.10,
            1.15,
            1.20,
        ]
    )
    ATM_VOLS = {
        7: 0.28,
        14: 0.24,
        30: 0.21,
        60: 0.19,
        90: 0.18,
        180: 0.17,
        270: 0.165,
        365: 0.160,
    }

    def vol_smile(K_S, T, atm):
        m = np.log(K_S)
        return np.clip(
            atm * (1 - 0.30 * m + 0.50 * m**2) + 0.02 * np.exp(-T * 2), 0.05, 0.90
        )

    vol_matrix = np.zeros((len(EXPIRIES), len(STRIKES)))
    for i, T_days in enumerate(EXPIRIES):
        T = T_days / 365
        for j, K in enumerate(STRIKES):
            vol_matrix[i, j] = vol_smile(K, T, ATM_VOLS[T_days])
    vol_matrix = np.clip(
        vol_matrix + rng.normal(0, 0.003, vol_matrix.shape), 0.05, 0.95
    )

    # SVI calibration
    k_arr = np.log(STRIKES)
    svi_params = {}
    for i, T_days in enumerate(EXPIRIES):
        svi_params[T_days] = fit_svi(k_arr, vol_matrix[i], T_days / 365)
        logger.info(
            "SVI T=%3dd: a=%.4f b=%.4f rho=%.4f m=%.4f sig=%.4f",
            T_days,
            *svi_params[T_days],
        )

    plot_smile(EXPIRIES, STRIKES, vol_matrix, svi_params, output_dir)

    # Spline surface
    T_arr = np.array(EXPIRIES) / 365
    spline = RectBivariateSpline(T_arr, STRIKES, vol_matrix, kx=3, ky=3)
    plot_surface(spline, EXPIRIES, STRIKES, output_dir)

    # Term structure
    atm_ivs = [float(spline(T / 365, 1.0)) for T in EXPIRIES]
    plot_term_structure(EXPIRIES, atm_ivs, output_dir)

    # Arbitrage check
    logger.info("Calendar spread arbitrage check (ATM total variance):")
    prev_w = 0.0
    ok = True
    for T_days, iv in zip(EXPIRIES, atm_ivs):
        T = T_days / 365
        w = iv**2 * T
        if w < prev_w - 1e-4:
            logger.warning("  BREACH at T=%dd: w=%.5f < prev=%.5f", T_days, w, prev_w)
            ok = False
        prev_w = w
    if ok:
        logger.info("  All expiries pass (no calendar spread arbitrage).")

    # Sample Greeks
    logger.info("Sample Greeks (ATM, T=30d):")
    g = bs_greeks(spot, spot, 30 / 365, r, q, float(spline(30 / 365, 1.0)))
    for name, val in g.items():
        logger.info("  %-8s: %.6f", name, val)

    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind Volatility Surface Example")
    p.add_argument("--spot", type=float, default=4500.0)
    p.add_argument("--r", type=float, default=0.05)
    p.add_argument("--q", type=float, default=0.015)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="vol_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Volatility Surface Example")
    run(args.spot, args.r, args.q, args.seed, args.output_dir)
