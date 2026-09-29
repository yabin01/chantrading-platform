"""Deterministic in-process runtime event bus."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class RuntimeEvent:
    name: str
    timestamp_ms: int
    payload: dict[str, Any]


class RuntimeEventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable[[RuntimeEvent], None]]] = {}
        self.history: list[RuntimeEvent] = []

    def subscribe(self, name: str, handler: Callable[[RuntimeEvent], None]):
        self._handlers.setdefault(name, []).append(handler)

    def publish(self, event: RuntimeEvent):
        self.history.append(event)
        for handler in tuple(self._handlers.get(event.name, ())):
            handler(event)

    def clear_history(self):
        self.history.clear()
