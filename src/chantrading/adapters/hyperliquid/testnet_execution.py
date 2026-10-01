"""Hyperliquid Testnet execution primitives.

Contains both the venue-neutral T3 backend and the existing deterministic
testnet order lifecycle used by the execution harness.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from chantrading.domain.execution import (
    ExecutionResult, OrderIntent, OrderStatus, OrderType, Position, Side,
)


@dataclass(frozen=True)
class TestnetOrderRequest:
    client_order_id: str
    instrument: str
    side: str
    quantity: str
    order_type: str
    reduce_only: bool = False


class OrderState(str, Enum):
    CREATED = "CREATED"
    SIGNING = "SIGNING"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TestnetOrder:
    request: TestnetOrderRequest
    state: OrderState
    venue_order_id: str | None = None
    filled_quantity: str = "0"


_ALLOWED = {
    OrderState.CREATED: {
        OrderState.SIGNING, OrderState.REJECTED, OrderState.UNKNOWN,
    },
    OrderState.SIGNING: {
        OrderState.SUBMITTED, OrderState.REJECTED, OrderState.UNKNOWN,
    },
    OrderState.SUBMITTED: {
        OrderState.OPEN, OrderState.PARTIALLY_FILLED,
        OrderState.FILLED, OrderState.REJECTED, OrderState.UNKNOWN,
    },
    OrderState.OPEN: {
        OrderState.PARTIALLY_FILLED, OrderState.FILLED,
        OrderState.CANCELED, OrderState.UNKNOWN,
    },
    OrderState.PARTIALLY_FILLED: {
        OrderState.PARTIALLY_FILLED, OrderState.FILLED,
        OrderState.CANCELED, OrderState.UNKNOWN,
    },
    OrderState.FILLED: {OrderState.FILLED},
    OrderState.CANCELED: {OrderState.CANCELED},
    OrderState.REJECTED: {OrderState.REJECTED},
    OrderState.UNKNOWN: {OrderState.UNKNOWN},
}


def transition(current: OrderState, target: OrderState) -> OrderState:
    if target not in _ALLOWED[current]:
        raise ValueError(f"invalid order transition: {current.value} -> {target.value}")
    return target


class TestnetExecutionLifecycle:
    def __init__(self) -> None:
        self._orders: dict[str, TestnetOrder] = {}

    def create(self, request: TestnetOrderRequest) -> TestnetOrder:
        if request.client_order_id in self._orders:
            raise ValueError("duplicate client_order_id")
        order = TestnetOrder(request=request, state=OrderState.CREATED)
        self._orders[request.client_order_id] = order
        return order

    def update(
        self,
        client_order_id: str,
        state: OrderState,
        venue_order_id: str | None = None,
        filled_quantity: str = "0",
    ) -> TestnetOrder:
        current = self._orders[client_order_id]
        target = transition(current.state, state)
        order = TestnetOrder(
            request=current.request,
            state=target,
            venue_order_id=venue_order_id or current.venue_order_id,
            filled_quantity=filled_quantity,
        )
        self._orders[client_order_id] = order
        return order

    def can_retry(self, client_order_id: str) -> bool:
        # UNKNOWN means the exchange outcome is uncertain; never blindly retry.
        return self._orders[client_order_id].state not in {
            OrderState.UNKNOWN,
            OrderState.FILLED,
            OrderState.CANCELED,
            OrderState.REJECTED,
        }


@dataclass
class HyperliquidTestnetBackend:
    exchange: object
    account_address: str

    def submit(self, intent: OrderIntent) -> ExecutionResult:
        if intent.order_type is not OrderType.MARKET:
            raise ValueError("T3 currently supports MARKET intents only")
        if not intent.instrument_id:
            raise ValueError("instrument_id is required")
        if intent.quantity <= 0:
            raise ValueError("quantity must be positive")

        price = self._market_price(intent)
        result = self.exchange.order(
            intent.instrument_id,
            intent.side is Side.BUY,
            float(intent.quantity),
            price,
            {"limit": {"tif": "Ioc"}},
            reduce_only=intent.reduce_only,
            cloid=intent.client_order_id,
        )
        return self._execution_result(intent, result)

    def cancel(self, order_id: str) -> ExecutionResult:
        raise NotImplementedError("T3 submit only; cancellation is T4")

    def get_position(self, instrument_id: str) -> Position | None:
        raise NotImplementedError("position reconciliation is T4")

    def get_open_orders(self, instrument_id: str) -> list[dict]:
        raise NotImplementedError("open-order reconciliation is T4")

    def get_recent_fills(self, instrument_id: str):
        raise NotImplementedError("fill reconciliation is T4")

    def reconcile(self, instrument_id: str):
        raise NotImplementedError("reconciliation is T4")

    def _market_price(self, intent: OrderIntent) -> float:
        if not hasattr(self.exchange, "_slippage_price"):
            raise RuntimeError("injected Hyperliquid Exchange lacks market-price support")
        return float(self.exchange._slippage_price(
            intent.instrument_id, intent.side is Side.BUY, 0.05
        ))

    @staticmethod
    def _execution_result(intent: OrderIntent, result) -> ExecutionResult:
        if not isinstance(result, dict):
            return ExecutionResult(intent.intent_id, OrderStatus.UNKNOWN,
                                   client_order_id=intent.client_order_id)
        if result.get("status") != "ok":
            return ExecutionResult(
                intent.intent_id, OrderStatus.REJECTED,
                client_order_id=intent.client_order_id,
                evidence_ref=str(result),
            )
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        first = statuses[0] if statuses else {}
        if "filled" in first:
            status, oid = OrderStatus.FILLED, first["filled"].get("oid")
        elif "resting" in first:
            status, oid = OrderStatus.OPEN, first["resting"].get("oid")
        else:
            status, oid = OrderStatus.UNKNOWN, None
        return ExecutionResult(
            intent.intent_id, status,
            venue_order_id=str(oid) if oid is not None else None,
            client_order_id=intent.client_order_id,
            evidence_ref=str(result),
        )
