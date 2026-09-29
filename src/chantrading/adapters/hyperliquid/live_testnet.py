"""Live Hyperliquid Testnet market-data canary transport.

This module is intentionally read-only: it connects to Testnet market data,
normalizes completed 1m candles, and emits them to the runtime callback.
Execution/signing is not enabled here.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Any

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


def normalize_candle_message(message: str | bytes) -> LiveCandle:
    payload = json.loads(message)
    data = payload.get("data", {})
    if data.get("channel") != "candle":
        raise ValueError("unexpected websocket channel")
    candle = data.get("data")
    if not candle:
        raise ValueError("missing candle data")
    if candle.get("i") != "1m":
        raise ValueError("live canary accepts only 1m candles")
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


def candle_subscription(coin: str) -> str:
    return json.dumps({
        "method": "subscribe",
        "subscription": {"type": "candle", "coin": coin, "interval": "1m"},
    }, separators=(",", ":"))


class LiveTestnetCandleStream:
    def __init__(self, ws_factory: Callable[..., Any], on_candle: Callable[[LiveCandle], None]):
        self.ws_factory = ws_factory
        self.on_candle = on_candle
        self.running = False
        self.received = 0
        self.last_candle_ts: int | None = None

    def run(self, coin: str = "ETH", duration_seconds: int = 600) -> int:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        ws = self.ws_factory(TESTNET_WS_URL)
        ws.send(candle_subscription(coin))
        self.running = True
        deadline = time.time() + duration_seconds
        try:
            while self.running and time.time() < deadline:
                raw = ws.recv()
                event = normalize_candle_message(raw)
                if self.last_candle_ts is not None and event.timestamp_ms < self.last_candle_ts:
                    raise RuntimeError("out-of-order candle")
                if event.timestamp_ms != self.last_candle_ts:
                    self.last_candle_ts = event.timestamp_ms
                    self.received += 1
                    self.on_candle(event)
        finally:
            self.running = False
            close = getattr(ws, "close", None)
            if close:
                close()
        return self.received

    def stop(self):
        self.running = False
