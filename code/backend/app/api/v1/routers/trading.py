"""Trading operations router — orders management."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    ticker: str
    side: str  # "BUY" | "SELL"
    quantity: float
    orderType: str  # "MARKET" | "LIMIT" | "STOP"
    price: Optional[float] = None


class Order(BaseModel):
    id: str
    ticker: str
    side: str
    quantity: float
    orderType: str
    price: Optional[float]
    status: str
    timestamp: str
    filledAt: Optional[str] = None


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_ORDERS: List[dict] = [
    {
        "id": "ord-001",
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 100.0,
        "orderType": "MARKET",
        "price": None,
        "status": "filled",
        "timestamp": "2024-01-15T09:30:00Z",
        "filledAt": "2024-01-15T09:30:01Z",
    },
    {
        "id": "ord-002",
        "ticker": "MSFT",
        "side": "BUY",
        "quantity": 50.0,
        "orderType": "LIMIT",
        "price": 298.0,
        "status": "filled",
        "timestamp": "2024-01-20T10:15:00Z",
        "filledAt": "2024-01-20T10:15:32Z",
    },
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/orders", response_model=List[Order])
async def get_orders():
    """Return all orders."""
    return _ORDERS


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Return a single order."""
    order = next((o for o in _ORDERS if o["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders", response_model=Order, status_code=201)
async def create_order(payload: OrderCreate):
    """Submit a new trading order."""
    now = datetime.utcnow().isoformat() + "Z"
    order = {
        "id": f"ord-{uuid.uuid4().hex[:8]}",
        "ticker": payload.ticker.upper(),
        "side": payload.side,
        "quantity": payload.quantity,
        "orderType": payload.orderType,
        "price": payload.price,
        "status": "pending",
        "timestamp": now,
        "filledAt": None,
    }
    _ORDERS.append(order)
    return order


@router.delete("/orders/{order_id}", status_code=204)
async def cancel_order(order_id: str):
    """Cancel a pending order."""
    order = next((o for o in _ORDERS if o["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status '{order['status']}'",
        )
    order["status"] = "cancelled"
