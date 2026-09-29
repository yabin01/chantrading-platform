"""Testnet execution lifecycle boundary."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class OrderState(str, Enum):
    CREATED="CREATED"
    SIGNING="SIGNING"
    SUBMITTED="SUBMITTED"
    OPEN="OPEN"
    FILLED="FILLED"
    CANCELED="CANCELED"
    REJECTED="REJECTED"
    UNKNOWN="UNKNOWN"


@dataclass(frozen=True)
class TestnetOrderRequest:
    client_order_id: str
    symbol: str
    side: str
    quantity: str
    order_type: str
    reduce_only: bool = False


@dataclass(frozen=True)
class TestnetOrderState:
    client_order_id: str
    state: OrderState
    exchange_order_id: str | None = None
    filled_quantity: str = "0"


_TERMINAL={OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED}


def transition(current: OrderState, target: OrderState) -> OrderState:
    if current in _TERMINAL and target != current:
        raise ValueError("terminal order cannot transition")
    if current == OrderState.UNKNOWN and target == OrderState.CREATED:
        raise ValueError("UNKNOWN order cannot be recreated blindly")
    return target


class TestnetExecutionLifecycle:
    def __init__(self):
        self.orders: dict[str, TestnetOrderState] = {}

    def create(self, request: TestnetOrderRequest) -> TestnetOrderState:
        if request.client_order_id in self.orders:
            raise ValueError("duplicate client_order_id")
        state=TestnetOrderState(request.client_order_id, OrderState.CREATED)
        self.orders[request.client_order_id]=state
        return state

    def update(self, client_order_id: str, target: OrderState, exchange_order_id=None, filled_quantity="0"):
        current=self.orders[client_order_id]
        new=transition(current.state,target)
        state=TestnetOrderState(client_order_id,new,exchange_order_id,filled_quantity)
        self.orders[client_order_id]=state
        return state

    def can_retry(self, client_order_id: str) -> bool:
        state=self.orders[client_order_id].state
        return state not in {OrderState.SUBMITTED, OrderState.OPEN, OrderState.UNKNOWN}
