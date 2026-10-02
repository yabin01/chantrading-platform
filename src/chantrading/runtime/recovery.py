"""Recovery state machine primitives for live 1M stream recovery.

This module is transport-agnostic. It defines the lifecycle contract that the
live runtime and future exchange history providers can use.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from chantrading.runtime.event_store import SQLiteEventStore, StoredEvent


class RecoveryState(str, Enum):
    HEALTHY = "healthy"
    GAP_DETECTED = "gap_detected"
    WAITING_RECONNECT = "waiting_reconnect"
    RECOVERING = "recovering"
    VERIFYING = "verifying"
    RECOVERED = "recovered"


_ALLOWED_TRANSITIONS: dict[RecoveryState, frozenset[RecoveryState]] = {
    RecoveryState.HEALTHY: frozenset({RecoveryState.GAP_DETECTED}),
    RecoveryState.GAP_DETECTED: frozenset({RecoveryState.WAITING_RECONNECT}),
    RecoveryState.WAITING_RECONNECT: frozenset({RecoveryState.RECOVERING}),
    RecoveryState.RECOVERING: frozenset({RecoveryState.VERIFYING}),
    RecoveryState.VERIFYING: frozenset({RecoveryState.RECOVERED, RecoveryState.GAP_DETECTED}),
    RecoveryState.RECOVERED: frozenset({RecoveryState.HEALTHY}),
}


class RecoveryStateMachine:
    def __init__(self, initial: RecoveryState = RecoveryState.HEALTHY):
        self._state = initial

    @property
    def state(self) -> RecoveryState:
        return self._state

    def transition(self, target: RecoveryState) -> RecoveryState:
        if target == self._state or target not in _ALLOWED_TRANSITIONS[self._state]:
            raise ValueError(f"invalid recovery transition: {self._state.value} -> {target.value}")
        self._state = target
        return self._state

    def reset(self) -> RecoveryState:
        if self._state != RecoveryState.RECOVERED:
            raise ValueError(f"recovery reset requires recovered state, got {self._state.value}")
        return self.transition(RecoveryState.HEALTHY)


@dataclass(frozen=True)
class RecoveryResult:
    restored_events: int
    latest_sequence: int


class RuntimeRecovery:
    """Deterministic replay boundary over SQLiteEventStore."""

    def __init__(self, store: SQLiteEventStore):
        self.store = store

    def replay(self, handler: Callable[[StoredEvent], None]) -> RecoveryResult:
        restored = self.store.replay(handler)
        return RecoveryResult(restored_events=restored, latest_sequence=self.store.latest_sequence())
