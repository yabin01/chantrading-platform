"""Raw WebSocket message router."""
from __future__ import annotations
from typing import Callable
from .normalizers import normalize_message


class HyperliquidEventRouter:
    def __init__(self, emit: Callable[[object], None]):
        self.emit = emit

    def on_message(self, message: dict, receive_time_ms: int) -> None:
        for event in normalize_message(message, receive_time_ms):
            self.emit(event)
