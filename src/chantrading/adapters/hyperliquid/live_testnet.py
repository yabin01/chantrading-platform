"""Live Hyperliquid Testnet market-data canary transport.

Read-only transport for the first real Testnet canary. Hyperliquid puts
channel at the websocket message top level; subscription acknowledgements
and other non-candle messages are ignored by the stream.

The websocket-client package is optional at import time so the rest of the
runtime/test suite can be imported without a live websocket dependency.
A real websocket factory is still required when running the canary.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

try:
    from websocket import WebSocketConnectionClosedException, WebSocketException, WebSocketTimeoutException
except ImportError:  # pragma: no cover - exercised only without websocket-client
    class WebSocketException(Exception):
        """Fallback used only when websocket-client is not installed."""

    class WebSocketConnectionClosedException(WebSocketException):
        """Fallback used only when websocket-client is not installed."""

    class WebSocketTimeoutException(TimeoutError):
        """Fallback used only when websocket-client is not installed."""


TESTNET_WS_URL = "wss://api.hyperliquid-testnet.xyz/ws"


@dataclass(frozen=True)
class LiveCandle:
    coin: str
    interval: str
    timestamp_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str


def parse_candle_message(message: str | bytes) -> LiveCandle | None:
    payload = json.loads(message)
    if payload.get("channel") != "candle":
        return None

    candle = payload.get("data")
    if not isinstance(candle, dict):
        raise ValueError("candle message missing data object")
    if candle.get("i") != "1m":
        raise ValueError("live canary accepts only 1m candles")

    required = ("s", "i", "t", "o", "h", "l", "c", "v")
    missing = [key for key in required if key not in candle]
    if missing:
        raise ValueError(f"candle message missing fields: {missing}")

    return LiveCandle(
        coin=str(candle["s"]),
        interval=str(candle["i"]),
        timestamp_ms=int(candle["t"]),
        open=str(candle["o"]),
        high=str(candle["h"]),
        low=str(candle["l"]),
        close=str(candle["c"]),
        volume=str(candle["v"]),
    )


def normalize_candle_message(message: str | bytes) -> LiveCandle:
    event = parse_candle_message(message)
    if event is None:
        raise ValueError("message is not a candle event")
    return event


def candle_subscription(coin: str) -> str:
    return json.dumps(
        {
            "method": "subscribe",
            "subscription": {
                "type": "candle",
                "coin": coin,
                "interval": "1m",
            },
        },
        separators=(",", ":"),
    )


class LiveTestnetCandleStream:
    def __init__(
        self,
        ws_factory: Callable[..., Any],
        on_candle: Callable[[LiveCandle], None],
        max_reconnects: int = 20,
        reconnect_delay_seconds: float = 1.0,
    ):
        if max_reconnects < 0:
            raise ValueError("max_reconnects must be non-negative")
        if reconnect_delay_seconds < 0:
            raise ValueError("reconnect_delay_seconds must be non-negative")
        self.ws_factory = ws_factory
        self.on_candle = on_candle
        self.running = False
        self.received = 0
        self.last_candle_ts: int | None = None
        self.max_reconnects = max_reconnects
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.reconnects = 0
        self.expected_candle_step_ms = 60_000
        self.gap_count = 0
        self.last_gap_ms = None
        self.last_health_at = None

    def run(self, coin: str = "ETH", duration_seconds: int = 600) -> int:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        self.running = True
        deadline = time.time() + duration_seconds
        ws = None

        try:
            while self.running and time.time() < deadline:
                if ws is None:
                    ws = self.ws_factory(TESTNET_WS_URL)
                    ws.send(candle_subscription(coin))

                try:
                    raw = ws.recv()
                except WebSocketTimeoutException:
                    continue
                except (WebSocketConnectionClosedException, WebSocketException, OSError):
                    close = getattr(ws, "close", None)
                    if close:
                        close()
                    ws = None
                    if self.reconnects >= self.max_reconnects:
                        raise
                    self.reconnects += 1
                    if self.reconnect_delay_seconds:
                        time.sleep(self.reconnect_delay_seconds)
                    continue

                event = parse_candle_message(raw)
                if event is None:
                    continue

                if self.last_candle_ts is not None and event.timestamp_ms < self.last_candle_ts:
                    raise RuntimeError("out-of-order candle")

                if event.timestamp_ms != self.last_candle_ts:
                    if self.last_candle_ts is not None:
                        gap_ms = event.timestamp_ms - self.last_candle_ts
                        if gap_ms > self.expected_candle_step_ms:
                            self.gap_count += 1
                            self.last_gap_ms = gap_ms
                    self.last_candle_ts = event.timestamp_ms
                    self.received += 1
                    self.on_candle(event)
        finally:
            self.running = False
            close = getattr(ws, "close", None) if ws is not None else None
            if close:
                close()

        return self.received

    def health_snapshot(self) -> dict[str, Any]:
        self.last_health_at = time.time()
        return {
            "running": self.running,
            "received": self.received,
            "last_candle_ts": self.last_candle_ts,
            "reconnects": self.reconnects,
            "gap_count": self.gap_count,
            "last_gap_ms": self.last_gap_ms,
        }

    def stop(self):
        self.running = False
