"""Canonical order lifecycle and UNKNOWN recovery."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class OrderState(str, Enum):
    CREATED="CREATED"; SUBMITTING="SUBMITTING"; SUBMITTED="SUBMITTED"
    ACKNOWLEDGED="ACKNOWLEDGED"; RESTING="RESTING"; PARTIAL="PARTIAL"
    FILLED="FILLED"; CANCELED="CANCELED"; REJECTED="REJECTED"
    EXPIRED="EXPIRED"; UNKNOWN="UNKNOWN"


TERMINAL={OrderState.FILLED,OrderState.CANCELED,OrderState.REJECTED,OrderState.EXPIRED}


@dataclass
class OrderLifecycle:
    state: OrderState = OrderState.CREATED
    native_oid: int | None = None
    client_order_id: str | None = None

    def transition(self, state: OrderState, oid: int | None = None) -> None:
        if self.state in TERMINAL and state != self.state:
            raise ValueError(f"terminal order cannot transition: {self.state}->{state}")
        if state == OrderState.FILLED and self.state not in {
            OrderState.SUBMITTED, OrderState.ACKNOWLEDGED, OrderState.RESTING, OrderState.PARTIAL
        }:
            raise ValueError("FILLED requires an acknowledged/submitted order")
        if oid is not None:
            self.native_oid = oid
        self.state = state

    @property
    def retry_allowed(self) -> bool:
        return self.state in {OrderState.CREATED, OrderState.REJECTED}

    @property
    def execution_final(self) -> bool:
        return self.state in TERMINAL


def resolve_order_status(status_payload: dict) -> OrderState:
    if status_payload.get("status") == "unknownOid":
        return OrderState.UNKNOWN
    order = status_payload.get("order", status_payload)
    status = str(order.get("status", "")).lower()
    mapping = {
        "open": OrderState.RESTING,
        "filled": OrderState.FILLED,
        "canceled": OrderState.CANCELED,
        "rejected": OrderState.REJECTED,
        "triggered": OrderState.ACKNOWLEDGED,
        "margincanceled": OrderState.CANCELED,
        "reduceonlycanceled": OrderState.CANCELED,
    }
    return mapping.get(status, OrderState.UNKNOWN)
