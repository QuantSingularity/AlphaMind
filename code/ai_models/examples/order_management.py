"""
order_management.py
--------------------
AlphaMind Examples | Execution

Demonstrates the Order Management System (OMS) from
code/backend/execution/order_management/.

Covers order lifecycle, smart order routing, fill simulation,
implementation shortfall decomposition, and execution quality reporting.

Usage
-----
    python order_management.py
    python order_management.py --adv 500000 --order-size 5000
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("order_management")
plt.style.use("seaborn-v0_8-darkgrid")
COLORS = ["#2563eb", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"
    VWAP = "vwap"
    IS = "implementation_shortfall"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    qty: int
    order_type: OrderType
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: int = 0
    avg_fill_px: float = 0.0
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    fills: List[dict] = field(default_factory=list)

    def fill(self, qty: int, price: float) -> None:
        prev = self.avg_fill_px * self.filled_qty
        self.filled_qty += qty
        self.avg_fill_px = (prev + qty * price) / self.filled_qty
        self.fills.append({"qty": qty, "price": price})
        self.status = (
            OrderStatus.FILLED if self.filled_qty >= self.qty else OrderStatus.PARTIAL
        )

    @property
    def remaining(self) -> int:
        return self.qty - self.filled_qty


class OrderManager:
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.history: List[dict] = []

    def submit(self, order: Order) -> str:
        order.status = OrderStatus.SUBMITTED
        self.orders[order.order_id] = order
        self._log(order, "SUBMITTED")
        return order.order_id

    def cancel(self, oid: str) -> bool:
        o = self.orders.get(oid)
        if o and o.status not in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            o.status = OrderStatus.CANCELLED
            self._log(o, "CANCELLED")
            return True
        return False

    def fill(self, oid: str, qty: int, px: float) -> None:
        o = self.orders.get(oid)
        if o and o.status not in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            o.fill(qty, px)
            self._log(o, f"FILL {qty}@{px:.4f}")

    def _log(self, o: Order, event: str) -> None:
        self.history.append(
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "event": event,
                "status": o.status.value,
            }
        )

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "ID": o.order_id,
                    "Symbol": o.symbol,
                    "Side": o.side.value,
                    "Type": o.order_type.value,
                    "Qty": o.qty,
                    "Filled": o.filled_qty,
                    "Avg Px": o.avg_fill_px,
                    "Status": o.status.value,
                }
                for o in self.orders.values()
            ]
        ).set_index("ID")


@dataclass
class Venue:
    name: str
    fee_bps: float
    rebate_bps: float
    fill_prob: float
    latency_us: float


VENUES = [
    Venue("NYSE", 0.10, 0.20, 0.85, 50),
    Venue("NASDAQ", 0.05, 0.15, 0.88, 40),
    Venue("IEX", 0.09, 0.00, 0.72, 350),
    Venue("CBOE", 0.12, 0.18, 0.78, 80),
    Venue("DARK", 0.02, 0.00, 0.45, 150),
]


def smart_route(order_qty: int, side: str, midpoint: float, rng) -> pd.DataFrame:
    scores = [
        v.fill_prob * 100 - (v.fee_bps - v.rebate_bps) - v.latency_us / 100
        for v in VENUES
    ]
    scores = np.array(scores)
    w = np.maximum(scores - scores.min(), 0)
    w /= w.sum()
    alloc = (w * order_qty).astype(int)
    alloc[-1] += order_qty - alloc.sum()
    rows = []
    for v, qty, wt in zip(VENUES, alloc, w):
        if qty:
            slip = rng.exponential(0.5) * (1 - v.fill_prob)
            px = midpoint * (1 + slip / 10000 * (1 if side == "buy" else -1))
            rows.append(
                {
                    "Venue": v.name,
                    "Qty": qty,
                    "Weight": wt,
                    "Fill Px": px,
                    "Fee (bps)": v.fee_bps - v.rebate_bps,
                }
            )
    return pd.DataFrame(rows).set_index("Venue")


def impact_sqrt(qty, adv, sigma, alpha=0.5, beta=0.6):
    return alpha * sigma * np.sqrt(qty / adv) * 10_000 * beta


def plot_order_book(mid: float, spread_bps: float, output_dir: str, rng) -> None:
    n = 5
    half = mid * spread_bps / 20_000
    bids = [
        {"px": mid - half * (i + 1), "qty": rng.integers(100, 2000)} for i in range(n)
    ]
    asks = [
        {"px": mid + half * (i + 1), "qty": rng.integers(100, 2000)} for i in range(n)
    ]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(
        [b["px"] for b in bids],
        [b["qty"] for b in bids],
        height=0.01,
        color=COLORS[2],
        alpha=0.8,
        label="Bids",
    )
    ax.barh(
        [a["px"] for a in asks],
        [a["qty"] for a in asks],
        height=0.01,
        color=COLORS[1],
        alpha=0.8,
        label="Asks",
    )
    ax.axhline(
        mid, color="black", linewidth=1.2, linestyle="--", label=f"Mid ${mid:.2f}"
    )
    ax.set_title("Limit Order Book (5 Levels)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Quantity")
    ax.set_ylabel("Price ($)")
    ax.legend()
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "order_book.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)


def run(
    adv: int = 1_000_000,
    order_size: int = 10_000,
    mid: float = 185.0,
    seed: int = 42,
    output_dir: str = "oms_output",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    oms = OrderManager()
    orders = [
        Order("AAPL", OrderSide.BUY, order_size, OrderType.TWAP),
        Order(
            "MSFT", OrderSide.SELL, order_size // 2, OrderType.LIMIT, limit_price=380.0
        ),
        Order("NVDA", OrderSide.BUY, order_size // 5, OrderType.VWAP),
    ]
    for o in orders:
        oms.submit(o)

    # Simulate fills
    for o in orders:
        px = mid * (1 + rng.normal(0, 0.0005))
        if o.limit_price and px > o.limit_price:
            continue
        fills = np.random.multinomial(o.qty, [0.4, 0.35, 0.25])
        for fq in fills:
            if fq:
                oms.fill(o.order_id, fq, px * (1 + rng.normal(0, 0.0003)))

    logger.info("Order Summary:\n%s", oms.summary().to_string())

    # Smart routing
    plan = smart_route(order_size, "buy", mid, rng)
    logger.info("Smart Route Plan:\n%s", plan.to_string())

    # Implementation shortfall
    spread_bps = 5.0
    exec_px = (plan["Qty"] * plan["Fill Px"]).sum() / plan["Qty"].sum()
    total_is = (exec_px / mid - 1) * 10_000
    spread_cost = spread_bps / 2
    logger.info(
        "Implementation Shortfall: %.2f bps (spread=%.2f, impact=%.2f)",
        total_is,
        spread_cost,
        total_is - spread_cost,
    )

    # Market impact by order size
    fracs = np.linspace(0.01, 0.20, 50)
    sigma = 0.20 / np.sqrt(252)
    imps = [impact_sqrt(f * adv, adv, sigma) for f in fracs]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(fracs * 100, imps, color=COLORS[0], linewidth=2)
    ax.set_title("Square-Root Market Impact Model", fontsize=12, fontweight="bold")
    ax.set_xlabel("Order Size (% ADV)")
    ax.set_ylabel("Impact (bps)")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    plt.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "market_impact.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)

    plot_order_book(mid, spread_bps, output_dir, rng)
    logger.info("Outputs saved to: %s/", output_dir)


def parse_args():
    p = argparse.ArgumentParser(description="AlphaMind OMS Example")
    p.add_argument("--adv", type=int, default=1_000_000)
    p.add_argument("--order-size", type=int, default=10_000)
    p.add_argument("--mid", type=float, default=185.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=str, default="oms_output")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("AlphaMind - Order Management Example")
    run(args.adv, args.order_size, args.mid, args.seed, args.output_dir)
