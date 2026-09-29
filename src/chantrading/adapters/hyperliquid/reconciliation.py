"""Deterministic order/fill/position reconciliation."""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class DriftType(str, Enum):
    MISSING_LOCAL_ORDER="MISSING_LOCAL_ORDER"
    MISSING_VENUE_ORDER="MISSING_VENUE_ORDER"
    UNPROCESSED_FILL="UNPROCESSED_FILL"
    DUPLICATE_FILL="DUPLICATE_FILL"
    POSITION_DRIFT="POSITION_DRIFT"
    LIFECYCLE_DRIFT="LIFECYCLE_DRIFT"


@dataclass(frozen=True)
class ReconciliationDrift:
    kind: DriftType
    key: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationReport:
    consistent: bool
    drifts: tuple[ReconciliationDrift, ...]


def _order_key(order: dict) -> str:
    return str(order["oid"])


def _fill_key(fill: dict) -> str:
    if fill.get("tid") is not None:
        return str(fill["tid"])
    return f'{fill.get("hash","")}:{fill.get("oid","")}:{fill.get("time","")}'


def reconcile_orders(local_orders: dict[str, dict], venue_orders: list[dict]) -> list[ReconciliationDrift]:
    venue = {_order_key(o): o for o in venue_orders}
    drifts = []
    for oid in local_orders:
        if oid not in venue:
            drifts.append(ReconciliationDrift(DriftType.MISSING_VENUE_ORDER, oid))
    for oid in venue:
        if oid not in local_orders:
            drifts.append(ReconciliationDrift(DriftType.MISSING_LOCAL_ORDER, oid))
    return drifts


def reconcile_fills(processed_fill_ids: set[str], venue_fills: list[dict]) -> list[ReconciliationDrift]:
    seen: set[str] = set()
    drifts = []
    for fill in venue_fills:
        key = _fill_key(fill)
        if key in seen:
            drifts.append(ReconciliationDrift(DriftType.DUPLICATE_FILL, key))
        seen.add(key)
        if key not in processed_fill_ids:
            drifts.append(ReconciliationDrift(DriftType.UNPROCESSED_FILL, key, {"fill": fill}))
    return drifts


def reconcile_position(local_size: Decimal, venue_size: Decimal, tolerance: Decimal = Decimal("0")) -> list[ReconciliationDrift]:
    if abs(local_size - venue_size) <= tolerance:
        return []
    return [ReconciliationDrift(
        DriftType.POSITION_DRIFT,
        "position",
        {"local_size": str(local_size), "venue_size": str(venue_size)},
    )]


class ReconciliationEngine:
    def reconcile(self, local_orders, venue_orders, processed_fill_ids, venue_fills,
                  local_position: Decimal, venue_position: Decimal,
                  tolerance: Decimal = Decimal("0")) -> ReconciliationReport:
        drifts = reconcile_orders(local_orders, venue_orders)
        drifts += reconcile_fills(processed_fill_ids, venue_fills)
        drifts += reconcile_position(local_position, venue_position, tolerance)
        return ReconciliationReport(not drifts, tuple(drifts))
