"""
Main FastAPI application for AlphaMind backend.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

from app.api.v1.routers import (
    alternative_data,
    backtest,
    health,
    market_data,
    portfolio,
    research,
    risk,
    strategies,
    trading,
)
from db.session import AsyncSessionLocal, create_all_tables
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from infrastructure.auth.authentication import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Demo-data seed (idempotent - skipped if positions already exist)
# ---------------------------------------------------------------------------


async def _seed_demo_data() -> None:
    """Populate the DB with demo positions and strategies on first run."""
    from db.models.position import Position
    from db.models.strategy import Strategy
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as session:
        count = (
            await session.execute(select(func.count()).select_from(Position))
        ).scalar_one()
        if count > 0:
            logger.info("Database already seeded - skipping demo data.")
            return

        logger.info("Seeding demo positions and strategies …")
        now = datetime.now(timezone.utc)

        positions = [
            Position(
                id="pos-001",
                portfolio_id="port-001",
                ticker="AAPL",
                sector="Technology",
                quantity=100.0,
                entry_price=150.0,
                current_price=175.5,
                unrealized_pnl=2550.0,
                realized_pnl=0.0,
                weight=0.28,
                beta=1.21,
                sharpe_contrib=0.42,
                var_95=1240.0,
                status="open",
                opened_at=now - timedelta(days=30),
                updated_at=now,
            ),
            Position(
                id="pos-002",
                portfolio_id="port-001",
                ticker="MSFT",
                sector="Technology",
                quantity=50.0,
                entry_price=300.0,
                current_price=338.0,
                unrealized_pnl=1900.0,
                realized_pnl=0.0,
                weight=0.27,
                beta=0.92,
                sharpe_contrib=0.38,
                var_95=980.0,
                status="open",
                opened_at=now - timedelta(days=25),
                updated_at=now,
            ),
            Position(
                id="pos-003",
                portfolio_id="port-001",
                ticker="GOOGL",
                sector="Communication",
                quantity=25.0,
                entry_price=2800.0,
                current_price=2950.0,
                unrealized_pnl=3750.0,
                realized_pnl=0.0,
                weight=0.19,
                beta=1.05,
                sharpe_contrib=0.29,
                var_95=1560.0,
                status="open",
                opened_at=now - timedelta(days=20),
                updated_at=now,
            ),
            Position(
                id="pos-004",
                portfolio_id="port-001",
                ticker="TSLA",
                sector="Consumer Disc.",
                quantity=30.0,
                entry_price=700.0,
                current_price=742.0,
                unrealized_pnl=1260.0,
                realized_pnl=0.0,
                weight=0.11,
                beta=1.89,
                sharpe_contrib=0.14,
                var_95=2100.0,
                status="open",
                opened_at=now - timedelta(days=15),
                updated_at=now,
            ),
            Position(
                id="pos-005",
                portfolio_id="port-001",
                ticker="JPM",
                sector="Financials",
                quantity=80.0,
                entry_price=130.0,
                current_price=148.25,
                unrealized_pnl=1460.0,
                realized_pnl=0.0,
                weight=0.15,
                beta=0.78,
                sharpe_contrib=0.22,
                var_95=680.0,
                status="open",
                opened_at=now - timedelta(days=10),
                updated_at=now,
            ),
        ]

        demo_strategies = [
            Strategy(
                id="strat-001",
                name="Momentum Alpha",
                description="Cross-sectional momentum with ML signal filtering",
                strategy_type="momentum",
                status="active",
                parameters_json='{"lookback": 12, "rebalance": "monthly", "top_decile": 0.1}',
                sharpe_ratio=2.31,
                max_drawdown=-0.089,
                profit_factor=1.84,
                win_rate=0.64,
                total_return=0.384,
                volatility=0.142,
                alpha=0.094,
                beta=0.88,
                created_at=now,
                updated_at=now,
            ),
            Strategy(
                id="strat-002",
                name="Mean Reversion",
                description="Statistical arbitrage using cointegrated pairs",
                strategy_type="mean_reversion",
                status="paused",
                parameters_json='{"z_entry": 2.0, "z_exit": 0.5, "half_life": 10}',
                sharpe_ratio=1.87,
                max_drawdown=-0.054,
                profit_factor=2.12,
                win_rate=0.71,
                total_return=0.221,
                volatility=0.098,
                alpha=0.067,
                beta=0.34,
                created_at=now,
                updated_at=now,
            ),
            Strategy(
                id="strat-003",
                name="RL Trading Agent",
                description="DDPG-based adaptive execution agent",
                strategy_type="rl_agent",
                status="paused",
                parameters_json='{"actor_lr": 0.0001, "critic_lr": 0.001, "gamma": 0.99}',
                sharpe_ratio=1.54,
                max_drawdown=-0.127,
                profit_factor=1.61,
                win_rate=0.58,
                total_return=0.298,
                volatility=0.189,
                alpha=0.052,
                beta=1.12,
                created_at=now,
                updated_at=now,
            ),
        ]

        session.add_all(positions)
        session.add_all(demo_strategies)
        await session.commit()
        logger.info("Demo data seeded successfully.")


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting AlphaMind API …")
    await create_all_tables()
    await _seed_demo_data()
    logger.info("API docs available at /docs")
    yield
    logger.info("Shutting down AlphaMind API …")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    lifespan=lifespan,
    title="AlphaMind API",
    description="Institutional-Grade Quantitative AI Trading System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
_cors_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:8081",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Also accept any localhost / 127.0.0.1 / private-LAN origin on any port.
    # Expo web, Vite, and other dev servers pick varying ports, and the app may
    # be opened via localhost or the machine's LAN IP (for example when
    # localhost forwarding or a browser VPN blocks localhost). This keeps local
    # development working without enumerating every host or port.
    allow_origin_regex=(
        r"https?://("
        r"localhost|127\.0\.0\.1|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers - versioned (canonical)
# ---------------------------------------------------------------------------
app.include_router(health.router, tags=["health"])
app.include_router(auth_router)
app.include_router(trading.router, prefix="/api/v1/trading", tags=["trading"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(
    market_data.router, prefix="/api/v1/market-data", tags=["market-data"]
)
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(
    alternative_data.router,
    prefix="/api/v1/alternative-data",
    tags=["alternative-data"],
)
app.include_router(research.router, prefix="/api/v1/research", tags=["research"])
app.include_router(research.router, prefix="/api/research", include_in_schema=False)

# Legacy unversioned aliases (hidden from OpenAPI docs)
app.include_router(portfolio.router, prefix="/api/portfolio", include_in_schema=False)
app.include_router(strategies.router, prefix="/api/strategies", include_in_schema=False)
app.include_router(
    market_data.router, prefix="/api/market-data", include_in_schema=False
)
app.include_router(risk.router, prefix="/api/risk", include_in_schema=False)
app.include_router(backtest.router, prefix="/api/backtest", include_in_schema=False)
app.include_router(
    alternative_data.router, prefix="/api/alternative-data", include_in_schema=False
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
