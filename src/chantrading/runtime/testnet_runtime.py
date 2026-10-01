"""Hyperliquid Testnet -> Live ChanLun runtime bridge.

Phase 1 foundation only:
- consumes existing LiveTestnetCandleStream
- forwards validated 1m candles into Live1MStructureEngine
- optionally persists runtime events through existing EventStore
- keeps execution out of this module
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chantrading.adapters.hyperliquid.live_testnet import LiveTestnetCandleStream
from chantrading.runtime.live_chanlun import Live1MStructureEngine, LiveStructureEvent
from chantrading.runtime.event_store import SQLiteEventStore


@dataclass
class TestnetRuntime:
    """Minimal live runtime composition for Hyperliquid Testnet canary."""

    structure_engine: Live1MStructureEngine = field(default_factory=Live1MStructureEngine)
    received_events: list[LiveStructureEvent] = field(default_factory=list)
    event_store: SQLiteEventStore | None = None
    _event_sequence: int = 0

    def on_candle(self, candle: Any) -> None:
        events = self.structure_engine.on_candle(candle)
        self.received_events.extend(events)
        self._persist(events)

    def _persist(self, events: list[LiveStructureEvent]) -> None:
        if self.event_store is None:
            return

        for event in events:
            self._event_sequence += 1
            event_id = f"testnet-runtime-{self._event_sequence}"
            self.event_store.append(
                event_id=event_id,
                name=event.type,
                timestamp_ms=event.timestamp_ms,
                payload=event.payload,
            )

    def restore_event_count(self) -> int:
        """Restore only runtime sequence position from durable events.

        Full ChanLun state reconstruction remains delegated to existing replay
        components. This Phase 1 hook prevents duplicate event identifiers
        after a runtime restart.
        """
        if self.event_store is None:
            return 0

        count = self.event_store.count()
        self._event_sequence = count
        return count

    def create_candle_stream(self, ws_factory: Any) -> LiveTestnetCandleStream:
        return LiveTestnetCandleStream(
            ws_factory=ws_factory,
            on_candle=self.on_candle,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "structure": self.structure_engine.snapshot(),
            "runtime_events": len(self.received_events),
            "stored_events": (
                self.event_store.count()
                if self.event_store is not None
                else 0
            ),
            "event_sequence": self._event_sequence,
        }
