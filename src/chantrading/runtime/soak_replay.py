"""SQLite-backed Live 1M recording and deterministic verification."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .deterministic_replay import DeterministicReplay, RecordedCandle, ReplayResult
from .event_store import SQLiteEventStore

@dataclass(frozen=True)
class SoakVerification:
    recorded_events: int
    replay: ReplayResult
    accepted_candles: int

class SQLiteCandleRecorder:
    """Persists canonical 1M candles as append-only runtime events."""
    def __init__(self, path: str):
        self.store = SQLiteEventStore(path)
        self._next = self.store.count() + 1

    def append(self, candle: Any) -> int | None:
        if candle.interval != "1m":
            raise ValueError("SQLiteCandleRecorder accepts only 1m candles")
        payload = {
            "coin": candle.coin, "interval": candle.interval,
            "timestamp_ms": candle.timestamp_ms, "open": candle.open,
            "high": candle.high, "low": candle.low, "close": candle.close,
            "volume": candle.volume,
        }
        return self.store.append(
            f"candle:{candle.coin}:{candle.timestamp_ms}",
            "CANDLE_ACCEPTED",
            candle.timestamp_ms,
            payload,
        )

    def recorded_candles(self) -> tuple[RecordedCandle, ...]:
        rows = []
        for event in self.store.iter_events():
            if event.name != "CANDLE_ACCEPTED":
                continue
            p = event.payload
            rows.append(RecordedCandle(
                sequence=event.sequence, coin=p["coin"], interval=p["interval"],
                timestamp_ms=int(p["timestamp_ms"]), open=str(p["open"]),
                high=str(p["high"]), low=str(p["low"]), close=str(p["close"]),
                volume=str(p["volume"]),
            ))
        return tuple(rows)

    def verify_replay(self) -> SoakVerification:
        candles = self.recorded_candles()
        result = DeterministicReplay().replay(candles)
        return SoakVerification(self.store.count(), result, len(candles))

    def close(self) -> None:
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
