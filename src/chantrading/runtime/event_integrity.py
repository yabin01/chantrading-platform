"""Canonical 1M event integrity classification.

This module is deliberately independent from ChanLun structure interpretation.
It answers only whether an observed candle is safe to enter the canonical
ordered 1M stream.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ONE_MINUTE_MS = 60_000

IntegrityAction = Literal["ACCEPT", "DROP_DUPLICATE", "RESYNC"]


@dataclass(frozen=True)
class EventIntegrityDecision:
    action: IntegrityAction
    reason: str
    expected_timestamp_ms: int | None
    received_timestamp_ms: int
    previous_timestamp_ms: int | None


@dataclass(frozen=True)
class CanonicalCandleIdentity:
    """Minimal identity used for duplicate/conflict detection."""

    coin: str
    interval: str
    timestamp_ms: int
    open: object
    high: object
    low: object
    close: object
    volume: object


def classify_1m_candle(
    candle: CanonicalCandleIdentity,
    previous: CanonicalCandleIdentity | None,
) -> EventIntegrityDecision:
    """Classify one observed 1M candle without mutating runtime state.

    Rules:
    - first candle is accepted;
    - a different symbol is a resync boundary;
    - same timestamp + identical payload is an idempotent duplicate;
    - same timestamp + different payload is a conflicting duplicate;
    - an older timestamp is out-of-order;
    - any timestamp other than exactly +60s is a gap;
    - only the exact next 1M timestamp is accepted.
    """
    if candle.interval != "1m":
        raise ValueError("canonical integrity classifier accepts only 1m candles")

    if previous is None:
        return EventIntegrityDecision(
            "ACCEPT",
            "initial_candle",
            None,
            candle.timestamp_ms,
            None,
        )

    expected = previous.timestamp_ms + ONE_MINUTE_MS

    if candle.coin != previous.coin:
        return EventIntegrityDecision(
            "RESYNC",
            "coin_changed",
            expected,
            candle.timestamp_ms,
            previous.timestamp_ms,
        )

    if candle.timestamp_ms == previous.timestamp_ms:
        if candle == previous:
            return EventIntegrityDecision(
                "DROP_DUPLICATE",
                "identical_timestamp_payload",
                candle.timestamp_ms,
                candle.timestamp_ms,
                previous.timestamp_ms,
            )
        return EventIntegrityDecision(
            "RESYNC",
            "conflicting_duplicate_timestamp",
            candle.timestamp_ms,
            candle.timestamp_ms,
            previous.timestamp_ms,
        )

    if candle.timestamp_ms < previous.timestamp_ms:
        return EventIntegrityDecision(
            "RESYNC",
            "out_of_order_timestamp",
            expected,
            candle.timestamp_ms,
            previous.timestamp_ms,
        )

    if candle.timestamp_ms != expected:
        return EventIntegrityDecision(
            "RESYNC",
            "timestamp_gap",
            expected,
            candle.timestamp_ms,
            previous.timestamp_ms,
        )

    return EventIntegrityDecision(
        "ACCEPT",
        "contiguous_1m",
        expected,
        candle.timestamp_ms,
        previous.timestamp_ms,
    )
