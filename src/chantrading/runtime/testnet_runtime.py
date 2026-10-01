"""Hyperliquid Testnet -> Live ChanLun runtime bridge.

Phase 1 foundation only:
- consumes existing LiveTestnetCandleStream
- forwards validated 1m candles into Live1MStructureEngine
- keeps execution out of this module
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chantrading.adapters.hyperliquid.live_testnet import LiveTestnetCandleStream
from chantrading.runtime.live_chanlun import Live1MStructureEngine, LiveStructureEvent


@dataclass
class TestnetRuntime:
    """Minimal live runtime composition for Hyperliquid Testnet canary."""

    structure_engine: Live1MStructureEngine = field(default_factory=Live1MStructureEngine)
    received_events: list[LiveStructureEvent] = field(default_factory=list)

    def on_candle(self, candle: Any) -> None:
        self.received_events.extend(self.structure_engine.on_candle(candle))

    def create_candle_stream(self, ws_factory: Any) -> LiveTestnetCandleStream:
        return LiveTestnetCandleStream(
            ws_factory=ws_factory,
            on_candle=self.on_candle,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "structure": self.structure_engine.snapshot(),
            "runtime_events": len(self.received_events),
        }
