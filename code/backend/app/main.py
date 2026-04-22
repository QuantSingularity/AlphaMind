"""
Main FastAPI application for AlphaMind backend.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.api.v1.routers import (
    alternative_data,
    backtest,
    health,
    market_data,
    portfolio,
    risk,
    strategies,
    trading,
)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from infrastructure.auth.authentication import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan."""
    logger.info("Starting AlphaMind API...")
    logger.info("API documentation available at /docs")
    yield
    logger.info("Shutting down AlphaMind API...")


app = FastAPI(
    lifespan=lifespan,
    title="AlphaMind API",
    description="Institutional-Grade Quantitative AI Trading System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_cors_origins_raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:8081",
)
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
# Health / root (no version prefix — used by K8s probes)
app.include_router(health.router, tags=["health"])

# Auth
app.include_router(auth_router)

# v1 API — all prefixed /api/v1/
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

# ---------------------------------------------------------------------------
# Legacy /api/* aliases — keeps backwards compat with any external callers
# ---------------------------------------------------------------------------
app.include_router(
    portfolio.router,
    prefix="/api/portfolio",
    tags=["portfolio-alias"],
    include_in_schema=False,
)
app.include_router(
    strategies.router,
    prefix="/api/strategies",
    tags=["strategies-alias"],
    include_in_schema=False,
)
app.include_router(
    market_data.router,
    prefix="/api/market-data",
    tags=["market-data-alias"],
    include_in_schema=False,
)
app.include_router(
    risk.router, prefix="/api/risk", tags=["risk-alias"], include_in_schema=False
)
app.include_router(
    backtest.router,
    prefix="/api/backtest",
    tags=["backtest-alias"],
    include_in_schema=False,
)
app.include_router(
    alternative_data.router,
    prefix="/api/alternative-data",
    tags=["alt-data-alias"],
    include_in_schema=False,
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
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
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
