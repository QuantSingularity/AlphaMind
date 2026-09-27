"""
Service layer for AlphaMind API.

Business logic sits between routers and the DB / execution layers.
Each service accepts an ``AsyncSession`` in its constructor so that a
single session - and therefore a single transaction - is shared across
all service calls within one request.

FastAPI dependency factories are provided here so routers can stay thin:

    @router.get("/")
    async def get_portfolio(svc: PortfolioService = Depends(get_portfolio_service)):
        return await svc.get_portfolio()
"""

from __future__ import annotations

from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.risk_service import RiskService
from app.services.strategy_service import StrategyService
from app.services.trading_service import TradingService
from db.session import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------


async def get_portfolio_service(
    session: AsyncSession = Depends(get_db),
) -> PortfolioService:
    return PortfolioService(session)


async def get_trading_service(
    session: AsyncSession = Depends(get_db),
) -> TradingService:
    return TradingService(session)


async def get_strategy_service(
    session: AsyncSession = Depends(get_db),
) -> StrategyService:
    return StrategyService(session)


async def get_risk_service(
    session: AsyncSession = Depends(get_db),
) -> RiskService:
    return RiskService(session)


# MarketDataService is stateless (holds only config from env), so we can
# share a singleton rather than constructing per-request.
_market_data_service = MarketDataService()


async def get_market_data_service() -> MarketDataService:
    return _market_data_service


__all__ = [
    "PortfolioService",
    "TradingService",
    "StrategyService",
    "RiskService",
    "MarketDataService",
    "get_portfolio_service",
    "get_trading_service",
    "get_strategy_service",
    "get_risk_service",
    "get_market_data_service",
]
