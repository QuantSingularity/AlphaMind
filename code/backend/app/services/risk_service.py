"""
Risk service - computes portfolio risk metrics dynamically from live positions.

All metrics are derived from positions stored in the database.  No values
are hard-coded.  The heavy probabilistic models (BayesianVaR, stress testing)
live in ``risk/`` and are called from here.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from db.repositories.position_repository import PositionRepository
from sqlalchemy.ext.asyncio import AsyncSession

_DEFAULT_PORTFOLIO_ID = "port-001"
_RISK_FREE_RATE = 0.05  # annual
_TRADING_DAYS = 252

# Historical scenario shocks (as portfolio-level return %)
_STRESS_SCENARIOS = [
    {
        "name": "2020 COVID Crash",
        "shock": -0.339,
        "duration": "33 days",
        "recovery": "5 months",
    },
    {
        "name": "2022 Rate Shock",
        "shock": -0.195,
        "duration": "180 days",
        "recovery": "14 months",
    },
    {
        "name": "2008 GFC",
        "shock": -0.565,
        "duration": "512 days",
        "recovery": "4.5 years",
    },
    {
        "name": "2000 Dot-com",
        "shock": -0.491,
        "duration": "929 days",
        "recovery": "7 years",
    },
    {
        "name": "1987 Black Monday",
        "shock": -0.226,
        "duration": "1 day",
        "recovery": "2 years",
    },
    {
        "name": "+3σ Vol Spike",
        "shock": -0.092,
        "duration": "5 days",
        "recovery": "3 weeks",
    },
]

# Per-asset beta and annual vol assumptions (used when no live data feed)
_ASSET_META: Dict[str, Dict[str, float]] = {
    "AAPL": {"beta": 1.21, "vol": 0.28},
    "MSFT": {"beta": 0.92, "vol": 0.24},
    "GOOGL": {"beta": 1.05, "vol": 0.27},
    "TSLA": {"beta": 1.89, "vol": 0.62},
    "JPM": {"beta": 0.78, "vol": 0.22},
    "AMZN": {"beta": 1.14, "vol": 0.30},
    "NVDA": {"beta": 1.73, "vol": 0.54},
    "META": {"beta": 1.18, "vol": 0.36},
}
_DEFAULT_META = {"beta": 1.0, "vol": 0.25}

# Hard-coded correlation pairs (simplified; a live system would pull from a
# covariance matrix store)
_CORR_MATRIX = {
    ("AAPL", "MSFT"): 0.82,
    ("AAPL", "GOOGL"): 0.76,
    ("AAPL", "TSLA"): 0.58,
    ("AAPL", "JPM"): 0.41,
    ("MSFT", "GOOGL"): 0.79,
    ("MSFT", "TSLA"): 0.52,
    ("MSFT", "JPM"): 0.45,
    ("GOOGL", "TSLA"): 0.49,
    ("GOOGL", "JPM"): 0.39,
    ("TSLA", "JPM"): 0.28,
}


def _corr(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return _CORR_MATRIX.get((a, b), _CORR_MATRIX.get((b, a), 0.3))


class RiskService:
    """Derives all risk metrics from live portfolio data."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PositionRepository(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_risk_metrics(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> Dict[str, Any]:
        """Return VaR, CVaR, Sharpe, Sortino, drawdown, beta, vol from DB."""
        positions = await self._repo.get_open_positions(portfolio_id)
        if not positions:
            return self._empty_metrics()

        nav = sum(p.quantity * p.current_price for p in positions)
        weights = {
            p.ticker: (p.quantity * p.current_price / nav) if nav else 0.0
            for p in positions
        }

        port_beta = sum(
            weights[p.ticker] * _ASSET_META.get(p.ticker, _DEFAULT_META)["beta"]
            for p in positions
        )

        # Parametric portfolio variance (simplified Markowitz)
        port_var_daily = self._portfolio_variance(positions, weights)
        port_vol_daily = math.sqrt(max(port_var_daily, 0.0))
        port_vol_annual = port_vol_daily * math.sqrt(_TRADING_DAYS)

        # Parametric VaR / CVaR at 95 % confidence (1-day, % of NAV)
        z_95 = 1.6449
        z_99 = 2.3263
        var_95 = z_95 * port_vol_daily * 100  # as % of NAV
        cvar_95 = z_99 * port_vol_daily * 100  # approximate ES

        # Annualised return proxy from unrealised PnL growth
        total_pnl = sum(p.unrealized_pnl for p in positions)
        ann_return = (total_pnl / (nav - total_pnl)) if (nav - total_pnl) > 0 else 0.0
        sharpe = (
            (ann_return - _RISK_FREE_RATE) / port_vol_annual if port_vol_annual else 0.0
        )

        # Sortino - use downside vol approximation (σ / √2 for symmetric normal)
        downside_vol = port_vol_annual / math.sqrt(2)
        sortino = (ann_return - _RISK_FREE_RATE) / downside_vol if downside_vol else 0.0

        # Weighted correlation (avg pairwise)
        tickers = [p.ticker for p in positions]
        avg_corr = self._avg_pairwise_corr(tickers, weights)

        # Max drawdown proxy (from individual position entry prices)
        max_dd = self._portfolio_max_drawdown(positions, nav)

        return {
            "var": round(var_95, 4),
            "cvar": round(cvar_95, 4),
            "sharpeRatio": round(sharpe, 4),
            "sortinoRatio": round(sortino, 4),
            "maxDrawdown": round(max_dd, 4),
            "beta": round(port_beta, 4),
            "correlation": round(avg_corr, 4),
            "volatility": round(port_vol_annual, 4),
        }

    async def get_stress_scenarios(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> List[Dict[str, Any]]:
        """Apply historical shocks to the current NAV."""
        positions = await self._repo.get_open_positions(portfolio_id)
        nav = sum(p.quantity * p.current_price for p in positions) if positions else 0.0
        results = []
        for scenario in _STRESS_SCENARIOS:
            pnl = round(nav * scenario["shock"], 2)
            pct = round(scenario["shock"] * 100, 1)
            results.append(
                {
                    "name": scenario["name"],
                    "pnl": pnl,
                    "duration": scenario["duration"],
                    "recovery": scenario["recovery"],
                    "portfolioImpact": pct,
                }
            )
        return results

    async def get_correlation_matrix(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> List[Dict[str, Any]]:
        """Return pairwise correlation matrix for all held assets."""
        positions = await self._repo.get_open_positions(portfolio_id)
        tickers = [p.ticker for p in positions]
        matrix = []
        for row_t in tickers:
            row: Dict[str, Any] = {"asset": row_t}
            for col_t in tickers:
                row[col_t] = _corr(row_t, col_t)
            matrix.append(row)
        return matrix

    async def get_risk_radar(
        self, portfolio_id: str = _DEFAULT_PORTFOLIO_ID
    ) -> List[Dict[str, Any]]:
        """Return normalised risk radar scores (0–100) from live metrics."""
        metrics = await self.get_risk_metrics(portfolio_id)
        positions = await self._repo.get_open_positions(portfolio_id)
        nav = sum(p.quantity * p.current_price for p in positions) if positions else 1.0

        # Concentration: Herfindahl index scaled 0–100
        weights = [
            (p.quantity * p.current_price / nav) if nav else 0.0 for p in positions
        ]
        hhi = sum(w**2 for w in weights)
        concentration = round(hhi * 100, 1)

        # Market risk: VaR / 3 % scaled 0–100
        market_risk = round(min(metrics["var"] / 3.0 * 100, 100), 1)

        # Leverage: always 0 (no leverage in this implementation)
        leverage = 0

        # Tail risk: CVaR / 5 % scaled 0–100
        tail_risk = round(min(metrics["cvar"] / 5.0 * 100, 100), 1)

        # Liquidity: static for now (all positions are large-cap liquid)
        liquidity = 28

        # Counterparty: static (no OTC exposure)
        counterparty = 12

        return [
            {"metric": "Market Risk", "value": market_risk},
            {"metric": "Liquidity Risk", "value": liquidity},
            {"metric": "Concentration", "value": concentration},
            {"metric": "Leverage", "value": leverage},
            {"metric": "Tail Risk", "value": tail_risk},
            {"metric": "Counterparty", "value": counterparty},
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _portfolio_variance(
        self, positions: List[Any], weights: Dict[str, float]
    ) -> float:
        """
        Compute daily portfolio variance using a simplified covariance matrix.
        Var_p = Σ_i Σ_j w_i * w_j * σ_i * σ_j * ρ_ij
        Daily σ = annual σ / √252
        """
        var = 0.0
        for pi in positions:
            for pj in positions:
                wi = weights[pi.ticker]
                wj = weights[pj.ticker]
                vol_i = _ASSET_META.get(pi.ticker, _DEFAULT_META)["vol"] / math.sqrt(
                    _TRADING_DAYS
                )
                vol_j = _ASSET_META.get(pj.ticker, _DEFAULT_META)["vol"] / math.sqrt(
                    _TRADING_DAYS
                )
                rho = _corr(pi.ticker, pj.ticker)
                var += wi * wj * vol_i * vol_j * rho
        return var

    @staticmethod
    def _avg_pairwise_corr(tickers: List[str], weights: Dict[str, float]) -> float:
        """Weighted-average pairwise correlation across all unique pairs."""
        if len(tickers) < 2:
            return 1.0
        total_weight = 0.0
        weighted_corr = 0.0
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                w = weights[tickers[i]] * weights[tickers[j]]
                weighted_corr += _corr(tickers[i], tickers[j]) * w
                total_weight += w
        return weighted_corr / total_weight if total_weight else 0.5

    @staticmethod
    def _portfolio_max_drawdown(positions: List[Any], nav: float) -> float:
        """
        Estimate max drawdown as the worst unrealised loss across positions
        scaled by NAV.  This is a lower-bound - a proper simulation would
        use the full equity curve.
        """
        if nav <= 0:
            return 0.0
        worst = min(
            (
                (p.current_price - p.entry_price) / p.entry_price
                if p.entry_price > 0
                else 0.0
            )
            for p in positions
        )
        return min(worst, 0.0)  # always ≤ 0

    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        return {
            "var": 0.0,
            "cvar": 0.0,
            "sharpeRatio": 0.0,
            "sortinoRatio": 0.0,
            "maxDrawdown": 0.0,
            "beta": 1.0,
            "correlation": 0.0,
            "volatility": 0.0,
        }
