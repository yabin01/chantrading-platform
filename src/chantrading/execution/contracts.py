"""Exchange-neutral adapter contracts."""
from __future__ import annotations

from typing import Callable, Iterable, Protocol

from chantrading.domain.execution import ExecutionResult, Fill, OrderIntent, Position


class ExecutionBackend(Protocol):
    def submit(self, intent: OrderIntent) -> ExecutionResult: ...
    def cancel(self, order_id: str) -> ExecutionResult: ...
    def get_position(self, instrument_id: str) -> Position | None: ...
    def get_open_orders(self, instrument_id: str) -> list[dict]: ...
    def get_recent_fills(self, instrument_id: str) -> list[Fill]: ...
    def reconcile(self, instrument_id: str) -> object: ...


class MarketDataBackend(Protocol):
    def subscribe_candles(
        self,
        instrument_id: str,
        interval: str,
        callback: Callable[[dict], None],
    ) -> str: ...

    def unsubscribe(self, subscription_id: str) -> None: ...


class CapabilityProvider(Protocol):
    def supports(self, capability: str) -> bool: ...


class Signer(Protocol):
    def sign(self, payload: dict) -> str: ...
