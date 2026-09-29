"""Pure WebSocket message normalizers."""
from __future__ import annotations
from decimal import Decimal
from typing import Any
from .events import AdapterEvent


def _event(event_id: str, channel: str, data: Any, event_time_ms: int, receive_time_ms: int, raw: Any) -> AdapterEvent:
    return AdapterEvent(event_id, channel, event_time_ms, receive_time_ms, data, raw)


def normalize_candle(message: dict, receive_time_ms: int) -> AdapterEvent:
    data = message["data"]
    return _event(
        f"candle:{data['s']}:{data['i']}:{data['t']}",
        "candle",
        {
            "instrument": str(data["s"]),
            "interval": str(data["i"]),
            "open_time_ms": int(data["t"]),
            "close_time_ms": int(data["T"]),
            "open": Decimal(str(data["o"])),
            "high": Decimal(str(data["h"])),
            "low": Decimal(str(data["l"])),
            "close": Decimal(str(data["c"])),
            "volume": Decimal(str(data["v"])),
            "final": int(data["T"]) <= receive_time_ms,
        },
        int(data["T"]),
        receive_time_ms,
        message,
    )


def normalize_user_fills(message: dict, receive_time_ms: int) -> list[AdapterEvent]:
    data = message["data"]
    events = []
    for fill in data.get("fills", []):
        tid = str(fill.get("tid") or fill.get("hash") or fill.get("oid"))
        events.append(_event(
            f"fill:{tid}",
            "userFills",
            fill,
            int(fill.get("time") or receive_time_ms),
            receive_time_ms,
            message,
        ))
    return events


def normalize_order_updates(message: dict, receive_time_ms: int) -> list[AdapterEvent]:
    data = message["data"]
    if not isinstance(data, list):
        data = [data]
    events = []
    for item in data:
        order = item.get("order", item) if isinstance(item, dict) else item
        oid = str(order.get("oid") or item.get("oid") if isinstance(order, dict) else "")
        status = str(item.get("status") or item.get("orderStatus") or "")
        events.append(_event(
            f"order:{oid}:{status}",
            "orderUpdates",
            item,
            int(item.get("statusTimestamp") or item.get("timestamp") or receive_time_ms),
            receive_time_ms,
            message,
        ))
    return events


def normalize_message(message: dict, receive_time_ms: int) -> list[AdapterEvent]:
    channel = message.get("channel")
    if channel == "candle":
        return [normalize_candle(message, receive_time_ms)]
    if channel == "userFills":
        return normalize_user_fills(message, receive_time_ms)
    if channel == "orderUpdates":
        return normalize_order_updates(message, receive_time_ms)
    return [_event(
        f"raw:{channel}:{receive_time_ms}",
        str(channel),
        message.get("data"),
        receive_time_ms,
        receive_time_ms,
        message,
    )]
