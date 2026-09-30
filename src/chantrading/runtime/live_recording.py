"""Live 1M runtime recording bridge.

The bridge records the accepted candle and every structural event emitted by
Live1MStructureEngine. It is read-only with respect to trading/execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from .deterministic_replay import DeterministicReplay, LiveStructureEvent, events_hash
from .event_store import SQLiteEventStore
from .live_chanlun import Live1MStructureEngine
from chantrading.adapters.hyperliquid.live_testnet import LiveCandle

@dataclass(frozen=True)
class LiveRecordingVerification:
    candle_count: int
    live_event_hash: str
    replay_event_hash: str
    live_snapshot: dict[str, Any]
    replay_snapshot: dict[str, Any]

    @property
    def matched(self) -> bool:
        return (
            self.live_event_hash == self.replay_event_hash
            and self.live_snapshot == self.replay_snapshot
        )

class Live1MRecordedRuntime:
    """Run the live structural engine while durably recording its evidence."""

    def __init__(self, path: str):
        self.store = SQLiteEventStore(path)
        self.engine = Live1MStructureEngine()
        self._event_ordinal = 0

    def on_candle(self, candle: LiveCandle) -> tuple[LiveStructureEvent, ...]:
        self._event_ordinal += 1
        candle_id = f"candle:{candle.coin}:{candle.timestamp_ms}"
        self.store.append(
            candle_id, "CANDLE_ACCEPTED", candle.timestamp_ms,
            {
                "coin": candle.coin, "interval": candle.interval,
                "timestamp_ms": candle.timestamp_ms, "open": candle.open,
                "high": candle.high, "low": candle.low,
                "close": candle.close, "volume": candle.volume,
            },
        )

        emitted = tuple(self.engine.on_candle(candle))
        for event in emitted:
            self._event_ordinal += 1
            event_id = (
                f"structure:{candle.coin}:{event.timestamp_ms}:"
                f"{self._event_ordinal}:{event.type}"
            )
            self.store.append(
                event_id, event.type, event.timestamp_ms,
                dict(event.payload),
            )
        return emitted

    def verification(self) -> LiveRecordingVerification:
        candles = []
        recorded_events = []
        for row in self.store.iter_events():
            if row.name == "CANDLE_ACCEPTED":
                p = row.payload
                from .deterministic_replay import RecordedCandle
                candles.append(RecordedCandle(
                    row.sequence, p["coin"], p["interval"],
                    int(p["timestamp_ms"]), str(p["open"]), str(p["high"]),
                    str(p["low"]), str(p["close"]), str(p["volume"]),
                ))
            elif row.name != "CANDLE_ACCEPTED":
                recorded_events.append(
                    LiveStructureEvent(row.name, row.timestamp_ms, row.payload)
                )

        replay = DeterministicReplay().replay(candles)
        return LiveRecordingVerification(
            len(candles),
            events_hash(recorded_events),
            replay.state_hash,
            self.engine.snapshot(),
            replay.snapshot,
        )

    def close(self) -> None:
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
