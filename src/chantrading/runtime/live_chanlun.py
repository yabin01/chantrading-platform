"""Live 1M ChanLun structural integration.

This module intentionally stops at the implemented structural boundary:
Hyperliquid 1M candle -> FractalEngine -> Strict BiEngine.

It is read-only and does not submit orders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chantrading.chanlun import Bi, BiEngine, Candle, Fractal, FractalEngine
from chantrading.adapters.hyperliquid.live_testnet import LiveCandle


@dataclass(frozen=True)
class LiveStructureEvent:
    type: str
    timestamp_ms: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Live1MStructureEngine:
    fractal: FractalEngine = field(default_factory=FractalEngine)
    bi: BiEngine = field(default_factory=BiEngine)
    candles_processed: int = 0
    events: list[LiveStructureEvent] = field(default_factory=list)
    latest_candle: LiveCandle | None = None
    latest_fractal: Fractal | None = None
    latest_bi: Bi | None = None

    def on_candle(self, event: LiveCandle) -> list[LiveStructureEvent]:
        if event.interval != "1m":
            raise ValueError("Live1MStructureEngine accepts only 1m candles")

        candle = Candle(
            timestamp=event.timestamp_ms,
            open=float(event.open),
            high=float(event.high),
            low=float(event.low),
            close=float(event.close),
            volume=float(event.volume),
        )

        self.latest_candle = event
        self.candles_processed += 1
        emitted: list[LiveStructureEvent] = [
            LiveStructureEvent(
                "CANDLE_ACCEPTED",
                event.timestamp_ms,
                {"coin": event.coin, "interval": event.interval},
            )
        ]

        fractal_events = self.fractal.update(candle)
        for fe in fractal_events:
            emitted.append(
                LiveStructureEvent(
                    fe.type,
                    event.timestamp_ms,
                    {"fractal_id": fe.fractal_id},
                )
            )

            if fe.type == "FRACTAL_CONFIRMED":
                self.latest_fractal = fe.fractal
                for be in self.bi.update(fe.fractal):
                    payload = {
                        "bi_id": be.bi_id,
                        "fractal_id": be.fractal_id,
                    }
                    if be.previous_fractal_id is not None:
                        payload["previous_fractal_id"] = be.previous_fractal_id
                    emitted.append(
                        LiveStructureEvent(be.type, event.timestamp_ms, payload)
                    )
                    if be.bi is not None:
                        self.latest_bi = be.bi

        self.events.extend(emitted)
        return emitted

    def snapshot(self) -> dict[str, Any]:
        return {
            "candles_processed": self.candles_processed,
            "latest_candle_timestamp_ms": (
                self.latest_candle.timestamp_ms
                if self.latest_candle is not None
                else None
            ),
            "latest_fractal_id": (
                self.latest_fractal.id if self.latest_fractal is not None else None
            ),
            "latest_bi_id": (
                self.latest_bi.id if self.latest_bi is not None else None
            ),
            "event_count": len(self.events),
        }
