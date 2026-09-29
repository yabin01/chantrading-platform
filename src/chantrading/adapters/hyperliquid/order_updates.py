"""Normalize Hyperliquid Testnet order/fill/position updates."""
from __future__ import annotations
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class OrderUpdate:
    client_order_id: str | None
    exchange_order_id: str | None
    status: str
    symbol: str | None
    filled_quantity: str = "0"


@dataclass(frozen=True)
class FillUpdate:
    exchange_order_id: str | None
    symbol: str
    side: str
    quantity: str
    price: str
    timestamp: int


@dataclass(frozen=True)
class PositionUpdate:
    symbol: str
    size: str
    entry_price: str
    timestamp: int


def _data(message):
    payload=json.loads(message)
    return payload.get("data", {})


def parse_order_update(message: str | bytes) -> OrderUpdate:
    data=_data(message)
    if data.get("channel") != "orderUpdates":
        raise ValueError("not an orderUpdates message")
    item=data.get("data")
    if isinstance(item, list):
        item=item[0] if item else {}
    order=item.get("order", item)
    return OrderUpdate(
        client_order_id=order.get("cloid") or order.get("clientOrderId"),
        exchange_order_id=str(order.get("oid")) if order.get("oid") is not None else None,
        status=str(item.get("status") or order.get("status") or "UNKNOWN").upper(),
        symbol=order.get("coin"),
        filled_quantity=str(order.get("filledSz") or item.get("filledSz") or "0"),
    )


def parse_fill(message: str | bytes) -> FillUpdate:
    data=_data(message)
    if data.get("channel") != "userFills":
        raise ValueError("not a userFills message")
    item=data.get("data")
    if isinstance(item, list):
        item=item[0] if item else {}
    return FillUpdate(
        exchange_order_id=str(item.get("oid")) if item.get("oid") is not None else None,
        symbol=str(item.get("coin")),
        side=str(item.get("side")),
        quantity=str(item.get("sz")),
        price=str(item.get("px")),
        timestamp=int(item.get("time")),
    )


def parse_position(message: str | bytes) -> PositionUpdate:
    data=_data(message)
    if data.get("channel") != "clearinghouseState":
        raise ValueError("not a clearinghouseState message")
    states=data.get("data", {}).get("assetPositions", [])
    if not states:
        raise ValueError("missing asset position")
    p=states[0].get("position", states[0])
    return PositionUpdate(
        symbol=str(p.get("coin")),
        size=str(p.get("szi")),
        entry_price=str(p.get("entryPx") or "0"),
        timestamp=int(data.get("time") or 0),
    )
