"""Pure venue-to-domain mappers."""
from __future__ import annotations
from decimal import Decimal
from typing import Any
from chantrading.domain.execution import Fill, Position, Side

def _decimal(value: Any) -> Decimal:
    if value is None:
        raise ValueError("numeric field is missing")
    return Decimal(str(value))

def map_fill(raw: dict) -> Fill:
    raw_side = str(raw.get("side", "")).upper()
    side_map = {"B": Side.BUY, "BUY": Side.BUY, "A": Side.SELL, "SELL": Side.SELL}
    if raw_side not in side_map:
        raise ValueError(f"unsupported fill side: {raw_side!r}")
    return Fill(
        fill_id=str(raw.get("tid") or raw.get("hash") or raw.get("id")),
        order_id=str(raw.get("oid") or ""),
        instrument_id=str(raw["coin"]),
        side=side_map[raw_side],
        quantity=_decimal(raw["sz"]),
        price=_decimal(raw["px"]),
        timestamp_ms=int(raw.get("time") or 0),
    )

def map_position(raw: dict) -> Position:
    position = raw.get("position", raw)
    return Position(
        instrument_id=str(position.get("coin") or ""),
        size=_decimal(position.get("szi", "0")),
        entry_price=_decimal(position["entryPx"]) if position.get("entryPx") is not None else None,
        liquidation_price=_decimal(position["liquidationPx"]) if position.get("liquidationPx") is not None else None,
        unrealized_pnl=_decimal(position["unrealizedPnl"]) if position.get("unrealizedPnl") is not None else None,
        leverage=int(position["leverage"]["value"]) if isinstance(position.get("leverage"), dict) and position["leverage"].get("value") is not None else None,
    )

def map_positions(clearinghouse_state: dict) -> list[Position]:
    return [map_position(item["position"]) for item in clearinghouse_state.get("assetPositions", []) if item.get("position") is not None]
