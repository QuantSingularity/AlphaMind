"""Alternative data router — satellite, sentiment, SEC filings, social media."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class AlternativeDataSource(BaseModel):
    id: str
    name: str
    type: str
    status: str
    lastUpdate: str
    dataPoints: int
    description: str
    latency: str


_SOURCES: List[dict] = [
    {
        "id": "alt-001",
        "name": "SEC 8-K Monitor",
        "type": "sec",
        "status": "active",
        "lastUpdate": (datetime.utcnow() - timedelta(minutes=12)).isoformat() + "Z",
        "dataPoints": 142_890,
        "description": "Real-time NLP processing of SEC 8-K filings with sentiment scoring",
        "latency": "<2 min",
    },
    {
        "id": "alt-002",
        "name": "Satellite Imagery Intelligence",
        "type": "satellite",
        "status": "active",
        "lastUpdate": (datetime.utcnow() - timedelta(hours=6)).isoformat() + "Z",
        "dataPoints": 38_400,
        "description": "Geospatial commodity intelligence — parking lots, oil tanks, crop yield",
        "latency": "6h",
    },
    {
        "id": "alt-003",
        "name": "Social Sentiment Engine",
        "type": "sentiment",
        "status": "active",
        "lastUpdate": (datetime.utcnow() - timedelta(minutes=3)).isoformat() + "Z",
        "dataPoints": 2_450_000,
        "description": "Real-time Twitter/Reddit/StockTwits sentiment aggregation with BERT models",
        "latency": "<1 min",
    },
    {
        "id": "alt-004",
        "name": "News NLP Pipeline",
        "type": "sentiment",
        "status": "active",
        "lastUpdate": (datetime.utcnow() - timedelta(minutes=8)).isoformat() + "Z",
        "dataPoints": 890_000,
        "description": "FinBERT-based news sentiment from 500+ financial news sources",
        "latency": "~5 min",
    },
    {
        "id": "alt-005",
        "name": "Credit Card Transaction Flow",
        "type": "social",
        "status": "inactive",
        "lastUpdate": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z",
        "dataPoints": 12_000_000,
        "description": "Anonymised consumer spending signals for retail sector analysis",
        "latency": "24h",
    },
]


@router.get("/sources", response_model=List[AlternativeDataSource])
async def get_sources():
    """Return all available alternative data sources."""
    return _SOURCES


@router.get("/sources/{source_id}", response_model=AlternativeDataSource)
async def get_source(source_id: str):
    """Return a single alternative data source."""
    src = next((s for s in _SOURCES if s["id"] == source_id), None)
    if not src:
        raise HTTPException(status_code=404, detail="Data source not found")
    return src


@router.get("/{source_id}")
async def get_alternative_data(
    source_id: str,
    ticker: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Return alternative data records for a source."""
    src = next((s for s in _SOURCES if s["id"] == source_id), None)
    if not src:
        raise HTTPException(status_code=404, detail="Data source not found")

    if src["type"] == "sec":
        return _sec_sample(ticker, limit)
    elif src["type"] == "sentiment":
        return _sentiment_sample(ticker, limit)
    elif src["type"] == "satellite":
        return _satellite_sample(ticker, limit)
    return {"sourceId": source_id, "records": []}


def _sec_sample(ticker: Optional[str], limit: int) -> List[dict]:
    tickers = [ticker.upper()] if ticker else ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM"]
    records = []
    for i, t in enumerate(tickers[:limit]):
        records.append(
            {
                "ticker": t,
                "filingDate": (datetime.utcnow() - timedelta(days=i * 3)).strftime(
                    "%Y-%m-%d"
                ),
                "formType": "8-K",
                "sentimentScore": round(0.62 + i * 0.03, 2),
                "headline": f"{t} reports material event",
            }
        )
    return records


def _sentiment_sample(ticker: Optional[str], limit: int) -> List[dict]:
    tickers = [ticker.upper()] if ticker else ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM"]
    records = []
    for i, t in enumerate(tickers[:limit]):
        records.append(
            {
                "ticker": t,
                "timestamp": (datetime.utcnow() - timedelta(minutes=i * 10)).isoformat()
                + "Z",
                "source": "Twitter",
                "sentimentScore": round(0.58 + i * 0.02, 2),
                "volume": 1200 + i * 150,
                "bullishPct": round(62 + i * 1.5, 1),
            }
        )
    return records


def _satellite_sample(ticker: Optional[str], limit: int) -> List[dict]:
    return [
        {
            "location": "Houston, TX",
            "assetType": "oil_tank",
            "fillLevel": 0.74,
            "changeWeekly": 0.05,
            "captureDate": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        }
    ]
