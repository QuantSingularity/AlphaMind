"""
risk_controls.py
-----------------
AlphaMind Examples | Risk Management

Demonstrates pre-trade and real-time risk controls from
code/backend/risk/controls/risk_controls.py.

Usage
-----
    python risk_controls.py
    python risk_controls.py --nav 50000000 --max-dd 0.08
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("risk_controls")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


@dataclass
class RiskLimits:
    max_single_pos: float = 0.10
    max_gross_exp: float = 1.50
    max_net_exp: float = 0.80
    max_sector_exp: float = 0.35
    max_drawdown: float = 0.12
    daily_loss_limit: float = 0.03
    max_liq_days: float = 10.0


class RiskStatus(Enum):
    PASS = "PASS"
    WARN = "WARN"
    REJECT = "REJECT"


@dataclass
class RiskCheck:
    name: str
    status: RiskStatus
    current: float
    limit: float
    message: str = ""


class DrawdownBreaker:
    def __init__(self, max_dd: float, cooldown: int = 45):
        self.max_dd = max_dd
        self.cooldown = cooldown
        self.halted = False
        self._halt_t: Optional[int] = None
        self.events: List[dict] = []

    def check(self, nav: float, peak: float, t: int) -> bool:
        dd = nav / peak - 1
        if dd < -self.max_dd and not self.halted:
            self.halted = True
            self._halt_t = t
            self.events.append({"t": t, "event": "HALT", "dd": dd})
        elif (
            self.halted
            and self._halt_t is not None
            and t - self._halt_t >= self.cooldown
            and dd > -self.max_dd * 0.5
        ):
            self.halted = False
            self.events.append({"t": t, "event": "RESUME", "dd": dd})
        return not self.halted


def pre_trade_checks(
    portfolio: pd.DataFrame,
    limits: RiskLimits,
    symbol: str,
    delta_weight: float,
    nav: float,
) -> List[RiskCheck]:
    checks = []
    cur_w = portfolio.set_index("Symbol")["Weight"].to_dict().get(symbol, 0.0)
    new_w = cur_w + delta_weight

    st = RiskStatus.PASS if new_w <= limits.max_single_pos else RiskStatus.REJECT
    checks.append(RiskCheck("Single Position", st, new_w, limits.max_single_pos))

    gross = portfolio["Weight"].abs().sum() + abs(delta_weight)
    st = RiskStatus.PASS if gross <= limits.max_gross_exp else RiskStatus.REJECT
    checks.append(RiskCheck("Gross Exposure", st, gross, limits.max_gross_exp))

    adv = (
        portfolio.set_index("Symbol")
        .get("ADV", pd.Series(dtype=float))
        .get(symbol, 1e6)
    )
    days = (new_w * nav) / (adv + 1e-8)
    st = (
        RiskStatus.PASS
        if days <= limits.max_liq_days
        else RiskStatus.WARN if days < limits.max_liq_days * 2 else RiskStatus.REJECT
    )
    checks.append(RiskCheck("Liquidity (days)", st, days, limits.max_liq_days))
    return checks


def plot_intraday_risk(nav: np.ndarray, limits: RiskLimits, output_dir: str) -> None:
    peak = np.maximum.accumulate(nav)
    dd = nav / peak - 1
    t = np.arange(len(nav))
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axes[0].plot(t, nav / 1e6, color=COLORS[0], linewidth=1.5)
    axes[0].plot(
        t, peak / 1e6, color=COLORS[3], linewidth=1.0, linestyle="--", label="Peak"
    )
    axes[0].set_title("Intraday NAV ($M)", fontweight="bold")
    axes[0].set_ylabel("NAV ($M)")
    axes[0].legend()
    axes[1].fill_between(t, dd * 100, 0, alpha=0.6, color=COLORS[1])
    axes[1].axhline(
        -limits.max_drawdown * 100,
        color="red",
        linestyle="--",
        linewidth=1.2,
        label=f"Limit {-limits.max_drawdown:.0%}",
    )
    axes[1].set_title("Intraday Drawdown", fontweight="bold")
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_xlabel("Minute")
    axes[1].legend()
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "intraday_risk.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def run(
    nav: float = 10_000_000,
    max_dd: float = 0.12,
    seed: int = 42,
    output_dir: str = "risk_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    limits = RiskLimits(max_drawdown=max_dd)

    # Build portfolio
    SYMBOLS = ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM", "GS", "XOM", "PFE"]
    SECTORS = ["Tech", "Tech", "Tech", "Tech", "Finance", "Finance", "Energy", "Health"]
    weights = np.abs(rng.normal(0, 0.08, len(SYMBOLS)))
    weights[0] = 0.13  # AAPL overweight for breach demo
    weights /= weights.sum() * 1.2
    portfolio = pd.DataFrame(
        {
            "Symbol": SYMBOLS,
            "Sector": SECTORS,
            "Weight": weights,
            "ADV": rng.lognormal(np.log(5e6), 0.5, len(SYMBOLS)),
        }
    )

    # Pre-trade checks
    for sym, delta in [("AAPL", 0.03), ("NVDA", -0.04)]:
        logger.info("Pre-trade check: %+.1f%% %s", delta * 100, sym)
        for chk in pre_trade_checks(portfolio, limits, sym, delta, nav):
            icon = {"PASS": "[OK]", "WARN": "[WARN]", "REJECT": "[REJECT]"}[
                chk.status.value
            ]
            logger.info(
                "  %s %-28s cur=%.3f  lim=%.3f", icon, chk.name, chk.current, chk.limit
            )

    # Intraday NAV simulation
    N = 390
    intraday_nav = nav * np.cumprod(1 + rng.normal(0.00005, 0.001, N))
    plot_intraday_risk(intraday_nav, limits, output_dir)

    # Drawdown breaker
    breaker = DrawdownBreaker(max_dd=max_dd, cooldown=45)
    peak = np.maximum.accumulate(intraday_nav)
    for t in range(N):
        breaker.check(intraday_nav[t], peak[t], t)

    if breaker.events:
        for ev in breaker.events:
            logger.info("  t=%4d  %s  DD=%.2f%%", ev["t"], ev["event"], ev["dd"] * 100)
    else:
        logger.info("  No drawdown breaker events triggered.")

    # Sector exposure
    sec_exp = portfolio.groupby("Sector")["Weight"].sum()
    breached = sec_exp[sec_exp > limits.max_sector_exp]
    if not breached.empty:
        logger.warning("Sector limit breaches: %s", breached.to_dict())
    else:
        logger.info("All sector exposures within limits.")
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind Risk Controls Example")
    p.add_argument("--nav", type=float, default=10_000_000)
    p.add_argument("--max-dd", type=float, default=0.12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="risk_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Risk Controls Example")
    run(args.nav, args.max_dd, args.seed, args.output_dir)
