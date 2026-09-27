"""
Synthetic OHLCV price generation for backtesting.

None of the connectors in backend/market_data/connectors talk to a real
provider without API credentials, and this codebase has no built-in mock
data source - so a backtest triggered on a fresh install had nothing to
run against. This module fills that gap with a simple, seeded GBM price
path so momentum/mean-reversion/ml_alpha backtests are always runnable
end-to-end. (rl_agent backtests don't need this - ai_models.environments
already simulates its own correlated multi-asset GBM paths internally.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_ohlcv(
    symbol: str,
    start_date: str,
    end_date: str,
    seed: int | None = None,
    initial_price: float = 100.0,
    annual_drift: float = 0.08,
    annual_vol: float = 0.25,
) -> pd.DataFrame:
    """Generate a single-symbol daily OHLCV series via Geometric Brownian Motion.

    Deterministic for a given (symbol, start_date, end_date, seed) so
    repeated backtests over the same window are reproducible.

    Returns a DataFrame indexed by date with columns open, high, low,
    close, volume - the shape backend.market_data.backtesting.BacktestEngine
    expects.
    """
    dates = pd.bdate_range(start=start_date, end=end_date)
    if len(dates) == 0:
        raise ValueError(f"No business days between {start_date} and {end_date}")

    rng = np.random.default_rng(seed if seed is not None else hash(symbol) % (2**32))
    n = len(dates)
    dt = 1 / 252
    drift = (annual_drift - 0.5 * annual_vol**2) * dt
    shocks = rng.normal(drift, annual_vol * np.sqrt(dt), n)
    close = initial_price * np.exp(np.cumsum(shocks))

    # Derive open/high/low from a small intraday noise band around close,
    # so BacktestEngine's limit/stop-order price logic has something
    # sensible to work with.
    intraday_range = np.abs(rng.normal(0, annual_vol * np.sqrt(dt) * 0.5, n)) * close
    open_ = np.roll(close, 1)
    open_[0] = initial_price
    high = np.maximum(open_, close) + intraday_range
    low = np.minimum(open_, close) - intraday_range
    low = np.clip(low, a_min=0.01, a_max=None)
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
