"""Canonical market-event bridge for Hyperliquid 1m candles."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class CanonicalMarketEvent:
    event_id: str
    source: str
    symbol: str
    interval: str
    timestamp: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    schema_version: str = "1.0"


def canonical_event_id(source: str, symbol: str, interval: str, timestamp: int) -> str:
    raw=f"{source}|{symbol}|{interval}|{timestamp}".encode()
    return sha256(raw).hexdigest()


def to_canonical_event(candle) -> CanonicalMarketEvent:
    if candle.interval != "1m":
        raise ValueError("only 1m candles are supported")
    source="hyperliquid.testnet"
    return CanonicalMarketEvent(
        event_id=canonical_event_id(source,candle.coin,candle.interval,candle.timestamp),
        source=source,
        symbol=candle.coin,
        interval=candle.interval,
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


class MarketEventGuard:
    def __init__(self, interval_ms: int = 60_000):
        self.interval_ms=interval_ms
        self.last_timestamp: dict[str,int]={}
        self.seen_ids:set[str]=set()

    def accept(self, event: CanonicalMarketEvent) -> str:
        if event.event_id in self.seen_ids:
            return "DUPLICATE"
        previous=self.last_timestamp.get(event.symbol)
        if previous is not None and event.timestamp < previous:
            return "OUT_OF_ORDER"
        if previous is not None and event.timestamp > previous + self.interval_ms:
            self.seen_ids.add(event.event_id)
            self.last_timestamp[event.symbol]=event.timestamp
            return "GAP"
        self.seen_ids.add(event.event_id)
        self.last_timestamp[event.symbol]=event.timestamp
        return "ACCEPTED"
