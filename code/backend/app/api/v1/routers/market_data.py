"""Market data router — quotes, historical OHLCV, and subscription helpers."""

import math
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Models
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


class OHLCV(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


# Reference prices (deterministic — no random)
_PRICES: dict = {
    "AAPL": 175.5,
    "MSFT": 338.0,
    "GOOGL": 2950.0,
    "TSLA": 742.0,
    "JPM": 148.25,
    "AMZN": 3420.0,
    "NVDA": 875.0,
    "META": 485.0,
    "BRK.B": 382.0,
    "V": 268.0,
}


def _deterministic_walk(base: float, i: int, vol: float = 0.018) -> float:
    """Return a deterministic price perturbation for day i."""
    return base * (1 + math.sin(i * 0.31) * vol + math.cos(i * 0.71) * vol * 0.5)


def _get_price(ticker: str) -> float:
    return _PRICES.get(ticker.upper(), 100.0)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/quote/{symbol}", response_model=Quote)
async def get_quote(symbol: str):
    """Return a live-style quote for a symbol."""
    price = _get_price(symbol)
    spread = price * 0.0005
    return {
        "ticker": symbol.upper(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "bid": round(price - spread, 2),
        "ask": round(price + spread, 2),
        "last": price,
        "volume": 12_500_000,
        "high": round(price * 1.012, 2),
        "low": round(price * 0.988, 2),
        "open": round(price * 0.997, 2),
        "close": round(price * 0.994, 2),
    }


@router.get("/quotes")
async def get_quotes(tickers: str = Query(..., description="Comma-separated tickers")):
    """Return quotes for multiple tickers."""
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    results = []
    for sym in symbols:
        price = _get_price(sym)
        spread = price * 0.0005
        results.append(
            {
                "ticker": sym,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "bid": round(price - spread, 2),
                "ask": round(price + spread, 2),
                "last": price,
                "volume": 12_500_000,
                "high": round(price * 1.012, 2),
                "low": round(price * 0.988, 2),
                "open": round(price * 0.997, 2),
                "close": round(price * 0.994, 2),
            }
        )
    return results


@router.get("/historical/{symbol}", response_model=List[OHLCV])
async def get_historical(
    symbol: str,
    days: int = Query(30, ge=1, le=730),
    interval: str = Query("1d"),
):
    """Return historical OHLCV data."""
    base = _get_price(symbol)
    data = []
    price = base * 0.85  # start a bit lower for an uptrend
    for i in range(days):
        price = _deterministic_walk(price, i)
        ts = (datetime.utcnow() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        daily_range = price * 0.015
        data.append(
            {
                "timestamp": ts,
                "open": round(price * 0.998, 2),
                "high": round(price + daily_range, 2),
                "low": round(price - daily_range, 2),
                "close": round(price, 2),
                "volume": 12_000_000 + int(math.sin(i) * 3_000_000),
            }
        )
    return data


@router.get("/")
async def list_market_data(
    ticker: Optional[str] = Query(None),
    interval: Optional[str] = Query("1d"),
):
    """Convenience endpoint: returns historical data for a ticker."""
    if not ticker:
        # Return summary for all known tickers
        return [
            {
                "ticker": sym,
                "last": price,
                "change": round(price * 0.012, 2),
                "changePct": 1.2,
            }
            for sym, price in _PRICES.items()
        ]
    return await get_historical(ticker, days=30, interval=interval)
