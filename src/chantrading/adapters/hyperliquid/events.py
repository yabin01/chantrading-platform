"""Canonical WebSocket event envelope."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterEvent:
    event_id: str
    channel: str
    event_time_ms: int
    receive_time_ms: int
    data: Any
    raw: Any = None
