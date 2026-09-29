"""Stream health model."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    RESYNCING = "RESYNCING"


@dataclass
class StreamHealth:
    state: HealthState = HealthState.STALE
    last_event_ms: int | None = None
    last_pong_ms: int | None = None
    counters: dict[str, int] = field(default_factory=dict)

    def observe_event(self, now_ms: int) -> None:
        self.last_event_ms = now_ms
        self.state = HealthState.HEALTHY

    def observe_pong(self, now_ms: int) -> None:
        self.last_pong_ms = now_ms

    def mark_resyncing(self) -> None:
        self.state = HealthState.RESYNCING

    def evaluate(self, now_ms: int, event_stale_ms: int, pong_stale_ms: int) -> HealthState:
        if self.state == HealthState.RESYNCING:
            return self.state
        event_stale = self.last_event_ms is None or now_ms - self.last_event_ms > event_stale_ms
        pong_stale = self.last_pong_ms is None or now_ms - self.last_pong_ms > pong_stale_ms
        if event_stale and pong_stale:
            self.state = HealthState.STALE
        elif event_stale or pong_stale:
            self.state = HealthState.DEGRADED
        else:
            self.state = HealthState.HEALTHY
        return self.state
