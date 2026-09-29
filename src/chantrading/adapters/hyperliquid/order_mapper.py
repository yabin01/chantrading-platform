"""Map canonical order mutations into Hyperliquid action payloads."""
from __future__ import annotations
from .order_requests import CancelOrderRequest, LimitOrderRequest


def map_limit_order(request: LimitOrderRequest, asset_id: int) -> dict:
    if request.quantity <= 0 or request.limit_price <= 0:
        raise ValueError("quantity and limit_price must be positive")
    if request.tif == "Alo" and request.reduce_only:
        # Keep policy explicit; venue acceptance must be tested before enablement.
        pass
    order = {
        "a": asset_id,
        "b": request.is_buy,
        "p": str(request.limit_price),
        "s": str(request.quantity),
        "r": request.reduce_only,
        "t": {"limit": {"tif": request.tif.value}},
    }
    if request.client_order_id:
        order["c"] = request.client_order_id
    return {"type": "order", "orders": [order], "grouping": "na"}


def map_cancel(request: CancelOrderRequest, asset_id: int) -> dict:
    if request.order_id is None:
        raise ValueError("order_id is required for v4.4.19 cancel")
    return {"type": "cancel", "cancels": [{"a": asset_id, "o": request.order_id}]}
