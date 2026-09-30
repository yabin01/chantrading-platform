"""Live 1M runtime recording and recovery bridge.

The bridge records accepted candles and structural events while enforcing a
strict 1M input stream contract: duplicate candles are ignored, gaps and
out-of-order/conflicting candles enter RESYNC, and only a contiguous stream
is forwarded to the structural engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .deterministic_replay import (
    DeterministicReplay,
    LiveStructureEvent,
    RecordedCandle,
    events_hash,
)
from .event_store import SQLiteEventStore
from .live_chanlun import Live1MStructureEngine
from chantrading.adapters.hyperliquid.live_testnet import LiveCandle


ONE_MINUTE_MS = 60_000


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


@dataclass(frozen=True)
class CandleRecoveryDecision:
    action: str
    reason: str
    expected_timestamp_ms: int | None
    received_timestamp_ms: int
    sequence: int


class Live1MRecordedRuntime:
    """Run the live structural engine with deterministic recovery semantics."""

    def __init__(self, path: str):
        self.store = SQLiteEventStore(path)
        self.engine = Live1MStructureEngine()
        self._event_ordinal = 0
        self._last_candle: LiveCandle | None = None
        self._connection_generation = 0
        self._resync_required = False

    @property
    def resync_required(self) -> bool:
        return self._resync_required

    @property
    def connection_generation(self) -> int:
        return self._connection_generation

    def on_disconnect(self, reason: str = "transport_disconnect") -> None:
        self._resync_required = True
        self._append_lifecycle("WS_DISCONNECTED", {"reason": reason})

    def on_reconnect(self) -> None:
        self._connection_generation += 1
        self._append_lifecycle(
            "WS_RECONNECTED",
            {"connection_generation": self._connection_generation},
        )

    def _append_lifecycle(self, name: str, payload: dict[str, Any]) -> None:
        self._event_ordinal += 1
        event_id = f"lifecycle:{self._connection_generation}:{self._event_ordinal}:{name}"
        self.store.append(event_id, name, 0, payload)

    def _append_recovery(
        self,
        candle: LiveCandle,
        action: str,
        reason: str,
        expected_timestamp_ms: int | None,
    ) -> CandleRecoveryDecision:
        self._event_ordinal += 1
        payload = {
            "coin": candle.coin,
            "interval": candle.interval,
            "timestamp_ms": candle.timestamp_ms,
            "action": action,
            "reason": reason,
            "expected_timestamp_ms": expected_timestamp_ms,
            "connection_generation": self._connection_generation,
        }
        sequence = self.store.append(
            f"recovery:{candle.coin}:{candle.timestamp_ms}:{action}:{self._event_ordinal}",
            "CANDLE_RECOVERY",
            candle.timestamp_ms,
            payload,
        )
        return CandleRecoveryDecision(
            action,
            reason,
            expected_timestamp_ms,
            candle.timestamp_ms,
            int(sequence or 0),
        )

    def classify_candle(self, candle: LiveCandle) -> CandleRecoveryDecision:
        if candle.interval != "1m":
            raise ValueError("Live1MRecordedRuntime accepts only 1m candles")

        previous = self._last_candle
        if previous is None:
            return CandleRecoveryDecision(
                "ACCEPT", "initial_candle", None, candle.timestamp_ms, 0
            )

        if candle.coin != previous.coin:
            return self._append_recovery(
                candle, "RESYNC", "coin_changed", previous.timestamp_ms + ONE_MINUTE_MS
            )

        if candle.timestamp_ms == previous.timestamp_ms:
            if candle == previous:
                return self._append_recovery(
                    candle, "DROP_DUPLICATE", "identical_timestamp_payload", candle.timestamp_ms
                )
            return self._append_recovery(
                candle, "RESYNC", "conflicting_duplicate_timestamp", candle.timestamp_ms
            )

        expected = previous.timestamp_ms + ONE_MINUTE_MS
        if candle.timestamp_ms < previous.timestamp_ms:
            return self._append_recovery(
                candle, "RESYNC", "out_of_order_timestamp", expected
            )
        if candle.timestamp_ms != expected:
            return self._append_recovery(
                candle, "RESYNC", "timestamp_gap", expected
            )

        return CandleRecoveryDecision(
            "ACCEPT", "contiguous_1m", expected, candle.timestamp_ms, 0
        )

    def recover(self, candles: list[LiveCandle] | tuple[LiveCandle, ...]) -> tuple[LiveStructureEvent, ...]:
        """Apply a contiguous recovery batch after disconnect/gap detection.

        Recovery never reorders input. The batch must start immediately after
        the last accepted candle and every candle must advance exactly 1m.
        This makes recovery deterministic and preserves the same structural
        engine input stream that a healthy connection would have produced.
        """
        if not candles:
            raise ValueError("recovery batch must not be empty")
        if not self._resync_required:
            raise RuntimeError("recovery is not required")
        expected = (
            None
            if self._last_candle is None
            else self._last_candle.timestamp_ms + ONE_MINUTE_MS
        )
        all_events: list[LiveStructureEvent] = []
        for candle in candles:
            if expected is not None and candle.timestamp_ms != expected:
                raise ValueError(
                    f"recovery batch is not contiguous: expected {expected}, "
                    f"got {candle.timestamp_ms}"
                )
            events = self.on_candle(candle)
            all_events.extend(events)
            expected = candle.timestamp_ms + ONE_MINUTE_MS
        if self._resync_required:
            raise RuntimeError("recovery batch did not restore contiguous state")
        self._append_lifecycle(
            "WS_RESYNC_COMPLETE",
            {"last_candle_timestamp_ms": self._last_candle.timestamp_ms},
        )
        return tuple(all_events)

    def on_candle(self, candle: LiveCandle) -> tuple[LiveStructureEvent, ...]:
        decision = self.classify_candle(candle)
        if decision.action == "DROP_DUPLICATE":
            return ()
        if decision.action == "RESYNC":
            self._resync_required = True
            return ()

        self._resync_required = False
        self._last_candle = candle
        self._event_ordinal += 1
        candle_id = f"candle:{candle.coin}:{candle.timestamp_ms}"
        self.store.append(
            candle_id,
            "CANDLE_ACCEPTED",
            candle.timestamp_ms,
            {
                "coin": candle.coin,
                "interval": candle.interval,
                "timestamp_ms": candle.timestamp_ms,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "connection_generation": self._connection_generation,
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
                event_id,
                event.type,
                event.timestamp_ms,
                dict(event.payload),
            )
        return emitted

    def verification(self) -> LiveRecordingVerification:
        candles: list[RecordedCandle] = []
        recorded_events: list[LiveStructureEvent] = []
        for row in self.store.iter_events():
            if row.name == "CANDLE_ACCEPTED":
                p = row.payload
                candles.append(
                    RecordedCandle(
                        row.sequence,
                        p["coin"],
                        p["interval"],
                        int(p["timestamp_ms"]),
                        str(p["open"]),
                        str(p["high"]),
                        str(p["low"]),
                        str(p["close"]),
                        str(p["volume"]),
                    )
                )
            elif row.name not in {"CANDLE_RECOVERY", "WS_DISCONNECTED", "WS_RECONNECTED"}:
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
