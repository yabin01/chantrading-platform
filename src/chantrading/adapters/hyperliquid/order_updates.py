"""Normalize Hyperliquid Testnet order/fill/position updates."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


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


def _payload(message: str | bytes) -> tuple[str, Any]:
    payload = json.loads(message)
    return str(payload.get("channel", "")), payload.get("data")


def parse_order_update(message: str | bytes) -> OrderUpdate:
    channel, data = _payload(message)
    if channel != "orderUpdates":
        raise ValueError("not an orderUpdates message")

    if isinstance(data, list):
        item = data[0] if data else {}
    elif isinstance(data, dict):
        item = data
    else:
        item = {}

    order = item.get("order", item)
    if not isinstance(order, dict):
        order = {}

    return OrderUpdate(
        client_order_id=order.get("cloid") or order.get("clientOrderId"),
        exchange_order_id=str(order.get("oid")) if order.get("oid") is not None else None,
        status=str(item.get("status") or order.get("status") or "UNKNOWN").upper(),
        symbol=order.get("coin"),
        filled_quantity=str(order.get("filledSz") or item.get("filledSz") or "0"),
    )


def parse_fill(message: str | bytes) -> FillUpdate:
    channel, data = _payload(message)
    if channel != "userFills":
        raise ValueError("not a userFills message")

    if isinstance(data, dict):
        fills = data.get("fills", [])
        item = fills[0] if isinstance(fills, list) and fills else data
    elif isinstance(data, list):
        item = data[0] if data else {}
    else:
        item = {}

    if not isinstance(item, dict):
        raise ValueError("missing fill payload")

    return FillUpdate(
        exchange_order_id=str(item.get("oid")) if item.get("oid") is not None else None,
        symbol=str(item.get("coin")),
        side=str(item.get("side")),
        quantity=str(item.get("sz")),
        price=str(item.get("px")),
        timestamp=int(item.get("time")),
    )


def parse_position(message: str | bytes) -> PositionUpdate:
    channel, data = _payload(message)
    if channel != "clearinghouseState":
        raise ValueError("not a clearinghouseState message")
    if not isinstance(data, dict):
        raise ValueError("missing clearinghouse payload")

    states = data.get("assetPositions", [])
    if not states:
        raise ValueError("missing asset position")

    state = states[0]
    p = state.get("position", state) if isinstance(state, dict) else {}
    if not isinstance(p, dict):
        raise ValueError("missing asset position")

    return PositionUpdate(
        symbol=str(p.get("coin")),
        size=str(p.get("szi")),
        entry_price=str(p.get("entryPx") or "0"),
        timestamp=int(data.get("time") or 0),
    )
