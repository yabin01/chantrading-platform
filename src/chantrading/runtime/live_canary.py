"""Read-only Testnet canary wiring for the live 1M ChanLun engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from chantrading.adapters.hyperliquid.live_testnet import LiveCandle, LiveTestnetCandleStream
from .live_chanlun import Live1MStructureEngine, LiveStructureEvent


@dataclass
class Live1MCanary:
    """Connect a Testnet 1M candle stream to the deterministic structural engine.

    This class is deliberately read-only: it receives candles, feeds the
    structural engine, and records observable counters. It has no execution
    or order-routing capability.
    """

    engine: Live1MStructureEngine = field(default_factory=Live1MStructureEngine)
    candles_received: int = 0
    structural_events: int = 0
    last_candle_timestamp_ms: int | None = None
    last_events: list[LiveStructureEvent] = field(default_factory=list)

    def on_candle(self, event: LiveCandle) -> None:
        if (
            self.last_candle_timestamp_ms is not None
            and event.timestamp_ms <= self.last_candle_timestamp_ms
        ):
            raise RuntimeError("canary requires strictly increasing candle timestamps")
        self.last_candle_timestamp_ms = event.timestamp_ms
        self.candles_received += 1
        emitted = self.engine.on_candle(event)
        self.last_events = emitted
        self.structural_events += len(emitted)

    def build_stream(self, ws_factory: Callable[..., Any]) -> LiveTestnetCandleStream:
        return LiveTestnetCandleStream(
            ws_factory=ws_factory,
            on_candle=self.on_candle,
        )

    def snapshot(self) -> dict[str, Any]:
        snapshot = self.engine.snapshot()
        snapshot.update({
            "candles_received": self.candles_received,
            "structural_events": self.structural_events,
            "last_candle_timestamp_ms": self.last_candle_timestamp_ms,
        })
        return snapshot
