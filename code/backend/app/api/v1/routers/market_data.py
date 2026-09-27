"""
Market data router - live quotes, OHLCV history, and ticker search.

Route inventory
---------------
GET /quotes              - all reference tickers (bulk)
GET /quotes/{ticker}     - single ticker quote   (canonical)
GET /quote/{ticker}      - alias kept for test_api.py / test_basic_api.py
GET /history/{ticker}    - OHLCV bars            (canonical)
GET /historical/{ticker} - alias kept for test_api.py / test_basic_api.py
GET /batch-quotes        - comma-separated tickers
"""

from typing import Any, Dict, List, Optional

from app.services import MarketDataService, get_market_data_service
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class Quote(BaseModel):
    ticker: str
    timestamp: str
    bid: float
    ask: float
    last: float
    volume: int
    high: float
    low: float
    open: float
    close: float
    source: Optional[str] = "synthetic"


class OHLCV(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


# ---------------------------------------------------------------------------
# Routes - fixed paths registered BEFORE wildcard paths
# ---------------------------------------------------------------------------


@router.get("/quotes", response_model=List[Quote])
async def get_all_quotes(
    svc: MarketDataService = Depends(get_market_data_service),
) -> List[Dict[str, Any]]:
    """Return quotes for all reference tickers."""
    return await svc.get_all_quotes()


@router.get("/batch-quotes")
async def get_batch_quotes(
    tickers: str = Query(..., description="Comma-separated ticker list"),
    svc: MarketDataService = Depends(get_market_data_service),
) -> List[Dict[str, Any]]:
    """Return quotes for a comma-separated list of tickers."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    return await svc.get_quotes(ticker_list)


# ---------------------------------------------------------------------------
# Single-ticker quote - two paths: canonical (/quotes/X) + alias (/quote/X)
# ---------------------------------------------------------------------------


async def _get_quote(
    ticker: str,
    svc: MarketDataService,
) -> Dict[str, Any]:
    return await svc.get_quote(ticker)


@router.get("/quotes/{ticker}", response_model=Quote)
async def get_quote_plural(
    ticker: str,
    svc: MarketDataService = Depends(get_market_data_service),
) -> Dict[str, Any]:
    """Return the latest quote for a single ticker (canonical path)."""
    return await _get_quote(ticker, svc)


@router.get("/quote/{ticker}", response_model=Quote)
async def get_quote_singular(
    ticker: str,
    svc: MarketDataService = Depends(get_market_data_service),
) -> Dict[str, Any]:
    """Return the latest quote for a single ticker (alias for /quotes/{ticker})."""
    return await _get_quote(ticker, svc)


# ---------------------------------------------------------------------------
# OHLCV history - two paths: canonical (/history/X) + alias (/historical/X)
# ---------------------------------------------------------------------------


async def _get_ohlcv(
    ticker: str,
    days: int,
    interval: str,
    svc: MarketDataService,
) -> List[Dict[str, Any]]:
    return await svc.get_ohlcv(ticker, days=days, interval=interval)


@router.get("/history/{ticker}", response_model=List[OHLCV])
async def get_ohlcv_history(
    ticker: str,
    days: int = Query(90, ge=1, le=1825, description="Number of calendar days"),
    interval: str = Query("1d", description="Bar interval: 1d | 1h | 5m"),
    svc: MarketDataService = Depends(get_market_data_service),
) -> List[Dict[str, Any]]:
    """Return OHLCV history for a ticker (canonical path)."""
    return await _get_ohlcv(ticker, days, interval, svc)


@router.get("/historical/{ticker}", response_model=List[OHLCV])
async def get_ohlcv_historical(
    ticker: str,
    days: int = Query(90, ge=1, le=1825, description="Number of calendar days"),
    interval: str = Query("1d", description="Bar interval: 1d | 1h | 5m"),
    svc: MarketDataService = Depends(get_market_data_service),
) -> List[Dict[str, Any]]:
    """Return OHLCV history for a ticker (alias for /history/{ticker})."""
    return await _get_ohlcv(ticker, days, interval, svc)
