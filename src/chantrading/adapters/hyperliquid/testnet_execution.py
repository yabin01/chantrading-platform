"""Hyperliquid Testnet execution backend.

Maps the venue-neutral OrderIntent into the official Hyperliquid SDK
Exchange.order contract. The backend is dependency-light: the SDK Exchange
instance is injected by the caller, so tests never sign or submit an order.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from chantrading.domain.execution import (
    ExecutionResult, OrderIntent, OrderStatus, OrderType, Position, Side,
)


@dataclass
class HyperliquidTestnetBackend:
    exchange: object
    account_address: str

    def submit(self, intent: OrderIntent) -> ExecutionResult:
        if intent.order_type is not OrderType.MARKET:
            raise ValueError("T3 currently supports MARKET intents only")
        if intent.instrument_id == "":
            raise ValueError("instrument_id is required")
        if intent.quantity <= 0:
            raise ValueError("quantity must be positive")

        # Hyperliquid SDK represents a market order as an aggressive IOC limit.
        # The adapter obtains the SDK-compatible limit price from the injected
        # exchange; no private key/signing logic lives in ChanTrading Core.
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
        return float(
            self.exchange._slippage_price(
                intent.instrument_id,
                intent.side is Side.BUY,
                0.05,
            )
        )

    @staticmethod
    def _execution_result(intent: OrderIntent, result) -> ExecutionResult:
        if not isinstance(result, dict):
            return ExecutionResult(
                intent.intent_id, OrderStatus.UNKNOWN,
                client_order_id=intent.client_order_id,
            )
        if result.get("status") != "ok":
            return ExecutionResult(
                intent.intent_id, OrderStatus.REJECTED,
                client_order_id=intent.client_order_id,
                evidence_ref=str(result),
            )

        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        first = statuses[0] if statuses else {}
        if "filled" in first:
            status = OrderStatus.FILLED
            oid = first["filled"].get("oid")
        elif "resting" in first:
            status = OrderStatus.OPEN
            oid = first["resting"].get("oid")
        else:
            status = OrderStatus.UNKNOWN
            oid = None
        return ExecutionResult(
            intent.intent_id, status,
            venue_order_id=str(oid) if oid is not None else None,
            client_order_id=intent.client_order_id,
            evidence_ref=str(result),
        )
