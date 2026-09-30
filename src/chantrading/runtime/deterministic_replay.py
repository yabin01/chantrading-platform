"""Deterministic recording and replay primitives for the Live 1M canary."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable
from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from .live_chanlun import Live1MStructureEngine, LiveStructureEvent

@dataclass(frozen=True)
class RecordedCandle:
    sequence: int
    coin: str
    interval: str
    timestamp_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str

    def to_live(self) -> LiveCandle:
        return LiveCandle(coin=self.coin, interval=self.interval, timestamp_ms=self.timestamp_ms,
            open=self.open, high=self.high, low=self.low, close=self.close, volume=self.volume)

@dataclass(frozen=True)
class ReplayResult:
    events: tuple[LiveStructureEvent, ...]
    snapshot: dict[str, Any]
    state_hash: str

def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def events_hash(events: Iterable[LiveStructureEvent]) -> str:
    rows = [{"type": e.type, "timestamp_ms": e.timestamp_ms, "payload": e.payload} for e in events]
    return hashlib.sha256(_canonical(rows)).hexdigest()

class DeterministicRecorder:
    """In-memory canonical recorder; persistence is intentionally separate."""
    def __init__(self) -> None:
        self._candles: list[RecordedCandle] = []

    def record(self, candle: LiveCandle) -> RecordedCandle:
        if self._candles and candle.timestamp_ms <= self._candles[-1].timestamp_ms:
            raise ValueError("recorded candles must have strictly increasing timestamps")
        item = RecordedCandle(len(self._candles) + 1, candle.coin, candle.interval, candle.timestamp_ms,
            candle.open, candle.high, candle.low, candle.close, candle.volume)
        self._candles.append(item)
        return item

    def candles(self) -> tuple[RecordedCandle, ...]:
        return tuple(self._candles)

class DeterministicReplay:
    def replay(self, candles: Iterable[RecordedCandle]) -> ReplayResult:
        engine = Live1MStructureEngine()
        emitted: list[LiveStructureEvent] = []
        for item in candles:
            emitted.extend(engine.on_candle(item.to_live()))
        return ReplayResult(tuple(emitted), engine.snapshot(), events_hash(emitted))

    def replay_live(self, candles: Iterable[LiveCandle]) -> ReplayResult:
        recorder = DeterministicRecorder()
        for candle in candles:
            recorder.record(candle)
        return self.replay(recorder.candles())
