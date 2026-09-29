"""Minimal deterministic event store and replay boundary."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class StoredEvent:
    sequence: int
    event_id: str
    timestamp: int
    payload: object


class DeterministicEventStore:
    def __init__(self):
        self._events: list[StoredEvent] = []
        self._ids: set[str] = set()

    def append(self, event) -> StoredEvent:
        if event.event_id in self._ids:
            raise ValueError(f"duplicate event: {event.event_id}")
        if self._events and event.timestamp < self._events[-1].timestamp:
            raise ValueError("event timestamp moved backwards")
        stored=StoredEvent(
            sequence=len(self._events),
            event_id=event.event_id,
            timestamp=event.timestamp,
            payload=event,
        )
        self._events.append(stored)
        self._ids.add(event.event_id)
        return stored

    def events(self) -> tuple[StoredEvent, ...]:
        return tuple(self._events)

    def replay(self, reducer: Callable[[object, object], object], initial_state):
        state=initial_state
        for stored in self._events:
            state=reducer(state, stored.payload)
        return state


def replay_events(events: Iterable[StoredEvent], reducer, initial_state):
    state=initial_state
    for stored in sorted(events, key=lambda x: x.sequence):
        state=reducer(state, stored.payload)
    return state
