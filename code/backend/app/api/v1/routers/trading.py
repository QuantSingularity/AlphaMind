"""Trading operations router - order submission and management."""

from typing import Any, Dict, List, Optional

from app.services import TradingService, get_trading_service
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    ticker: str
    side: str  # BUY | SELL
    quantity: float
    orderType: str  # MARKET | LIMIT | STOP
    price: Optional[float] = None

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        v = v.upper()
        if v not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        return v

    @field_validator("orderType")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        v = v.upper()
        if v not in {"MARKET", "LIMIT", "STOP"}:
            raise ValueError("orderType must be MARKET, LIMIT, or STOP")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v


class Order(BaseModel):
    id: str
    ticker: str
    side: str
    quantity: float
    orderType: str
    price: Optional[float] = None
    filledPrice: Optional[float] = None
    status: str
    timestamp: Optional[str] = None
    filledAt: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/orders", response_model=List[Order])
async def get_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    svc: TradingService = Depends(get_trading_service),
) -> List[Dict[str, Any]]:
    """Return all orders, optionally filtered by status."""
    return await svc.get_orders(status=status)


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    svc: TradingService = Depends(get_trading_service),
) -> Dict[str, Any]:
    """Return a single order by ID."""
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders", response_model=Order, status_code=201)
async def create_order(
    payload: OrderCreate,
    svc: TradingService = Depends(get_trading_service),
) -> Dict[str, Any]:
    """Submit a new trading order."""
    return await svc.create_order(
        ticker=payload.ticker,
        side=payload.side,
        quantity=payload.quantity,
        order_type=payload.orderType,
        price=payload.price,
    )


@router.delete("/orders/{order_id}", status_code=204)
async def cancel_order(
    order_id: str,
    svc: TradingService = Depends(get_trading_service),
) -> None:
    """Cancel a pending order."""
    result = await svc.cancel_order(order_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found or is not in a cancellable state",
        )
