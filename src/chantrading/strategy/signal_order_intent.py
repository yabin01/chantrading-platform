"""Deterministic adapter from a completed 1M decision to OrderIntent.

T2 only translates an already-confirmed trade signal into the venue-neutral
execution contract. Quantity and execution parameters are supplied explicitly
by the caller; risk sizing and exchange-specific mapping remain downstream.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib

from chantrading.domain.execution import OrderIntent, OrderType, Side, TimeInForce
from chantrading.strategy.live_decision import DecisionSignal, SignalSide


@dataclass(frozen=True)
class OrderIntentContext:
    instrument_id: str
    quantity: Decimal
    decision_id: str
    signal_id: str
    client_order_id: str
    reduce_only: bool = False
    order_type: OrderType = OrderType.MARKET
    limit_price: Decimal | None = None
    trigger_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    post_only: bool = False


class SignalToOrderIntent:
    """Translate LONG/SHORT signals; HOLD never creates an intent."""

    def build(
        self, signal: DecisionSignal, context: OrderIntentContext
    ) -> OrderIntent | None:
        if signal.side is SignalSide.HOLD:
            return None
        if signal.trigger_fractal_id is None:
            raise ValueError("trade signal must have a confirmed trigger fractal")
        if context.quantity <= 0:
            raise ValueError("quantity must be positive")
        if not context.instrument_id:
            raise ValueError("instrument_id is required")
        if not context.decision_id or not context.signal_id:
            raise ValueError("decision_id and signal_id are required")
        if not context.client_order_id:
            raise ValueError("client_order_id is required")

        side = Side.BUY if signal.side is SignalSide.LONG else Side.SELL
        return OrderIntent(
            intent_id=self._intent_id(signal, context),
            instrument_id=context.instrument_id,
            side=side,
            quantity=context.quantity,
            order_type=context.order_type,
            limit_price=context.limit_price,
            trigger_price=context.trigger_price,
            time_in_force=context.time_in_force,
            reduce_only=context.reduce_only,
            post_only=context.post_only,
            client_order_id=context.client_order_id,
        )

    @staticmethod
    def _intent_id(signal: DecisionSignal, context: OrderIntentContext) -> str:
        material = "|".join((
            context.decision_id, context.signal_id, signal.side.value,
            signal.trigger_fractal_id or "", context.instrument_id,
            str(context.quantity), context.client_order_id,
        ))
        return "OI-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
