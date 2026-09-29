"""Top-level Hyperliquid adapter.

The first implementation is deliberately transport-light: it establishes the
stable boundary without leaking SDK-specific objects into ChanTrading Core.
"""
from __future__ import annotations

from chantrading.domain.execution import ExecutionResult, OrderIntent, OrderStatus, Position
from chantrading.adapters.hyperliquid.capabilities import HyperliquidCapabilities
from chantrading.adapters.hyperliquid.config import HyperliquidConfig


class HyperliquidAdapter:
    def __init__(
        self,
        config: HyperliquidConfig,
        backend=None,
        capabilities: HyperliquidCapabilities | None = None,
    ) -> None:
        self.config = config
        self.backend = backend
        self.capabilities = capabilities or HyperliquidCapabilities()

    def submit(self, intent: OrderIntent) -> ExecutionResult:
        if intent.reduce_only and not self.capabilities.reduce_only:
            return ExecutionResult(intent.intent_id, OrderStatus.REJECTED)
        if self.backend is None:
            raise RuntimeError("Hyperliquid backend is not configured")
        return self.backend.submit(intent)

    def cancel(self, order_id: str) -> ExecutionResult:
        if self.backend is None:
            raise RuntimeError("Hyperliquid backend is not configured")
        return self.backend.cancel(order_id)

    def get_position(self, instrument_id: str) -> Position | None:
        if self.backend is None:
            raise RuntimeError("Hyperliquid backend is not configured")
        return self.backend.get_position(instrument_id)

    def get_open_orders(self, instrument_id: str) -> list[dict]:
        if self.backend is None:
            raise RuntimeError("Hyperliquid backend is not configured")
        return self.backend.get_open_orders(instrument_id)

    def get_recent_fills(self, instrument_id: str):
        if self.backend is None:
            raise RuntimeError("Hyperliquid backend is not configured")
        return self.backend.get_recent_fills(instrument_id)

    def reconcile(self, instrument_id: str):
        if self.backend is None:
            raise RuntimeError("Hyperliquid backend is not configured")
        return self.backend.reconcile(instrument_id)
