"""Injectable WebSocket transport boundary.

The default implementation is intentionally absent; production transport is
added only after the event normalization contract is stable.
"""
from __future__ import annotations
from typing import Callable, Protocol


class WebSocketTransport(Protocol):
    def connect(self, on_message: Callable[[dict], None], on_close: Callable[[], None]) -> None: ...
    def send(self, payload: dict) -> None: ...
    def close(self) -> None: ...


class InMemoryWebSocketTransport:
    def __init__(self):
        self.sent: list[dict] = []
        self.connected = False
        self._on_message = None
        self._on_close = None

    def connect(self, on_message, on_close) -> None:
        self.connected = True
        self._on_message = on_message
        self._on_close = on_close

    def send(self, payload: dict) -> None:
        if not self.connected:
            raise RuntimeError("transport is not connected")
        self.sent.append(payload)

    def emit(self, message: dict) -> None:
        if self.connected and self._on_message:
            self._on_message(message)

    def close(self) -> None:
        was_connected = self.connected
        self.connected = False
        if was_connected and self._on_close:
            self._on_close()
