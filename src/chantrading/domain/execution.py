"""Venue-neutral execution domain models for ChanTrading.

This module intentionally contains no exchange-specific imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    ALO = "ALO"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTING = "SUBMITTING"
    UNKNOWN = "UNKNOWN"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    instrument_id: str
    side: Side
    quantity: Decimal
    order_type: OrderType
    limit_price: Optional[Decimal] = None
    trigger_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    post_only: bool = False
    client_order_id: Optional[str] = None


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    instrument_id: str
    side: Side
    quantity: Decimal
    price: Decimal
    timestamp_ms: int


@dataclass(frozen=True)
class Position:
    instrument_id: str
    size: Decimal
    entry_price: Optional[Decimal]
    liquidation_price: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    leverage: Optional[int]


@dataclass(frozen=True)
class ExecutionResult:
    intent_id: str
    status: OrderStatus
    venue_order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    evidence_ref: Optional[str] = None


@dataclass
class ReconciliationResult:
    status: str
    details: dict = field(default_factory=dict)
