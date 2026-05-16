"""
ab_testing.py
--------------
AlphaMind Examples | Analytics

End-to-end strategy A/B testing using code/backend/analytics/ab_testing/.
Covers frequentist t-test, SPRT, Bayesian analysis, and multi-variant
comparison.

Usage
-----
    python ab_testing.py
    python ab_testing.py --n-obs 504 --alpha 0.05
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm, ttest_ind

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("ab_testing")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


def required_sample_size(
    effect: float, alpha: float = 0.05, power: float = 0.80, sigma: float = 0.01
) -> int:
    za = norm.ppf(1 - alpha / 2)
    zb = norm.ppf(power)
    return int(np.ceil(((za + zb) * sigma / effect) ** 2))


def sprt(
    diffs: np.ndarray,
    h0_mean: float,
    h1_mean: float,
    sigma: float,
    alpha: float = 0.05,
    beta: float = 0.20,
) -> List[dict]:
    A = np.log((1 - beta) / alpha)
    B = np.log(beta / (1 - alpha))
    llr = 0.0
    out = []
    for x in diffs:
        llr += x * (h1_mean - h0_mean) / sigma**2 - (h1_mean**2 - h0_mean**2) / (
            2 * sigma**2
        )
        dec = "accept_H1" if llr >= A else "accept_H0" if llr <= B else "continue"
        out.append({"llr": llr, "decision": dec})
    return out


def bayesian_update(
    diffs: np.ndarray, prior_mu: float = 0.0, prior_sigma: float = 0.005
) -> dict:
    n = len(diffs)
    sig = diffs.std()
    post_var = 1 / (1 / prior_sigma**2 + n / sig**2)
    post_mu = post_var * (prior_mu / prior_sigma**2 + diffs.mean() * n / sig**2)
    post_sig = np.sqrt(post_var)
    prob = 1 - norm.cdf(0, post_mu, post_sig)
    return {"post_mu": post_mu, "post_sigma": post_sig, "prob_better": prob}


def plot_results(
    ctrl: np.ndarray,
    trt: np.ndarray,
    sprt_log: List[dict],
    bay: dict,
    alpha: float,
    output_dir: str,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Distribution comparison
    axes[0].hist(
        ctrl * 100, bins=50, density=True, alpha=0.6, color=COLORS[0], label="Control"
    )
    axes[0].hist(
        trt * 100, bins=50, density=True, alpha=0.6, color=COLORS[1], label="Treatment"
    )
    axes[0].set_title("Daily Return Distributions", fontweight="bold")
    axes[0].set_xlabel("Daily Return (%)")
    axes[0].legend()

    # SPRT
    llrs = [s["llr"] for s in sprt_log]
    A = np.log(0.80 / alpha)
    B = np.log(0.20 / (1 - alpha))
    axes[1].plot(llrs, color=COLORS[0], linewidth=1.5)
    axes[1].axhline(
        A, color=COLORS[2], linestyle="--", linewidth=1.2, label=f"H1 ({A:.2f})"
    )
    axes[1].axhline(
        B, color=COLORS[1], linestyle="--", linewidth=1.2, label=f"H0 ({B:.2f})"
    )
    axes[1].set_title("SPRT Log-Likelihood Ratio", fontweight="bold")
    axes[1].set_xlabel("Observation")
    axes[1].set_ylabel("LLR")
    axes[1].legend()

    # Bayesian posterior
    x = np.linspace(-0.002, 0.002, 500)
    mu, sig = bay["post_mu"], bay["post_sigma"]
    axes[2].plot(
        x * 252,
        norm.pdf(x, mu, sig),
        color=COLORS[0],
        linewidth=2.5,
        label=f"P(trt>ctrl)={bay['prob_better']:.1%}",
    )
    axes[2].axvline(0, color="black", linestyle=":", linewidth=0.8)
    axes[2].fill_between(
        x * 252, norm.pdf(x, mu, sig), where=x > 0, alpha=0.2, color=COLORS[2]
    )
    axes[2].set_title("Bayesian Posterior on Return Diff (Ann.)", fontweight="bold")
    axes[2].set_xlabel("Annual Return Difference")
    axes[2].legend()

    plt.suptitle("A/B Test Results Dashboard", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "ab_test_results.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def run(
    n_obs: int = 252,
    alpha: float = 0.05,
    true_effect: float = 0.003,
    seed: int = 42,
    output_dir: str = "ab_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    ctrl = rng.normal(0.0004, 0.010, n_obs)
    trt = rng.normal(0.0004 + true_effect / 252, 0.010, n_obs)

    # Required sample size
    n_req = required_sample_size(0.002, alpha)
    logger.info("Required sample size (effect=0.002): %d observations", n_req)

    # Frequentist
    t_stat, p_val = ttest_ind(trt, ctrl)
    reject = p_val < alpha
    pooled = np.sqrt((ctrl.var() + trt.var()) / 2)
    cohens_d = (trt.mean() - ctrl.mean()) / pooled
    logger.info(
        "t-stat=%.4f  p=%.4f  Significant=%s  Cohen d=%.4f",
        t_stat,
        p_val,
        reject,
        cohens_d,
    )

    # SPRT
    sprt_log = sprt(trt - ctrl, 0.0, true_effect / 252, ctrl.std(), alpha)
    first_dec = next(
        (i for i, s in enumerate(sprt_log) if s["decision"] != "continue"), None
    )
    if first_dec:
        logger.info(
            "SPRT early decision at obs %d: %s",
            first_dec,
            sprt_log[first_dec]["decision"],
        )

    # Bayesian
    bay = bayesian_update(trt - ctrl)
    logger.info("P(Treatment > Control) = %.1f%%", bay["prob_better"] * 100)
    logger.info(
        "Posterior mean diff = %.5f (ann. %.4f)", bay["post_mu"], bay["post_mu"] * 252
    )

    plot_results(ctrl, trt, sprt_log, bay, alpha, output_dir)

    # Multi-variant
    variants: Dict[str, np.ndarray] = {
        "Momentum": rng.normal(0.0004, 0.010, n_obs),
        "Mom+Sent": rng.normal(0.0007, 0.010, n_obs),
        "Value+Qual": rng.normal(0.0005, 0.009, n_obs),
        "Ensemble": rng.normal(0.0009, 0.008, n_obs),
    }
    logger.info("Multi-variant Sharpe comparison:")
    for name, r in variants.items():
        sr = r.mean() / r.std() * np.sqrt(252)
        logger.info("  %-12s: Sharpe=%.3f", name, sr)
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind A/B Testing Example")
    p.add_argument("--n-obs", type=int, default=252)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--true-effect", type=float, default=0.003)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="ab_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - A/B Testing Example")
    run(args.n_obs, args.alpha, args.true_effect, args.seed, args.output_dir)
