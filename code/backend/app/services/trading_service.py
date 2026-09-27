"""
Trading service - order submission, cancellation, and lifecycle management.

Orders are persisted to the database via OrderRepository.  When a MARKET
order is submitted it is immediately "filled" (simulated fill) so the UI
reflects a realistic order flow.  A fill price is only recorded when a
reference price is available - if none is provided, filled_price is left
as None to avoid returning a meaningless $100 sentinel.

LIMIT and STOP orders remain pending until an explicit fill trigger.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.repositories.order_repository import OrderRepository
from sqlalchemy.ext.asyncio import AsyncSession

_DEFAULT_PORTFOLIO_ID = "port-001"
_SLIPPAGE = 0.0005  # 0.05 % market-order slippage


class TradingService:
    """Handles order creation, retrieval, and cancellation."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrderRepository(session)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_orders(
        self,
        portfolio_id: str = _DEFAULT_PORTFOLIO_ID,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        orders = await self._repo.get_by_portfolio(
            portfolio_id, limit=200, status=status
        )
        return [self._order_to_dict(o) for o in orders]

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        order = await self._repo.get(order_id)
        if order is None:
            return None
        return self._order_to_dict(order)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def create_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None,
        portfolio_id: str = _DEFAULT_PORTFOLIO_ID,
    ) -> Dict[str, Any]:
        """
        Persist a new order.

        MARKET orders are immediately simulated as filled.
        Fill price = submitted price * (1 + slippage) when a price is given.
        If no price is given for a market order, filled_price remains None
        (a live system would fetch the current market price here).

        LIMIT / STOP orders remain pending.
        """
        # BUG-9 fix: only apply slippage when caller supplies a reference price.
        # Using a hard-coded $100 sentinel was semantically wrong.
        now = datetime.now(timezone.utc)
        order_id = f"ord-{uuid.uuid4().hex[:8]}"
        is_market = order_type.upper() == "MARKET"

        if is_market and price is not None:
            filled_price: Optional[float] = round(price * (1 + _SLIPPAGE), 4)
        else:
            filled_price = None

        order = await self._repo.create(
            id=order_id,
            portfolio_id=portfolio_id,
            ticker=ticker.upper(),
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=quantity,
            price=price,
            filled_price=filled_price,
            status="filled" if is_market else "pending",
            created_at=now,
            filled_at=now if is_market else None,
            updated_at=now,
        )
        return self._order_to_dict(order)

    async def cancel_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Cancel a pending order.

        Returns None if the order does not exist or is not cancellable.
        """
        order = await self._repo.get(order_id)
        if order is None or order.status != "pending":
            return None
        updated = await self._repo.update(
            order_id,
            status="cancelled",
            updated_at=datetime.now(timezone.utc),
        )
        if updated is None:
            return None
        return self._order_to_dict(updated)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _order_to_dict(o: Any) -> Dict[str, Any]:
        return {
            "id": o.id,
            "ticker": o.ticker,
            "side": o.side,
            "quantity": o.quantity,
            "orderType": o.order_type,
            "price": o.price,
            "filledPrice": o.filled_price,
            "status": o.status,
            "timestamp": o.created_at.isoformat() if o.created_at else None,
            "filledAt": o.filled_at.isoformat() if o.filled_at else None,
        }
