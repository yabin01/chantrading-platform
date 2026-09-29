"""Production-oriented WebSocket transport boundary."""
from __future__ import annotations
import json
from typing import Callable, Protocol

class WebSocketTransport(Protocol):
    def connect(self, on_message: Callable[[dict], None], on_close: Callable[[], None]) -> None: ...
    def send(self, payload: dict) -> None: ...
    def close(self) -> None: ...

class WebSocketAppTransport:
    """Adapter around websocket-client; import is lazy for test isolation."""
    def __init__(self, url: str):
        self.url = url
        self._ws = None

    def connect(self, on_message, on_close) -> None:
        import websocket
        self._ws = websocket.WebSocketApp(
            self.url,
            on_message=lambda _ws, message: on_message(json.loads(message)),
            on_close=lambda *_args: on_close(),
        )
        self._ws.run_forever()

    def send(self, payload: dict) -> None:
        if self._ws is None:
            raise RuntimeError("websocket transport is not connected")
        self._ws.send(json.dumps(payload))

    def close(self) -> None:
        if self._ws is not None:
            self._ws.close()

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
