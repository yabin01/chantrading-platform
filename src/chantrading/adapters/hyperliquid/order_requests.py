"""Canonical order mutation requests."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TimeInForce(str, Enum):
    GTC="Gtc"; IOC="Ioc"; ALO="Alo"


@dataclass(frozen=True)
class LimitOrderRequest:
    instrument: str
    is_buy: bool
    quantity: Decimal
    limit_price: Decimal
    tif: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    client_order_id: str | None = None


@dataclass(frozen=True)
class CancelOrderRequest:
    instrument: str
    order_id: int | None = None
    client_order_id: str | None = None
